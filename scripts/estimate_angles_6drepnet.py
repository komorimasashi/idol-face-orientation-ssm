# -*- coding: utf-8 -*-
"""
6DRepNet + MediaPipe FaceMesh で画像を一括処理して yaw/pitch/roll をCSV出力する

使い方:
  (1) 一括モード（親フォルダ直下のサブフォルダを全部処理）
      python estimate_angles_6drepnet.py <親フォルダ> [--gpu-id -1]

  (2) 通常モード（1フォルダだけ処理）
      python estimate_angles_6drepnet.py <画像フォルダ> <出力CSV> [--gpu-id -1]

  (3) 可視化付き（重いので必要時だけ）
      python estimate_angles_6drepnet.py <画像フォルダ> <出力CSV> --vis <可視化フォルダ> [--gpu-id -1]

ポイント:
- roll は符号反転して保存
- 一括モードでは「*_analysis」フォルダは自動でスキップ
- FaceMesh / SixDRepNet は1回だけ作って使い回す（安定＆速い）
- 可視化はデフォルトOFF（メモリ節約）
"""

import os
import glob
import csv
import argparse
import re
import sys
import gc

import cv2
import numpy as np
import mediapipe as mp
from sixdrepnet import SixDRepNet


def natural_sort_key(path: str):
    filename = os.path.basename(path)
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", filename)]


def detect_faces_mediapipe(img_bgr, face_mesh_detector):
    """
    MediaPipe Face Meshで顔を検出し、(x, y, w, h) のlistを返す
    """
    faces = []
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    results = face_mesh_detector.process(img_rgb)

    if results.multi_face_landmarks:
        h, w, _ = img_bgr.shape
        for face_landmarks in results.multi_face_landmarks:
            x_coords = [lm.x for lm in face_landmarks.landmark]
            y_coords = [lm.y for lm in face_landmarks.landmark]

            x_min = int(min(x_coords) * w)
            y_min = int(min(y_coords) * h)
            x_max = int(max(x_coords) * w)
            y_max = int(max(y_coords) * h)

            x_min = max(0, min(w - 1, x_min))
            y_min = max(0, min(h - 1, y_min))
            x_max = max(0, min(w, x_max))
            y_max = max(0, min(h, y_max))

            bw = max(1, x_max - x_min)
            bh = max(1, y_max - y_min)
            faces.append((x_min, y_min, bw, bh))

    return faces


def crop_square(img, x, y, w, h, margin=0.25):
    """顔矩形を少し広めに正方形クロップ"""
    cx, cy = x + w // 2, y + h // 2
    side = int(max(w, h) * (1.0 + margin))

    x1 = max(0, cx - side // 2)
    y1 = max(0, cy - side // 2)
    x2 = min(img.shape[1], x1 + side)
    y2 = min(img.shape[0], y1 + side)

    return img[y1:y2, x1:x2], (x1, y1, x2 - x1, y2 - y1)


def to_float_scalar(x):
    """
    sixdrepnet の predict() が numpy配列で返る場合があるので
    float に落とす（TypeError: unsupported format ... 対策）
    """
    if isinstance(x, (list, tuple)) and len(x) == 1:
        x = x[0]
    if isinstance(x, np.ndarray):
        return float(np.ravel(x)[0])
    return float(x)


def process_one_folder(img_dir, out_csv, model, face_mesh, vis_dir=None):
    """
    1つの画像フォルダに対して角度推定してCSV出力（＋任意で可視化）
    """
    if vis_dir:
        os.makedirs(vis_dir, exist_ok=True)

    rows = [("image", "yaw_deg", "pitch_deg", "roll_deg")]

    exts = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp")
    paths = []
    for e in exts:
        paths.extend(glob.glob(os.path.join(img_dir, e)))

    paths.sort(key=natural_sort_key)

    for p in paths:
        img = cv2.imread(p)
        if img is None:
            print(f"[WARN] 読み込み失敗: {p}")
            continue

        faces = detect_faces_mediapipe(img, face_mesh)

        if faces:
            x, y, w, h = faces[0]
            roi, (rx, ry, rw, rh) = crop_square(img, x, y, w, h, margin=0.25)
            tdx, tdy = x + w // 2, y + h // 2
        else:
            print(f"[INFO] 顔検出失敗、画像全体で推定: {os.path.basename(p)}")
            roi = img
            h_img, w_img = img.shape[:2]
            tdx, tdy = w_img // 2, h_img // 2
            rx = ry = rw = rh = None

        pitch, yaw, roll = model.predict(roi)  # [deg]
        pitch = to_float_scalar(pitch)
        yaw = to_float_scalar(yaw)
        roll = to_float_scalar(roll)

        roll = -roll  # 符号反転

        rows.append((os.path.basename(p), f"{yaw:.4f}", f"{pitch:.4f}", f"{roll:.4f}"))

        if vis_dir:
            # ここが一番メモリ食うので、visが必要なときだけONにする
            vis = img.copy()
            if rx is not None:
                cv2.rectangle(vis, (rx, ry), (rx + rw, ry + rh), (0, 255, 0), 2)
            model.draw_axis(vis, yaw, pitch, roll, tdx=tdx, tdy=tdy, size=120)
            out_path = os.path.join(vis_dir, os.path.basename(p))
            cv2.imwrite(out_path, vis)
            del vis

        # 画像を早めに解放
        del img, roi, faces
        gc.collect()

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"[OK] {img_dir} → {out_csv} 生成完了")


def build_model(gpu_id):
    return SixDRepNet(gpu_id=gpu_id)


def main():
    gpu_id = 0
    if "--gpu-id" in sys.argv:
        i = sys.argv.index("--gpu-id")
        gpu_id = int(sys.argv[i + 1])
        del sys.argv[i:i + 2]

    # 一括モード: python 6DRepNet_GPU2.py <親フォルダ>
    if len(sys.argv) == 2:
        root_dir = sys.argv[1]
        if not os.path.isdir(root_dir):
            print(f"[ERROR] 指定したパスがフォルダではありません: {root_dir}")
            sys.exit(1)

        # 1回だけ作って使い回す
        model = build_model(gpu_id)
        mp_face_mesh = mp.solutions.face_mesh
        with mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=5,
            min_detection_confidence=0.5
        ) as face_mesh:

            # 直下のサブフォルダを列挙
            for name in os.listdir(root_dir):
                subdir = os.path.join(root_dir, name)
                if not os.path.isdir(subdir):
                    continue

                # 重要: 解析用フォルダは処理対象から除外（勝手に増殖して無限ループ気味になるのを防ぐ）
                if name.lower().endswith("_analysis"):
                    continue

                out_csv = os.path.join(root_dir, f"{name}_angle.csv")

                # 一括モードではデフォルト可視化OFF（メモリ節約）
                vis_dir = None

                print(f"\n=== {name} を処理します ===")
                process_one_folder(subdir, out_csv, model=model, face_mesh=face_mesh, vis_dir=vis_dir)

        print("\n[ALL DONE] すべてのサブフォルダを処理しました。")
        return

    # 通常モード: python 6DRepNet_GPU2.py <画像フォルダ> <出力CSV> [--vis visdir]
    ap = argparse.ArgumentParser(description="MediaPipe + 6DRepNet 顔姿勢推定")
    ap.add_argument("img_dir", help="入力画像フォルダ")
    ap.add_argument("out_csv", help="出力CSVパス")
    ap.add_argument("--vis", help="可視化出力フォルダ（任意・重い）")
    ap.add_argument("--gpu-id", type=int, default=gpu_id, help="GPU識別子。CPU実行は -1")
    args = ap.parse_args()

    model = build_model(args.gpu_id)
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=5,
        min_detection_confidence=0.5
    ) as face_mesh:
        process_one_folder(args.img_dir, args.out_csv, model=model, face_mesh=face_mesh, vis_dir=args.vis)


if __name__ == "__main__":
    main()
