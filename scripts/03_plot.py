# -*- coding: utf-8 -*-
"""
脚本 3 / 可视化
读取姿态 CSV(02_attitude.csv)，输出图片到 output/figures/

图 1  四路吃水时间序列
图 2  姿态角时间序列（纵倾角 / 横倾角，双子图）
图 3  姿态角分布直方图
图 4  中拱中垂一致性检验（hog_sag 时间序列）
"""
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

import config as C

# 中文字体（环境已确认有 SimHei / Microsoft YaHei）
matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
matplotlib.rcParams["axes.unicode_minus"] = False


def load() -> pd.DataFrame:
    df = pd.read_csv(C.ATTI_CSV, parse_dates=["timestamp"])
    # 横轴用“距起点分钟”，比绝对 UTC 时间更直观
    df["t_min"] = df["elapsed_s"] / 60.0
    return df


def fig_drafts(df, path):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df.t_min, df.d_fore, lw=0.8, label="艏吃水")
    ax.plot(df.t_min, df.d_midL, lw=0.8, label="中左吃水")
    ax.plot(df.t_min, df.d_midR, lw=0.8, label="中右吃水")
    ax.plot(df.t_min, df.d_aft,  lw=0.8, label="艉吃水")
    ax.set_xlabel("时间 (min)")
    ax.set_ylabel("吃水 (m)")
    ax.set_title("四路吃水读数时间序列（清洗后）")
    ax.legend(ncol=4, loc="upper right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_angles(df, path):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    ax1.plot(df.t_min, df.trim_deg, lw=0.8, color="#1f77b4")
    ax1.axhline(0, color="k", lw=0.6, ls="--")
    ax1.set_ylabel("纵倾角 (°)")
    ax1.set_title("船舶姿态角时间序列  (纵倾角 +尾倾 / 横倾角 +右倾)")
    ax1.grid(alpha=0.3)

    ax2.plot(df.t_min, df.heel_deg, lw=0.8, color="#d62728")
    ax2.axhline(0, color="k", lw=0.6, ls="--")
    ax2.set_ylabel("横倾角 (°)")
    ax2.set_xlabel("时间 (min)")
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_hist(df, path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.hist(df.trim_deg.dropna(), bins=60, color="#1f77b4", alpha=0.85)
    ax1.set_xlabel("纵倾角 (°)"); ax1.set_ylabel("频数"); ax1.set_title("纵倾角分布")
    ax1.grid(alpha=0.3)
    ax2.hist(df.heel_deg.dropna(), bins=60, color="#d62728", alpha=0.85)
    ax2.set_xlabel("横倾角 (°)"); ax2.set_ylabel("频数"); ax2.set_title("横倾角分布")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_hogsag(df, path):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df.t_min, df.hog_sag, lw=0.8, color="#2ca02c")
    ax.axhline(0, color="k", lw=0.6, ls="--")
    ax.set_xlabel("时间 (min)")
    ax.set_ylabel("舯部均值 - 首尾均值 (m)")
    ax.set_title("中拱(+)/中垂(-) 一致性检验（应在 0 附近小幅波动）")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    C.FIG_DIR.mkdir(parents=True, exist_ok=True)
    df = load()
    fig_drafts(df, C.FIG_DIR / "fig1_drafts.png")
    fig_angles(df, C.FIG_DIR / "fig2_attitude_angles.png")
    fig_hist(df,   C.FIG_DIR / "fig3_angle_hist.png")
    fig_hogsag(df, C.FIG_DIR / "fig4_hog_sag_check.png")
    print(f"[完成] 4 张图已写入 {C.FIG_DIR}")


if __name__ == "__main__":
    main()
