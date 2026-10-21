# -*- coding: utf-8 -*-
"""
脚本 2 / 姿态换算
清洗后的吃水 CSV -> 船舶姿态 CSV(02_attitude.csv)

由四个吃水读数反算刚体姿态：
  平均吃水   d_mean   = (艏吃水 + 艉吃水) / 2
  纵倾(量)   trim_m   = 艉吃水 - 艏吃水            (>0 尾倾)
  横倾(量)   heel_m   = 中右吃水 - 中左吃水         (>0 右倾)
  纵倾角     trim_deg = atan(trim_m / L_DRAFT)      [度]
  横倾角     heel_deg = atan(heel_m / B_DRAFT)      [度]
  中拱中垂   hog_sag  = (中左+中右)/2 - (艏+艉)/2    (>0 中拱, 一致性检验用)

L_DRAFT / B_DRAFT 见 config.py，是结果数值的唯一标定量。
"""
import numpy as np
import pandas as pd

import config as C

COLS = ["d_fore", "d_midL", "d_midR", "d_aft"]


def compute_attitude(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # 平均吃水：首尾平均（标准定义）与舯部平均（用于一致性检验）
    out["d_mean"]     = (df["d_fore"] + df["d_aft"]) / 2.0
    out["d_mean_mid"] = (df["d_midL"] + df["d_midR"]) / 2.0

    # 纵倾、横倾（线量，单位 m）
    out["trim_m"] = df["d_aft"]  - df["d_fore"]   # 尾倾为正
    out["heel_m"] = df["d_midR"] - df["d_midL"]   # 右倾为正

    # 姿态角（度）。用 arctan2 保证数值稳健（分母为正常量）
    out["trim_deg"] = np.degrees(np.arctan2(out["trim_m"], C.L_DRAFT))
    out["heel_deg"] = np.degrees(np.arctan2(out["heel_m"], C.B_DRAFT))

    # 中拱(+)/中垂(-)：舯部均值减首尾均值，应接近 0，用作数据可信度检验
    out["hog_sag"] = out["d_mean_mid"] - out["d_mean"]

    return out


def main():
    df = pd.read_csv(C.CLEAN_CSV, parse_dates=["timestamp"])

    atti = compute_attitude(df)

    # 输出列顺序：时间 + 原始吃水 + 派生量
    cols = (["timestamp", "elapsed_s"] + COLS +
            ["d_mean", "d_mean_mid", "hog_sag",
             "trim_m", "heel_m", "trim_deg", "heel_deg"])
    atti = atti[cols]
    atti.to_csv(C.ATTI_CSV, index=False, encoding="utf-8-sig")

    # 控制台摘要，便于快速核对量级与符号
    def rng(col):
        s = atti[col]
        return f"{s.min():+.3f} ~ {s.max():+.3f} (均值 {s.mean():+.3f})"

    print(f"标定间距: L_DRAFT={C.L_DRAFT} m, B_DRAFT={C.B_DRAFT} m")
    print("-" * 56)
    print(f"平均吃水   d_mean   [m]  : {rng('d_mean')}")
    print(f"纵倾量     trim_m   [m]  : {rng('trim_m')}")
    print(f"横倾量     heel_m   [m]  : {rng('heel_m')}")
    print(f"纵倾角     trim_deg [deg]: {rng('trim_deg')}  (+尾倾)")
    print(f"横倾角     heel_deg [deg]: {rng('heel_deg')}  (+右倾)")
    print(f"中拱中垂   hog_sag  [m]  : {rng('hog_sag')}  (应≈0)")
    print("-" * 56)
    print(f"[完成] 已写出 {C.ATTI_CSV}")


if __name__ == "__main__":
    main()
