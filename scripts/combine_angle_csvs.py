from pathlib import Path
import argparse

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        default="data/angle_estimates",
        help="グループ別の angle CSV を入れたディレクトリ",
    )
    parser.add_argument(
        "--output",
        default="data/combined/all_groups_combined.csv",
        help="結合後CSVの出力先",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)
    csv_files = sorted(input_dir.glob("*/*_angle.csv"))

    if not csv_files:
        raise FileNotFoundError(f"角度CSVが見つかりません: {input_dir}")

    frames = []
    for csv_path in csv_files:
        df = pd.read_csv(csv_path)
        df["Group"] = csv_path.parent.name
        df["source_csv"] = csv_path.name
        frames.append(df)

    combined_df = pd.concat(frames, axis=0, ignore_index=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"[OK] wrote {output_path}")
    print(f"[INFO] files={len(csv_files)} rows={len(combined_df)}")


if __name__ == "__main__":
    main()
