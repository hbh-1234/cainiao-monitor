# -*- coding: utf-8 -*-
"""快递100 聚合查询数据源（账号模式不可用时的降级方案 / 详情补充）
接口：https://www.kuaidi100.com/query  （公开网页版接口，个人使用）
"""
from __future__ import annotations

import hashlib
import json
import random

from ..constants import KUADI100_POLL, KUADI100_QUERY
from ..models import Package, TraceNode, sort_trace_desc
from .http_client import ApiError, NetworkError, request


class Kuaidi100Error(ApiError):
    pass


def query(session, postid: str, com: str, phone: str = "") -> tuple[list[TraceNode], str]:
    """查询单个运单的物流轨迹。
    返回 (节点列表[新→旧], 状态码 state: 0在途 1揽收 2疑难 3签收 4退签 5派件 6退回 7转投)
    可能抛出 NetworkError / Kuaidi100Error
    """
    if not com:
        raise Kuaidi100Error("未知快递公司，请先在「添加包裹」中选择快递公司")
    params = {
        "type": com,
        "postid": postid,
        "temp": "%.3f" % random.random(),
        "phone": (phone or "")[-4:],
    }
    resp = request(session, "GET", KUADI100_QUERY, params=params,
                   headers={"Referer": "https://www.kuaidi100.com/"})
    try:
        j = resp.json()
    except Exception as e:
        raise Kuaidi100Error("快递100返回了无法解析的数据（可能被风控，请稍后再试）") from e

    status = str(j.get("status", ""))
    if status != "200":
        msg = str(j.get("message") or "查询失败") or ""
        if "验证" in msg or "频率" in msg:
            raise Kuaidi100Error("快递100接口触发频率限制，请稍后重试")
        raise Kuaidi100Error(f"查询失败：{msg}（请检查运单号是否正确）")

    data = j.get("data") or []
    nodes: list[TraceNode] = []
    for d in data:
        ctx = str(d.get("context") or "").strip()
        t = str(d.get("time") or "").strip()
        if not ctx:
            continue
        nodes.append(TraceNode(time=t, status=ctx, location=str(d.get("location") or "")))
    if not nodes:
        raise Kuaidi100Error("该运单暂无物流轨迹数据")
    nodes = sort_trace_desc(nodes)
    if nodes:
        nodes[0].kind = "end"
        nodes[-1].kind = "start"
    return nodes, str(j.get("state", "0"))


def query_package(session, mail_no: str, com: str, phone: str = "") -> Package:
    """查询并组装成 Package 对象（用于手动添加的包裹）"""
    nodes, state = query(session, mail_no, com, phone)
    head = nodes[0] if nodes else None
    return Package(
        mail_no=mail_no,
        company_code=_company_code_of_com(com),
        company_name=_company_name_of_com(com),
        latest_status=head.status if head else "",
        latest_time=head.time if head else "",
        state=_state_label(state),
        source="kuaidi100",
        trace=nodes,
    )


def query_official(session, customer: str, key: str, postid: str, com: str,
                    phone: str = "") -> tuple[list[TraceNode], str]:
    """快递100 企业版轮询查询接口（需用户提供 customer + key）
    签名：sign = MD5(param + key + customer).upper()
    """
    if not customer or not key:
        raise Kuaidi100Error("请先在登录页填写快递100 的 customer 与 key")
    param = json.dumps({"com": com, "num": postid, "phone": (phone or "")[-4:]},
                       ensure_ascii=False)
    sign = hashlib.md5((param + key + customer).encode("utf-8")).hexdigest().upper()
    resp = request(session, "POST", KUADI100_POLL,
                   data={"customer": customer, "sign": sign, "param": param},
                   headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
    try:
        j = resp.json()
    except Exception as e:
        raise Kuaidi100Error("快递100返回了无法解析的数据（可能被风控，请稍后再试）") from e
    status = str(j.get("status", ""))
    if status != "200":
        raise Kuaidi100Error("快递100查询失败：" + str(j.get("message") or status))
    data = j.get("data") or []
    nodes = []
    for d in data:
        ctx = str(d.get("context") or "").strip()
        t = str(d.get("time") or "").strip()
        if not ctx:
            continue
        nodes.append(TraceNode(time=t, status=ctx, location=str(d.get("location") or "")))
    if not nodes:
        raise Kuaidi100Error("该运单暂无物流轨迹数据")
    nodes = sort_trace_desc(nodes)
    if nodes:
        nodes[0].kind = "end"
        nodes[-1].kind = "start"
    return nodes, str(j.get("state", "0"))


def _state_label(state: str) -> str:
    return {
        "3": "signed", "4": "problem", "5": "delivering",
        "6": "problem", "2": "problem",
    }.get(state, "transporting")


def _company_code_of_com(com: str) -> str:
    from ..constants import COMPANIES
    for _code, _name, _short, _color, c100 in COMPANIES:
        if c100 == com:
            return _code
    return "OTHER"


def _company_name_of_com(com: str) -> str:
    from ..constants import COMPANIES
    for _code, _name, _short, _color, c100 in COMPANIES:
        if c100 == com:
            return _name
    return "其他快递"
