# -*- coding: utf-8 -*-
"""模拟数据源：不联网生成演示包裹（完整轨迹 + 经纬度坐标）
用于没有真实手机号/网络受限时，完整体验「登录→列表→详情→刷新→通知」全流程。
特性：每次刷新会让其中一个包裹"前进"一个物流节点（模拟新更新），
从而驱动指纹变化检测与托盘通知。
"""
from __future__ import annotations

import random
import time

from ..models import Package, TraceNode

_TICK = {"n": 0}

# 演示包裹模板：(运单号, 公司编码, [(状态, 城市, lat, lon), ...]) 新→旧
_TEMPLATES = [
    ("SF1427395820135", "SF", [
        ("快件已到达【杭州转运中心】，准备发往下一站", "杭州", 30.2741, 120.1551),
        ("快件在【上海浦东新区】已装车", "上海", 31.2304, 121.4737),
        ("快件已从【上海浦东新区】发出", "上海", 31.2304, 121.4737),
        ("顺丰速运已收取快件", "上海", 31.2304, 121.4737),
    ]),
    ("YT7684951203498", "YTO", [
        ("派件中，快递员正在为您派送", "杭州", 30.2741, 120.1551),
        ("快件已到达【杭州市西湖区】网点", "杭州", 30.2598, 120.1303),
        ("快件在【金华转运中心】完成分拣", "金华", 29.0789, 119.6474),
        ("商家已发货，等待揽收", "义乌", 29.3068, 120.0752),
    ]),
    ("JT9912045612377", "JT", [
        ("快件已到达【南京市雨花台区】网点", "南京", 32.0603, 118.7781),
        ("快件在【无锡转运中心】完成分拣", "无锡", 31.4912, 120.3119),
        ("快件已从【苏州市】发出", "苏州", 31.2989, 120.5853),
    ]),
]

# 每次刷新可能"前进"的城市序列（用于制造新更新）
_PROGRESS = [
    ("快件已到达【南京市中转场】", "南京", 32.0403, 118.7681),
    ("快件在【镇江分拨中心】完成分拣", "镇江", 32.1878, 119.4252),
    ("快件已从【南京市】发出", "南京", 32.0603, 118.7781),
    ("快件已到达【上海市青浦区】转运中心", "上海", 31.1498, 121.1242),
    ("派件中，快递员正在为您派送", "上海", 31.2304, 121.4737),
]


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def fetch_packages() -> list[Package]:
    """生成/推进演示包裹。每次调用改变一个包裹的最新节点，触发更新通知。"""
    _TICK["n"] += 1
    tick = _TICK["n"]
    packages: list[Package] = []

    for idx, (mail_no, code, nodes) in enumerate(_TEMPLATES):
        # 每次刷新把一个包裹"推进"一步（从第 2 次调用开始）
        if tick > 1 and idx == (tick - 2) % len(_TEMPLATES):
            st, city, lat, lon = _PROGRESS[(tick - 2) % len(_PROGRESS)]
            nodes = [(st, city, lat, lon)] + list(nodes)
        trace: list[TraceNode] = []
        coords: list[list[float]] = []
        now = _now_str()
        for i, (st, city, lat, lon) in enumerate(nodes):
            # 时间：最新节点为当前时间，越早的节点越旧
            t = now if i == 0 else time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(time.time() - (i * 3600 + random.randint(0, 40) * 60)))
            node = TraceNode(time=t, status=st, location=city,
                             kind="end" if i == 0 else ("start" if i == len(nodes) - 1 else "mid"))
            trace.append(node)
            coords.append([lat, lon])
        pkg = Package(
            mail_no=mail_no,
            company_code=code,
            company_name={"SF": "顺丰速运", "YTO": "圆通速递", "JT": "极兔速递"}.get(code, "其他快递"),
            latest_status=trace[0].status,
            latest_time=trace[0].time,
            state="delivering" if idx % 3 == 1 else "transporting",
            source="demo",
            trace=trace,
            extra={"coords": coords, "demo": True},
        )
        packages.append(pkg)
    return packages


def demo_package() -> Package:
    """返回第一个演示包裹（供 UI 冒烟测试直接使用）"""
    return fetch_packages()[0]
