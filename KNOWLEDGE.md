# XPS → MMD 转换 · 实战知识库(KNOWLEDGE)

> 这是把「XPS/XNALara 模型自动转成 MMD(PMX)」整个调研 + 实战(在真实 Blender 3.6 上跑通、对照真实目标 PMX、逐字节/逐计数验证)沉淀下来的**自包含知识文档**。
> 目的:重开会话 / 重写项目时,**直接据此动手,不必重做调研**。
> 标注约定:**【验证】**=已用真实模型/mmd_tools 逐字节或逐计数核实;**【实测值】**=从真实 PMX 二进制量得;**【理论】**=来自规范/源码但本项目未单独验证;**【坑】**=实际踩到的 bug 及修法。

---

## 0. 目标与自动化边界(先认清现实)

把**任意 XPS** 转成**能在 MMD 加载、能吃 VMD 动作、权重无损**的 PMX。

**能自动**(本项目已做到):几何/UV/法线、骨名映射(XNALara→MMD 日文标准骨)、权重复用与垃圾骨合并、MMD 标准 rig(全ての親/センター/グルーブ/腰/IK/腰キャンセル/肩P-C/捩/D骨)+ 腿 IK + 付与、材质+diffuse 贴图、身高对齐。

**不能从单个 XPS 自动复刻**(本质缺失,需手工/更丰富源):
- **表情 morph**(XPS 用骨摆脸,无 morph 数据)
- **物理**(刚体/关节)
- **额外几何**(精修网格、独立头发等——真实目标常比单个 XPS 多 2~4× 顶点)
- 高度专用骨(下巴绑定、耳骨、头发物理骨)

> **【坑·心态】** 找一个"人工精修的成品 PMX"当对照,会发现它顶点是源的 3.4×、还有 19 morph / 35 刚体——这不是你转换差,而是它**不是同一个东西**。把差异目标定在**可自动化维度(rig/权重/材质/比例)**,其余如实标注。

---

## 1. XPS / XNALara 格式(写原生解析器用)【验证:逐字节对齐 johnzero7 XNALaraMesh】

### 1.1 三态与分派
- `.xps`:带头二进制(新格式,"Generic Item 2")。
- `.mesh`:legacy 无头二进制。
- `.mesh.ascii` / `.ascii`:文本,行式。
- **分派**:读第一个 `uint32`;`== 323232`(MAGIC)→ 带头 `.xps`;否则该 uint32 就是 legacy `.mesh` 的骨数。`.ascii` 按扩展名或"前 64 字节可打印且无 \0"判定。
- 全部**小端**。字符串 = **.NET 7-bit 变长长度前缀** + **UTF-8(用 `utf-8-sig` 解码吸收 BOM)**。

### 1.2 .NET 7-bit varint(字符串长度)
```
result=0; shift=0
loop: b=read_byte(); result |= (b & 0x7F) << shift; if not (b & 0x80): break; shift+=7
```
johnzero7 只处理 1~2 字节(LIMIT=128),但写通用多字节更稳。

### 1.3 .xps 头(消费到骨数为止)
顺序:`u32 magic(323232)`、`u16 verMajor`、`u16 verMinor`、`string xna_aral("XNAaraL")`、`u32 settingsLen`、`string machine`、`string user`、`string files`,然后 settings 块:
- **旧格式**(`hasTangent` 为真,见下):直接读 `settingsLen * 4` 字节跳过。
- **新格式**:`u32 hash`、`u32 items`,然后每个 item:`u32 optType`、`u32 optCount`、`u32 optInfo`,按 optType 消费字节:
  - `0` None:`optCount` 个 u32(= `optCount*4` 字节)
  - `1` Pose:`roundUp(optCount, 4)` 字节(等价于 johnzero7 读 optInfo 行+补齐)
  - `2` Flags:`optCount` 对 (u32,u32)(= `optCount*8` 字节)
  - 其它(未知):读到 `settingsLen*4 - 已消费` 字节后 break(兜底)

### 1.4 版本布尔(决定顶点布局,**极关键**)
```
hasTangent       = (verMinor<=12 and verMajor<=2)  if 有头 else True
hasVariableWeights = (verMajor>=3)                  if 有头 else False
```
**【实测】** 真实游戏 rip 常是 v(3,15):**无 tangent、变量权重**。

### 1.5 骨 / 网格 / 顶点
- 骨:`u32 count`;每根 `string name`、`int16 parentId`(-1/0xFFFF=根)、`3×float pos`(**模型空间绝对坐标**)。
- 网格:`u32 count`;每个 `string name`、`u32 uvLayerCount`、`u32 texCount` + 每贴图(`string file`(取 basename)、`u32 uvLayerId`)、`u32 vertCount` + 顶点、`u32 triCount` + 每三角 `3×u32`。
- 顶点:`3f pos`、`3f normal`、`4×uint8 RGBA color`、每 uv 层 `2f uv`(若 hasTangent 再 `4f tangent` 丢弃)、若有骨:`hasVariableWeights` 时先 `int16 weightCount` 否则 4,然后 `count×int16 boneIdx`、`count×float weight`。

### 1.6 ASCII 格式
行式:数值行用空格分隔、字符串值独占一行(**保留内部空格**,如 "root ground")、`#` 起注释。无 tangent、骨权重恒 4(零填充)。

### 1.7 坐标系(**只在导入做一次**)【验证】
XPS = 左手 Y-up、+Z 朝里;Blender = 右手 Z-up。导入变换:
- 位置/法线:`(x,y,z) → (x, -z, y)`
- 三角绕序:`[0,1,2] → [0,2,1]`(翻转)
- UV:`v → 1 - v`(u 不变)
**解析器返回原始 XPS 坐标,变换交给导入层做一次**;PMX 那一侧的轴交给 mmd_tools。中间**绝不再翻轴**(否则模型躺倒/镜像)。

### 1.8 网格名编码
`<renderGroupId>_<name>_<p1>_<p2>_<p3>`(下划线分隔);首段是 int 则为 render group。**【实测】** 本项目模型材质名是 `24_0001-Object002_1.0_16.0_16.0` 这种。

---

## 2. PMX 2.0/2.1 格式(写读取器/校验用)【验证:与 mmd_tools 计数全等】

- 头:`'PMX '`(0x50 4D 58 20)+ `float version` + `uint8 globalsCount(8)` + 8 globals:`[0]编码(0=UTF16LE,1=UTF8)`、`[1]附加UV数`、`[2]顶点索引大小`、`[3]贴图`、`[4]材质`、`[5]骨`、`[6]morph`、`[7]刚体` 索引字节大小(1/2/4)。
- 文本字段:`int32 字节长` + 按编码的字节(**导出默认 UTF-16LE 兼容性最好**)。
- 段序:顶点 → 面(int32 = 索引数 = 三角×3)→ 贴图 → 材质 → 骨 → morph → **显示枠** → 刚体 → 关节(→软体仅2.1)。
- **索引有符号性(最易错):顶点索引无符号;骨/贴图/材质/morph/刚体索引有符号,-1=无。** 大小按数量算:顶点 `<256→1,<65536→2,else4`;有符号 `<128→1,<32768→2,else4`(留 -1)。
- 顶点权重类型:`0 BDEF1 / 1 BDEF2 / 2 BDEF4 / 3 SDEF / 4 QDEF(2.1)`。Blender 只出 BDEF;SDEF 只能 PMXEditor 设。
- 骨 flags(uint16)位:`0x0001 indexed-tail`、`0x0002 可旋`、`0x0004 可移`、`0x0008 可见`、`0x0010 可操作`、`0x0020 IK`、`0x0100 付与回転`、`0x0200 付与移动`、`0x0400 固定轴`、`0x0800 局部轴`、`0x1000 物理后变形`、`0x2000 外部父`。tail 按 0x0001 是骨索引或 vec3;付与位则读 `骨索引+float权重`;IK 位读 target/loop/limit/links。
- 目标 **PMX 2.0**(MMD 本体不完整支持 2.1 的 QDEF/SoftBody)。

---

## 3. 骨映射:XNALara generic → MMD【验证:真实模型 58改/12并/39留】

### 3.1 关键:先算"哪些骨带蒙皮权重"
**遍历顶点统计每骨加权顶点数**,据此分类:
- **带权重 → rename**(给 MMD 名,权重原样跟过去)。
- **零权重 / 名含 unused/foretwist/twist/muscle/xtra → merge**(ADD 权重并入最近的 rename/keep 祖先)。
- **其它(面部/头发/胸链等)→ keep**(目标也保留为 Jaw/Tongue/QQ/hair)。

### 3.2 名字归一化 + 侧别
NFKC 全角→半角、转小写、按 `空格 _ - . : \ /` 切 token、剥 junk token(`unused/bip001/bip01/valvebiped/mixamorig/def`)、识别侧别(`left/l`→L,`right/r`→R),剩余 token 拼接当 key 查别名表。**只归一化源名;MMD 目标名按动作库惯例输出全/半角。**

### 3.3 XNALara generic → MMD 对照(本项目实测有效)
```
root ground→全ての親  root hips→センター(零权重控制)
unused bip001 pelvis→下半身(★带 6892 权重=真骨盆,别被"unused"骗)
spine lower→上半身  spine middle→上半身2  spine upper→上半身3
head neck lower→首  head neck upper→頭
leg {l/r} thigh→足  knee→ひざ  ankle→足首  toes→つま先
arm {l/r} shoulder 1→肩  shoulder 2→腕  elbow→ひじ  wrist→手首
arm {l/r} finger 1a/b/c→親指０/１/２  2*→人指１/２/３  3*→中指  4*→薬指  5*→小指
head eyeball {l/r}→目   boob {l/r} 1→胸
```
**【坑】** 手指数字用**全角**(親指０ 非 親指0);`左/右` 是**前缀**,`腰キャンセル左/右` 是**后缀**(别写成 左腰キャンセル);spine 3 段全带权重→映 上半身/2/3 不切权重。前臂权重常在 `foretwist` 上→并入 `ひじ`。

---

## 4. 权重处理(**最重要,CLAUDE 强约束 + 真 bug 在这**)

### 4.1 铁律
1. **尽量复用 XPS 现有权重**(质量好);**不到万不得已不切分**;**任何切分先经用户确认**。
2. **改名=原子操作**:网格侧顶点组先改/合并 → 再改骨名 → 再刷 depsgraph(`obj.data.update_tag(); view_layer.update()`)。绝不靠 Blender 隐式联动(顶点组名≠骨名就静默脱钩)。
3. **合并=ADD**(把源组权重 ADD 进目标组再删源组);**删骨前先 ADD**,否则丢权重。
4. **控制骨(全ての親/センター/グルーブ/腰/操作中心/IK/肩P/足IK親)必须空权重 + use_deform=False。**
5. 导出前 `Limit Total=4` + 重归一(XPS≤4 骨,PMX BDEF4 上限 4)。
6. **每步前后跑权重完整性检查**(每顶点权重总和守恒、无新增零权重顶点、无组被清空)。

### 4.2 ★★★ 真 bug:控制骨带权重 → 动作时尖刺(本项目踩到并修复)
**现象**:套 VMD 后上半身随 センター 平移,而 `全ての親`(由 `root ground` 改名)**身上背着 3362 个源蒙皮权重**留在原点 → 顶点在身体和原点间被拉成**长尖刺**。
**根因**:XPS 常把零散蒙皮权重挂在 root 上;改名成 全ての親 后违反"控制骨空权重"。
**修法 `clear_control_weights`**:对每个挂在控制骨上的顶点,把控制骨那份权重**按该顶点的其它真实骨重新归一化吸收**(`factor=(ctrl_w+other_sum)/other_sum`,逐组 REPLACE),再删控制骨组;若顶点只有控制骨权重则回退到 `下半身`。**总量守恒、非切分、是强约束要求的清理。** 修后模型随 VMD 正确变形。
> **【教训】** 写完一定要**自己套个 VMD 渲一帧看**——这个 bug 计数/单测都查不出,只有实际摆 pose 才暴露。

---

## 5. 补全 MMD rig(空权重控制骨,不碰权重)

### 5.1 要加的骨 + 层级
- 根链:`操作中心(根)`、`全ての親(根)`、`センター`、`グルーブ`、`腰`,且 `全ての親→センター→グルーブ→腰→{下半身, 上半身}`。
  - **【坑】** 源里 `上半身` 常挂在 `下半身`(骨盆)下,要 **reparent 到 腰**,形成 MMD 的上下半身分叉。
  - **【坑】** `センター` 别用源 `root hips` 的位置(太高);**放到骨盆中心=两大腿根中点**(`midpoint(左足.head, 右足.head)`),否则 VMD センター 旋转支点偏。
- `両目`(头上,付与驱动左右目 1.0)。
- 每侧:`腰キャンセル{左/右}`(付与 腰 -1.0,腿挂其下)、`足IK親/足ＩＫ/つま先ＩＫ`、`肩P/肩C`(肩C 付与 肩P -1.0,reparent 肩→肩P、腕→肩C)、`腕捩(+1/2/3)`、`手捩(+1/2/3)`、`ダミー`、`指０`(人指/中指/薬指/小指,reparent 指１ 到其下)、`足D/ひざD/足首D/足先EX`。

### 5.2 付与系数【实测·取自真实 Reika PMX,与目标完全吻合】
```
肩C ← 肩P            -1.0
腰キャンセル ← 腰      -1.0
腕捩1/2/3 ← 腕捩      0.25 / 0.5 / 0.75
手捩1/2/3 ← 手捩      0.25 / 0.5 / 0.75
足D/ひざD/足首D ← 足/ひざ/足首   1.0
目 ← 両目            1.0
```

### 5.3 身高对齐
导出 scale 默认 ×12.5(米→MMD)。要对齐某目标身高:`fit_scale = 目标高 / Blender模型高(世界顶点Z跨度)`。本项目目标高 **20.836**,得 scale≈11.91,导出后高度精确相等。
> **【坑·尺寸误判】** 别用 `scale=0.08` 导入到 Blender 测就说"太小了"——那是导入比例,PMX 本身是绝对 MMD 尺寸。比尺寸要量**顶点包围盒**,不是骨跨度。

---

## 6. 付与 / dummy / shadow(交给 mmd_tools,别手建)【验证 + 源码核实】

- `_dummy_/_shadow_` 是 **mmd_tools 在视口模拟付与的内部辅助骨,不是导出数据**;导出器靠 `is_mmd_shadow_bone` 跳过它们。
- **做法**:① 在 pose bone 上设 `mmd_bone.has_additional_rotation=True`、`additional_transform_bone='<源骨>'`、`additional_transform_influence=<系数>`、`transform_order=1`(源骨留 0);② 调 `bpy.ops.mmd_tools.apply_additional_transform()` 让 mmd_tools **规范生成** dummy/shadow;③ 再 convert/export。
- **【坑】** Convert-to-MMD(uitcis,参考项目)手建 dummy/shadow 但**不设 mmd_bone 付与字段** → 导出 PMX 付与系数全 0、扭转骨在 MMD 里失效。**别学。** `influence=0` 会让 mmd_tools 删约束。

---

## 7. mmd_tools API(Blender 3.6 / mmd_tools v2.x,**已验证可用**)

```python
# 读 PMX 不建场景(校验/对照用):
from mmd_tools.core.pmx import load
p = load(path)          # p.vertices/faces/textures/materials/bones/morphs/display/rigids/joints

# 把 armature 包成 MMD 模型:
bpy.ops.mmd_tools.convert_to_mmd_model(convert_material_nodes=False)  # 选中 armature
from mmd_tools.core.model import FnModel
root = FnModel.find_root_object(arm_obj)   # 找 ROOT 空物体

# 生成付与影子骨:
bpy.ops.mmd_tools.apply_additional_transform()  # 选中 root

# 导出 PMX(选中 root):
bpy.ops.mmd_tools.export_pmx(filepath=..., scale=11.91, copy_textures=True)
#  v4.x 用 copy_textures_mode='OVERWRITE' 替代 copy_textures

# 导入 PMX(测试用) + VMD:
bpy.ops.mmd_tools.import_model(filepath=pmx, scale=0.08, clean_model=False)
bpy.ops.mmd_tools.import_vmd(filepath=vmd)   # 作用于活动 MMD 模型
```
- 材质:`material.mmd_material.is_double_sided / enabled_toon_edge / is_shared_toon_texture / shared_toon_texture`。本项目目标材质=**両面、无描边、内置 toon0**(很朴素,易复刻)。
- IK:用 Blender pose-bone IK 约束;`足首` 上加 IK 约束 target=arm subtarget=`足ＩＫ` chain_count=2 → 导出为 PMX 腿 IK(✓)。**【坑·未解】** `つま先ＩＫ`(约束放 つま先 chain=1)mmd_tools 没导出成 PMX IK(本项目腿 IK 4 只成 2);趾 IK 的 mmd_tools 表示需进一步研究(可导入目标 PMX 看它的约束怎么设)。

---

## 8. 工具链与许可
- **XPS 导入解析**:`johnzero7/XNALaraMesh`(原版停更、Blender 4.1+ 报错;fork:`mayloglog`、`Valerie-Bosco`、`Mysteryem`)。**纯解析层 bpy 无关、可 vendor/重写**;GPL。
- **PMX 导出/数据中枢**:`MMD-Blender/blender_mmd_tools`(UuuNyaa,GPL,v4.x=Blender4.2+,v2.x=3.6)。
- **骨名字典**:`absolute-quantum/cats-blender-plugin`(**MIT**,`tools/armature_bones.py` 含 XPS 反斜杠骨名)。
- **转换思路参考**:`uitcis/Convert-to-MMD`(GPL,多源→MMD,含 xna_lara 预设、IK、物理;但有上述付与 bug,别照抄)。
- 整插件 **GPL-3.0-or-later**。

---

## 9. 远程 Blender 联调(本项目实际用法)
- 远程 Win + Blender 3.6 + blender-mcp(TCP socket),经 VPS 隧道暴露。协议:`{"type":"execute_code","params":{"code":...}}`→ 返回 stdout 在 `result.result`(**注意**:不是某些桥用的 `{"type":"code"}`)。
- dev 循环:`zip(core+blender)` → 上传 → 远程解压加 sys.path → import 跑。bpy 无关的 `core/` 本机直接 pytest。
- **【坑】** 加载 16万顶点的目标 PMX + 9000 帧 VMD 播放会**崩 Blender**;测试只加载自己的模型、单帧渲染,别加载重目标。

---

## 10. 给 v2 重写的架构建议(吸取本项目经验)
1. **分层**:`core/`(bpy 无关:xps 解析 / pmx 读写 / 骨名解析,**全 pytest**)+ `blender/`(导入/权重/补全/导出)+ `__init__.py`(addon 入口 manifest+面板+算子)。这套结构本项目验证好用。
2. **权重安全模块是地基**,先写并测:原子改名、ADD 合并、`clear_control_weights`、`weight_integrity_check`。**控制骨清权重必做**(否则尖刺)。
3. **骨映射做成"归一化+别名字典+拓扑兜底+加权统计分类(rename/merge/keep)"**,别用死预设;XNALara generic 名先覆盖,其它 rip 加 CATS 字典 + 拓扑(2 条腿子树=骨盆等)。
4. **必须有 PMX 读取器当差异/验收基座**,并**每次改动套 VMD 渲一帧**自测(本项目的尖刺 bug 就是这么抓到的)。
5. 早期就接 **mmd_tools 导出**(别自研 PMX 写出器——坐标/符号 quirk 太多),`fit_scale` 对齐身高。
6. 付与走 `mmd_bone.*` + `apply_additional_transform`,**不手建 dummy/shadow**。
7. **明确把 morph/物理/额外几何划为"非自动、文档说明"**,不要试图从单 XPS 造。
8. 切分权重(扭转/D骨真形变)做成**可选、默认关、需用户确认**。

---

## 11. 一句话总览
**XPS 解析(逐字节)→ Blender 导入(轴只翻一次)→ 加权统计分类骨(rename/merge/keep)→ 权重安全改名/合并 + 清控制骨权重 → 补全 MMD rig(实测付与系数)+ 腿 IK → 材质両面 → fit 身高 → mmd_tools 导出 PMX。morph/物理/额外几何无法自动。**
