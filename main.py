"""
视觉程序入口

启动状态机主循环，持续处理下位机命令并执行对应视觉任务。

使用方式:
    # 使用默认虚拟串口 /tmp/ttyV1，波特率 115200
    python main.py

    # 指定串口和波特率
    python main.py /dev/ttyUSB0 9600

调试方式:
    1. 先运行 scripts/setup_virtual_serial.sh 创建虚拟串口对
    2. 启动本程序（连接 /tmp/ttyV1）
    3. 运行 scripts/send_cmd.sh C1 发送命令模拟下位机
    4. 运行 scripts/monitor_reply.sh 查看视觉回复
"""

import sys
import logging

from src.camera import Camera
from src.serial_comm import SerialComm
from src.state_machine import StateMachine


def _setup_logging():
    """配置日志输出格式"""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    """主函数

    解析命令行参数，初始化相机、串口和状态机，进入主循环。
    """
    _setup_logging()
    logger = logging.getLogger("Main")

    # 解析命令行参数
    port = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ttyV1"
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200

    logger.info(f"串口: {port}, 波特率: {baud}")

    # 初始化相机（默认摄像头 0，640x480）
    logger.info("正在初始化摄像头...")
    camera = Camera(device="./resources/qr_loop.mp4", width=640, height=480)
    logger.info("摄像头初始化成功")

    # 初始化串口
    logger.info(f"正在打开串口 {port}...")
    serial = SerialComm(port, baud)
    logger.info("串口打开成功")

    # 启动状态机主循环（阻塞，永不返回）
    logger.info("启动状态机主循环")
    sm = StateMachine(camera, serial)
    sm.run()


if __name__ == "__main__":
    main()
