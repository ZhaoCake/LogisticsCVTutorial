"""
显示模块 - 封装 OpenCV 窗口

提供实时可视化功能，用于调试时查看相机画面。
在帧上叠加显示当前状态名称和检测结果。
通过 enabled 开关控制是否实际显示，关闭时所有方法为无操作。

支持按键:
  ESC / Q  → 触发 KeyboardInterrupt 退出程序
"""

import logging
import cv2
import numpy as np

logger = logging.getLogger("Display")


class Display:
    """OpenCV 窗口封装

    使用示例:
        display = Display(enabled=True, window_name="CVTutorial")
        display.show(frame, state="SCAN_QR", result="123+321")
        display.close()
    """

    def __init__(self, enabled: bool = False, window_name: str = "CVTutorial"):
        """初始化显示窗口

        参数:
            enabled:     是否启用可视化，默认关闭
            window_name: 窗口标题
        """
        self._enabled = enabled
        self._window_name = window_name

        if self._enabled:
            cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
            logger.info(f"可视化窗口已创建: {self._window_name}")

    def show(self, frame, state: str = "", result: str = ""):
        """显示一帧图像，叠加状态和结果文字

        enabled=False 时直接返回，不做任何操作。

        文字位置: 左上角
          - 第一行: 当前状态 (绿色粗体)
          - 第二行: 检测结果 (黄色)

        参数:
            frame:  OpenCV BGR 图像 (numpy.ndarray)
            state:  当前状态名称，如 "SCAN_QR"
            result: 检测结果字符串，如 "123+321"

        返回:
            True 表示正常运行，False 表示检测到退出按键
        """
        if not self._enabled or frame is None:
            return True

        # ── 叠加调试信息 ──
        overlay = frame.copy()

        # 左上角半透明背景
        h, w = overlay.shape[:2]
        cv2.rectangle(overlay, (0, 0), (w, 90), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)

        # 状态行 (绿色)
        cv2.putText(
            frame, f"State: {state}", (12, 36),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 255, 50), 2,
        )

        # 结果行 (黄色)
        cv2.putText(
            frame, f"Result: {result}", (12, 68),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 255, 255), 2,
        )

        # ── 显示 ──
        cv2.imshow(self._window_name, frame)
        key = cv2.waitKey(1) & 0xFF

        if key in (27, ord("q"), ord("Q")):
            logger.info("检测到退出按键，关闭窗口")
            return False

        return True

    def close(self):
        """关闭显示窗口"""
        if self._enabled:
            cv2.destroyWindow(self._window_name)
            logger.info("可视化窗口已关闭")

    @property
    def enabled(self):
        """是否启用可视化"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """动态开关可视化"""
        self._enabled = value
