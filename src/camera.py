"""
相机模块 - 封装 OpenCV VideoCapture

负责初始化摄像头，持续读取帧，对外提供最新帧。
IDLE 状态下持续调用 get_frame() 以维持视频流不中断。
"""

import cv2


class Camera:
    """OpenCV 相机封装

    使用示例:
        camera = Camera(0)            # 打开默认摄像头
        frame = camera.get_frame()    # 获取最新帧
        if frame is not None:
            ... 处理帧 ...

        camera.release()              # 释放摄像头
    """

    def __init__(self, device: int = 0, width: int = 640, height: int = 480):
        """初始化摄像头

        参数:
            device: 摄像头设备编号，默认 0（通常为内置摄像头或 USB 摄像头）
            width:  采集宽度，默认 640
            height: 采集高度，默认 480
        """
        self._cap = cv2.VideoCapture(device)

        # 设置分辨率
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        if not self._cap.isOpened():
            raise RuntimeError(f"无法打开摄像头设备 {device}")

    def get_frame(self):
        """获取最新一帧

        返回:
            numpy.ndarray 或 None（读取失败时）
        """
        ret, frame = self._cap.read()
        if not ret:
            return None
        return frame

    def release(self):
        """释放摄像头资源"""
        if self._cap is not None and self._cap.isOpened():
            self._cap.release()

    def __del__(self):
        self.release()
