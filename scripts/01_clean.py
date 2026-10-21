# -*- coding: utf-8 -*-
"""
脚本 1 / 数据清洗
原始 xlsx 吃水读数 -> 清洗后的吃水 CSV(01_cleaned_draft.csv)

清洗步骤：
  1. 读取 Sheet1，统一列名、解析时间戳(UTC)
  2. 去重、按时间排序
  3. 物理越界剔除（吃水 <0 或 >型深 一律置为缺失）
  4. Hampel 滤波剔除孤立毛刺（滑动中位数 ± n·MAD）——保留波浪引起的真实波动
  5. 小空缺按时间线性插值；可选重采样到均匀 1s 网格
  6. 输出清洗结果，并打印每一步剔除/插值的数量，便于人工复核

设计取舍：清洗以“去毛刺、补小空缺”为目标，刻意不做低通平滑，
         以免抹掉船舶对波浪的姿态响应（正是本研究要分析的信号）。
"""
import numpy as np
import pandas as pd

import config as C

COLS = ["d_fore", "d_midL", "d_midR", "d_aft"]
CN_NAME = {"d_fore": "艏吃水", "d_midL": "中左吃水", "d_midR": "中右吃水", "d_aft": "艉吃水"}


def load_raw() -> pd.DataFrame:
    """读取原始 Excel，规范列名与时间戳。"""
    df = pd.read_excel(C.RAW_XLSX, sheet_name="Sheet1", header=0)
    df = df.iloc[:, :5]
    df.columns = ["timestamp"] + COLS
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df[COLS] = df[COLS].apply(pd.to_numeric, errors="coerce")

    # 去重 + 排序：重复时间戳保留首条
    n0 = len(df)
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    if len(df) < n0:
        print(f"[去重] 删除重复时间戳 {n0 - len(df)} 行")
    return df


def drop_out_of_range(df: pd.DataFrame) -> pd.DataFrame:
    """物理越界值置为 NaN（不可能为负、不可能超过型深）。"""
    for c in COLS:
        bad = (df[c] < C.DRAFT_MIN) | (df[c] > C.DRAFT_MAX)
        if bad.any():
            print(f"[越界] {CN_NAME[c]}: 剔除 {int(bad.sum())} 个越界点")
            df.loc[bad, c] = np.nan
    return df


def hampel_filter(s: pd.Series, window: int, nsigma: float):
    """
    Hampel 滤波：以滑动中位数为基准，偏离超过 nsigma·(1.4826·MAD) 判为毛刺，
    将毛刺置为 NaN（后续统一插值）。对孤立尖峰鲁棒，对连续真实波动不敏感。
    """
    med = s.rolling(window, center=True, min_periods=1).median()
    mad = (s - med).abs().rolling(window, center=True, min_periods=1).median()
    threshold = nsigma * 1.4826 * mad
    spike = (s - med).abs() > threshold
    out = s.copy()
    out[spike] = np.nan
    return out, int(spike.sum())


def clean_channels(df: pd.DataFrame) -> pd.DataFrame:
    """逐通道 Hampel 去毛刺。"""
    for c in COLS:
        df[c], n = hampel_filter(df[c], C.HAMPEL_WINDOW, C.HAMPEL_NSIGMA)
        print(f"[毛刺] {CN_NAME[c]}: 剔除 {n} 个尖峰")
    return df


def to_uniform_grid(df: pd.DataFrame) -> pd.DataFrame:
    """重采样到均匀时间网格 + 限长线性插值，便于下游频谱分析。"""
    g = df.set_index("timestamp")
    if C.RESAMPLE_TO_UNIFORM:
        full_idx = pd.date_range(g.index.min(), g.index.max(), freq=C.RESAMPLE_RULE)
        g = g.reindex(g.index.union(full_idx))  # 先并入完整网格
        # 按时间插值，但只填补不超过 INTERP_LIMIT_S 秒的连续空缺
        limit = max(1, int(C.INTERP_LIMIT_S))
        g[COLS] = g[COLS].interpolate(method="time", limit=limit, limit_area="inside")
        g = g.reindex(full_idx)              # 只保留均匀网格点
        g.index.name = "timestamp"
    else:
        g[COLS] = g[COLS].interpolate(method="time",
                                      limit=max(1, int(C.INTERP_LIMIT_S)),
                                      limit_area="inside")
    return g.reset_index()


def main():
    C.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_raw()
    print(f"原始行数: {len(df)}, 时间范围: {df.timestamp.min()} ~ {df.timestamp.max()}")
    print(f"原始缺失: " + ", ".join(f"{CN_NAME[c]}={int(df[c].isna().sum())}" for c in COLS))

    df = drop_out_of_range(df)
    df = clean_channels(df)
    df = to_uniform_grid(df)

    # 增加“距起点秒数”，方便下游做时间轴/FFT
    df["elapsed_s"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()

    remain_na = {CN_NAME[c]: int(df[c].isna().sum()) for c in COLS}
    print(f"清洗后行数: {len(df)} (均匀网格={C.RESAMPLE_TO_UNIFORM})")
    print(f"清洗后剩余缺失(大空缺未插值): {remain_na}")

    df = df[["timestamp", "elapsed_s"] + COLS]
    df.to_csv(C.CLEAN_CSV, index=False, encoding="utf-8-sig")
    print(f"[完成] 已写出 {C.CLEAN_CSV}")


if __name__ == "__main__":
    main()
