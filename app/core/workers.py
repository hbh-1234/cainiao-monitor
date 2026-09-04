# -*- coding: utf-8 -*-
"""后台线程的“非阻塞分离”收尾
问题：对话框 closeEvent 里同步 wait() 会冻结 UI（用户点 × 感觉“卡死”）。
方案：关窗时把线程与窗口分离（setParent(None)），线程在后台自然结束；
      程序退出前统一 wait_all()，避免“QThread destroyed while running”崩溃。
"""
from __future__ import annotations

import threading

_LINGERING: list = []
_LOCK = threading.Lock()


def detach_thread(thread) -> None:
    """把运行中的 QThread 与父对象分离，加入后台收尾队列"""
    try:
        thread.setParent(None)
    except Exception:
        pass
    with _LOCK:
        if thread not in _LINGERING:
            _LINGERING.append(thread)

    def _done():
        with _LOCK:
            if thread in _LINGERING:
                _LINGERING.remove(thread)
        # 不调用 deleteLater：线程已结束，对象交由引用计数销毁即可

    try:
        thread.finished.connect(_done)
    except Exception:
        pass


def wait_all(timeout_ms: int = 10000) -> None:
    """程序退出前：等待所有后台线程结束（最多 timeout_ms）"""
    with _LOCK:
        items = list(_LINGERING)
    for t in items:
        try:
            if t.isRunning():
                t.wait(timeout_ms)
        except Exception:
            pass
    with _LOCK:
        _LINGERING.clear()
