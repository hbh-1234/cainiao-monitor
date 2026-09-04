# -*- coding: utf-8 -*-
"""淘宝物流助手（wuliu.taobao.com）数据源
- 列表页：https://wuliu.taobao.com/user/query_package_list.htm （未登录时返回登录页）
- 详情页：https://wuliu.taobao.com/trace/query_package_detail.htm?mailNo=xxx
说明：淘宝网页版页面结构可能随官方改版而变化，这里采用“多策略容错解析”，
解析不到时会把原始 HTML 存到数据目录，方便排查。
"""
from __future__ import annotations

import html as html_mod
import json
import os
import re

from ..config import app_data_dir
from ..constants import (COMPANY_NAME_MAP, WULIU_DETAIL, WULIU_LIST,
                         company_info)
from ..logger import get_logger
from ..models import TRACKING_RE, TIME_RE, Package, TraceNode, sort_trace_desc
from .http_client import ApiError, LoginRequired, NetworkError, request

log = get_logger()

# ---------- 正则 ----------
# 详情链接（含 mailNo 参数）
MAILNO_LINK_RE = re.compile(
    r'<a[^>]+href=["\'][^"\']*?(?:mailNo|mail_no|mailno)=([^"\'&]+)[^"\']*["\'][^>]*>(.*?)</a>',
    re.I | re.S)
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
TD_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
LI_BLOCK_RE = re.compile(r"<(?:li|div|tr)[^>]*>(.*?)</(?:li|div|tr)>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.I | re.S)
STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.I | re.S)
JSON_MAILNO_RE = re.compile(r'"mailNo"\s*:\s*"([^"]+)"')


def _strip_tags(s: str) -> str:
    s = SCRIPT_RE.sub(" ", s)
    s = STYLE_RE.sub(" ", s)
    s = TAG_RE.sub(" ", s)
    s = html_mod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _dump_html(html_text: str, tag: str) -> str:
    """把原始 HTML 保存到数据目录，返回路径"""
    try:
        d = os.path.join(app_data_dir(), "debug")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"wuliu_{tag}.html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(html_text)
        return p
    except Exception:
        return ""


# ---------------------------------------------------------------
# 登录态判断
# ---------------------------------------------------------------
def _looks_logged_in(html_text: str) -> bool:
    """通过页面标记判断是否已登录（启发式）"""
    low = html_text.lower()
    login_markers = ["loginlegacy", "havanaone", "member/login", "qrlogin",
                     "view-login", "id=\"login\"", "passport.taobao"]
    has_login = any(m in low for m in login_markers)
    has_data = any(k in low for k in
                   ["mailno", "运单号", "包裹", "package", "trace",
                    "物流公司", "快件", "快递"])
    return has_data and not (has_login and not has_data)


def check_login(session, base_url: str = WULIU_LIST) -> bool:
    """检测 Cookie 是否仍然有效（能拿到包裹列表页）"""
    resp = request(session, "GET", base_url,
                   headers={"Referer": "https://wuliu.taobao.com/"})
    text = resp.text
    if _looks_logged_in(text):
        return True
    if not _looks_logged_in(text):
        return False
    return False


# ---------------------------------------------------------------
# 列表解析
# ---------------------------------------------------------------
def _cells_of_row(row: str) -> list[str]:
    return [_strip_tags(c) for c in TD_RE.findall(row)]


def _row_containing(html_text: str, pos: int) -> str:
    """取包含 pos 位置的外层 <tr>…</tr>"""
    start = html_text.rfind("<tr", 0, pos)
    end = html_text.find("</tr>", pos)
    if start < 0 or end < 0:
        return ""
    return html_text[start:end + 5]


def _guess_company(text: str) -> str:
    """从文本猜测公司 cpCode，猜不到返回 OTHER"""
    for name, code in COMPANY_NAME_MAP.items():
        if name and name in text:
            return code
    return "OTHER"


def parse_list_html(html_text: str) -> tuple[list[Package], bool, list[str]]:
    """解析包裹列表页 HTML。
    返回 (包裹列表, 是否已登录, 调试信息列表)
    可能抛出 LoginRequired / ApiError
    """
    if not _looks_logged_in(html_text):
        raise LoginRequired("登录态已失效，请重新登录")
    if "验证" in html_text and ("滑块" in html_text or "安全验证" in html_text):
        raise ApiError("页面触发安全验证，请稍后重试，或重新登录一次")

    pkgs: list[Package] = []
    debug: list[str] = []
    seen: set[str] = set()

    # ---- 策略1：带 mailNo 参数的链接（最常见的老版表格结构）----
    for m in MAILNO_LINK_RE.finditer(html_text):
        mail_no = html_mod.unescape(m.group(1)).strip()
        anchor_text = _strip_tags(m.group(2))
        if not mail_no or mail_no in seen:
            continue
        row = _row_containing(html_text, m.start())
        cells = _cells_of_row(row)
        if not cells:
            cells = [anchor_text]
        p = _package_from_cells(mail_no, cells, source="wuliu")
        if p:
            pkgs.append(p)
            seen.add(mail_no)
    if pkgs:
        debug.append("strategy: mailNo links, count=%d" % len(pkgs))
        return pkgs, True, debug

    # ---- 策略2：页面内嵌 JSON（SPA 场景）----
    for m in JSON_MAILNO_RE.finditer(html_text):
        mail_no = m.group(1).strip()
        if not mail_no or mail_no in seen:
            continue
        # 在 mailNo 前后找 company/status 字段
        ctx = html_text[max(0, m.start() - 600):m.end() + 600]
        comp_m = re.search(r'"(?:cpCode|companyCode|company)"\s*:\s*"([^"]+)"', ctx)
        stat_m = re.search(r'"(?:latestStatus|status|desc)"\s*:\s*"([^"]+)"', ctx)
        time_m = re.search(r'"(?:latestTime|time)"\s*:\s*"([^"]+)"', ctx)
        code = comp_m.group(1) if comp_m else "OTHER"
        info = company_info(code)
        p = Package(mail_no=mail_no, company_code=info[0], company_name=info[1],
                    latest_status=stat_m.group(1) if stat_m else "",
                    latest_time=time_m.group(1) if time_m else "",
                    source="wuliu")
        pkgs.append(p)
        seen.add(mail_no)
    if pkgs:
        debug.append("strategy: embedded JSON, count=%d" % len(pkgs))
        return pkgs, True, debug

    # ---- 策略3：普通表格行（按列内容启发式识别）----
    for row in TR_RE.findall(html_text):
        cells = _cells_of_row(row)
        if len(cells) < 2:
            continue
        mail_no = ""
        company_code = "OTHER"
        status = ""
        ttime = ""
        for c in cells:
            m2 = TRACKING_RE.search(c)
            if m2 and not mail_no:
                mail_no = m2.group(1)
                continue
            tm = TIME_RE.search(c)
            if tm and not ttime:
                ttime = tm.group(0).strip()
                continue
            if _guess_company(c) != "OTHER" and company_code == "OTHER":
                company_code = _guess_company(c)
                continue
            if c and not status:
                status = c
        if mail_no and mail_no not in seen:
            info = company_info(company_code)
            p = Package(mail_no=mail_no, company_code=info[0], company_name=info[1],
                        latest_status=status, latest_time=ttime, source="wuliu")
            pkgs.append(p)
            seen.add(mail_no)
    if pkgs:
        debug.append("strategy: table rows, count=%d" % len(pkgs))
        return pkgs, True, debug

    # ---- 全部失败：保存原始页面供排查 ----
    path = _dump_html(html_text, "list_parse_fail")
    debug.append("all strategies failed, dumped html: " + path)
    raise ApiError("暂未能从页面中解析出包裹数据（页面结构可能已改版）。"
                   "原始页面已保存：%s" % path)


def _package_from_cells(mail_no: str, cells: list[str], source: str) -> Package | None:
    """根据一行单元格文本构造 Package（启发式）"""
    company_code = "OTHER"
    status = ""
    ttime = ""
    for c in cells:
        c = c.strip()
        if not c or c == mail_no:
            continue
        tm = TIME_RE.search(c)
        if tm:
            if not ttime:
                ttime = tm.group(0).strip()
            continue
        gc = _guess_company(c)
        if gc != "OTHER" and company_code == "OTHER":
            company_code = gc
            continue
        if not status and len(c) < 80:
            status = c
    info = company_info(company_code)
    return Package(mail_no=mail_no, company_code=info[0], company_name=info[1],
                   latest_status=status or "运输中", latest_time=ttime,
                   source=source)


# ---------------------------------------------------------------
# 详情（时间线）解析
# ---------------------------------------------------------------
def parse_detail_html(html_text: str) -> list[TraceNode]:
    """解析详情页时间线。返回按时间倒序的节点列表。"""
    if not _looks_logged_in(html_text):
        raise LoginRequired("登录态已失效，请重新登录")
    nodes: list[TraceNode] = []

    # 策略1：li/div/tr 块内带时间文本的条目
    for blk in LI_BLOCK_RE.findall(html_text):
        text = _strip_tags(blk)
        if not text or len(text) > 300:
            continue
        tm = TIME_RE.search(text)
        if not tm:
            continue
        time_str = tm.group(0).strip()
        status = text.replace(time_str, "", 1).strip()
        if not status:
            continue
        nodes.append(TraceNode(time=time_str, status=status,
                               location=extract_location(status)))

    if not nodes:
        # 策略2：纯文本逐行（时间 + 描述在同一行）
        for line in html_text.splitlines():
            text = _strip_tags(line)
            tm = TIME_RE.search(text)
            if tm and len(text) < 300:
                time_str = tm.group(0).strip()
                status = text.replace(time_str, "", 1).strip()
                if status:
                    nodes.append(TraceNode(time=time_str, status=status,
                                           location=extract_location(status)))
    if not nodes:
        _dump_html(html_text, "detail_parse_fail")
        raise ApiError("未能解析出物流时间线（页面结构可能已改版）")
    # 标记首尾
    nodes = sort_trace_desc(nodes)
    if nodes:
        nodes[0].kind = "end"
        nodes[-1].kind = "start"
    return nodes


# ---------------------------------------------------------------
# 对外抓取函数
# ---------------------------------------------------------------
def fetch_packages(session, page: int = 1) -> list[Package]:
    """抓取账号下包裹列表（淘宝物流助手）"""
    resp = request(session, "GET", WULIU_LIST,
                   params={"page": page} if page > 1 else None,
                   headers={"Referer": "https://wuliu.taobao.com/"})
    pkgs, ok, debug = parse_list_html(resp.text)
    for d in debug:
        log.info("wuliu list: %s", d)
    return pkgs


def fetch_detail(session, mail_no: str, cp_code: str = "") -> list[TraceNode]:
    """抓取单个包裹的完整时间线"""
    resp = request(session, "GET", WULIU_DETAIL,
                   params={"mailNo": mail_no, "cpCode": cp_code},
                   headers={"Referer": WULIU_LIST})
    return parse_detail_html(resp.text)


# ---------------------------------------------------------------
# 地点提取（供地图使用）
# ---------------------------------------------------------------
def extract_location(status: str) -> str:
    """从物流描述中尽量提取地点文本：
    优先取【】内容，其次取“到/达/在 … 派送/签收”等模式，最后取“省市”关键字"""
    if not status:
        return ""
    m = re.search(r"[【\[]([^】\]]{1,30})[】\]]", status)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:在|到达|已到达|抵达|离开|运输至|发往|到达)\s*([\u4e00-\u9fa5]{2,30}?(?:市|县|区|镇|街道|中心|分拨|转运)[\u4e00-\u9fa5]{0,10})", status)
    if m:
        return m.group(1).strip()
    m = re.search(r"([\u4e00-\u9fa5]{2,10}?(?:省|市|自治区))", status)
    if m:
        return m.group(1).strip()
    return ""
