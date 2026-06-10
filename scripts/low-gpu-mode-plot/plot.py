import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# =========================
# 1. 数据准备
# =========================

data = {
    "vLLM运行的模型": [
        "Qwen3.6-35B-A3B-FP8",
        "Qwen3-Embedding-0.6B",
        "Qwen3-Reranker-0.6B"
    ],
    "模型静态文件大小(GB)": [35.0, 1.2, 1.2],
    "常驻显存占用(GB)": [42.61, 5.27, 5.28],
    "释放权重后显存占用(GB)": [1.56, 0.71, 0.71],
    "wake_up耗时(s)": [2.45, 0.12, 0.11],
    "sleep耗时(s)": [1.58, 0.09, 0.09]
}

df = pd.DataFrame(data)

df["显存释放量(GB)"] = df["常驻显存占用(GB)"] - df["释放权重后显存占用(GB)"]
df["显存释放比例(%)"] = df["显存释放量(GB)"] / df["常驻显存占用(GB)"] * 100

output_dir = Path("figures")
output_dir.mkdir(exist_ok=True)

# =========================
# 2. 全局绘图设置：调大字号
# =========================

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC"]
plt.rcParams["axes.unicode_minus"] = False

plt.rcParams["font.size"] = 18
plt.rcParams["axes.titlesize"] = 24
plt.rcParams["axes.labelsize"] = 21
plt.rcParams["xtick.labelsize"] = 17
plt.rcParams["ytick.labelsize"] = 18
plt.rcParams["legend.fontsize"] = 18

models = df["vLLM运行的模型"]
x = np.arange(len(models))
width = 0.36

# =========================
# 3. 图1：显存占用对比柱状图
# =========================

fig, ax = plt.subplots(figsize=(14, 8))

bars1 = ax.bar(
    x - width / 2,
    df["常驻显存占用(GB)"],
    width,
    label="常驻显存占用"
)

bars2 = ax.bar(
    x + width / 2,
    df["释放权重后显存占用(GB)"],
    width,
    label="释放权重后显存占用"
)

ax.set_title("低显存模式前后显存占用对比", pad=20)
ax.set_ylabel("显存占用量/GB")
ax.set_xticks(x)
# ax.set_xticklabels(models, rotation=12, ha="right")
ax.set_xticklabels(models)
ax.legend(
    loc="upper right",
    frameon=True,
    fontsize=18
)
ax.grid(axis="y", linestyle="--", alpha=0.4)

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{height:.2f}",
            ha="center",
            va="bottom",
            fontsize=17
        )

plt.tight_layout()
plt.savefig(output_dir / "vram_usage_comparison.png", dpi=300)
plt.savefig(output_dir / "vram_usage_comparison.svg")
plt.show()

# =========================
# 4. 图2：显存释放比例
# =========================

fig, ax = plt.subplots(figsize=(14, 8))

bars = ax.bar(
    x,
    df["显存释放比例(%)"],
    width=0.52
)

ax.set_title("低显存模式显存释放比例", pad=20)
ax.set_ylabel("显存释放比例 / %")
ax.set_xticks(x)
ax.set_xticklabels(models, rotation=12, ha="right")
ax.set_ylim(0, 105)
ax.grid(axis="y", linestyle="--", alpha=0.4)

for bar, value in zip(bars, df["显存释放比例(%)"]):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        value,
        f"{value:.1f}%",
        ha="center",
        va="bottom",
        fontsize=18
    )

plt.tight_layout()
plt.savefig(output_dir / "vram_release_ratio.png", dpi=300)
plt.savefig(output_dir / "vram_release_ratio.svg")
plt.show()

# =========================
# 5. 图3：wake_up 与 sleep 耗时对比
# =========================

fig, ax = plt.subplots(figsize=(14, 8))

bars1 = ax.bar(
    x - width / 2,
    df["wake_up耗时(s)"],
    width,
    label="wake_up 耗时"
)

bars2 = ax.bar(
    x + width / 2,
    df["sleep耗时(s)"],
    width,
    label="sleep 耗时"
)

ax.set_title("模型唤醒与休眠耗时对比", pad=20)
ax.set_ylabel("耗时 / s")
ax.set_xticks(x)
ax.set_xticklabels(models, rotation=12, ha="right")
ax.legend(
    loc="upper right",
    frameon=True,
    fontsize=18
)
ax.grid(axis="y", linestyle="--", alpha=0.4)

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            f"{height:.2f}s",
            ha="center",
            va="bottom",
            fontsize=17
        )

plt.tight_layout()
plt.savefig(output_dir / "sleep_wakeup_time_comparison.png", dpi=300)
plt.savefig(output_dir / "sleep_wakeup_time_comparison.svg")
plt.show()

print(df[[
    "vLLM运行的模型",
    "常驻显存占用(GB)",
    "释放权重后显存占用(GB)",
    "显存释放量(GB)",
    "显存释放比例(%)",
    "wake_up耗时(s)",
    "sleep耗时(s)"
]])
