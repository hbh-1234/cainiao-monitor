# -*- coding: utf-8 -*-
"""UI 冒烟测试（离屏渲染 + 截图）
用法：python tests/test_ui_smoke.py [输出目录]
注意：需要已安装 PySide6；WebEngine 不会在此测试中加载。
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAINIAO_NO_WEBENGINE"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QFrame

from app.config import Config
from app.models import Package, TraceNode
from app.ui.theme import apply_theme
from app.ui.icons import make_app_icon, company_badge, status_dot
from app.ui.package_card import PackageCard
from app.ui.main_window import MainWindow
from app.ui.detail_dialog import DetailDialog
from app.ui.login_window import LoginWindow

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "_shots")
os.makedirs(OUT, exist_ok=True)

app = QApplication(sys.argv)
apply_theme(app)


def demo_packages() -> list[Package]:
    now = "2025-06-08 14:32:10"
    return [
        Package(mail_no="SF1427395820135", company_code="SF",
                latest_status="快件已到达【杭州转运中心】，准备发往下一站",
                latest_time=now, state="transporting",
                trace=[TraceNode(time=now, status="快件已到达【杭州转运中心】，准备发往下一站"),
                       TraceNode(time="2025-06-08 08:12:00", status="快件在【上海浦东新区】已装车")]),
        Package(mail_no="YT7684951203498", company_code="YTO",
                latest_status="派件中，快递员正在为您派送",
                latest_time="2025-06-08 13:05:44", state="delivering",
                trace=[TraceNode(time="2025-06-08 13:05:44", status="派件中，快递员正在为您派送")]),
        Package(mail_no="JT9912045612377", company_code="JT",
                latest_status="快件已签收，签收人：菜鸟驿站（代收）",
                latest_time="2025-06-07 11:20:00", state="signed",
                trace=[TraceNode(time="2025-06-07 11:20:00", status="快件已签收")]),
        Package(mail_no="ZT8823471901234", company_code="ZTO",
                latest_status="运输中，快件已到达【郑州分拨中心】",
                latest_time="2025-06-08 07:15:00", state="transporting",
                trace=[]),
    ]


def shot(widget, name: str):
    widget.resize(1200, 800)
    widget.show()
    app.processEvents()
    pm = widget.grab()
    path = os.path.join(OUT, name)
    pm.save(path)
    print("saved:", path)


# 1) 图标
icon = make_app_icon(64)
assert not icon.isNull()
assert not company_badge("SF", 44).isNull()
assert not status_dot("signed").isNull()
print("icons OK")

# 2) 主窗口 + 卡片
config = Config(os.path.join(OUT, "smoke_config.json"))
win = MainWindow(config)
win.on_packages(demo_packages())
shot(win, "main_window.png")
win.close()

# 3) 详情弹窗（模拟模式：直接渲染演示数据，不联网、不弹窗）
from app.api import demo as demo_api
cfg_demo0 = Config(os.path.join(OUT, "smoke_demo0.json"))
cfg_demo0.set_demo(True)
pkg = demo_api.demo_package()
dlg = DetailDialog(pkg, cfg_demo0)
dlg._on_ready(pkg.trace)
dlg.resize(1020, 620)
dlg.show()
app.processEvents()
dlg.grab().save(os.path.join(OUT, "detail_dialog.png"))
print("saved: detail_dialog.png")
dlg.close()


# 5) 登录窗口（无 WebEngine 降级路径）
lw = LoginWindow(config)
shot(lw, "login_window.png")
lw.close()

# 6) 空状态
win2 = MainWindow(config)
win2.on_packages([])
shot(win2, "main_window_empty.png")
win2.close()


# 7) 模拟模式完整管线：MonitorWorker(模拟数据) → packages_ready → 刷新 → updates_detected
from app.core.monitor import MonitorWorker
from PySide6.QtCore import QEventLoop, QTimer

cfg_demo = Config(os.path.join(OUT, "smoke_demo.json"))
cfg_demo.set_demo(True)
cfg_demo.set_phone("13800138000")
worker = MonitorWorker(cfg_demo)
received = []
updates = []


def _on_pkgs(pkgs):
    received.append(list(pkgs))


def _on_updates(items):
    updates.extend(items)


worker.packages_ready.connect(_on_pkgs)
worker.updates_detected.connect(_on_updates)
loop = QEventLoop()
worker.finished.connect(loop.quit)
worker.start()


def _check_first():
    assert received and len(received[0]) >= 2, "模拟模式应收到包裹列表"
    worker.refresh_now()   # 第二次刷新应产生更新


def _check_second():
    assert updates, "第二次刷新应检测到物流更新（驱动托盘通知）"
    loop.quit()


QTimer.singleShot(8000, _check_first)
QTimer.singleShot(16000, _check_second)
loop.exec()
worker.stop()
worker.wait(3000)
print("SIMULATION PIPELINE OK: packages=%d updates=%d" % (len(received[0]), len(updates)))

# 8) 模拟模式详情弹窗（直接用演示数据，不联网）
from app.api import demo as demo_api
pkg = demo_api.demo_package()
cfg_demo.set_demo(True)
dlg2 = DetailDialog(pkg, cfg_demo)
dlg2._on_ready(pkg.trace)
dlg2.resize(1020, 640)
dlg2.show()
app.processEvents()
dlg2.grab().save(os.path.join(OUT, "detail_demo.png"))
print("saved: detail_demo.png")
dlg2.close()

print("\nALL UI SMOKE TESTS PASSED ->", OUT)
