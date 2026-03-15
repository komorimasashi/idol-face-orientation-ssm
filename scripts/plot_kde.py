import os
import glob
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm

mpl.rcParams["pdf.fonttype"] = 42


# =========================
# Font
# =========================
def set_japanese_font():
    candidates = ["Meiryo", "Yu Gothic", "Yu Gothic UI",
                  "MS Gothic", "MS PGothic", "Noto Sans CJK JP"]
    installed = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            mpl.rcParams["font.family"] = name
            return name
    return None


# =========================
# Group normalization
# =========================
def normalize_group_name(raw: str) -> str | None:
    if raw is None:
        return None

    s = str(raw).strip()
    s_low = s.lower()

    # ---- 誤記吸収 ----
    s_low = s_low.replace("sut48", "stu48")
    s_low = s_low.replace("hinatazka46", "hinatazaka46")

    # ---- 46なし補完 ----
    if s_low == "nogizaka":
        s_low = "nogizaka46"
    if s_low == "sakurazaka":
        s_low = "sakurazaka46"
    if s_low == "hinatazaka":
        s_low = "hinatazaka46"

    mapping = {
        "akb48": "AKB48",
        "hkt48": "HKT48",
        "ngt48": "NGT48",
        "nmb48": "NMB48",
        "ske48": "SKE48",
        "stu48": "STU48",

        "nogizaka46": "乃木坂46",
        "sakurazaka46": "櫻坂46",
        "hinatazaka46": "日向坂46",

        "keyakizaka46+sakurazaka46": "櫻坂46",
        "keyakizaka46+hinatazaka46": "日向坂46",
    }

    return mapping.get(s_low, s)


def group_name_from_filename(path: str) -> str:
    name = os.path.splitext(os.path.basename(path))[0]
    name = name.replace("data_", "")
    return normalize_group_name(name)


def group_name_from_image_value(image_value: str) -> str | None:
    if image_value is None:
        return None
    s = os.path.basename(str(image_value))
    if "_" not in s:
        return None
    raw_group = s.split("_", 1)[0].strip()
    return normalize_group_name(raw_group)


# =========================
# Column detection
# =========================
def detect_col(df: pd.DataFrame, axis: str) -> str:
    axis = axis.lower()
    for c in df.columns:
        cl = str(c).lower()
        if cl == axis or cl == f"{axis}_deg":
            return c
    for c in df.columns:
        if axis in str(c).lower():
            return c
    raise ValueError(f"{axis} の列が見つかりません: {list(df.columns)}")


def list_csvs(data_dir: str, csvs_arg: str | None):
    if csvs_arg:
        parts = [t.strip() for t in csvs_arg.split(",") if t.strip()]
        return [os.path.join(data_dir, p) if not os.path.isabs(p) else p for p in parts]
    return sorted(glob.glob(os.path.join(data_dir, "data_*.csv")))


# =========================
# Tick helpers
# =========================
def floor_to_step(x: float, step: float) -> float:
    return float(np.floor(x / step) * step)


def ceil_to_step(x: float, step: float) -> float:
    return float(np.ceil(x / step) * step)


def fixed_xlim_ticks(xmin: float, xmax: float, step: float):
    lo, hi = floor_to_step(xmin, step), ceil_to_step(xmax, step)
    return lo, hi, np.arange(lo, hi + step, step)


def auto_xlim_ticks(values: np.ndarray, step: float, symmetric: bool, pad_steps: int):
    values = values[np.isfinite(values)]
    vmin, vmax = float(np.min(values)), float(np.max(values))
    if symmetric:
        m = max(abs(vmin), abs(vmax))
        hi = ceil_to_step(m, step) + pad_steps * step
        lo = -hi
    else:
        lo = floor_to_step(vmin, step) - pad_steps * step
        hi = ceil_to_step(vmax, step) + pad_steps * step
    return lo, hi, np.arange(lo, hi + step, step)


# =========================
# KDE
# =========================
def kde_1d_sklearn(x: np.ndarray, grid: np.ndarray, bandwidth: float):
    from sklearn.neighbors import KernelDensity
    x = x[np.isfinite(x)]
    if x.size < 3:
        return None
    kde = KernelDensity(kernel="gaussian", bandwidth=float(bandwidth)).fit(x.reshape(-1, 1))
    return np.exp(kde.score_samples(grid.reshape(-1, 1)))


def make_kde_overlay_plot(
    all_df, group_order, axis, out_path,
    tick_step, pad_steps, symmetric,
    x_min, x_max,
    bandwidth, n_grid, normalize, fill, fill_alpha,
    line_alpha, lw, hide_yticks, show_grid_x,
    legend, legend_loc, legend_ncol, legend_fontsize,
):
    labels = [g for g in group_order if (all_df["group"] == g).any()]
    if not labels:
        print("[WARN] 描画対象グループなし:", axis)
        return

    all_vals = all_df.loc[all_df["group"].isin(labels), axis].astype(float).to_numpy()
    if (x_min is not None) and (x_max is not None):
        lo, hi, xticks = fixed_xlim_ticks(x_min, x_max, tick_step)
    else:
        lo, hi, xticks = auto_xlim_ticks(all_vals, tick_step, symmetric, pad_steps)

    grid = np.linspace(lo, hi, int(n_grid))
    fig, ax = plt.subplots(figsize=(10.0, 4.0))
    ax.axhline(0, color="black", linewidth=0.8)

    curves = []
    max_y = 0.0
    for g in labels:
        x = all_df.loc[all_df["group"] == g, axis].astype(float).to_numpy()
        x = x[np.isfinite(x)]
        if x.size < 3:
            continue
        y = kde_1d_sklearn(x, grid, bandwidth)
        if y is None:
            continue
        max_y = max(max_y, float(np.max(y)))
        curves.append((g, y))

    legend_label_map = {
        "櫻坂46": "欅坂46→櫻坂46",
        "日向坂46": "けやき坂46→日向坂46",
    }

    for g, y in curves:
        y2 = (y / max_y) if (normalize and max_y > 0) else y
        legend_label = legend_label_map.get(g, g)
        line, = ax.plot(grid, y2, linewidth=lw, alpha=line_alpha, label=str(legend_label))
        if fill:
            ax.fill_between(grid, 0, y2, color=line.get_color(), alpha=fill_alpha)

    ax.set_xlabel("角度（deg）")
    ax.set_ylabel("密度（正規化）" if normalize else "密度")
    ax.set_xlim(lo, hi)
    ax.set_xticks(xticks)

    if hide_yticks:
        ax.set_yticks([])
    if show_grid_x:
        ax.grid(True, axis="x", linestyle="--", alpha=0.3)
    if legend and curves:
        ax.legend(loc=legend_loc, frameon=False,
                  fontsize=legend_fontsize, ncol=legend_ncol)

    fig.tight_layout()
    final_out = os.path.splitext(out_path)[0] + ".pdf"
    os.makedirs(os.path.dirname(final_out) or ".", exist_ok=True)
    fig.savefig(final_out, format="pdf")
    plt.close(fig)
    print("[OK] saved:", final_out)


# =========================
# Main
# =========================
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_dir", default="data/angle_estimates")
    parser.add_argument("--csvs", default=None)
    parser.add_argument("--combined_csv", default=None)
    parser.add_argument("--image_col", default="image")
    parser.add_argument("--group_col", default=None)

    parser.add_argument("--out_dir", default="results/kde")
    parser.add_argument("--prefix", default="kde_")

    parser.add_argument("--axes", default="yaw,pitch,roll")
    parser.add_argument("--tick_step", type=float, default=10.0)
    parser.add_argument("--pad_steps", type=int, default=1)
    parser.add_argument("--symmetric", default="yaw,roll")
    parser.add_argument("--no_symmetric", action="store_true")

    parser.add_argument("--yaw_min", type=float, default=None)
    parser.add_argument("--yaw_max", type=float, default=None)
    parser.add_argument("--pitch_min", type=float, default=None)
    parser.add_argument("--pitch_max", type=float, default=None)
    parser.add_argument("--roll_min", type=float, default=None)
    parser.add_argument("--roll_max", type=float, default=None)

    parser.add_argument("--bandwidth", type=float, default=1.2)
    parser.add_argument("--n_grid", type=int, default=500)
    parser.add_argument("--no_normalize", action="store_true")

    parser.add_argument("--fill", action="store_true")
    parser.add_argument("--fill_alpha", type=float, default=0.15)
    parser.add_argument("--line_alpha", type=float, default=0.9)
    parser.add_argument("--lw", type=float, default=1.5)
    parser.add_argument("--hide_yticks", action="store_true")
    parser.add_argument("--no_grid_x", action="store_true")
    parser.add_argument("--legend", action="store_true")
    parser.add_argument("--legend_loc", default="upper right")
    parser.add_argument("--legend_ncol", type=int, default=3)
    parser.add_argument("--legend_fontsize", type=float, default=9.0)

    args = parser.parse_args()
    set_japanese_font()

    allowed_groups = ["乃木坂46", "日向坂46", "櫻坂46",
                      "AKB48", "HKT48", "SKE48",
                      "NMB48", "NGT48", "STU48"]

    dfs = []

    if args.combined_csv:
        path = args.combined_csv
        if not os.path.isabs(path):
            path = os.path.join(args.data_dir, path)

        df = pd.read_csv(path)

        cols = {a: detect_col(df, a) for a in ["yaw", "pitch", "roll"]}
        tmp = df[[cols["yaw"], cols["pitch"], cols["roll"]]].copy()
        tmp.columns = ["yaw", "pitch", "roll"]

        if args.group_col and args.group_col in df.columns:
            g = df[args.group_col].map(normalize_group_name)
        else:
            g = df[args.image_col].map(group_name_from_image_value)

        tmp["group"] = g
        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna()
        tmp = tmp[tmp["group"].isin(allowed_groups)]

        if len(tmp) > 0:
            dfs.append(tmp)

    else:
        csv_paths = list_csvs(args.data_dir, args.csvs)
        for path in csv_paths:
            try:
                df = pd.read_csv(path)
                gname = group_name_from_filename(path)
                if gname not in allowed_groups:
                    continue

                cols = {a: detect_col(df, a) for a in ["yaw", "pitch", "roll"]}
                tmp = df[list(cols.values())].copy()
                tmp.columns = ["yaw", "pitch", "roll"]
                tmp["group"] = gname
                tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna()
                dfs.append(tmp)
            except Exception:
                continue

    if not dfs:
        print("[WARN] 有効なデータがありません")
        return

    all_df = pd.concat(dfs, ignore_index=True)

    sym_set = set() if args.no_symmetric else {a.strip().lower() for a in args.symmetric.split(",")}
    limits = {
        "yaw": (args.yaw_min, args.yaw_max),
        "pitch": (args.pitch_min, args.pitch_max),
        "roll": (args.roll_min, args.roll_max),
    }

    for axname in [a.strip().lower() for a in args.axes.split(",")]:
        if axname not in limits:
            continue
        make_kde_overlay_plot(
            all_df,
            allowed_groups,
            axname,
            os.path.join(args.out_dir, f"{args.prefix}{axname}.pdf"),
            args.tick_step,
            args.pad_steps,
            (axname in sym_set),
            limits[axname][0],
            limits[axname][1],
            args.bandwidth,
            args.n_grid,
            (not args.no_normalize),
            args.fill,
            args.fill_alpha,
            args.line_alpha,
            args.lw,
            args.hide_yticks,
            (not args.no_grid_x),
            args.legend,
            args.legend_loc,
            args.legend_ncol,
            args.legend_fontsize,
        )


if __name__ == "__main__":
    main()
