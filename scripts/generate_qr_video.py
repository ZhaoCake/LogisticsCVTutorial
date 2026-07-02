"""
生成 QR 码测试视频

生成所有 "123+321" 型组合的二维码图片，并合成循环视频。
可用作视觉调试时的模拟输入源。

QR 码格式: "XXX+YYY"
  - X/Y 分别是 {1,2,3} 的全排列
  - 共 6 × 6 = 36 种组合

输出:
  resources/qr_frames/    → 每一帧的 QR 码图片
  resources/qr_loop.mp4   → 所有帧循环播放的视频（30fps, 1秒/帧）
"""

import itertools
import os
import sys

import cv2
import numpy as np
import qrcode

# 把项目根目录加入 path，方便 import resources 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "resources")
FRAMES_DIR = os.path.join(RESOURCES_DIR, "qr_frames")
VIDEO_PATH = os.path.join(RESOURCES_DIR, "qr_loop.mp4")

# 每帧持续秒数
FRAME_DURATION = 1.0
FPS = 30
FRAMES_PER_QR = int(FPS * FRAME_DURATION)  # 每张 QR 码重复的帧数

# 图片尺寸（二维码内容不大，太小看不清）
QR_SIZE = 480
CANVAS_H = 520  # 底部留 40px 给文字标注


def main():
    os.makedirs(FRAMES_DIR, exist_ok=True)

    # 生成所有 {1,2,3} 全排列
    perms = [''.join(p) for p in itertools.permutations("123")]
    print(f"共 {len(perms)} 种排列: {perms}")

    # 生成所有 "XXX+YYY" 组合
    combinations = [f"{a}+{b}" for a in perms for b in perms]
    print(f"共 {len(combinations)} 种组合")

    all_frames = []

    for i, text in enumerate(combinations, 1):
        # ── 生成 QR 码图片 ──
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(text)
        qr.make(fit=True)

        # qrcode.make_image 返回 PIL Image，转成 OpenCV BGR
        pil_img = qr.make_image(fill_color="black", back_color="white")
        # PIL RGB → numpy → OpenCV BGR
        rgb = np.array(pil_img.convert("RGB"))
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        # 缩放到统一尺寸（添加白边填充）
        h, w = bgr.shape[:2]
        scale = min(QR_SIZE / h, QR_SIZE / w)
        new_h, new_w = int(h * scale), int(w * scale)
        resized = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

        # 居中放在白色画布上（画布比 QR 码区域高，底部留白给文字）
        canvas = np.full((CANVAS_H, QR_SIZE, 3), 255, dtype=np.uint8)
        y_off = (QR_SIZE - new_h) // 2
        x_off = (QR_SIZE - new_w) // 2
        canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized

        # 在底部添加文字标注（不干扰 QR 码区域）
        cv2.putText(
            canvas, text, (20, QR_SIZE + 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2,
        )

        # ── 保存单帧图片 ──
        frame_path = os.path.join(FRAMES_DIR, f"qr_{i:02d}_{text.replace('+', '_')}.png")
        cv2.imwrite(frame_path, canvas)
        print(f"  [{i:02d}/{len(combinations)}] {text} → {os.path.basename(frame_path)}")

        # 为视频准备多帧（每张 QR 重复 FRAMES_PER_QR 帧）
        all_frames.extend([canvas] * FRAMES_PER_QR)

    # ── 合成为视频 ──
    print(f"\n正在合成视频: {VIDEO_PATH}")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video = cv2.VideoWriter(VIDEO_PATH, fourcc, FPS, (QR_SIZE, CANVAS_H))

    for frame in all_frames:
        video.write(frame)

    video.release()
    print(f"视频已生成: {VIDEO_PATH}")
    print(f"  分辨率: {QR_SIZE}×{CANVAS_H}")
    print(f"  帧率: {FPS} FPS")
    print(f"  时长: {len(all_frames) / FPS:.1f} 秒 ({len(combinations)} 种 QR, 各 {FRAME_DURATION:.0f} 秒)")
    print(f"  总帧数: {len(all_frames)}")


if __name__ == "__main__":
    main()
