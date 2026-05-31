# x_to_mmd 调研记录

> 目标:一个 Blender 插件,把**任意 XPS/XNALara 格式的模型自动转换成 MMD(PMX)**。
> 本文件是调研的**事实/依据**记录;可执行方案见 [PLAN.md](PLAN.md),进度见 [PROGRESS.md](PROGRESS.md)。
> 调研方式:多智能体工作流(内部 `x_wiki` 知识库挖掘 + 外部仓库/规范 + 对抗式核查)。日期:2026-05。

---

## 1. 可行性结论

**可行,但"自动化"分层看。** `x_wiki` 自身结论最准:自动转换只能保证**"模型能显示"**,不能保证**"看起来/动起来像 MMD"**——卡通描边、物理、表情、IK、显示枠本质是手艺活,**但其中很大一部分可用"模板生成"自动化**。

- 市面上**没有一键 XPS→MMD 工具**。现状是 4 段式多工具手工流水线。
- 关键先例:
  - **`uitcis/Convert-to-MMD`(CTMMD)** — 多源骨架→MMD 的 Blender 插件,GPL-3.0,Blender 3.0+,**自带 `xna_lara` 预设**、IK 生成、足D/肩P/扭转骨、显示枠、胸/身体物理,末端调 mmd_tools 转换/导出。**这是要建立在其上的基座**(见 §4)。
  - **`wikid24/ffxiv_mmd_tools_helper`** — 真·几次点击的 FFXIV→MMD 转换器(自动骨映射/骨morph/刚体+关节/裙子绑定/贴图)。**证明架构可行,只是没人为 XPS 做。要对标的就是它。**
  - **`Hogarth-MMD/mmd_tools_helper`** — 通用但脆弱;骨名要先对;显示枠**有语义分组**(核查确认)。

---

## 2. 技术要点

### 2.1 XPS 格式
- 三态:legacy 无头 `.mesh`(首 `uint32`=骨数)、带头 `.xps`(首 `uint32`==`323232` 魔数,带版本)、文本 `.mesh.ascii/.ascii`(行式)。
- 结构:扁平骨列表(名+父索引+**模型空间**位置)→ 网格列表(名编码 render group、贴图、交错顶点、三角面)。
- 顶点:position/normal/RGBA color/N×UV/可选 tangent/4(或可变)骨索引+权重。版本布尔:`hasTangent=(major<=2 且 minor<=12)`、`hasVariableWeights=(major>=3)`。
- 字符串:.NET 7-bit 变长前缀 + UTF-8。
- **坐标系:左手 Y-up、+Z 朝里**;Blender 右手 Z-up。导入变换 `(x,y,z)→(x,-z,y)` + 绕序翻转 `[0,2,1]` + UV `v→1-v`(U 不变)。导出取逆。**只做一次**。

### 2.2 PMX 格式
- 头:`'PMX '` + float 版本 + 8 字节 globals(文本编码 0=UTF-16LE、附加UV数、各段索引字节大小 1/2/4)。
- 段序:顶点→面→贴图→材质→骨→morph→显示枠→刚体→关节(→软体仅 2.1)。
- **顶点索引无符号;骨/贴图/材质/morph/刚体索引有符号,-1=无。**
- 顶点权重 BDEF1/2/4/SDEF/QDEF。**目标 PMX 2.0**(MMD 本体不完整支持 2.1)。
- Blender 无 SDEF(只导出 BDEF);SDEF/材质绘制顺序/准标准骨插件属 **PMXEditor 交接**(Windows-only 不可脚本化)。

### 2.3 XPS 缺、MMD 必须有的 5 样(实测默认值,取自 Reika18 真模型)
| 系统 | 生成默认 |
|---|---|
| **IK** | `足ＩＫ`(target=足首, chain=2[ひざ,足])、`つま先ＩＫ`(chain=1);父链 `足ＩＫ→足IK親→全ての親`;膝盖微前弯 |
| **付与** | 肩C←肩P `-1.0`;腕捩/手捩 1/2/3 `0.25/0.5/0.75`;足D/ひざD/足首D `1.0`;目←両目 `1.0`;腰キャンセル←腰 `-1.0` |
| **物理** | dynamic 阻尼 0.9、摩擦/弹性 0、关节 rotX ±10~30° |
| **表情** | 最小集 `まばたき+あいうえお`(lossy,只搭脚手架,文档说明手工重建) |
| **显示枠** | Root/表情/IK/体上下/指/物理/その他;**所有 morph 必须进"表情"枠** |
| **センター/全ての親** | XPS 无全局根/重心概念,必须生成(纯控制骨、空权重) |

### 2.4 材质
- XPS:render group 编号 + 贴图槽(1=Diffuse,2=Lightmap/AO,3=Normal,4=Specular/Mask)。
- MMD:Diffuse/Ambient/Specular + 10 共享 toon + Sphere(SPH 乘/SPA 加)+ 描边 + Alpha。
- 自动可做:保留 diffuse、**置白 diffuse(1,1,1)避免全黑**、剥离 `_N/_AO/_s`、默认 toon(肤 toon02/脸 toon07/其余 toon01)、开描边、両面。艺术性 toon/sphere 选择仍手工。

### 2.5 全/半角(VMD 致命)
- VMD 按日文字符串**精确匹配**,全/半角不可混。Reika 实测:拇指 `親指０`(全角)、`ＩＫ`(全角)。
- **只归一化"源"骨名;MMD 目标名按动作库惯例输出。** CTMMD 内部存在全/半角不一致(`bone_map_and_group.py` 全角 `親指０` vs `0mmd_japanese.json` 半角)——需审计。

---

## 3. 工具链评估
| 工具 | 角色 | 状态/注意 |
|---|---|---|
| **xps_tools**(johnzero7/XNALaraMesh) | XPS 导入 | 原版停更 ~5 年、Blender 4.1+ 报错、无 in-repo LICENSE(但 Blender Extensions 以 GPL-3.0 分发)。4.x/5.x 用 fork:`mayloglog`、`Valerie-Bosco`、`Mysteryem`。**纯解析层 bpy 无关、可 vendor** |
| **mmd_tools**(MMD-Blender/blender_mmd_tools) | PMX 导出 + MMD 数据中枢 | GPL-3.0,v4.5.x,Blender 4.2+。导出算子 `mmd_tools.export_pmx`,内部 `mmd_tools.core.pmx.exporter.export(filepath, root=, armature=, meshes=, ...)`;scale 默认 12.5。付与真字段 `mmd_bone.additional_transform_*` |
| **CATS**(absolute-quantum,**MIT**) | 骨名识别字典 | `tools/armature_bones.py` ~2300 行,**含 XPS 反斜杠骨名**;强归一化。**MIT 可直接复用做"源识别"**。标准名是 Unity-humanoid 不是 MMD,需补"CATS英文→MMD日文"第二跳。4.x fork:Tuxedo/TeamNeoneko(GPL) |
| **PMXEditor** | 导出后精修 | Windows-only **不可脚本化**:SDEF、材质绘制顺序、准标准ボーン插件 → 交接 |

---

## 4. 架构决策:建立在 Convert-to-MMD 之上

调研工作流(独立于 CTMMD)对抗式核查后推荐 **方案 C(混合)**:vendor XPS 解析 + 自研 骨/材质/物理 智能 + 驱动 mmd_tools 导出。

**CTMMD 恰好已实现"方案 C 的右半边"**(自研骨/物理智能 + 驱动 mmd_tools)。因此结论:

- ✅ **fork/扩展 CTMMD**(GPL 允许;署名原作者 UITCIS / Gitee / B站)。
- ✅ **导出用 mmd_tools**(对抗式核查 + CTMMD 双双指向:自研 PMX 写出器要复刻 mmd_tools 已做对的坐标/符号 quirk,极易产出镜像/翻面)。**收回早前"自研 PMX 写出器"的倾向。**
- ✅ 整插件 GPL-3.0-or-later,目标 Blender 4.2+ Extension。

### CTMMD 的 4 大缺口(要补的)
1. **无 XPS 导入前端**(假设已在 Blender 里)→ vendor johnzero7 纯解析层 或 集成 xps_tools fork。**头号必做。**
2. **`xna_lara.json` 只认标准 generic 骨架** → 真实 rip 匹配 0 命中。
3. **无材质 toon/描边自动化。**
4. **全/半角不一致。**

---

## 5. 七个硬问题逐条剖析(对照 CTMMD 真实代码)

> 每条:现状 → 缺口/bug → 正确做法 → 关键值 → 排序位置。这是 PLAN.md 的依据。

### 5.1 骨映射(`rename_bones_operator.py` / `xna_lara.json`)
- **现状:** 不做拓扑识别;靠每 rig 的预设 dict 精确字符串匹配 `pose.bones.get(name)`。
- **bug:** 无归一化(大小写/分隔符/前缀/全半角任一不同→0 命中);无别名字典;`下半身` 缺失/错配;hip-vs-センター 无规则;clavicle-vs-肩 预设写死;多段 spine 无原则映射;镜像用首个匹配规则有顺序 bug;**不认 XPS `\L/\R`**。
- **正确做法:** 4 段解析器,严格按序 ——
  1. **归一化**(抄 CATS):NFKC 全角→半角、转小写、剥前缀 `valvebiped_/bip01_/bip001 /mixamorig:/def_/cf_s_`、统一分隔符 ` -.:`→`_`、折叠重复、剥后缀 `_bone/_le/_ri`;**双向展开侧标记** `\l/\left/.l/_l/-l/ l/left/左/-l`→canonical L(R 同理)。
  2. **别名字典匹配**:一个 slot→别名列表(CATS `bone_rename`)取代 24 死预设。
  3. **拓扑兜底**:`下半身`=有≥2 腿子树的骨;`肩 vs 腕`=胸↔肘间 2 根→[肩,腕]、1 根→[腕](补肩);L/R 用 `head.x` 符号(**仅在归正后**)。
  4. **人工确认**歧义(pelvis→下半身 vs センター、spine 切分)。
- **陷阱:** 归一化只为匹配、别过度剥(别把 `spine`/`shoulder1` 数字剥掉);名与拓扑冲突时信拓扑;长 spine 合并要转权重;真 pelvis 存在则**复用**为下半身(别瞎造)。
- **排序:** 第一个语义步,紧接导入+归正,**先于**补全/IK/分组/导出。

### 5.2 权重(`merge_bones_operator.py` / rename / `add_leg_d_bones`)
- **现状:** 3 条路径碰权重,无统一安全层。改名靠 Blender 隐式联动;合并用 `for vertex...for group` 纯 Python。
- **bug:** 顶点组名≠骨名→改名**静默脱钩**;目标名预存→**重名无效数据**(#135438);改名后不刷 depsgraph(#93892);删骨不先 ADD 权重→**丢权重**;ADD 后不重归一(>1);跳过非 armature-modifier 网格;**无 Limit Total=4**(mmd_tools 导出任意裁 top-4,可能丢关键骨);控制骨残留旧权重→移动控制骨"甩飞"网格;D骨靠重命名顶点组(同样脆);扭转骨权重 split 缩到 0.65→**欠权重**。
- **正确做法:** 建**一个共享的权重安全转移模块**,所有改名/合并/D骨/补全都走它。原子改名:网格侧组先 改/合并、再改骨名、再 `obj.data.update()`+depsgraph 刷新。合并=ADD 进保留骨再删组。
- **关键值:** >4 骨/顶点→`Limit Total=4`+重归一;控制/IK 骨(`全ての親 センター グルーブ 腰 操作中心 足ＩＫ つま先ＩＫ 足IK親 肩P`)空权重+`use_deform=False`。
- **排序:** 不是单一阶段,**3 处强制**:改名时(原子携带)、合并/D骨时(ADD 守恒)、导出前(限 4+清控制骨)。

### 5.3 缺失骨生成(`complete_bones_operator.py`)
- **bug:** `センター/グルーブ` 高度=`bbox*0.125` 魔数(被头发/裙子/道具污染)→飞半空;`センター` tail 在 head 之上(应朝下);`下半身.head=上半身.head` 盲设;`下半身` 硬挂 `腰` 无兜底;X/Y 强制 0(假设已归正);`下半身` 零权重死骨。
- **正确做法:** 从**实测几何**算:骨盆中心 `P=midpoint(左足.head,右足.head)`;`z_floor`=脚骨最低 Z;`全ての親`=(0,0,z_floor);`下半身/センター` tail **朝下**;层级 `全ての親→センター→グルーブ→腰→{下半身;上半身→上半身2→首→頭}`、`全ての親→足IK親`;控制骨空权重。
- **排序:** 改名+归正后,IK/扭转/分组/导出前。

### 5.4 上半身拆分(`complete_bones` / `auto_detect_upper_body_chain`)
- **bug:** 无几何 spine 切分器(单骨 spine 无法拆 上半身/上半身2,也无法分出 下半身);未映射 pelvis→`下半身` 永不生成;**无腰部权重重分配**(骨盆权重留在 上半身);腰分叉锚死 `上半身.head`(若映射到胸则分叉在胸);超 `上半身5` 静默丢骨。
- **正确做法:** 腰分叉点=骨盆顶=`上半身.head==下半身.head==腰.tail` 同点,**上半身朝上、下半身朝下**;单骨 spine **细分**(腰→胸=上半身、胸→颈=上半身2);**按腰部水平面切骨盆顶点权重给上/下半身**;超段**合并不丢**。
- **关键值:** `上半身2` 切在胸/胸骨;`下半身` 方向朝下;MMD 链上限 `上半身2..5`。

### 5.5 扭转骨/D骨/肩P + 付与(`add_twist_bone`/`add_leg_d_bones`/`add_shoulder_p_bones`)
- **bug(重要):** **从不设 `mmd_bone.additional_transform_*`**(grep 零命中)→ 只建了 Blender 约束 + `_shadow_/_dummy_` → **导出 PMX 付与系数=0,扭转骨在 MMD 里啥也不做**;扭转子骨 tail 指 +Z、roll=0 → 轴不对 → candy-wrapper;无 FixedAxis;名/父硬编码(`上半身2`/`下半身`)。
- **正确做法:** 设 `mmd_bone.has_additional_rotation=True`、`additional_transform_bone=主扭转`、`additional_transform_influence=0.25/0.5/0.75`;`足D/ひざD/足首D` influence=1.0 **并把形变权重挪到 D 骨**;`肩C←肩P=-1.0`;扭转骨 **FixedAxis=手臂方向**、轴对齐 head→tail。
- **关键值:** 腕捩/手捩 1/2/3 = 0.25/0.5/0.75;D骨=1.0;肩C=-1.0;腰キャンセル=-1.0;目=1.0。父链 `上半身2→肩P→肩→肩C→腕→腕捩→ひじ→手捩→手首`。
- **排序:** 晚期,**必须在 roll 归一之后**(扭转轴=手臂轴)。

### 5.6 IK(`ik_operator.py`)
- **bug("木棍腿"双因):** IK 约束**错放在 ひざ 上**(`足ＩＫ.head=ひざ.tail`,chain=2)→ 足首没被驱动;**无膝盖前弯**→直腿是 IK 奇异,解不动;双腿骨场景挂到**无权重**骨;ankle damped-track 指向 ひざ(应指趾);重跑叠加约束。
- **正确做法:** 仅在 骨映射+补全+腿合并+roll+缩放 都对之后建。`足ＩＫ` target=`足首`、chain=2`[ひざ,足]`、**约束放足首上**;膝盖先 +Y 微弯(腿长 1~2%);`足IK親(脚底)→足ＩＫ(在足首)→つま先ＩＫ`;父 `全ての親→足IK親`;`use_deform=False`。
- **关键值:** 膝 X 限位 `+0.5°(min)~+180°(max)`,Y/Z 锁 0;迭代 Blender 预览 48(膝)/6(踝);`bone_length=身高/8`。
- **排序:** 骨处理阶段**最后**,严格在 改名/补全/腿合并/roll/Apply Scale 之后。

### 5.7 mmd_tools 转换 + dummy/shadow + 变形顺序(`preset_operator.use_mmd_tools_convert` / `add_twist_bone` / `bone_map_and_group`)
- **现状:** CTMMD **手动预建** `_shadow_{骨}`/`_dummy_{骨}` 编辑骨 + 同名约束(`mmd_additional_rotation` TRANSFORM、`mmd_tools_at_dummy` COPY_TRANSFORMS),并把它们丢进隐藏集合 `mmd_dummy`/`mmd_shadow`;末端调 `bpy.ops.mmd_tools.convert_to_mmd_model(convert_material_nodes=False)`。
- **bug:**
  - 手建的 `_dummy_/_shadow_` **不设 `is_mmd_shadow_bone=True` / `mmd_shadow_bone_type`** → PMX 导出器靠 `if p_bone.is_mmd_shadow_bone: continue` 跳过它们,标志没设 → **有被当真骨导出的风险**;且 mmd_tools 的 `clean_additional_transformation` 不认这些预建骨 → 与规范生成的那套**重复并存**。
  - **从不设 `mmd_bone.has_additional_rotation / additional_transform_bone / additional_transform_influence`** → 导出器读这几个字段写 PMX 付与表;空 → **导出 PMX 完全没有付与数据**(腕捩 1/2/3 的 0.25/0.5/0.75 在 MMD 里失效)。
  - **从不设 `mmd_bone.transform_order`**(默认 0)→ PMX 付与骨的变形层级必须 > 源骨,全 0 会让评估顺序错 → 手臂扭曲。
  - 扭转骨权重 split 缩到 0.65(欠权重,见 §5.5)。
- **正确做法:** ① 等**所有骨齐后**(改名/补全/IK/扭转/D骨/肩P 全做完);② 对每个付与骨设 `mmd_bone.has_additional_rotation=True`、`additional_transform_bone=<源骨>`、`additional_transform_influence=<系数>`(腕捩/手捩 0.25/0.5/0.75、足D/ひざD/足首D=1.0、肩C=-1.0)、`transform_order=1`(源骨留 0);③ 调 `FnBone.apply_additional_transformation()`(或 `bpy.ops.mmd_tools.apply_additional_transform()`)**让 mmd_tools 规范地生成** `_dummy_/_shadow_`(带 `is_mmd_shadow_bone`、正确父子/roll、`use_deform=False`)——**不要手动预建**(CTMMD 的错);④ 再 `convert_to_mmd_model`;⑤ 导出时导出器按 `mmd_bone_order_override` 顶点组索引排序、跳过影子骨、从 RNA 字段写付与。
- **关键值/陷阱:** `influence=0` 会让 mmd_tools **删除**约束(不生成付与);付与源骨在骨数组里须排在付与子骨**之前**(否则 mmd_tools 面板报 ERROR 图标);`_dummy_` 父=源骨、`_shadow_` 父=源骨之父,均 `use_deform=False`;`apply_additional_transformation` 须在全部骨就位后**一次性**调用(否则后加骨的影子几何错位)。
- **要点:** `_dummy_/_shadow_/ダミー` 是 **mmd_tools 对付与的内部"可视化模拟骨",不是导出数据**;真正导出的付与在 `mmd_bone.additional_transform_*` + `transform_order`。
- **排序:** 必然**最后**(所有骨齐了才能转)。

---

## 6. 参考链接
- XPS 导入:`github.com/johnzero7/XNALaraMesh` + fork `mayloglog/XNALaraMesh-blender4.4`、`Valerie-Bosco/XNALara-io-Tools`、`Mysteryem/XNALaraMesh`;Blender Extensions `io_xnalara`。
- PMX 导出:`github.com/MMD-Blender/blender_mmd_tools`(GPL-3.0)。
- 骨名字典:`github.com/absolute-quantum/cats-blender-plugin`(MIT,`tools/armature_bones.py`);`feilen/Tuxedo`、`teamneoneko`。
- 先例:`github.com/uitcis/Convert-to-MMD`(基座)、`Hogarth-MMD/mmd_tools_helper`、`wikid24/ffxiv_mmd_tools_helper`。
- 规范/文档:PMX 2.0/2.1 spec;Blender `blender_manifest.toml` / `extension build`。
- 内部:`/opt/claudework/xps/x_wiki/wiki/`(骨骼映射、材质差异、物理、坐标朝向、Reika 范本)。

---

## 7. 调研出处与可信度说明
- 两轮多智能体工作流:① 可行性+架构(7 路 Survey + 对抗式 Verify:4 confirmed / 1 refuted);② 硬问题剖析(7 路 Dissect,**第 7 条 agent 卡死、Verify 未跑**,该条由人工读码补全)。
- 上述结论**直接引用 CTMMD 真实代码 + mmd_tools/CATS/wiki 实测值**(付与系数取自 Reika 实测、IK 取自 mmd_tools_helper 已知问题),可信度高。
- **最该用真实 XPS 模型回归的三处:** 权重切分、IK 弯曲、付与导出。
