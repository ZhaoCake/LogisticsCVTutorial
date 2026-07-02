"""
CVTutorial 视觉模块

用于工训赛智能物流赛道小车的视觉部分。
提供串口通信、状态机管理和任务处理功能。
"""

from src.protocol import (
    FRAME_HEADER,
    FRAME_TAIL,
    ACK,
    CMD_IDLE,
    CMD_QR,
    CMD_COLOR,
    CMD_CIRCLE,
    CMD_NAMES,
    parse_frame,
    build_data_frame,
)

from src.serial_comm import SerialComm
from src.camera import Camera
from src.display import Display
from src.state_machine import StateMachine, State

__all__ = [
    "FRAME_HEADER", "FRAME_TAIL", "ACK",
    "CMD_IDLE", "CMD_QR", "CMD_COLOR", "CMD_CIRCLE", "CMD_NAMES",
    "parse_frame", "build_data_frame",
    "SerialComm", "Camera", "Display", "StateMachine", "State",
]
