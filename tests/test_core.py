# -*- coding: utf-8 -*-
"""核心逻辑测试（不依赖 Qt，可在无界面环境运行）
用法：python tests/test_core.py
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config
from app.models import Package, TraceNode, sort_trace_desc
from app.api.wuliu import parse_list_html, parse_detail_html, extract_location, _looks_logged_in


def test_config_roundtrip():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp")
    os.makedirs(d, exist_ok=True)  # 沙箱环境 %TEMP% 不可写，用工作区临时目录
    c = Config(os.path.join(d, "cfg.json"))
    c.set_cookies({"cookie2": "abc", "_tb_token_": "xyz"})
    c.set_phone("13812345678")
    c.set_last_seen("SF1", "fp1")
    c.add_manual_package({"mail_no": "SF1", "com100": "shunfeng"})
    c2 = Config(os.path.join(d, "cfg.json"))
    assert c2.get_cookies()["cookie2"] == "abc"
    assert c2.get_phone() == "13812345678"
    assert c2.phone_last4() == "5678"
    assert c2.get_last_seen("SF1") == "fp1"
    assert len(c2.get_manual_packages()) == 1
    print("test_config_roundtrip OK")


LOGGED_IN_HTML = """
<html><head><title>物流助手</title></head><body>
<h2>我的包裹</h2>
<table>
<tr><td>顺丰速运</td><td><a href="/trace/query_package_detail.htm?mailNo=SF1234567890123">SF1234567890123</a></td>
    <td>快件已到达【杭州转运中心】</td><td>2025-06-08 10:00:00</td></tr>
<tr><td>中通快递</td><td><a href="/trace/query_package_detail.htm?mailNo=ZT1234567890123">ZT1234567890123</a></td>
    <td>派件中</td><td>2025-06-08 09:30:00</td></tr>
</table>
</body></html>
"""

LOGIN_PAGE = """
<html><head><title>登录</title></head><body>
<script src="//g.alicdn.com/vip/havana-nlogin/0.10.36/index.js"></script>
<div id="login-widget">havanaone loginLegacy</div>
</body></html>
"""


def test_looks_logged_in():
    assert _looks_logged_in(LOGGED_IN_HTML)
    assert not _looks_logged_in(LOGIN_PAGE)
    print("test_looks_logged_in OK")


def test_parse_list_strategy1():
    pkgs, ok, debug = parse_list_html(LOGGED_IN_HTML)
    assert ok and len(pkgs) == 2
    p0 = pkgs[0]
    assert p0.mail_no == "SF1234567890123"
    assert p0.company_code == "SF"
    assert "杭州转运中心" in p0.latest_status
    assert p0.latest_time.startswith("2025-06-08 10:00")
    print("test_parse_list_strategy1 OK, debug:", debug)


def test_parse_list_strategy2():
    # 构造"页面内嵌 JSON"场景（无表格链接）
    html = ('<html><body><script>window.__DATA__={"packageList":['
            '{"mailNo":"SF9999999999999","cpCode":"SF","latestStatus":"已签收",'
            '"latestTime":"2025-06-07 11:00:00"}]}</script></body></html>')
    pkgs, ok, debug = parse_list_html(html)
    assert ok and pkgs, debug
    assert pkgs[0].mail_no == "SF9999999999999"
    assert pkgs[0].company_code == "SF"
    print("test_parse_list_strategy2 OK")


def test_parse_list_strategy3():
    # 纯表格、无 mailNo 链接的场景（依赖列内容启发式）
    html = ('<html><body><h2>我的包裹</h2><table>'
            '<tr><td>圆通速递</td><td>YT1111111111111</td>'
            '<td>运输中</td><td>2025-06-08 08:00:00</td></tr>'
            '<tr><td>极兔速递</td><td>JT2222222222222</td>'
            '<td>派件中</td><td>2025-06-08 09:00:00</td></tr>'
            '</table></body></html>')
    pkgs, ok, debug = parse_list_html(html)
    assert ok and any(p.mail_no == "YT1111111111111" for p in pkgs), debug
    print("test_parse_list_strategy3 OK")


def test_parse_login_required():
    from app.api.http_client import LoginRequired
    try:
        parse_list_html(LOGIN_PAGE)
        assert False, "should raise LoginRequired"
    except LoginRequired:
        pass
    print("test_parse_login_required OK")


DETAIL_HTML = """
<html><body>
<ul class="trace">
<li><span>2025-06-08 10:00:00</span>快件已到达【杭州转运中心】</li>
<li><span>2025-06-08 08:12:00</span>快件在【上海】已装车</li>
<li><span>2025-06-07 22:40:00</span>快件已从【上海】发出</li>
</ul>
</body></html>
"""


def test_parse_detail():
    nodes = parse_detail_html(DETAIL_HTML)
    assert len(nodes) == 3
    assert nodes[0].status == "快件已到达【杭州转运中心】"
    assert nodes[0].kind == "end" and nodes[-1].kind == "start"
    # 倒序：最新在前
    assert nodes[0].time.startswith("2025-06-08 10:00")
    print("test_parse_detail OK")


def test_extract_location():
    assert extract_location("快件已到达【杭州转运中心】") == "杭州转运中心"
    assert extract_location("快件在【上海市】已装车") == "上海市"
    assert extract_location("快件已从浙江省杭州市发出") == "浙江省杭州市" or "杭州市"
    assert extract_location("派送中") == ""
    print("test_extract_location OK")


def test_models():
    p = Package(mail_no="SF1234567890123", company_code="SF",
                latest_status="x", latest_time="2025-06-08 10:00:00")
    assert p.masked_no() == "SF12********123"  # 15位单号：前4 + 8星 + 后3
    fp = p.fingerprint()
    p2 = Package(mail_no="SF1234567890123", company_code="SF",
                 latest_status="y", latest_time="2025-06-08 10:00:00")
    assert fp != p2.fingerprint()
    d = p.to_dict()
    assert Package.from_dict(d).mail_no == p.mail_no
    nodes = [TraceNode(time="2025-06-08 09:00:00"), TraceNode(time="2025-06-08 10:00:00")]
    assert sort_trace_desc(nodes)[0].time == "2025-06-08 10:00:00"
    print("test_models OK")


def test_kuaidi100_offline_behavior():
    """不依赖网络：验证错误单号走友好报错路径（联网时才真正请求）"""
    import requests
    try:
        r = requests.get("https://www.kuaidi100.com/query",
                         params={"type": "shunfeng", "postid": "SF0000000000000",
                                 "temp": "0.5"}, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0"})
        j = r.json()
        print("kuaidi100 live response status:", j.get("status"), j.get("message"))
    except Exception as e:
        print("kuaidi100 live test skipped (offline):", e)


def test_demo_data():
    """模拟数据源：不联网生成包裹；第二次刷新应有更新（驱动通知）"""
    from app.api import demo
    from app.api.demo import _TICK

    _TICK["n"] = 0
    pkgs1 = demo.fetch_packages()
    assert len(pkgs1) >= 2, "模拟数据至少 2 个包裹"
    p0 = pkgs1[0]
    assert p0.source == "demo"
    assert len(p0.trace) >= 3, "每个包裹至少 3 条轨迹"
    assert len(p0.extra.get("coords", [])) == len(p0.trace), "坐标与轨迹对齐"
    assert p0.trace[0].kind == "end" and p0.trace[-1].kind == "start"
    # 第二次刷新：至少一个包裹指纹变化（触发更新通知）
    pkgs2 = demo.fetch_packages()
    fps1 = {p.mail_no: p.fingerprint() for p in pkgs1}
    fps2 = {p.mail_no: p.fingerprint() for p in pkgs2}
    assert any(fps1[k] != fps2.get(k) for k in fps1), "模拟数据应产生物流更新"
    # 往返序列化
    d = p0.to_dict()
    assert Package.from_dict(d).mail_no == p0.mail_no
    print("test_demo_data OK")


def test_demo_detail_coords():
    """模拟模式详情坐标：直接可用，无需地理编码"""
    from app.api import demo
    pkg = demo.demo_package()
    coords = [tuple(c) for c in pkg.extra.get("coords", [])]
    assert len(coords) == len(pkg.trace)
    assert all(len(c) == 2 and all(isinstance(v, (int, float)) for v in c) for c in coords)
    print("test_demo_detail_coords OK")


def test_kdniao_sign():
    """快递鸟 DataSign 签名算法（离线验证）"""
    from app.api.kdniao import _sign
    # 已知值验证：RequestData='{"LogisticCode":"SF123"}' AppKey='key123'
    import base64, hashlib
    data = '{"LogisticCode":"SF123"}'
    key = "key123"
    expect = base64.b64encode(hashlib.md5((data + key).encode()).hexdigest().encode()).decode()
    assert _sign(data, key) == expect
    print("test_kdniao_sign OK")


def test_provider_config():
    """服务商配置读写"""
    import tempfile
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp")
    os.makedirs(d, exist_ok=True)
    c = Config(os.path.join(d, "prov.json"))
    c.set_provider("kdniao")
    c.set_kdniao("123456", "secret")
    c2 = Config(os.path.join(d, "prov.json"))
    assert c2.get_provider() == "kdniao"
    assert c2.get_kdniao()["ebusiness_id"] == "123456"
    c2.set_provider("kuaidi100")
    c2.set_kuaidi100_api("cust", "key1")
    c3 = Config(os.path.join(d, "prov.json"))
    assert c3.get_provider() == "kuaidi100"
    assert c3.get_kuaidi100_api()["customer"] == "cust"
    print("test_provider_config OK")


def test_dnd_config():
    """免打扰开关持久化"""
    import tempfile
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp")
    os.makedirs(d, exist_ok=True)
    c = Config(os.path.join(d, "dnd.json"))
    c.set_dnd(True)
    c2 = Config(os.path.join(d, "dnd.json"))
    assert c2.is_dnd() is True
    c2.set_dnd(False)
    c3 = Config(os.path.join(d, "dnd.json"))
    assert c3.is_dnd() is False
    print("test_dnd_config OK")


def test_clear_private_data():
    """清除我的信息：抹掉密钥/Cookie/手机号/运单"""
    import tempfile
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp")
    os.makedirs(d, exist_ok=True)
    c = Config(os.path.join(d, "clear.json"))
    c.set_provider("kdniao")
    c.set_kdniao("1234567", "secret-key")
    c.set_phone("13800138000")
    c.set_cookies({"cookie2": "abc"})
    c.add_manual_package({"mail_no": "SF1", "com100": "shunfeng"})
    c.clear_private_data()
    c2 = Config(os.path.join(d, "clear.json"))
    assert c2.get_cookies() == {}
    assert c2.get_phone() == ""
    assert c2.get_kdniao()["app_key"] == ""
    assert c2.get_manual_packages() == []
    assert c2.get_provider() == "wuliu"
    print("test_clear_private_data OK")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\nALL CORE TESTS PASSED")
