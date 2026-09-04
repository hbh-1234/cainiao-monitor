# -*- coding: utf-8 -*-
"""后台监控线程：定时拉取所有包裹，检测状态变化并发出信号。
- 数据源1：淘宝物流助手（账号 Cookie）
- 数据源2：手动添加的运单（快递100）
- 变化检测：每个包裹的「最新节点时间+最新状态」指纹，与上次比较
- 网络失败：用上次成功缓存兜底，避免界面空白
"""
from __future__ import annotations

import time
import threading

from PySide6.QtCore import QThread, Signal

from ..api.http_client import LoginRequired, build_session
from ..api.kuaidi100 import query_package
from ..api.wuliu import fetch_packages
from ..config import Config
from ..logger import get_logger
from ..models import Package

log = get_logger()


class MonitorWorker(QThread):
    """监控线程。start() 后立即刷新一次，之后按配置间隔循环。"""

    packages_ready = Signal(object)      # list[Package]：最新包裹列表
    updates_detected = Signal(object)    # list[dict]：有新更新的包裹
    error_occurred = Signal(str)         # 非致命错误提示
    login_expired = Signal()             # 登录态失效
    status_changed = Signal(str)         # 状态栏文案

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self._stop = threading.Event()
        self._wake = threading.Event()
        self.session = None

    def stop(self):
        """请求线程停止（非阻塞）"""
        self._stop.set()
        self._wake.set()

    def refresh_now(self):
        """立即刷新一次（手动刷新按钮）"""
        self._wake.set()

    # ---------------------------------------------------------------
    def run(self):
        while not self._stop.is_set():
            try:
                self._refresh_once()
            except LoginRequired:
                self.login_expired.emit()
                break
            except Exception as e:
                log.exception("monitor refresh failed")
                self.error_occurred.emit(f"刷新失败：{e}")
            interval = max(30, self.config.refresh_minutes() * 60)
            self._wake.clear()
            self._wake.wait(interval)   # 等待定时唤醒或被手动刷新唤醒

    # ---------------------------------------------------------------
    def _refresh_once(self):
        self.status_changed.emit("正在刷新…")
        packages: list[Package] = []
        errors: list[str] = []

        # 服务商分发
        provider = self.config.get_provider()

        # 模拟模式：使用演示数据（无需手机号/不联网）
        if provider == "demo" or self.config.is_demo():
            # 用户主动选择的模拟才持久化；--simulate/启动器触发的仅本次运行生效
            if not self.config.is_runtime_demo():
                self.config.set_provider("demo")
            try:
                from ..api import demo
                packages = demo.fetch_packages()
            except Exception as e:
                errors.append(f"模拟数据生成失败：{e}")
            # 运行期模拟（--simulate/启动器标志）：不写缓存/last_seen，避免污染真实配置
            if self.config.is_runtime_demo():
                for e in errors:
                    self.error_occurred.emit(e)
                self.packages_ready.emit(packages)
                return
            # 用户主动选择的模拟：走完整管线（缓存 + 变化检测 + 通知）
            self._finish_refresh(packages, errors)
            return

        self.session = build_session(self.config.get_cookies())

        if provider == "kdniao":
            # 快递鸟 API：逐个查询手动添加的运单
            cred = self.config.get_kdniao()
            from ..api.kdniao import query_package as kd_query_package
            for item in self.config.get_manual_packages():
                try:
                    pkg = kd_query_package(
                        self.session, cred["ebusiness_id"], cred["app_key"],
                        str(item.get("mail_no", "")),
                        str(item.get("company_code", "OTHER")),
                        str(item.get("phone_last4", "") or self.config.phone_last4()),
                    )
                    packages.append(pkg)
                except Exception as e:
                    errors.append(f"运单 {item.get('mail_no')} 查询失败：{e}")
        elif provider == "kuaidi100":
            # 快递100：有企业 key 用企业接口，否则用公开查询
            api = self.config.get_kuaidi100_api()
            from ..api.kuaidi100 import query_official
            for item in self.config.get_manual_packages():
                try:
                    if api["customer"] and api["key"]:
                        nodes, state = query_official(
                            self.session, api["customer"], api["key"],
                            str(item.get("mail_no", "")),
                            str(item.get("com100", "")),
                            str(item.get("phone_last4", "") or self.config.phone_last4()))
                        from ..api.kuaidi100 import _state_label, _company_code_of_com, _company_name_of_com
                        pkg = Package(
                            mail_no=str(item.get("mail_no", "")),
                            company_code=_company_code_of_com(item.get("com100", "")),
                            company_name=_company_name_of_com(item.get("com100", "")),
                            latest_status=nodes[0].status if nodes else "",
                            latest_time=nodes[0].time if nodes else "",
                            state=_state_label(state), source="kuaidi100", trace=nodes)
                    else:
                        pkg = query_package(
                            self.session,
                            str(item.get("mail_no", "")),
                            str(item.get("com100", "")),
                            str(item.get("phone_last4", "") or self.config.phone_last4()))
                    packages.append(pkg)
                except Exception as e:
                    errors.append(f"运单 {item.get('mail_no')} 查询失败：{e}")
        else:
            # 默认：菜鸟账号（淘宝物流助手）+ 手动运单（快递100公开查询）
            if self.config.get_cookies():
                try:
                    packages.extend(fetch_packages(self.session))
                except LoginRequired:
                    raise  # 登录失效，向上层报告
                except Exception as e:
                    errors.append(f"账号数据获取失败：{e}")
            for item in self.config.get_manual_packages():
                try:
                    pkg = query_package(
                        self.session,
                        str(item.get("mail_no", "")),
                        str(item.get("com100", "")),
                        str(item.get("phone_last4", "") or self.config.phone_last4()),
                    )
                    packages.append(pkg)
                except Exception as e:
                    errors.append(f"运单 {item.get('mail_no')} 查询失败：{e}")

        # 全部失败时用缓存兜底
        if not packages:
            cached = self.config.get_cached_packages()
            if cached:
                packages = [Package.from_dict(d) for d in cached]
                self.status_changed.emit("网络异常，显示上次缓存数据")
            else:
                self.status_changed.emit("暂无数据")

        # 变化检测（指纹比较）
        updated = []
        for pkg in packages:
            fp = pkg.fingerprint()
            last = self.config.get_last_seen(pkg.mail_no)
            if last and last != fp:
                updated.append({"package": pkg, "old": last, "new": fp})
            self.config.set_last_seen(pkg.mail_no, fp)

        # 缓存最新列表
        try:
            self.config.set_cached_packages([p.to_dict() for p in packages])
        except Exception:
            pass

        self._finish_refresh(packages, errors)

    def _finish_refresh(self, packages, errors) -> None:
        """收尾：缓存 / 指纹变化检测 / 发信号"""
        # 变化检测（指纹比较）
        updated = []
        for pkg in packages:
            fp = pkg.fingerprint()
            last = self.config.get_last_seen(pkg.mail_no)
            if last and last != fp:
                updated.append({"package": pkg, "old": last, "new": fp})
            self.config.set_last_seen(pkg.mail_no, fp)

        # 缓存最新列表
        try:
            self.config.set_cached_packages([p.to_dict() for p in packages])
        except Exception:
            pass

        for e in errors:
            self.error_occurred.emit(e)
        self.packages_ready.emit(packages)
        if updated:
            self.updates_detected.emit(updated)
        self.status_changed.emit(
            f"上次刷新：{time.strftime('%H:%M:%S')} · 共 {len(packages)} 件 · "
            f"间隔 {self.config.refresh_minutes()} 分钟")
