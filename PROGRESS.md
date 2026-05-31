# x_to_mmd 进度

> 配合 [PLAN.md](PLAN.md) / [RESEARCH.md](RESEARCH.md) 使用。更新:2026-05-31。
> 重开续上:先读本文件 → PLAN.md → RESEARCH.md(或用 catchup 技能)。

## Checkpoint(2026-05-31)
- **Current task:** 工程已打通+打包成插件;diff 大幅收敛;等用户 `yaoxiang.vmd` 实测反馈(尤其尺寸/扭转/IK),据此定扭转·D骨是否切权重。
- **Done:** XPS解析器/PMX读取器/导入器/骨映射/权重安全转换/补全rig(含D骨)+腿IK/材质(両面)/**身高对齐目标**/**打包成 Blender 插件**(`__init__.py` bl_info + `blender_manifest.toml` + 算子 + N 面板 + `pipeline.run` 一键)/README——全部真机验证;**权重零丢失**;8/8 单测。
- **diff 收敛:** 骨重合 62→**112**/219、标准rig 56→**98**/102、付与 0→**24**(达标22)、IK 0→**2**/4、材质 1→**8**(全両面)、贴图 0→**6**、高度 **20.836=20.836 精确**。
- **关键修复(自测发现):** 渲染 `yaoxiang.vmd` pose 时上半身随 センター 平移、而 `全ての親` 背着 3362 源蒙皮权重留原点 → 尖刺。修:`clear_control_weights` 把控制骨权重按每顶点真实骨**重归一化吸收**(CLAUDE.md§1 控制骨空权重,非切分,总量守恒)。**修后模型随 VMD 正确变形(IK 跪姿、无散架)。**
- **Next:** 用户实测动作 → 据效果决定扭转/D骨是否切权重(Q2 已答"先看效果");つま先IK 正确导出、D骨、贴图随PMX拷贝、addon 打包(manifest+UI+算子)、blender 层测试。
- **Decisions(用户):** 差异硬底走"逼近可自动化项"(morph/物理/额外几何无法从单 XPS 复刻);扭转/D骨权重切分"先看效果再定"(当前不切,保持空权重付与骨)。
- **Blockers:** 无。
- **Gotchas:** `cli.py upload` 会把文件嵌成 `...\x2m.zip\x2m.zip`(脚本已兼容);导出 PMX 贴图为相对路径 `..\mywork\...`,从 `E:\_x2m_dev\` 正好解析到源贴图;开发循环 = `zip(core+blender)→cli.py upload→dev/blender_rpc.py --file`。
- **Files touched:** `core/{xps,pmx,bonemap}/*`, `blender/{importer,weights,convert,complete}.py`, `tests/test_{xps_parser,bonemap}.py`, `dev/*`, `CLAUDE.md`, `PLAN.md`, `RESEARCH.md`。

## 历史状态:调研完成 + 已连上远程 Blender(P0 起点)

### 已完成
- ✅ 目标明确:Blender 插件,任意 XPS/XNALara → MMD(PMX)。
- ✅ 两轮多智能体调研 + 七硬问题逐条对照 `Convert-to-MMD` 代码剖析 → `RESEARCH.md`、`PLAN.md`。
- ✅ **架构决策:** fork `uitcis/Convert-to-MMD`(GPL-3.0)为基座;**vendor 原生 XPS 解析器**做导入(用户已定,不依赖 xps_tools);**导出走 mmd_tools**;**开发基线 Blender 3.6**(后续再上 4.2+);整体 GPL-3.0-or-later。
- ✅ addon 骨架 + GPL `LICENSE` + 拉取 johnzero7 解析器源码(`/tmp/jz7/`,地面真值)。
- ✅ **已连上远程 Windows 的 Blender 3.6.15**(详见跨会话记忆 `remote-blender-access`):
  - 工具 `dev/blender_rpc.py`(`--code/--file/--scene`),走 VPS `49.233.189.223:9876`。
  - 环境核实:`mmd_tools` 可用(`core.pmx.exporter`/`core.model`)、`XNALaraMesh` 可用(做对照导入)。

### 目录结构(addon 骨架,尚无实现代码)
```
core/xps/        # 待写:原生 XPS 解析器(bpy 无关,可纯 python 跑 pytest)
core/bonemap/    # 待写:骨名归一化 + 别名字典 + 拓扑解析(核心 bpy 无关)
blender/         # 待写:导入建场景 / 权重安全转移 / 拓扑 / 归正 / 算子(需 bpy)
tests/           # 待写:core 的 pytest
dev/             # blender_rpc.py(远程 Blender RPC)、probe_env.py 等(不随 addon 发布)
```

### 已完成(P0 ①:原生 XPS 解析器)✅
- `core/xps/`(types/binreader/read_bin/read_ascii/__init__)写好,`tests/test_xps_parser.py` **5/5 通过**(ASCII / legacy .mesh / .xps 头+变量权重 / .NET varint / mesh 名)。
- **真实模型逐字节验证**:对 `xps-b.xps` 与远程 Blender 的 XNALaraMesh 解析结果**完全一致**——109 骨 / 8 网格 / 50124 顶点 / 79198 面,版本 (3,15)、骨父索引全表、采样顶点(坐标/法线/UV/骨/权重)、面索引全同。
- 该模型实测特征(对后续映射重要):**标准 XNALara generic 命名**(root ground/root hips/leg left thigh/spine lower-middle-upper/arm left shoulder 1-2/arm left finger 1a…)+ 一批 **`unused bip001 …` 垃圾/扭转骨**(pelvis/foretwist/muscle_elbow)+ **spine 3 段**(lower/middle/upper → 应映射 下半身/上半身/上半身2)。
- 验证脚本:`dev/remote_parse_xps.py`、`dev/remote_fingerprint.py`(走 `dev/blender_rpc.py`)。

### 已完成(P0 ②:Blender 导入器 + 远程 dev 循环)✅
- `blender/importer.py`:`XpsModel`→骨架+网格+顶点组+UV+自定义法线;坐标变换 `(x,-z,y)`+绕序 `[0,2,1]`+UV `v→1-v` 只做一次;**权重原样复用 XPS**。
- **远程 live Blender 验证通过**:导入 `xps-b.xps` → 109 骨 / 8 网格 / 50124 顶点 / 79198 面(全等),v0 坐标变换正确,v0 权重 `spine upper=1.0` 正确。
- 远程 dev 循环:`python3 -c 'zipfile 打包 core+blender'` → `cli.py upload` → `dev/blender_rpc.py --file dev/remote_test_import.py`(在 `E:\_x2m_dev\pkg` 解压导入)。注意 cli.py upload 会把文件嵌成 `...\x2m.zip\x2m.zip`,脚本已兼容。
- **PMX 读取器** `core/pmx/` 写好 + 与 mmd_tools 计数全等;目标规格存 `tests/fixtures/target_inase18_spec.json`。

### 目标 PMX 实情(`Purifier Inase 18 None.pmx`)
- 219 骨 / 169575 顶点 / 15 材质 / 19 morph / 35 刚体 / 16 关节 —— **重度人工精修**,顶点是源 3.4 倍(含额外头发/牙齿/物理)。
- 骨 0-101 = 标准 MMD rig;付与系数 = Reika 实测(腰キャンセル/肩C -1.0,腕捩/手捩 0.25/0.5/0.75);骨 102+ = Teeth/Jaw/Tongue/QQ 下巴骨/ear/hair 物理骨/Anus/Genitals/toe/D骨。
- 材质朴素(diffuse + sphere 禁用 + 内置 toon0 + **无描边**)→ 易复刻;morph/物理/QQ骨/额外几何 = **无法从单 XPS 自动复刻**(如实标注)。

### 源骨骼实测(xps-b.xps,关键映射依据)
- **`unused bip001 pelvis`(2)带 6892 顶点权重 = 真·下半身**(腿+脊柱在它下分叉);`root hips`(1)零权重 = センター。
- 零权重骨(并入/控制):`root hips`→センター、`arm left/right elbow`(前臂权重在 foretwist 上)、`hair c/l/r`。
- spine 3 段(lower/middle/upper)全带权重 → 拟 上半身/上半身2/上半身3(不切权重);前臂权重在 `unused bip001 *foretwist` 上 → 捩骨处理。
- 富含 facial/hair/boob 骨(目标也保留为 Jaw/Tongue/QQ/hair)。

### ✅ 端到端管线已打通(import→映射→权重安全转换→补全rig→IK→材质→mmd_tools导出 PMX)
全部在远程 live Blender 验证;`dev/remote_test_export.py` 一键跑通。各模块:
- `blender/weights.py` 权重安全转移(原子改名/ADD合并/`weight_integrity_check`)——**权重零丢失**。
- `blender/convert.py` `apply_bone_plan`(58改名/12合并)+ `mmd_convert_and_export`(convert_to_mmd_model + apply_additional_transform + export_pmx)。
- `blender/complete.py` `add_mmd_rig`(+42控制骨/18付与:操作中心/グルーブ/腰/両目/腰キャンセル/足IK親/足ＩＫ/つま先ＩＫ/肩P/肩C/腕捩123/手捩123/ダミー/指０,修正torso fork)+ `add_leg_ik`(腿IK约束)。
- `blender/importer.py` 加材质+贴图(从源文件夹载 diffuse PNG)。

### 当前 diff(mine vs target `Purifier Inase 18`)
| 维度 | 起点 | **现在** | 目标 | 说明 |
|---|---|---|---|---|
| 骨名重合/219 | 62 | **112** | 219 | 目标 tail ~80 骨(QQ下巴/头发物理/ear/toe)来自更丰富源 |
| 标准rig/102 | 56 | **98** | 102 | 仅缺 上半身1/首1(目标多段,源无)、乳奶(我用胸,命名差异) |
| 付与 | 0 | **24** | 22 | ✅达标(含 D骨 grant) |
| IK | 0 | **2** | 4 | 腿IK通;つま先IK(mmd_tools 链表示特殊)记为已知小限制 |
| 材质/贴图 | 1/0 | **8/6** | 15/16 | 我=源8网格全両面;目标更细分 |
| 高度 | — | **20.836** | 20.836 | ✅精确对齐(fit_scale) |
| 顶点/面 | 50125/79198 | 同 | 169575/199734 | **源几何固定,无法自动增** |
| morph/物理 | 0/0 | 0/0 | 19/35 | **手工内容,无法从单XPS自动复刻** |
| 权重完整性 | — | **0 丢失** | — | 复用XPS权重,ADD不切分;9/9 单测 |

### 下一步(继续缩小可自动化差异)
1. つま先ＩＫ 正确导出(对照 mmd_tools 导入目标 PMX 的 IK 表示)。
2. D骨(足D/ひざD/足首D/足先EX)作空权重付与骨(不切权重)→ +8骨 +grant。
3. 贴图随PMX拷贝(`copy_textures`)使PMX可移植;材质 toon/両面 标志。
4. 打包成真正 addon(`blender_manifest.toml`/`bl_info` + UI 面板 + 一键算子);加 blender 层测试。
5. 在 MMD/Blender 用 `yaoxiang.vmd` 实测动作(腿IK/付与是否动得对)。
6. 文档化无法自动复刻项(morph/物理/额外几何)。

### 关键提醒(不要重复 CTMMD 的坑,详见 RESEARCH.md §5)
- 改名**原子携带权重**;控制骨**空权重+use_deform=False**;删骨前先 ADD 权重;导出前 Limit Total=4。
- 付与真字段 `mmd_bone.additional_transform_*`+`transform_order`;dummy/shadow 交给 `apply_additional_transformation()` 生成,别预建。
- 轴翻转只在导入做一次;几何判断只在归正后;全/半角对齐动作库。

### 远程 Blender(每次重开可能要重新拉隧道)
若 `dev/blender_rpc.py` 连不上(9876 refused):用户需在 Blender 里"Start MCP Server",且远程要跑 `start_blender.py` 起 9876 隧道。完整方法见跨会话记忆 `remote-blender-access`。
