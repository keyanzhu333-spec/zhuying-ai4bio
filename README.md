# ZY-AI4Bio

**面向结构生物学与药物发现的 Codex 技能集。** 从蛋白和配体准备，到分子对接、虚拟筛选、相互作用分析、分子动力学与文献查询，ZY-AI4Bio 根据研究任务选择相应技能，并保留输入、参数和结果。

ZY-AI4Bio 是工作流入口，不是新的对接算法或实验验证方法。仓库提供技能说明和脚本；科学软件、模型权重、API 凭据及大型化合物库需另行准备。

## 能做什么

| 研究任务 | 仓库内技能 | 需要另行准备 |
| --- | --- | --- |
| 蛋白-小分子盲对接 | `diffdock` | NVIDIA DiffDock API 凭据 |
| 已知口袋对接、CNN 复评分、互作图 | `gnina-dock` | GNINA；绘图和互作分析需 PyMOL、PLIP |
| 小分子库 GPU 虚拟筛选 | `unidock-vscreen` | UniDock-Pro `udp`、受体和配体 PDBQT |
| 一个小分子对多个蛋白的反向筛选 | `reverse-target-vscreen` | Open Babel、UniDock-Pro、靶点与口袋清单；后续步骤按需配置 |
| 蛋白-蛋白、蛋白-DNA/RNA 对接 | `lightdock` | LightDock 和可用的结构文件 |
| 蛋白互作候选库筛选 | `ppi-vscreen` | LightDock；Chai-1 等复核工具按需配置 |
| 有实验约束的蛋白-核酸对接 | `haddock3-nucleic-acid` | HADDOCK3 |
| 序列驱动的复合物结构预测 | `chai1-complex` | Chai-1 和模型权重 |
| 五类体系的分子动力学与绘图 | `gromacs-md` | GROMACS；配体或金属参数化工具按体系配置 |
| 抗体 Fab 结构预测 | `igfold` | IgFold 和模型权重 |
| 文献 RSS/Atom 跟踪 | `literature-skill` | 可访问的文献源 |

`zy-ai4bio` 是上述技能的统一路由。数据库查询、序列查看和结构查看还可与 Codex 中另行安装的生命科学数据库、文献和查看器技能协同使用；这些插件不随本仓库安装。

## 安装

需要 Python 3 和 Codex。克隆仓库后，在仓库根目录运行：

```bash
git clone https://github.com/keyanzhu333-spec/zhuying-ai4bio.git
cd zhuying-ai4bio
python3 scripts/install_skills.py --list
python3 scripts/install_skills.py --dry-run
python3 scripts/install_skills.py
```

安装器默认复制到 `${CODEX_HOME:-$HOME/.codex}/skills`，遇到已存在的同名技能会停止并保留原文件。也可以用 `--skills zy-ai4bio diffdock gnina-dock` 只安装所需技能，或用 `--target` 指定测试目录。安装技能文件后，还需按上表配置实际计算软件。UniDock-Pro 路径可用 `UNIDOCK_PRO_BIN` 指定，或通过 `--udp` 传入。

## 从研究问题开始

在 Codex 中可以这样描述任务：

> 用 EGFR 蛋白和阿司匹林探索可能的结合构象，保存结构、相互作用图和计算参数。

> 用准备好的受体 PDBQT 和配体库 `ligand_index.txt` 运行 UniDock-Pro 筛选，列出得分靠前的候选物与失败记录。

> 对一个蛋白-DNA 复合物使用实验约束进行 HADDOCK3 对接；检查约束满足情况和界面残基。

> 为蛋白-小分子复合物建立 GROMACS 模拟项目，先检查拓扑并做短程测试，再分析轨迹。

不同任务采用不同的结果目录。UniDock-Pro 筛选项目使用 `inputs/`、`docking/`、`report/`；分子动力学项目使用 `inputs/`、`simulation/`、`analysis/`。详见各技能的 `SKILL.md`。

## 仓库结构

```text
zy-ai4bio/                Codex 工作流路由
skills/                   11 个可独立安装的子技能
scripts/install_skills.py 安装器
docs/                     公众号文案与本地筛选库接入说明
SKILL.md + scripts/       早期 ZYDock 接口，保留兼容
```

大型筛选库的 SDF、PDBQT、SQLite 和原始下载文件不包含在 Git 仓库中。已有本地库可通过 `ligand_index.txt` 接入 UniDock-Pro；数据准备、来源和质量控制见[虚拟筛选库说明](docs/virtual-screening-library.md)。

## 如何解读结果

DiffDock 置信度描述候选构象，GNINA 和 UniDock-Pro 分数用于同一设置下的候选排序。它们不是实验结合亲和力；跨靶点比较需要校准。分子动力学结果依赖力场、参数、采样长度与收敛情况，MM/PBSA 仅在体系和轨迹通过检查时作为可选分析。计算结论应与结构证据、文献及实验结果分别报告。

项目介绍可参考[公众号文案](docs/zy-ai4bio-public-account.md)。仓库代码采用 [MIT License](LICENSE)；外部软件和数据遵循各自许可证。
