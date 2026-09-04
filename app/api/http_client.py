# -*- coding: utf-8 -*-
"""HTTP 客户端：统一超时 / 重试 / UA / Cookie 管理
注意：requests.Session 不是线程安全的，每个工作线程使用自己的实例。
"""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..constants import USER_AGENT


class NetworkError(Exception):
    """网络异常（含超时、连接失败）"""


class LoginRequired(Exception):
    """登录态失效 / 需要登录"""


class ApiError(Exception):
    """接口业务错误（如解析失败、风控拦截）"""


def build_session(cookies: dict | None = None) -> requests.Session:
    """创建一个带重试与 UA 的 Session"""
    s = requests.Session()
    retry = Retry(total=2, connect=2, backoff_factor=0.8,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET", "POST"])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers["User-Agent"] = USER_AGENT
    s.headers["Accept"] = "*/*"
    if cookies:
        s.cookies.update(cookies)
    return s


def request(session: requests.Session, method: str, url: str, **kwargs) -> requests.Response:
    """统一请求入口：超时 + 异常翻译"""
    kwargs.setdefault("timeout", 15)
    try:
        resp = session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp
    except requests.exceptions.Timeout as e:
        raise NetworkError("网络请求超时，请检查网络后重试") from e
    except requests.exceptions.ConnectionError as e:
        raise NetworkError("无法连接服务器，请检查网络后重试") from e
    except requests.exceptions.HTTPError as e:
        raise ApiError(f"服务器返回异常状态码 {resp.status_code}") from e
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"网络错误：{e}") from e


def cookie_header(cookies: dict) -> str:
    """把 cookie 字典转成 Cookie 头字符串（用于调试/日志）"""
    return "; ".join(f"{k}={v}" for k, v in cookies.items())
