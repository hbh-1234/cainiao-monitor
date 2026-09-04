# -*- coding: utf-8 -*-
"""快递鸟（KDNiao）即时查询 API 客户端
接口：https://api.kdniao.com/api/dist （生产环境）
- RequestType=8001（即时查询）
- DataType=2（JSON）
- 签名：DataSign = Base64(MD5(RequestData + ApiKey))，程序自动计算
需要用户提供：EBusinessID 与 ApiKey（登录页「快递鸟 API」处填写）
"""

from __future__ import annotations

import base64
import hashlib
import json

from ..constants import KDNIAO_CODE_MAP, KDNIAO_URL

# 快递鸟即时查询请求类型（新接口 api/dist）
KDNIAO_REQUEST_TYPE = "8001"
from ..models import Package, TraceNode, sort_trace_desc
from .http_client import ApiError, request


class KdniaoError(ApiError):
    pass


def _sign(request_data: str, app_key: str) -> str:
    """DataSign = Base64(MD5(RequestData + AppKey))"""
    md5 = hashlib.md5((request_data + app_key).encode("utf-8")).hexdigest()
    return base64.b64encode(md5.encode("utf-8")).decode("utf-8")


def query(session, ebusiness_id: str, app_key: str,
          logistic_code: str, shipper_code: str = "",
          phone_last4: str = "") -> tuple[list[TraceNode], str]:
    """即时查询单个运单。返回 (节点列表[新→旧], 状态码 state)
    state: 0无轨迹 1已揽收 2在途 3签收 4问题件 5转投 6清关
    """
    if not ebusiness_id or not app_key:
        raise KdniaoError("请先在登录页填写快递鸟 EBusinessID 与 AppKey")
    if not shipper_code:
        shipper_code = KDNIAO_CODE_MAP.get("OTHER", "")
    request_data = {"LogisticCode": logistic_code, "ShipperCode": shipper_code}
    if phone_last4:
        request_data["CustomerName"] = phone_last4
    data_str = json.dumps(request_data, ensure_ascii=False)
    params = {
        "RequestData": data_str,
        "EBusinessID": ebusiness_id,
        "RequestType": KDNIAO_REQUEST_TYPE,
        "DataSign": _sign(data_str, app_key),
        "DataType": "2",
    }
    resp = request(session, "POST", KDNIAO_URL, data=params,
                   headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
    try:
        j = resp.json()
    except Exception as e:
        raise KdniaoError("快递鸟返回了无法解析的数据（请检查网络后重试）") from e

    if not j.get("Success"):
        raise KdniaoError("快递鸟查询失败：" + str(j.get("Reason") or "未知原因"))

    traces = j.get("Traces") or []
    nodes: list[TraceNode] = []
    for t in traces:
        time_str = str(t.get("AcceptTime") or "").strip()
        station = str(t.get("AcceptStation") or "").strip()
        remark = str(t.get("Remark") or "").strip()
        status = station or remark
        if not status:
            continue
        nodes.append(TraceNode(time=time_str, status=status, location=""))
    if not nodes:
        # 无轨迹但有基础信息
        raise KdniaoError("该运单暂无物流轨迹数据")
    nodes = sort_trace_desc(nodes)
    if nodes:
        nodes[0].kind = "end"
        nodes[-1].kind = "start"
    return nodes, str(j.get("State", "0"))


def query_package(session, ebusiness_id: str, app_key: str,
                  mail_no: str, company_code: str, phone_last4: str = "") -> Package:
    """查询并组装 Package（快递鸟数据源）"""
    shipper = KDNIAO_CODE_MAP.get(company_code, "")
    nodes, state = query(session, ebusiness_id, app_key, mail_no,
                         shipper, phone_last4)
    from ..constants import company_info
    info = company_info(company_code)
    head = nodes[0] if nodes else None
    return Package(
        mail_no=mail_no,
        company_code=info[0],
        company_name=info[1],
        latest_status=head.status if head else "",
        latest_time=head.time if head else "",
        state=_state_label(state),
        source="kdniao",
        trace=nodes,
    )


def _state_label(state: str) -> str:
    return {
        "3": "signed", "4": "problem", "5": "problem",
        "1": "transporting", "6": "transporting",
    }.get(state, "transporting")
