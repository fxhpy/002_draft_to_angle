# 002_draft_to_angle：船舶吃水数据清洗与姿态角换算

将四路吃水测量值整理为时间序列，计算纵倾角、横倾角及相关差值，并生成检查图。处理流程由 `scripts/` 中的三个脚本组成：

```text
draft.xlsx → 数据清洗 → 01_cleaned_draft.csv
                         ↓
                     姿态角换算 → 02_attitude.csv → 4 张检查图
```

本项目处理吃水数据，不包含航向/波浪匹配、相机运动计算或视频处理。

## 目录与文件

| 路径 | 用途 |
| --- | --- |
| `scripts/config.py` | 数据路径、船舶尺寸、测点间距和清洗参数 |
| `scripts/01_clean.py` | 读取 Excel、去重、剔除越界值和毛刺、插值及生成时间网格 |
| `scripts/02_convert.py` | 由四路吃水计算平均吃水、纵倾/横倾差值和角度 |
| `scripts/03_plot.py` | 绘制吃水、姿态角、角度直方图和中部/首尾差值图 |
| `parameters.txt` | 船舶尺寸及资料说明；脚本不会自动读取 |
| `camera/` | 随项目保留的相机标定文件；当前三个脚本未使用 |
| `requirements.txt` | Python 依赖 |
| `draft.xlsx` | 本地原始数据，需自行准备，不上传 GitHub |
| `output/` | 运行生成的 CSV 和图片，不上传 GitHub |

原始压缩包和已解压的本地数据保留不动。仓库忽略 Excel、CSV、缓存、虚拟环境和运行输出；从 GitHub 克隆代码后，需要另行准备输入数据。

## 安装依赖

在项目根目录打开 PowerShell，创建 Python 环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

依赖包括 NumPy、pandas、openpyxl 和 Matplotlib。`openpyxl` 用于读取 `.xlsx` 文件。绘图脚本优先使用 SimHei / Microsoft YaHei 字体；环境缺少这些字体时，中文可能无法正常显示。

## 输入数据

将原始文件放在项目根目录，命名为 `draft.xlsx`，或修改 `scripts/config.py` 中的 `RAW_XLSX`。

脚本读取工作表 **`Sheet1`**，将第一行作为表头，只取前五列，并按以下固定顺序重新命名，因此输入列的顺序必须正确：

| 列序号 | 输出列名 | 含义 | 单位/约定 |
| --- | --- | --- | --- |
| 1 | `timestamp` | 测量时间 | 可由 pandas 解析的时间；统一转为 UTC |
| 2 | `d_fore` | 艏吃水 | m |
| 3 | `d_midL` | 中左吃水 | m |
| 4 | `d_midR` | 中右吃水 | m |
| 5 | `d_aft` | 艉吃水 | m |

不带时区的输入时间会直接按 UTC 解释。若原始记录是北京时间等本地时间，需先正确转换，脚本不会自动识别原始时区。吃水列中无法解析的数值变为缺失值；无法解析的时间戳会使读取失败。

## 配置

统一修改 `scripts/config.py`，无需逐个修改处理脚本。

| 参数 | 当前默认值 | 作用 |
| --- | --- | --- |
| `L_DRAFT` | `206.55` m | 艏、艉吃水测点的纵向间距，默认取垂线间长 |
| `B_DRAFT` | `34.80` m | 中左、中右测点的横向间距，默认取型宽 |
| `DRAFT_MIN` / `DRAFT_MAX` | `0.0` / `18.0` m | 允许的吃水范围，超出范围置为缺失 |
| `HAMPEL_WINDOW` | `11` 个样本 | 滑动中位数/MAD 窗口大小 |
| `HAMPEL_NSIGMA` | `4.0` | 毛刺判断阈值系数 |
| `RESAMPLE_TO_UNIFORM` | `True` | 从首个时间戳开始生成均匀时间网格 |
| `RESAMPLE_RULE` | `"1s"` | 目标网格间隔 |
| `INTERP_LIMIT_S` | `5` | 传入 pandas 插值 `limit` 的值，见下方限制 |

角度大小取决于实际测点间距。当前配置假定艏、艉测点间距等于垂线间长，左右测点间距等于型宽；换船或更换测点后必须核对这两项。

## 运行顺序

在项目根目录依次执行，前一步成功后再执行下一步：

```powershell
.\.venv\Scripts\python.exe scripts\01_clean.py
.\.venv\Scripts\python.exe scripts\02_convert.py
.\.venv\Scripts\python.exe scripts\03_plot.py
```

1. **清洗**：按时间戳去重（保留首条）并排序，将越界值和按滑动中位数/MAD 判定的毛刺置为缺失，再进行时间插值；默认输出均匀 1 秒时间网格。`elapsed_s` 为距首条记录的秒数。
2. **换算**：读取清洗结果，保留时间与原始吃水列，增加下列派生量。
3. **绘图**：读取姿态结果，在 `output/figures/` 中保存四张 PNG。

### 换算结果与符号

以下公式均对应当前代码实现，`atan2` 的结果转换为度：

| 输出列 | 计算方式 | 单位/符号 |
| --- | --- | --- |
| `d_mean` | `(d_fore + d_aft) / 2` | m，首尾平均 |
| `d_mean_mid` | `(d_midL + d_midR) / 2` | m，中部平均 |
| `trim_m` | `d_aft - d_fore` | m，正值表示尾倾 |
| `heel_m` | `d_midR - d_midL` | m，正值表示右倾 |
| `trim_deg` | `degrees(atan2(trim_m, L_DRAFT))` | 度，正值表示尾倾 |
| `heel_deg` | `degrees(atan2(heel_m, B_DRAFT))` | 度，正值表示右倾 |
| `hog_sag` | `d_mean_mid - d_mean` | m，中部与首尾平均吃水之差；代码标注正值为“中拱” |

`hog_sag` 在本项目中是用于比较测点一致性的差值，不能仅凭该列认定船体变形原因。

### 输出文件

```text
output/
  01_cleaned_draft.csv
  02_attitude.csv
  figures/
    fig1_drafts.png
    fig2_attitude_angles.png
    fig3_angle_hist.png
    fig4_hog_sag_check.png
```

两个 CSV 均使用 UTF-8 BOM 编码。脚本重复执行时会覆盖同名结果。第一步创建 `output/`，第三步创建图片目录。

## 当前实现的边界

- 清洗不做低通平滑，也不提供频谱、六自由度运动或升沉计算。
- `INTERP_LIMIT_S` 虽然以 `_S` 命名，实际控制的是插值允许连续填充的**缺失条数**。在原始时间戳与均匀网格合并后的索引上，它不严格等于物理秒数；较长空缺也可能被部分填充。调整采样间隔后应复核结果，不能把它当作严格的最长缺测时长限制。
- 插值不会填充时间序列首尾外侧的缺失值。仍有缺失的读数会继续传递到角度结果，需结合控制台统计和图表检查。
- Hampel 阈值依赖滑动 MAD；局部 MAD 为零时，偏离局部中位数的点也可能被剔除，参数需按数据特性复核。
- 运行需要非空且包含有效时间的数据。代码没有提供命令行参数，所有配置通过 `scripts/config.py` 修改。
