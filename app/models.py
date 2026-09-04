# -*- coding: utf-8 -*-
"""数据模型：包裹与物流节点"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 运单号粗略匹配：1-4 位字母 + 9~16 位数字（常见国内快递单号）
TRACKING_RE = re.compile(r"(?<![0-9A-Za-z])([A-Za-z]{0,4}\d{9,16})(?![0-9A-Za-z])")
TIME_RE = re.compile(r"\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}[日]?\s*\d{1,2}:\d{2}(?::\d{2})?")


@dataclass
class TraceNode:
    """一条物流轨迹节点"""
    time: str = ""          # 节点时间（原始字符串）
    status: str = ""        # 节点描述
    location: str = ""      # 地点（尽量从描述中提取）
    kind: str = "mid"       # start / mid / end（用于地图标记）

    def to_dict(self) -> dict:
        return {"time": self.time, "status": self.status,
                "location": self.location, "kind": self.kind}

    @staticmethod
    def from_dict(d: dict) -> "TraceNode":
        return TraceNode(time=d.get("time", ""), status=d.get("status", ""),
                         location=d.get("location", ""), kind=d.get("kind", "mid"))


@dataclass
class Package:
    """一个包裹"""
    mail_no: str                # 运单号
    company_code: str = "OTHER" # 菜鸟公司编码
    company_name: str = "其他快递"
    latest_status: str = ""     # 最新物流状态
    latest_time: str = ""       # 最近更新时间
    state: str = "transporting" # transporting/delivering/signed/problem
    source: str = "wuliu"       # 数据来源：wuliu(淘宝物流助手) / kuaidi100
    trace: list[TraceNode] = field(default_factory=list)
    detail_url: str = ""        # 网页详情链接（可选）
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "mail_no": self.mail_no, "company_code": self.company_code,
            "company_name": self.company_name, "latest_status": self.latest_status,
            "latest_time": self.latest_time, "state": self.state,
            "source": self.source, "detail_url": self.detail_url,
            "extra": self.extra,
            "trace": [n.to_dict() for n in self.trace],
        }

    @staticmethod
    def from_dict(d: dict) -> "Package":
        return Package(
            mail_no=d.get("mail_no", ""),
            company_code=d.get("company_code", "OTHER"),
            company_name=d.get("company_name", "其他快递"),
            latest_status=d.get("latest_status", ""),
            latest_time=d.get("latest_time", ""),
            state=d.get("state", "transporting"),
            source=d.get("source", "wuliu"),
            detail_url=d.get("detail_url", ""),
            extra=d.get("extra", {}),
            trace=[TraceNode.from_dict(x) for x in d.get("trace", [])],
        )

    # ---------- 便捷方法 ----------
    def fingerprint(self) -> str:
        """包裹状态指纹：用于判断是否有新更新"""
        head = self.trace[0] if self.trace else None
        sig = (head.time if head else self.latest_time) + "|" + (head.status if head else self.latest_status)
        return sig

    def masked_no(self) -> str:
        """运单号打码显示：保留前4后3"""
        n = self.mail_no
        if len(n) <= 8:
            return n
        return n[:4] + "*" * (len(n) - 7) + n[-3:]


def sort_trace_desc(nodes: list[TraceNode]) -> list[TraceNode]:
    """按时间倒序排序（新→旧）。解析失败时保持原顺序。"""
    def _key(n: TraceNode):
        t = n.time.strip().replace("/", "-").replace("年", "-").replace("月", "-").replace("日", " ")
        t = re.sub(r"[^.0-9: -]", "", t)
        return t
    try:
        return sorted(nodes, key=_key, reverse=True)
    except Exception:
        return nodes
