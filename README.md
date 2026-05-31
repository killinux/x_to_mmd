# x_to_mmd

把**任意 XPS/XNALara 模型自动转换成 MMD(PMX)**的 Blender 插件。
方案与依据见 [PLAN.md](PLAN.md) / [RESEARCH.md](RESEARCH.md);强约束见 [CLAUDE.md](CLAUDE.md);进度见 [PROGRESS.md](PROGRESS.md)。

## 它做什么
导入 XPS(`.xps/.mesh/.mesh.ascii`)→ **自动骨名映射**(XNALara→MMD 日文标准骨)→ **权重安全改名/合并**(复用 XPS 权重、ADD 不切分)→ **补全 MMD rig**(全ての親/センター/グルーブ/腰/IK/腰キャンセル/肩P-C/腕捩-手捩/D骨/付与)→ **腿 IK** → **材质+贴图** → 调 **mmd_tools 导出 PMX**(高度可对齐目标)。

## 安装
- **Blender 3.x**:`编辑 > 偏好设置 > 插件 > 安装`,选本仓库打包的 zip(含 `__init__.py`/`core`/`blender`)。
- **Blender 4.2+**:作为扩展安装(`blender_manifest.toml`)。
- **依赖**:导出 PMX 需先装 [mmd_tools](https://extensions.blender.org/add-ons/mmd-tools/)。

## 用法
`View3D > 侧栏(N) > XPS→MMD` → **Import & Convert XPS → MMD** → 选 XPS 文件。
可选填 `Export PMX` 路径与 `Fit height`(对齐目标身高,0=默认 ×12.5)。

## 自动化边界(重要,实事求是)
**能自动**:几何/UV/法线、骨名映射、权重复用与垃圾骨合并、MMD 标准 rig + 腿 IK + 付与(腕捩/手捩/肩C/腰キャンセル/D骨,系数取自实测)、材质+diffuse 贴图(両面/toon)、身高对齐。
**不能从单个 XPS 自动复刻**(需手工 / 更丰富的源):
- **表情 morph**(XPS 用骨摆脸,无 morph 数据)
- **物理**(刚体/关节,头发/裙子/胸)
- **额外几何**(精修网格、独立头发等——若目标比源多 N 倍顶点)
- 高度专用骨(下巴 QQ 绑定、耳骨等)

> 设计原则(CLAUDE.md):**优先复用 XPS 权重,不到万不得已不切分;任何切分权重先经用户确认。**

## 代码结构
| 目录 | 说明 |
|---|---|
| `core/xps/` | XPS 解析器(bpy 无关,逐字节对齐 XNALaraMesh,pytest 覆盖) |
| `core/pmx/` | PMX 读取器(差异/验收基座,与 mmd_tools 计数一致) |
| `core/bonemap/` | 骨名归一化 + XNALara→MMD 别名 + 解析(rename/merge/keep) |
| `blender/` | 导入建场景 / 权重安全转移 / 补全 rig+IK / 材质 / mmd_tools 导出 / 一键编排 |
| `tests/` | `core/` 的纯 Python 单测 |
| `dev/` | 远程 Blender 联调脚本(不随插件发布) |

## 开发/测试
- `core/*` 纯 Python 可直接 pytest(本机无需 Blender)。
- `blender/*` 需 Blender;本项目用远程 Blender 3.6 联调(`dev/blender_rpc.py`)。

## 许可
GPL-3.0-or-later。骨名识别参考 CATS(MIT)、解析格式参考 johnzero7/XNALaraMesh(GPL);转换思路参考 `uitcis/Convert-to-MMD`(GPL,致谢 UITCIS)。
