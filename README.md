# idol-face-orientation-ssm

`pitch` `roll` `yaw` の月次顔向き平均データを、1つのフォルダで管理するための統合作業フォルダです。

## 構成

- `data/`: 入力CSV
- `nonhier_rw_forecast.stan`: 共通Stanモデル
- `face_orientation_common.R`: 共通処理
- `run_analysis.R`: 分析実行用スクリプト
- `plot_forecast.R`: 描画用スクリプト
- `out_rstan_forecast/<axis>/`: 軸ごとの推定結果
- `out_plot/`: 図の出力先

## 使い方

### RStudioで実行

`run_analysis.R` または `plot_forecast.R` をRStudioで開いて、先頭の `cfg <- list(...)` を編集してから `Source` もしくは `Run` で実行します。

分析側でよく触る項目:

- `axis = "pitch"` を `"roll"` や `"yaw"` に変える
- `cutoff`
- `iter`, `warmup`, `chains`

描画側でよく触る項目:

- `axis = "pitch"` を `"roll"` や `"yaw"` に変える
- `what = "lv"` または `"y"`
- `x_start`, `x_end`

### コマンドラインで実行

分析:

```bash
cd idol-face-orientation-ssm
Rscript run_analysis.R --axis pitch
Rscript run_analysis.R --axis roll
Rscript run_analysis.R --axis yaw
```

描画:

```bash
cd idol-face-orientation-ssm
Rscript plot_forecast.R --axis pitch
Rscript plot_forecast.R --axis roll
Rscript plot_forecast.R --axis yaw
```

追加オプションの例:

```bash
Rscript run_analysis.R --axis pitch --cutoff 2026-01-01 --iter 4000 --warmup 2000
Rscript plot_forecast.R --axis pitch --what y --x-start 2010-01-01 --x-end 2026-01-01
```
