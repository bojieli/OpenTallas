#!/usr/bin/env python3
"""DIE-S81-39 one-block clock-entry fix (12.20 / 12.3 v5.0 early taps; COORD 18:59: routed arrivals only).
Parent early core tap rows for the S81 leaf/attention hard cores at the ROUTED pin-register clock arrival means
(same pin_register_mean form as the existing rows), read from the cores' own routed 6_final view sign-off runs at
flow tag e-s81 (S81-CORES-KITS-7, resign.py signoff.json corners.{tt,ff}.insertion_pinflops; OpenSTA + 6_final.spef):
  ot_s81sl_ve_m      TT 374.24 / FF 304.76  rt22m two-mode (n=1260), was 308.4 / 252.8 (CTS probe)
  ot_s81sl_vn_a      TT 424.07 / FF 343.61  rt22a (n=914), was 386.0 / 323.4 (CTS probe)
  ot_s81c_attn_hcore TT 364.38 / FF 291.94  rt22m (n=1213), was 354.2 / 286.9 (CTS-only rt22 probe)
  ot_s81sl_vq        TT 341.37 / FF 268.48  rt6e_hx3 SIGNED (n=700), NEW rows (vq had no early tap;
                     xy = pins_file clk transformed by orient + track_offset)
ot_s81sl_vn_b is NOT changed (no routed view yet: rt22a still in GRT repair) -> its rows keep 387.0 / 324.3.
FF values are the routed FF-corner views (no 0.81 derivation).  Only those rows (insertion_ps / insertion_ff_ps /
budget_owner / note) change, and the vq rows are appended to the type's clock.taps (types with core_taps 'early'
only).  Rest of the plan byte-identical (textual edit, json equality asserted).  Base: DIE-S81-37 3ea69f6887f.
usage (repo root): delta_leaf_etap_1030.py PLAN   (rewrites PLAN in place; a second run refuses)"""
import json
import re
import sys

VAL = {"ot_s81sl_ve_m": (374.24, 304.76, "ve_m rt22m two-mode, epyc2 /srv/opentallas-scratch2/claude/s81ck7/ve_m_rt22m_resign_e-s81 NOT SIGNED (drv slew)"),
       "ot_s81sl_vn_a": (424.07, 343.61, "vn_a rt22a, epyc2 /srv/opentallas-scratch2/claude/s81ck7/vn_a_rt22a_resign_e-s81 NOT SIGNED (hold/skew)"),
       "ot_s81c_attn_hcore": (364.38, 291.94, "attn rt22m two-mode, epyc2 /srv/opentallas-scratch2/claude/s81ck7/attn_rt22m_resign_e-s81 NOT SIGNED"),
       "ot_s81sl_vq": (341.37, 268.48, "vq rt6e_hx3, intel1 /srv/opentallas-scratch2/claude/s81ck7/vq_rt6e_hx3_resign_e-s81 SIGNED")}
VQ_PINS = "physical/die_plan/s81/inputs/core_pins/ot_s81sl_vq_tpl.json"


def owner(m):
    tt, ff, src = VAL[m]
    return ("parent_budget pin_register_mean ROUTED 6_final+SPEF OpenSTA TT/FF (signoff.json insertion_pinflops, flow tag "
            "e-s81; %s); FF %.2f measured on the routed FF view; DIE-S81-39 2026-10-30; refresh if the counted sign-off "
            "view differs" % (src, ff))


NOTE = "early core tap (12.3 v5.0) at the routed core view (COORD 15:44 (2) + 18:59 routed arrivals only); DIE-S81-39"
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
