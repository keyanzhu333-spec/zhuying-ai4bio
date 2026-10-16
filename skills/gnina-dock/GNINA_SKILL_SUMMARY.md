# GNINA-PyMOL-PLIP Skill 远程部署摘要

## 这个 skill 做什么

这是一个结构基础分子对接工作流：

1. 使用 GNINA 对受体和配体进行对接，并提取 `minimizedAffinity`、`CNNscore`、`CNNaffinity`。
2. 按 CNN 评分和经验评分整理候选 pose，输出 CSV/JSON 排名结果。
3. 使用 PyMOL 合并受体与选定 pose，生成复合物 PDB、PyMOL 会话和整体图。
4. 使用 PLIP 分析氢键、疏水作用、π-堆积、盐桥、卤键、金属接触等。
5. 生成结合位点局部图：整体 cartoon 透明显示，接触残基用 sticks 显示，并标出相互作用。
6. 输出日志、参数清单和 Markdown 结果报告，便于复现和审阅。

## 远程服务器需要的环境

远程 Linux 服务器需要自行准备以下命令：

```text
gnina
pymol
plip
python
rdkit
```

如果使用 GPU，还需要兼容的 NVIDIA 驱动、CUDA 运行环境；GPU 不可用时可以使用 GNINA CPU 模式完成验证。

本压缩包不包含 Windows 运行时和大型二进制文件，避免把约 800 MB 的本地运行时错误复制到 Linux 服务器。远程服务器建议通过 conda、系统包管理器或管理员提供的模块加载环境安装依赖。

## 上传到远程服务器后

```bash
unzip gnina-dock_remote_skill_*.zip
cd gnina-dock
chmod +x scripts/*.py
python scripts/run_gnina_pipeline.py \
  --receptor receptor.pdb \
  --ligand ligand.sdf \
  --center 12.4 -3.1 8.7 \
  --size 20 20 20 \
  --out-dir docking \
  --gnina-bin /opt/gnina/gnina \
  --pymol-bin pymol \
  --plip-bin plip \
  --cnn-scoring rescore \
  --exhaustiveness 16 \
  --num-modes 10 \
  --seed 42 \
  --run-pymol --run-plip
```

如果有共晶配体，优先使用自动盒子：

```bash
--autobox-ligand crystal_ligand.sdf --autobox-add 4
```

## 主要输出

```text
docking/
├── docked.sdf
├── ranking.csv
├── ranking.json
├── manifest.json
├── gnina.log
├── complex_pose1.pdb
├── complex_pose1.pse
├── complex_pose1.png
├── plip_pose1/
│   ├── complex_pose1_report.txt
│   ├── complex_pose1_report.xml
│   ├── plip_pose1_interactions.png
│   └── plip_pose1_interactions.pse
└── report.md
```

把 `docking/` 下载回本地后，可以用本地 GUI 查看 PNG、Markdown 报告和 PyMOL 会话。

## 结果解释原则

- `CNNscore` 是 pose 可信度/合理性指标，不是结合亲和力。
- `CNNaffinity` 是模型预测的类亲和力分数，不等于实验 `Kd` 或 `ΔG`。
- `minimizedAffinity` 只适合在相同设置、相同准备流程下进行相对比较。
- PLIP 检测到的接触需要结合质子化状态、配体互变异构体、金属和水分子进行人工复核。
- 单个 docking pose 不能直接证明分子具有生物活性。

## 与本地软件的关系

本 skill 是远程计算流程；本地 `GNINA Dock Studio` 是图形界面。推荐使用“本地界面提交任务 → 远程服务器计算 → 下载结果到本地查看”的方式。Windows 专用的 GUI 和 bundled runtime 不需要上传到远程 Linux 服务器。
