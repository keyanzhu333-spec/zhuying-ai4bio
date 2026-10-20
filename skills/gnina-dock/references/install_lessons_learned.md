# WSL2 安装与对接实战经验（2026-10 实测）

本文件记录在 Windows + WSL2 环境下安装 GNINA 工具链并完成对接/出图时遇到的实际问题与解决方案，供后续复用。

## 一、环境准备：WSL2 优先，不要跨 /mnt/c 装包

### 关键教训：pip 装大包必须用 Linux 原生文件系统

在 `/mnt/c/...`（Windows 文件系统）上执行 `pip install` 会出两类问题：

1. **哈希校验失败**：下载的 wheel 文件哈希与 PyPI 声明不一致（如 `rdkit` 37MB wheel 报 `THESE PACKAGES DO NOT MATCH THE HASHES`）。原因是跨文件系统写入容易损坏。
2. **速度极慢**：RDKit/SciPy 等大包解压到 Windows 盘要几分钟甚至更久。

**正确做法**：在 WSL 的 Linux 原生文件系统（`~/` 下）建工作区，用 `pip install --user` 安装：

```bash
# WSL 内
mkdir -p ~/gnina_work && cd ~/gnina_work
python3 -m pip install --user rdkit openbabel==3.2.1 meeko==0.7.1
python3 -m pip install --user pymol-open-source-whl==3.2.0.2
python3 -m pip install --user plip==3.0.1
```

GNINA 二进制（Linux ELF）可以直接从 Windows 侧下载后放任意位置，WSL 里 `chmod +x` 后即可运行。

### WSL 探测要点

- `wsl.exe` 若被 WorkBuddy「程序黑名单」拦截，需要在「设置 → 命令安全 → 程序黑名单」移除。
- 判断发行版是否已初始化：看 `~AppData/Local/Packages/<发行版>/LocalState/ext4.vhdx` 是否存在且体积较大。
- WSL 内用 `python3 --version` 确认版本（本机为 3.10.12），这决定了 wheel 的 ABI 选择。

## 二、install_gnina_runtime.py 的版本清单有坑

仓库自带安装脚本 `install_gnina_runtime.py` 的 `CORE_PACKAGES` 里有两个版本在 Python 3.10 下装不上：

| 包 | 脚本写死版本 | 问题 |
|---|---|---|
| `scipy` | `1.18.0` | 该版本无 cp310 wheel（仅支持 Python 3.12+） |
| `prody` | `2.6.1` | PyPI 上该版本的 sdist 元数据名称是 "unknown"，pip 拒绝安装 |

**关键结论**：`scipy` 和 `prody` 对「跑 GNINA 对接 + PyMOL 出图 + PLIP 分析」**完全不需要**，直接跳过即可。真正需要的只有：

- **GNINA**（对接引擎，Linux 二进制）
- **RDKit**（配体 3D 生成 + 打分解析）
- **openbabel**（格式转换）
- **PyMOL**（出图）
- **PLIP**（相互作用分析，真实依赖只有 openbabel + lxml + numpy）

所以不要跑完整安装脚本，按需手动装上面几个包即可，几分钟搞定。

## 三、GNINA 使用要点

### SMILES 输入会报 tree.h(185) 错误

GNINA 1.0.3（2023 构建版）对 `-l aspirin.smi` 的 SMILES 输入支持有 bug，会报：

```
An internal error occurred in /root/gnina/gninasrc/lib/tree.h(185).
```

**正确做法**：先用 RDKit 从 SMILES 生成 3D SDF，再喂给 GNINA：

```python
from rdkit import Chem
from rdkit.Chem import AllChem
mol = Chem.MolFromSmiles('CC(=O)Oc1ccccc1C(=O)O')
mol = Chem.AddHs(mol)
AllChem.EmbedMolecule(mol, randomSeed=42)
AllChem.MMFFOptimizeMolecule(mol)
Chem.SDWriter('aspirin.sdf').write(mol)
```

### 参考配体格式

`--autobox_ligand` 需要 SDF/MOL2/PDBQT 格式（不是 PDB），否则也会报 tree.h 错误。更稳妥的做法是**用 `--center X Y Z --size SX SY SZ` 显式指定口袋**——从共晶配体算质心作中心即可。

### CPU 模式

无 NVIDIA GPU 时加 `--no_gpu`，避免 CUDA 初始化段错误（WSL 下尤其容易 exit 139）。

## 四、PyMOL 无头出图要点

### 无头渲染命令

```bash
python3 -m pymol -cq render.pml
```

### 白底 vs 透明底

`set ray_opaque_background, 0` 是透明背景，在图片查看器里显示为**黑底**；要白底必须用 `set ray_opaque_background, 1`。

### label 语法坑

`cmd.label(sel, '"TEXT"')` 的第二个参数是**表达式**（通常是引号包裹的文本），不是选择串。写成选择串会报 `SyntaxError`。

```python
# 正确
cmd.label('res_745', '"LYS 745"')
# 错误
cmd.label('res_745', 'chain A and resi 745 and name CA')
```

## 五、PLIP 分析要点

### 单独安装（不要被安装脚本连累）

PLIP 3.0.1 真实依赖只有 `openbabel>=3.2.0` + `lxml>=4.2.1` + `numpy`，单独装一次就成功：

```bash
python3 -m pip install --user plip==3.0.1
```

### 调用与输出

```bash
# -y 生成 PyMOL 会话 .pse（自带相互作用虚线），--txt --xml 生成文本/XML 报告
python3 -m plip.plipcmd -f complex.pdb -o out_dir -y --txt --xml
```

- 报告文件是 `<结构名>_report.txt`（如 `complex_report.txt`），不是固定的 `report.txt`。
- `.pse` 会话文件（如 `8A27_UNL_Z_1.pse`）里带 PLIP 自己画的相互作用虚线，PyMOL 加载它比手画 `distance` 更准确。

### 复合物准备

PLIP 需要一个「纯蛋白 + 配体」的复合物 PDB：
- 受体去掉所有 HETATM（水/离子/共晶配体），只保留 ATOM 蛋白
- 配体转成 `HETATM` 记录，残基名 `UNL`、链 `Z`
- 用 openbabel 把配体 SDF 转 PDB，再手工改成 UNL/Z

## 六、与 diffdock 一致的作图渲染参数

gnina-dock 与 diffdock 的统一渲染风格（已对齐）：

```
bg_color white
set ray_opaque_background, 1      # 白底
set ray_trace_mode, 1
set ray_trace_fog, 0
set depth_cue, 0
set antialias, 2
set line_smooth, 1
set hash_max, 300                 # 线条质量
set light_count, 8                # 8 灯照明
set specular, 0.3
set shininess, 50
set ambient, 0.7
set direct, 0.4
set reflect, 0.1
set surface_quality, 1
set cartoon_oval_length, 1.2
set cartoon_oval_width, 0.4
set cartoon_rect_length, 1.2
set cartoon_rect_width, 0.5
set cartoon_loop_radius, 0.7
set label_font_id, 7
set label_size, 18                # 残基标签字号
set label_color, black
set label_shadow_mode, 1
```

两张标准输出图：
- `interaction_bindingsite.png` — 结合位点特写（cartoon 透明 0.8 + 残基标签 + PLIP 会话虚线）
- `complex_overview.png` — 整体图（仅蛋白不透明 cartoon + 配体 sticks；不显示口袋残基 sticks、高亮、标签、编号、图例或引线，保存的 PyMOL 会话采用同样样式）

## 七、一键复现命令速查

```bash
# 1. 装工具（WSL 内，--user 到 Linux 原生目录）
python3 -m pip install --user rdkit openbabel==3.2.1 meeko==0.7.1 pymol-open-source-whl==3.2.0.2 plip==3.0.1

# 2. 配体 3D 生成（RDKit）
python3 -c "from rdkit import Chem; from rdkit.Chem import AllChem; m=Chem.AddHs(Chem.MolFromSmiles('SMILES')); AllChem.EmbedMolecule(m,randomSeed=42); AllChem.MMFFOptimizeMolecule(m); Chem.SDWriter('lig.sdf').write(m)"

# 3. GNINA 对接（CPU，显式口袋坐标）
gnina -r receptor.pdb -l lig.sdf --center_x X --center_y Y --center_z Z --size_x 22 --size_y 22 --size_z 22 --cnn_scoring rescore --num_modes 10 --exhaustiveness 16 --seed 42 --no_gpu -o docked.sdf

# 4. PLIP 分析（含 .pse 会话）
python3 -m plip.plipcmd -f complex.pdb -o plip_out -y --txt --xml

# 5. PyMOL 出图（加载 PLIP .pse）
python3 -m pymol -cq render.pml
```
