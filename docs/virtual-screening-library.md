# 本地虚拟筛选库接入

本仓库提供 UniDock-Pro 筛选技能和结果整理脚本。大型化合物库的原始文件、规范化 SDF/SMILES、三维结构、PDBQT 和 SQLite 保存在数据持有者自己的磁盘，不随 Git 仓库分发。

## 输入要求

运行 `unidock-vscreen` 时，准备受体 PDBQT、搜索框中心与大小，以及一个配体 PDBQT 目录或 `ligand_index.txt`。索引文件每行一个 PDBQT 路径；相对路径以索引文件所在目录为基准。运行前应核查文件实际存在、配体状态、受体质子化、保留的金属/辅因子和口袋定义。

```bash
python skills/unidock-vscreen/scripts/check_unidock.py --udp /path/to/udp
python skills/unidock-vscreen/scripts/run_unidock_screen.py \
  --udp /path/to/udp \
  --receptor /path/to/receptor.pdbqt \
  --ligand-index /path/to/ligand_index.txt \
  --center 30 40 50 --size 25 25 25 \
  --search-mode fast --dry-run \
  --out-dir /path/to/screen_run
```

确认 `inputs/run_config.json` 和配体清单无误后，再用新的输出目录进行正式筛选。

## 数据记录建议

每个专题库至少保留来源 URL、版本、许可证、原始结构、清洗决定、去重规则、三维化失败、PDBQT 转换失败、可筛选数量和 `ligand_index.txt`。药物、天然产物、海洋天然产物、微生物天然产物、中药及药用植物等可作为专题分类；实际可筛选条目应以各库的校验报告为准。

不要把数据库网页展示的化合物总数直接当作可筛选 PDBQT 数量，也不要把对接评分当作实验亲和力。对于反向筛选，不同蛋白靶点的原始分数需要校准后才能用于稳健比较。
