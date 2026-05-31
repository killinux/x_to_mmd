"""Complete the MMD standard rig (bpy): add the control / semi-standard bones the
source lacks, fix the torso hierarchy, and set append-transform (付与) metadata.

All added bones are non-deform, EMPTY-weight control bones — so this touches NO
skin weights (no split, no integrity risk; CLAUDE.md §1/§2 satisfied). Twist
bones are added as 付与 controls only; moving forearm skin onto them would be a
weight split and is intentionally NOT done here.
"""
from __future__ import annotations

from math import radians

import bpy  # type: ignore
from mathutils import Vector  # type: ignore


def _v(b):
    return Vector(b.head), Vector(b.tail)


def add_mmd_rig(arm_obj):
    arm = arm_obj.data
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.edit_bones
    added = []

    def g(name):
        return eb.get(name)

    def mk(name, head, tail, parent):
        b = eb.get(name)
        if b is None:
            b = eb.new(name)
            added.append(name)
        b.head = head
        b.tail = tail
        b.use_connect = False
        b.use_deform = False
        b.parent = eb.get(parent) if isinstance(parent, str) else parent
        return b

    def reparent(child, parent):
        c = eb.get(child)
        if c is not None:
            c.parent = eb.get(parent) if isinstance(parent, str) else parent

    # ---- anchors ----
    allp = g("全ての親")
    center = g("センター")
    up = g("上半身")
    head_b = g("頭")
    eyeL, eyeR = g("左目"), g("右目")

    up_len = (Vector(up.tail) - Vector(up.head)).length if up else 0.3
    L = max(up_len, 0.1)

    # ---- root chain: 操作中心 / グルーブ / 腰, and fix torso fork ----
    legL, legR = g("左足"), g("右足")
    if center:
        # reposition センター to the true centre-of-gravity (pelvis = midpoint of
        # the thigh joints), not the source 'root hips' which sits too high.
        if legL and legR:
            waist = (Vector(legL.head) + Vector(legR.head)) * 0.5
            waist.x = 0.0
            center.head = waist
            center.tail = waist + Vector((0, 0, L * 0.4))
        ch = Vector(center.head)
        mk("操作中心", Vector((0, 0, 0)), Vector((0, 0, L)), None)
        mk("グルーブ", ch, ch + Vector((0, 0, L * 0.4)), "センター")
        mk("腰", ch, ch + Vector((0, 0, L * 0.5)), "グルーブ")
        reparent("下半身", "腰")
        reparent("上半身", "腰")     # source had 上半身 under 下半身 — fix to MMD fork
        if g("左胸"):
            reparent("左胸", "上半身")
        if g("右胸"):
            reparent("右胸", "上半身")

    # ---- 両目 + eye grant ----
    if head_b and eyeL and eyeR:
        mid = (Vector(eyeL.head) + Vector(eyeR.head)) * 0.5
        mk("両目", mid + Vector((0, 0, L * 0.4)), mid + Vector((0, 0, L * 0.7)), "頭")

    # ---- per-side limbs ----
    for s, jp in (("左", "L"), ("右", "R")):
        leg, ank, toe = g(s + "足"), g(s + "足首"), g(s + "つま先")
        sh, arm_b, elb, wri = g(s + "肩"), g(s + "腕"), g(s + "ひじ"), g(s + "手首")
        chest = g("上半身3") or g("上半身2") or g("上半身")

        # 腰キャンセル + reparent leg
        if leg and g("腰"):
            wh = Vector(g("腰").head)
            mk("腰キャンセル" + s, wh, wh + Vector((0, 0, -L * 0.3)), "下半身")
            reparent(s + "足", "腰キャンセル" + s)

        # leg IK bones (control only; IK constraints added in add_leg_ik)
        if ank:
            ah = Vector(ank.head)
            floor = Vector((ah.x, ah.y, 0.0))
            mk(s + "足IK親", floor, ah, "全ての親")
            mk(s + "足ＩＫ", ah, ah + Vector((0, -L * 0.4, 0)), s + "足IK親")
            if toe:
                th = Vector(toe.head)
                mk(s + "つま先ＩＫ", th, th + Vector((0, 0, -L * 0.3)), s + "足ＩＫ")

        # leg D-bones (足D/ひざD/足首D/足先EX) — control-only 付与 copies (no weight split)
        if leg:
            dparent = ("腰キャンセル" + s) if g("腰キャンセル" + s) else "下半身"
            for jp in ("足", "ひざ", "足首"):
                vis = g(s + jp)
                if vis:
                    mk(s + jp + "D", Vector(vis.head), Vector(vis.tail), dparent)
                    dparent = s + jp + "D"
            if toe and g(s + "足首D"):
                mk(s + "足先EX", Vector(toe.head), Vector(toe.tail), s + "足首D")

        # shoulder P/C + reparent arm chain
        if sh and arm_b and chest:
            shh = Vector(sh.head)
            mk(s + "肩P", shh, shh + Vector((0, 0, L * 0.2)), chest.name)
            reparent(s + "肩", s + "肩P")
            ah = Vector(arm_b.head)
            mk(s + "肩C", ah, ah + Vector((0, 0, -L * 0.1)), s + "肩")
            reparent(s + "腕", s + "肩C")

        # arm twist 腕捩 / 手捩 (+1/2/3), control-only
        def twist(prefix, a, b):
            if not (a and b):
                return
            A, B = Vector(a.head), Vector(b.head)
            d = B - A
            mk(s + prefix, A + d * 0.5, A + d * 0.6, a.name)
            for i, t in enumerate((0.25, 0.5, 0.75), start=1):
                mk(s + prefix + str(i), A + d * t, A + d * (t + 0.05), a.name)

        twist("腕捩", arm_b, elb)
        twist("手捩", elb, wri)

        # ダミー
        if wri:
            wh = Vector(wri.head)
            mk(s + "ダミー", wh, wh + Vector((0, -L * 0.2, 0)), s + "手首")

        # finger-0 (palm) bones for index/middle/ring/little, reparent finger1
        for jpn, eng in (("人指", "人指"), ("中指", "中指"), ("薬指", "薬指"), ("小指", "小指")):
            f1 = g(s + jpn + "１")
            if wri and f1:
                wh, fh = Vector(wri.head), Vector(f1.head)
                mid = wh + (fh - wh) * 0.6
                mk(s + jpn + "０", mid, fh, s + "手首")
                reparent(s + jpn + "１", s + jpn + "０")

    bpy.ops.object.mode_set(mode="OBJECT")

    # ---- append transform (付与) on pose bones ----
    pb = arm_obj.pose.bones

    def grant(name, src, influence, order=1):
        p = pb.get(name)
        s = pb.get(src)
        if p is None or s is None:
            return
        mb = p.mmd_bone
        mb.has_additional_rotation = True
        mb.additional_transform_bone = src
        mb.additional_transform_influence = influence
        mb.transform_order = order

    grants = 0
    for s in ("左", "右"):
        if pb.get(s + "肩C") and pb.get(s + "肩P"):
            grant(s + "肩C", s + "肩P", -1.0); grants += 1
        if pb.get("腰キャンセル" + s) and pb.get("腰"):
            grant("腰キャンセル" + s, "腰", -1.0); grants += 1
        for i, w in ((1, 0.25), (2, 0.5), (3, 0.75)):
            if pb.get(s + "腕捩" + str(i)):
                grant(s + "腕捩" + str(i), s + "腕捩", w); grants += 1
            if pb.get(s + "手捩" + str(i)):
                grant(s + "手捩" + str(i), s + "手捩", w); grants += 1
        if pb.get(s + "目") and pb.get("両目"):
            grant(s + "目", "両目", 1.0); grants += 1
        for jp in ("足", "ひざ", "足首"):
            if pb.get(s + jp + "D") and pb.get(s + jp):
                grant(s + jp + "D", s + jp, 1.0); grants += 1

    return {"added_bones": len(added), "grants": grants, "bones_total": len(arm.bones)}


def add_leg_ik(arm_obj):
    """Add MMD leg IK as Blender pose-bone IK constraints (mmd_tools exports these
    as PMX IK). 足ＩＫ drives 足首 over chain [ひざ,足]; つま先ＩＫ drives the toe.
    Knee gets an X-axis limit so it bends forward (avoids the straight-leg singularity).
    """
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    n = 0
    for s in ("左", "右"):
        ank, ikb = pb.get(s + "足首"), pb.get(s + "足ＩＫ")
        toe, toeik = pb.get(s + "つま先"), pb.get(s + "つま先ＩＫ")
        knee = pb.get(s + "ひざ")
        if ank and ikb:
            c = ank.constraints.new("IK")
            c.name = "mmd_ik"
            c.target = arm_obj
            c.subtarget = s + "足ＩＫ"
            c.chain_count = 2
            n += 1
        if knee:
            knee.use_ik_limit_x = True
            knee.ik_min_x = radians(0.5)
            knee.ik_max_x = radians(180.0)
            knee.lock_ik_y = True
            knee.lock_ik_z = True
        if toe and toeik:
            c = toe.constraints.new("IK")
            c.name = "mmd_ik_toe"
            c.target = arm_obj
            c.subtarget = s + "つま先ＩＫ"
            c.chain_count = 1
            n += 1
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ik_constraints": n}

