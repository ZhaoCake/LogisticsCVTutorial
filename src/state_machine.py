"""
状态机核心模块

管理视觉系统的四种运行状态，支持命令中断与状态切换。

状态流转规则:
  ┌─────────┐  收到 C1/C2/C3   ┌─────────────┐
  │  IDLE   │ ───────────────→ │  任务状态    │
  │         │ ←─────────────── │ (QR/Color/   │
  │         │    收到 C0       │  Circle)     │
  └─────────┘                  └─────────────┘
       ↑                            │
       └────────────────────────────┘
          任何任务状态收到 C0 回到 IDLE

任何状态下收到 C0/C1/C2/C3 都会切换对应状态。
"""

import logging

from enum import Enum, auto
from src.protocol import (
    CMD_IDLE,
    CMD_QR,
    CMD_COLOR,
    CMD_CIRCLE,
    CMD_NAMES,
    parse_frame,
    build_data_frame,
)
from src.display import Display
from src.tasks import qr_task, color_task, circle_task

# ── 日志配置 ──────────────────────────────────────────────
logger = logging.getLogger("StateMachine")


class State(Enum):
    """状态枚举"""
    IDLE = auto()
    SCAN_QR = auto()
    DETECT_COLOR = auto()
    DETECT_CIRCLE = auto()


class StateMachine:
    """视觉状态机

    使用示例:
        sm = StateMachine(camera, serial_comm)
        sm.run()   # 进入主循环，永不返回
    """

    def __init__(self, camera, serial_comm, display: Display | None = None):
        """初始化状态机

        参数:
            camera:      Camera 实例
            serial_comm: SerialComm 实例
            display:     Display 实例，用于实时可视化（可选）
        """
        self.camera = camera
        self.serial = serial_comm
        self.display = display or Display(enabled=False)
        self.state = State.IDLE

        logger.info(f"状态机初始化完成，初始状态: {self.state.name}")

    def run(self):
        """进入状态机主循环，永不返回

        每个状态内部自循环:
          - 执行对应任务逻辑
          - 非阻塞检查是否有新命令
          - 有命令则回复 CC 并切换状态
        """
        logger.info("状态机主循环启动")

        try:
            while True:
                if self.state == State.IDLE:
                    self._run_idle()
                elif self.state == State.SCAN_QR:
                    self._run_task("SCAN_QR", qr_task)
                elif self.state == State.DETECT_COLOR:
                    self._run_task("DETECT_COLOR", color_task)
                elif self.state == State.DETECT_CIRCLE:
                    self._run_task("DETECT_CIRCLE", circle_task)
        except KeyboardInterrupt:
            logger.info("收到中断信号，状态机关闭")
        except Exception as e:
            logger.error(f"状态机异常退出: {e}", exc_info=True)
        finally:
            self.display.close()

    def _check_and_handle_command(self):
        """非阻塞检查串口是否有新命令

        如果收到命令:
          1. 记录日志
          2. 回复 CC
          3. 切换到对应状态

        返回:
            新状态(如果有命令)，或 None(无命令)
        """
        result = self.serial.read_frame(blocking=False)
        if result is None:
            return None

        cmd, payload = result
        cmd_name = CMD_NAMES.get(cmd, f"UNKNOWN(0x{cmd:02X})")
        logger.info(f"收到命令: {cmd_name} (0x{cmd:02X}), 负载: {payload}")

        # 回复应答
        self.serial.send_ack()

        # 根据命令码切换状态
        if cmd == CMD_IDLE:
            return State.IDLE
        elif cmd == CMD_QR:
            return State.SCAN_QR
        elif cmd == CMD_COLOR:
            return State.DETECT_COLOR
        elif cmd == CMD_CIRCLE:
            return State.DETECT_CIRCLE
        else:
            logger.warning(f"未知命令: 0x{cmd:02X}")
            return None

    def _run_idle(self):
        """IDLE 状态主循环

        非阻塞轮询等待下位机命令:
           1. 持续读取并显示相机帧（实时视频流）
           2. 非阻塞检查串口命令
           3. 收到命令后回复 CC 并切换状态
        """
        logger.info("进入 IDLE 状态，等待命令...")

        while True:
            # 持续读取帧，使相机缓冲区保持最新
            self.camera.get_frame()

            # 实时显示当前画面
            if not self.display.show(self.camera.last_frame, state="IDLE", result=""):
                raise KeyboardInterrupt()

            # 非阻塞检查命令
            result = self.serial.read_frame(blocking=False)
            if result is None:
                import time
                time.sleep(0.01)
                continue

            cmd, payload = result
            cmd_name = CMD_NAMES.get(cmd, f"UNKNOWN(0x{cmd:02X})")
            logger.info(f"收到命令: {cmd_name} (0x{cmd:02X}), 负载: {payload}")

            # 回复应答
            self.serial.send_ack()

            if cmd == CMD_IDLE:
                logger.debug("收到 C0，继续 IDLE")
                continue
            elif cmd == CMD_QR:
                logger.info("切换至 SCAN_QR 状态")
                self.state = State.SCAN_QR
                return
            elif cmd == CMD_COLOR:
                logger.info("切换至 DETECT_COLOR 状态")
                self.state = State.DETECT_COLOR
                return
            elif cmd == CMD_CIRCLE:
                logger.info("切换至 DETECT_CIRCLE 状态")
                self.state = State.DETECT_CIRCLE
                return
            else:
                logger.warning(f"未知命令: 0x{cmd:02X}，忽略")

    def _run_task(self, task_name: str, task_module):
        """任务状态通用运行循环

        参数:
            task_name:   任务名称，用于日志
            task_module: 任务模块，需要提供 run(camera, serial) 函数
        """
        logger.info(f"进入 {task_name} 状态")

        # 上一次的检测结果，用于显示（先显示，检测异步更新结果）
        last_result = ""

        while True:
            # 先获取最新帧并显示（带上一次结果，不等待本次检测）
            self.camera.get_frame()
            if not self.display.show(self.camera.last_frame, state=task_name, result=last_result):
                raise KeyboardInterrupt()

            # 再执行检测逻辑（内部会 sleep），更新结果
            task_result = task_module.run(self.camera, self.serial)
            if task_result:
                last_result = task_result

            # 非阻塞检查是否有新命令
            result = self._check_and_handle_command()
            if result is not None:
                self.state = result
                logger.info(f"切换至 {result.name} 状态")
                return
