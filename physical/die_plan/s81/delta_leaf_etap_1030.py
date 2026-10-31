#!/usr/bin/env python3
"""DIE-S81-37 one-block clock-entry fix (12.20; COORD 15:44 (2) + S81-CORES-KITS-6 ASK 17:57, default APPROVED form =
DIE-S81-36/ATTNTAP): parent early core tap rows for the rt 2x2 leaf cores, at the kit-measured CTS tap means
(S81-CORES-KITS-6 ot_rt_ck_cts_tt.tsv; kits are IO-referenced to these values, core_io_reference plan_declared form):
  ot_s81sl_ve_m TT 359.0 / FF 290.8   (existing rows, were 308.4 / 252.8 CORELAT-SQ-1)
  ot_s81sl_vn_a TT 385.4 / FF 312.2   (existing rows, were 386.0 / 323.4)
  ot_s81sl_vn_b TT 390.9 / FF 316.6   (existing rows, were 387.0 / 324.3)
  ot_s81sl_vq   TT 327.8 / FF 265.5   (NEW rows: vq had no early tap; xy = pins_file clk transformed by orient)
FF = 0.81 x TT DERIVED (no FF view), all values CTS-only placement RC, UNCHECKED until the kits' signed routed means
replace them.  Only those rows (insertion_ps / insertion_ff_ps / budget_owner / note) change, and the vq rows are
appended to the type's clock.taps (types with core_taps 'early' only).  Rest of the plan byte-identical
(textual edit, json equality asserted).
usage (repo root): delta_leaf_etap_1030.py PLAN   (rewrites PLAN in place; a second run refuses)"""
import json
import re
import sys

VAL = {"ot_s81sl_ve_m": (359.0, 290.8, "ve_m rt22m kit, tap means 358-360"),
       "ot_s81sl_vn_a": (385.4, 312.2, "vn_a rt22a kit"),
       "ot_s81sl_vn_b": (390.9, 316.6, "vn_b rt22 kit, n=29944, 372.7-447.8"),
       "ot_s81sl_vq": (327.8, 265.5, "vq rt6 kit, n=10314, 308.8-360.0")}
VQ_PINS = "physical/die_plan/s81/inputs/core_pins/ot_s81sl_vq_tpl.json"


def owner(m):
    tt, ff, src = VAL[m]
    return ("parent_budget CTS tap mean OpenSTA placement-RC (S81-CORES-KITS-6 %s ot_rt_ck_cts_tt.tsv; NOT SIGNED, not "
            "extracted); FF %.1f = 0.81 x TT DERIVED, UNCHECKED (no FF view); DIE-S81-37 2026-10-30; replace with the "
            "SIGNED routed means at sign-off" % (src, ff))


NOTE = "early core tap (12.3 v5.0) for the rt 2x2 leaf core (COORD 15:44 (2), S81-CORES-KITS-6 ASK 17:57); DIE-S81-37"
NOTE_VQ = NOTE + "; xy = pins_file clock pin clk transformed by orient + track_offset"


def xf(h, px, py):
    (ox, oy), (w, hh) = h["origin_um"], h["outline_um"]
    o = h["orient"]
    x = {"R0": px, "MX": px, "MY": w - px, "R180": w - px}[o]
    y = {"R0": py, "MX": hh - py, "MY": py, "R180": hh - py}[o]
    dx, dy = h.get("track_offset_um", [0.0, 0.0])
    return [round(ox + x + dx, 4), round(oy + y + dy, 4)]


def jstr(s):
    return json.dumps(s)


def main():
    pp = sys.argv[1]
    text = open(pp).read()
    plan = json.loads(text)
    pt = plan["partition_types"]
    want = json.loads(text)
    vqpin = next(q for q in json.load(open(VQ_PINS))["pins"] if q["name"] == "clk")
    stats = {m: 0 for m in VAL}
    types = 0
    # process types in reverse text order so earlier offsets stay valid
    spans = []
    for tn in pt:
        m = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, end = json.JSONDecoder().raw_decode(text, m.end())
        spans.append((m.end(), end, tn))
    for start, end, tn in sorted(spans, reverse=True):
        t = pt[tn]
        ck = t.get("clock") or {}
        hcs = {h["inst"]: h for h in t.get("hard_cores", [])}
        rows = ck.get("taps") or []
        upd = []
        for i, r in enumerate(rows):
            if r.get("kind") != "core":
                continue
            h = hcs.get(r["name"].rsplit(".", 1)[0])
            if h and h["module"] in VAL and h["module"] != "ot_s81sl_vq":
                upd.append((i, h["module"]))
        vqs = [h for h in t.get("hard_cores", []) if h["module"] == "ot_s81sl_vq"]
        if vqs:
            assert ck.get("core_taps") == "early", (tn, "vq in a type without early core taps")
            assert not any(r["name"] == h["inst"] + ".clk" for h in vqs for r in rows), (tn, "vq row exists: rerun?")
        if not upd and not vqs:
            continue
        types += 1
        seg = text[start:end]
        wrows = want["partition_types"][tn]["clock"]["taps"]
        for i, m in upd:
            tt, ff, _ = VAL[m]
            assert rows[i]["insertion_ps"] != tt or rows[i]["budget_owner"] != owner(m), (tn, "already applied")
            wrows[i]["insertion_ps"] = tt
            wrows[i]["insertion_ff_ps"] = ff
            wrows[i]["budget_owner"] = owner(m)
            wrows[i]["note"] = NOTE
            a = seg.index('"name": ' + jstr(rows[i]["name"]) + ",")
            for key, old, new in (("insertion_ps", rows[i]["insertion_ps"], tt),
                                  ("insertion_ff_ps", rows[i]["insertion_ff_ps"], ff),
                                  ("budget_owner", rows[i]["budget_owner"], owner(m)),
                                  ("note", rows[i]["note"], NOTE)):
                pat = '"%s": %s' % (key, jstr(old))
                k = seg.index(pat, a)
                seg = seg[:k] + '"%s": %s' % (key, jstr(new)) + seg[k + len(pat):]
            stats[m] += 1
        if vqs:
            tt, ff, _ = VAL["ot_s81sl_vq"]
            new = [dict(name=h["inst"] + ".clk", kind="core", xy=xf(h, vqpin["x"], vqpin["y"]), insertion_ps=tt,
                        insertion_ff_ps=ff, budget_owner=owner("ot_s81sl_vq"), note=NOTE_VQ) for h in vqs]
            wrows.extend(new)
            # insert before the closing bracket of clock.taps
            ci = seg.index('"clock": ')
            ti = seg.index('"taps": [', ci)
            arr0 = ti + len('"taps": ')
            _, aend = json.JSONDecoder().raw_decode(seg, arr0)
            close = aend - 1
            assert seg[close] == "]"
            ls = seg.rfind("\n", 0, ti) + 1
            ind = seg[ls:ti]
            rind = ind + " "
            body = ",\n".join(rind + json.dumps(r, indent=1).replace("\n", "\n" + rind) for r in new)
            before = seg[:close].rstrip()
            sep = "," if before.endswith("}") else ""
            seg = before + sep + "\n" + body + "\n" + ind + seg[close:]
            stats["ot_s81sl_vq"] += len(new)
        text = text[:start] + seg + text[end:]
    assert json.loads(text) == want, "unexpected plan edit"
    open(pp, "w").write(text)
    print(types, "types;", ", ".join("%s %d" % (k, v) for k, v in stats.items()))


if __name__ == "__main__":
    main()
