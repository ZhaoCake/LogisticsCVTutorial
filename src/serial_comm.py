"""
串口通信封装层 - 基于 pyserial 提供串口读写与协议帧解析

职责:
  1. 管理串口的打开/关闭/读写
  2. 维护接收缓冲区，配合 protocol.parse_frame 解析帧
  3. 提供阻塞/非阻塞两种读帧方式
  4. 提供发送应答(CC)和发送数据帧的方法
"""

import serial
from src.protocol import (
    ACK,
    parse_frame,
    build_data_frame,
)


class SerialComm:
    """串口通信封装

    使用示例:
        comm = SerialComm("/tmp/ttyV1", 115200)
        cmd, payload = comm.read_frame()        # 阻塞等待帧
        comm.send_ack()                          # 回复 CC
        comm.send_data_frame("123456")           # 发送 AA 123456 55
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.05):
        """初始化串口

        参数:
            port:     串口路径，如 "/tmp/ttyV1" 或 "COM3"
            baudrate: 波特率，默认 115200
            timeout:  读超时(秒)，默认 50ms，用于非阻塞轮询
        """
        self._ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
        # 接收缓冲区，累积串口读取的数据
        self._buffer = bytearray()

    # ── 属性 ──────────────────────────────────────────────

    @property
    def is_open(self):
        """串口是否已打开"""
        return self._ser.is_open

    @property
    def port(self):
        """串口路径"""
        return self._ser.port

    # ── 生命周期 ──────────────────────────────────────────

    def close(self):
        """关闭串口"""
        if self._ser.is_open:
            self._ser.close()

    def __del__(self):
        self.close()

    # ── 读取 ──────────────────────────────────────────────

    def _read_to_buffer(self):
        """从串口读取可用字节追加到缓冲区"""
        if not self._ser.is_open:
            return
        bytes_to_read = self._ser.in_waiting
        if bytes_to_read > 0:
            data = self._ser.read(bytes_to_read)
            self._buffer.extend(data)

    def read_frame(self, blocking: bool = True):
        """读取一个完整协议帧

        非阻塞模式下，每次只从串口读一次可用字节，尝试解析一帧。
        如果帧不完整立即返回 None。

        阻塞模式下，持续尝试读取直到获得完整帧。
        适用于 IDLE 状态等待命令。

        参数:
            blocking: True=阻塞等待直到读到帧, False=非阻塞

        返回:
            (cmd, payload) 元组，或 None（无完整帧）
        """
        while True:
            # 从串口读取可用字节
            self._read_to_buffer()

            # 尝试从缓冲区解析帧
            result = parse_frame(self._buffer)
            if result is not None:
                return result

            # 非阻塞模式下没读到就直接返回
            if not blocking:
                return None

            # 阻塞模式下等待一会再试
            import time
            time.sleep(0.005)

    # ── 发送 ──────────────────────────────────────────────

    def send_ack(self):
        """发送应答字节 CC

        视觉收到命令后立即回复 CC，通知下位机已收到命令。
        """
        if not self._ser.is_open:
            return
        self._ser.write(bytes([ACK]))

    def send_data_frame(self, data_str: str):
        """发送组帧数据

        将字符串包装为 AA DATA 55 后通过串口发送。
        在任务状态下持续调用此方法，向下位机发送检测结果。

        参数:
            data_str: 要发送的数据字符串，如 "123456" 或 "(123,123)"
        """
        if not self._ser.is_open:
            return
        frame = build_data_frame(data_str)
        self._ser.write(frame)
