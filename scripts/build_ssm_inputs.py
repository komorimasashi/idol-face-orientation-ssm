# -*- coding: utf-8 -*-
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd


def normalize_group_name(raw: str):
    if raw is None or pd.isna(raw):
        return None

    s = str(raw).strip().lower()
    s = s.replace("sut48", "stu48")
    s = s.replace("hinatazka46", "hinatazaka46")

    mapping = {
        "akb48": "AKB48",
        "hkt48": "HKT48",
        "ngt48": "NGT48",
        "nmb48": "NMB48",
        "ske48": "SKE48",
        "stu48": "STU48",
        "nogizaka": "Nogizaka46",
        "nogizaka46": "Nogizaka46",
        "hinatazaka": "Hinatazaka46",
        "hinatazaka46": "Hinatazaka46",
        "keyakizaka": "Sakurazaka46",
        "keyakizaka46": "Sakurazaka46",
        "sakurazaka": "Sakurazaka46",
        "sakurazaka46": "Sakurazaka46",
    }
    return mapping.get(s, str(raw).strip())


def parse_group_and_date_from_image(image_name: str):
    """
    例:
      AKB48_20110119 (1).jpg  -> group=AKB48, date=2011-01-19
      Nogizaka46_20140222.jpg -> group=Nogizaka46, date=2014-02-22
    """
    s = str(image_name)

    # 拡張子とフォルダを除外
    s = Path(s).name

    # group は最初の "_" より前を基本とする
    if "_" in s:
        group = s.split("_", 1)[0]
    else:
        group = None

    # 8桁日付を探す（YYYYMMDD）
    m = re.search(r"(19|20)\d{2}[01]\d[0-3]\d", s)
    date = None
    if m:
        ymd = m.group(0)
        date = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"

    return group, date


def standard_error(x: pd.Series) -> float:
    x = pd.to_numeric(x, errors="coerce").dropna()
    n = len(x)
    if n <= 1:
        return np.nan
    return float(x.std(ddof=1) / np.sqrt(n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", default="data/combined/all_groups_combined.csv",
                    help="入力CSV（画像1枚ごとの yaw/pitch/roll が入っている）")
    ap.add_argument("--out_dir", default="data/ssm_inputs", help="出力先フォルダ")
    ap.add_argument("--time_mode", choices=["date", "year_month"], default="date",
                    help="date: YYYY-MM-DD / year_month: YYYY-MM（同月で集計）")
    ap.add_argument("--min_n", type=int, default=2, help="1点あたり最低枚数（未満は除外）")
    args = ap.parse_args()

    in_path = Path(args.in_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(in_path)

    # 列名の候補（あなたのCSVに合わせる）
    # 期待: image, yaw_deg, pitch_deg, roll_deg, Group（Groupは使わなくてもOK）
    col_image = None
    for c in df.columns:
        if c.lower() in ["image", "img", "filename", "file", "path"]:
            col_image = c
            break
    if col_image is None:
        raise ValueError(f"画像名列が見つかりません。列一覧: {list(df.columns)}")

    # 角度列
    def pick_angle(*names):
        for name in names:
            for c in df.columns:
                if c.lower() == name.lower():
                    return c
        return None

    col_yaw = pick_angle("yaw_deg", "yaw", "mean_yaw")
    col_pitch = pick_angle("pitch_deg", "pitch", "mean_pitch")
    col_roll = pick_angle("roll_deg", "roll", "mean_roll")

    missing = [k for k, v in [
        ("yaw", col_yaw), ("pitch", col_pitch), ("roll", col_roll)] if v is None]
    if missing:
        raise ValueError(f"角度列が不足しています: {missing} / 列一覧: {list(df.columns)}")

    # group/date を image から作る
    parsed = df[col_image].apply(parse_group_and_date_from_image)
    parsed_group = parsed.apply(lambda t: t[0])
    df["date_parsed"] = parsed.apply(lambda t: t[1])

    if "Group" in df.columns:
        df["group_parsed"] = df["Group"].apply(normalize_group_name)
    else:
        df["group_parsed"] = parsed_group.apply(normalize_group_name)

    # パースできない行は落とす
    before = len(df)
    df = df.dropna(subset=["group_parsed", "date_parsed"]).copy()
    dropped = before - len(df)
    if dropped > 0:
        print(f"[INFO] group/date をパースできず {dropped} 行を除外")

    # time 列を作る
    if args.time_mode == "date":
        df["time"] = df["date_parsed"]
    else:
        # YYYY-MM に丸める
        dt = pd.to_datetime(df["date_parsed"], errors="coerce")
        df["time"] = dt.dt.strftime("%Y-%m")

    # 数値化
    for c in [col_yaw, col_pitch, col_roll]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # group x time で集計（平均＋標準誤差）
    gcols = ["group_parsed", "time"]

    def agg_one(angle_col: str, axis_name: str):
        agg = df.groupby(gcols)[angle_col].agg(
            y="mean",
            n="count",
            se=standard_error,
        ).reset_index()

        # n が少なすぎる点は落とす（seが不安定＆SSMも意味が薄い）
        agg = agg[agg["n"] >= args.min_n].copy()

        # se が NaN のところは、同軸の se の中央値で埋める（run_ssm.py 側でも補正するが、ここでも整える）
        if agg["se"].isna().any():
            med = float(np.nanmedian(agg["se"].to_numpy()))
            if not np.isfinite(med):
                med = 1.0
            agg["se"] = agg["se"].fillna(med)

        out = agg.rename(columns={"group_parsed": "group"})[
            ["group", "time", "y", "se"]]
        out_path = out_dir / f"ssm_input_{axis_name}.csv"
        out.to_csv(out_path, index=False)
        print("[OK] wrote", out_path.resolve(), "rows=", len(out))

    agg_one(col_pitch, "pitch")
    agg_one(col_yaw, "yaw")
    agg_one(col_roll, "roll")


if __name__ == "__main__":
    main()
