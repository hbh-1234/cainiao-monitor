# -*- coding: utf-8 -*-
"""配置管理：Cookie、设置、状态指纹、地理缓存等，JSON 持久化到 %APPDATA%"""
from __future__ import annotations

import json
import os
import tempfile
import threading

APP_DIR_NAME = "CainiaoMonitor"


def app_data_dir() -> str:
    """应用数据目录（优先 APPDATA，不可写时退回用户目录/临时目录）"""
    candidates = []
    if os.name == "nt" and os.environ.get("APPDATA"):
        candidates.append(os.path.join(os.environ["APPDATA"], APP_DIR_NAME))
    candidates.append(os.path.join(os.path.expanduser("~"), "." + APP_DIR_NAME))
    candidates.append(os.path.join(tempfile.gettempdir(), APP_DIR_NAME))
    for c in candidates:
        try:
            os.makedirs(c, exist_ok=True)
            probe = os.path.join(c, ".write_test")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
            return c
        except Exception:
            continue
    return candidates[-1]


class Config:
    """线程安全的 JSON 配置。"""

    def __init__(self, path: str | None = None):
        self._lock = threading.RLock()
        self.path = path or os.path.join(app_data_dir(), "config.json")
        self.data: dict = {}
        self.load()

    # ---------- 基础读写 ----------
    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            self.data = {}
        self.data.setdefault("cookies", {})            # name -> value
        self.data.setdefault("phone", "")
        self.data.setdefault("last_seen", {})           # mail_no -> 指纹
        self.data.setdefault("manual_packages", [])     # 手动添加的运单
        self.data.setdefault("provider", "wuliu")    # wuliu/kdniao/kuaidi100/demo
        self.data.setdefault("kdniao", {"ebusiness_id": "", "app_key": ""})
        self.data.setdefault("kuaidi100_api", {"customer": "", "key": ""})
        self._runtime_demo = False   # 模拟模式（仅本次运行生效，不写盘）
        self.data.setdefault("settings", {})
        self.data["settings"].setdefault("refresh_min", 5)
        self.data["settings"].setdefault("notify_enabled", True)
        self.data["settings"].setdefault("dnd", False)          # 免打扰：不弹通知
        self.data["settings"].setdefault("appearance", {
            "mode": "dark", "scheme": "极光青",
            "accent": "#00D4FF", "accent2": "#3E7BFA", "accent3": "#8B5CF6"})

    def save(self) -> None:
        with self._lock:
            try:
                tmp = self.path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                os.replace(tmp, self.path)
            except Exception:
                pass  # 保存失败不影响运行

    def get(self, key: str, default=None):
        with self._lock:
            return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        with self._lock:
            self.data[key] = value
            self.save()

    # ---------- 业务方法 ----------
    def set_cookies(self, cookies: dict) -> None:
        self.set("cookies", dict(cookies) if cookies else {})

    def get_cookies(self) -> dict:
        return dict(self.get("cookies", {}) or {})

    def set_phone(self, phone: str) -> None:
        self.set("phone", phone or "")

    def get_phone(self) -> str:
        return str(self.get("phone", "") or "")

    def phone_last4(self) -> str:
        p = self.get_phone()
        return p[-4:] if len(p) >= 4 else ""

    def get_manual_packages(self) -> list[dict]:
        return list(self.get("manual_packages", []) or [])

    def add_manual_package(self, item: dict) -> None:
        with self._lock:
            items = list(self.data.get("manual_packages", []) or [])
            items = [x for x in items if x.get("mail_no") != item.get("mail_no")]
            items.append(item)
            self.data["manual_packages"] = items
            self.save()

    def remove_manual_package(self, mail_no: str) -> None:
        with self._lock:
            items = list(self.data.get("manual_packages", []) or [])
            self.data["manual_packages"] = [x for x in items if x.get("mail_no") != mail_no]
            self.save()

    def get_last_seen(self, mail_no: str) -> str:
        return str((self.get("last_seen", {}) or {}).get(mail_no, ""))

    def set_last_seen(self, mail_no: str, fingerprint: str) -> None:
        with self._lock:
            d = dict(self.data.get("last_seen", {}) or {})
            d[mail_no] = fingerprint
            self.data["last_seen"] = d
            self.save()

    def settings(self) -> dict:
        return dict(self.get("settings", {}) or {})

    # ---------- 包裹数据缓存（网络失败时兜底展示） ----------
    def get_cached_packages(self) -> list[dict]:
        return list(self.get("cached_packages", []) or [])

    def set_cached_packages(self, packages: list) -> None:
        """packages: 已序列化的 dict 列表"""
        with self._lock:
            self.data["cached_packages"] = packages
            self.save()

    # ---------- 服务商（菜鸟账号 / 快递鸟 / 快递100 / 模拟） ----------
    def set_provider(self, name: str) -> None:
        self.set("provider", name if name in ("wuliu", "kdniao", "kuaidi100", "demo") else "wuliu")

    def get_provider(self) -> str:
        return str(self.get("provider", "wuliu") or "wuliu")

    def set_kdniao(self, ebusiness_id: str, app_key: str) -> None:
        self.set("kdniao", {"ebusiness_id": ebusiness_id or "", "app_key": app_key or ""})

    def get_kdniao(self) -> dict:
        d = self.get("kdniao", {}) or {}
        return {"ebusiness_id": str(d.get("ebusiness_id", "") or ""),
                "app_key": str(d.get("app_key", "") or "")}

    def set_kuaidi100_api(self, customer: str, key: str) -> None:
        self.set("kuaidi100_api", {"customer": customer or "", "key": key or ""})

    def get_kuaidi100_api(self) -> dict:
        d = self.get("kuaidi100_api", {}) or {}
        return {"customer": str(d.get("customer", "") or ""),
                "key": str(d.get("key", "") or "")}

    # ---------- 模拟模式（无需手机号/不联网的演示数据） ----------
    def set_demo(self, on: bool = True) -> None:
        self.set("demo", bool(on))

    def is_demo(self) -> bool:
        return self._runtime_demo or bool(self.get("demo", False))

    def set_runtime_demo(self, on: bool = True) -> None:
        """仅本次运行进入模拟模式（不写入磁盘，不覆盖用户真实服务商）"""
        self._runtime_demo = bool(on)

    def is_runtime_demo(self) -> bool:
        return self._runtime_demo

    # ---------- 免打扰 ----------
    def set_dnd(self, on: bool) -> None:
        with self._lock:
            self.data["settings"]["dnd"] = bool(on)
            self.save()

    def is_dnd(self) -> bool:
        return bool(self.settings().get("dnd", False))

    # ---------- 外观（深浅色/跟随系统 + 配色方案三色） ----------
    def get_appearance(self) -> dict:
        d = self.settings().get("appearance", {}) or {}
        mode = d.get("mode", "dark")
        if mode not in ("dark", "light", "system"):
            mode = "dark"
        return {
            "mode": mode,
            "scheme": str(d.get("scheme", "极光青") or "极光青"),
            "accent": str(d.get("accent", "#00D4FF") or "#00D4FF"),
            "accent2": str(d.get("accent2", "#3E7BFA") or "#3E7BFA"),
            "accent3": str(d.get("accent3", "#8B5CF6") or "#8B5CF6"),
        }

    def set_appearance(self, mode: str, scheme: str,
                       accent: str, accent2: str, accent3: str) -> None:
        with self._lock:
            self.data["settings"]["appearance"] = {
                "mode": mode if mode in ("dark", "light", "system") else "dark",
                "scheme": scheme or "极光青",
                "accent": accent or "#00D4FF",
                "accent2": accent2 or "#3E7BFA",
                "accent3": accent3 or "#8B5CF6",
            }
            self.save()

    # ---------- API 服务商凭证是否已配置（可直接进主界面） ----------
    def has_api_credentials(self) -> bool:
        p = self.get_provider()
        if p == "kdniao":
            d = self.get_kdniao()
            return bool(d.get("ebusiness_id")) and bool(d.get("app_key"))
        if p == "kuaidi100":
            d = self.get_kuaidi100_api()
            return bool(d.get("customer")) or bool(d.get("key"))
        return False

    # ---------- 清除我的信息（分享前 / 换账号） ----------
    def clear_private_data(self) -> None:
        """抹除密钥/Cookie/手机号/手动运单，回到未登录状态"""
        with self._lock:
            self.data["cookies"] = {}
            self.data["phone"] = ""
            self.data["kdniao"] = {"ebusiness_id": "", "app_key": ""}
            self.data["kuaidi100_api"] = {"customer": "", "key": ""}
            self.data["manual_packages"] = []
            self.data["provider"] = "wuliu"
            self.data["demo"] = False
            self.save()

    def refresh_minutes(self) -> int:
        try:
            v = int(self.settings().get("refresh_min", 5))
        except Exception:
            v = 5
        return max(1, min(v, 120))
