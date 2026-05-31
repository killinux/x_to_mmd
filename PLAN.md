# x_to_mmd 实施方案

> 一个 Blender 插件:把**任意 XPS/XNALara 模型自动转换成 MMD(PMX)**。
> 依据见 [RESEARCH.md](RESEARCH.md);进度见 [PROGRESS.md](PROGRESS.md)。

---

## 0. 决策摘要
- **基座:fork `uitcis/Convert-to-MMD`(CTMMD)**(GPL-3.0,Blender 3.0+),它已实现"转换层"(预设改名/补全骨/IK/足D-肩P-扭转/显示枠/胸+身体物理/调 mmd_tools)。署名原作者 UITCIS(Gitee / B站)。
- **架构:混合**。导入=vendor XPS 解析(或集成 xps_tools fork);转换=自研智能;**导出=驱动 mmd_tools**(不自研 PMX 写出器)。
- **许可证:GPL-3.0-or-later;目标 Blender 4.2+ Extension(`blender_manifest.toml`)。输出 PMX 2.0 / BDEF。**
- **范围外:** 表情生成(lossy,只搭脚手架)、SDEF/材质绘制顺序/准标准ボーン插件(PMXEditor 交接)。

## 1. 核心结论:先补两个地基
CTMMD 几乎所有问题是**两个缺失地基**的下游症状,**必须最先做**:
1. **骨名归一化 + 拓扑识别层** —— 否则真实 rip 换分隔符/前缀就匹配 0 命中,`下半身` 缺失、`上半身` 无从拆。
2. **权重安全转移层** —— 否则改名静默脱钩、合并删骨丢权重、新建 `下半身`/D骨 零权重死骨。

---

## 2. 实现顺序(build order,MVP 优先)

| 阶段 | 交付物 | 依赖 |
|---|---|---|
| **P0 地基(MVP)** | ① XPS 导入前端(`.xps/.mesh/.ascii`→骨架,轴翻转只一次,权重完整,>4 裁 top-4)② **权重安全转移模块**(原子改名/合并:网格侧组先改/合并→改骨名→刷 depsgraph;**含 `weight_integrity_check` 检查器**,补全/IK/扭转前后调用,丢权重报警)③ **骨映射解析器**(归一化+别名字典[CATS MIT]+拓扑兜底+人工确认)④ 变换/原点/缩放/脚底 归正 | — |
| **P1 骨结构** | ⑤ 实测几何生成缺失骨(骨盆中心=`midpoint(左足.head,右足.head)`、脚底=最低 Z;`下半身/センター` tail 朝下;控制骨空权重)⑥ 上半身拆分(**优先复用 XPS 现有骨权重;切分权重需用户确认** —— 见 [CLAUDE.md](CLAUDE.md) 强约束) | P0 |
| **P2 IK** | ⑦ arm/leg 链 roll 归一(`ひざ roll=0`)⑧ 腿 IK:约束放**足首**上、`足ＩＫ` target=足首 chain=2[ひざ,足]、膝盖 +Y 微弯、挂到带权重的形变骨 | P1 |
| **P3 次标准骨** | ⑨ 扭转骨/D骨/肩P + **真·付与**(设 `mmd_bone.additional_transform_bone/influence`,非仅 Blender 约束;扭转骨 FixedAxis=手臂方向;D骨搬运形变权重) | P2 |
| **P4 收尾** | ⑩ Limit Total=4 + 重归一 + 清控制骨权重 ⑪ 显示枠 ⑫ 材质(置白 diffuse / 默认 toon / 开描边 / 剥 `_N/_AO/_s`)⑬ 物理模板(扩 CTMMD 现有胸/身体物理到头发/裙子) | P1+ |
| **P5** | QA 报告(对标 `导出前qa清单`)、Blender/mmd_tools 版本探测、PMXEditor 交接文档、一键流水线(各步可单独重跑) | 全部 |

---

## 3. 运行期 pipeline(操作在模型上的先后)

```
① 导入(.xps/.mesh/.ascii → 骨架+网格,(x,-z,y)+绕序[0,2,1]+v→1-v 只一次)
② 归正(应用变换 / 原点移到骨盆下 / 脚底 z=0 / 统一缩放)   ← 任何几何判断之前
③ 骨名归一化 + 拓扑映射(产出 MMD 名;歧义弹确认)          ← 第一个语义步
④ 权重安全改名(网格侧组先改/合并 → 改骨名 → 刷 depsgraph)
⑤ 合并重复/垃圾骨(ADD 权重再删;双腿骨保留带权重的形变骨)
⑥ 上半身拆分(上半身朝上/下半身朝下,同点分叉;**权重优先复用、切分需用户确认** —— 见 CLAUDE.md)
⑦ 缺失骨(实测几何;控制骨空权重;**补全前后跑权重完整性检查,丢权重即报警停下**)
⑧ roll 归一(arm/leg 链)
⑨ 腿 IK(约束放足首;膝盖预弯;足IK親→全ての親)
⑩ 扭转骨/D骨/肩P + 付与(mmd_bone.additional_transform_*;FixedAxis)
⑪ Limit Total=4 + 重归一 + 清控制骨权重
⑫ 显示枠 ; 材质(可并行)
⑬ mmd_tools convert_to_mmd_model(它生成 _dummy_/_shadow_ + 变形层级)→ 导出 PMX 2.0
```
> 每步的"怎么做 / 修了 CTMMD 什么 bug / 关键值",见 RESEARCH.md §5。

---

## 4. 贯穿全程的不变量(每步都要守)
1. **改名=原子操作**:网格侧顶点组先改/合并 → 再改骨名 → 再刷 depsgraph;永不靠 Blender 隐式联动。
2. **删骨前必先 ADD 权重**;任何合并/拆分后**每顶点权重重归一到 1.0**。
3. **控制骨(全ての親/センター/グルーブ/腰/IK/肩P/足IK親)永远空权重 + `use_deform=False`**。
4. **轴翻转只在导入做一次**;中间绝不再翻。
5. **只归一化"源"骨名;MMD 目标名按动作库惯例输出全/半角**(VMD 字节精确匹配)。
6. **几何判断(L/R、骨盆中心、bone_length)只在归正后做。**
7. **付与/扭转的真相在 `mmd_bone.additional_transform_*`,不在 Blender 约束;dummy/shadow 交给 mmd_tools 生成,不要预建。**

---

## 5. MVP 定义与验收
- **MVP = P0:** 输入单个 `.xps/.mesh/.ascii` → 产出**能在 MMD 加载、面朝前、比例正确、权重完整、骨名为 MMD 标准**的 PMX(无 IK/物理/表情亦可)。
- **验收回归(必须用真实 XPS 模型):**
  1. 改名后**权重不脱钩**(肢体跟随 MMD 骨)。
  2. 加一个通用 VMD,标准骨能动、不穿模、不躺倒/镜像。
  3. (P2 后)膝盖能弯、非"木棍腿"。
  4. (P3 后)`腕捩/手捩` 在 MMD 里真生效(付与系数≠0)。

## 6. 风险
- **期望落差**(最高非技术风险):输出是"未精修的 XPS rip"基线,UI/README 要讲清"自动做了什么 / 要手工什么"。
- **mmd_tools 内部 API 耦合**:`exporter.export()` 是内部函数 → 锁版本范围 + 薄适配层 + 公开算子 `export_pmx` 兜底。
- **全/半角**:VMD 字节匹配,生成名宽度必须对齐动作库。
- **>4 权重**:导出前 `Limit Total=4`,否则 mmd_tools 任意裁 top-4 丢关键骨。
- **坐标/绕序/UV**:翻转只一次;facing 视觉回归。

## 7. 待决问题
1. **导入前端:** vendor 原生 XPS 解析器(一站式)vs 要求装 xps_tools fork(更快到 MVP)?
2. **人工确认 UI 粒度:** 歧义项(pelvis→下半身 vs センター、spine 切分点)做到多细?
3. **测试模型:** 需要 1–2 个真实 XPS 模型做权重/IK/付与回归。
4. **fork 形态:** 直接 fork CTMMD 改造,还是新建仓库 + 移植其模块?(倾向 fork,保留 git 历史与署名)
