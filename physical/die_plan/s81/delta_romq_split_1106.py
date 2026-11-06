#!/usr/bin/env python3
"""S81 plan event ROMQ-SPLIT-1106 (DIE-S81-70, COORD 13:0x (1) option A): the rom_q hard core
ot_v41_rom_elem_q_qxpq_w10_gb (NB=2, 536.76 x 221.4) becomes its two NB=1 halves, each its own hard core / design:
  <inst>.u_w = ot_v41_rom_elem_q_qxpq_w10_gb_hw (MSEL 0) at the slot origin,
  <inst>.u_e = ot_v41_rom_elem_q_qxpq_w10_gb_he (MSEL 1) at origin + 268.416 um (whole M5 tracks, 0.036 um seam),
both 268.38 x 221.4 (the DIE-S81-65 11-05 split form, RTL ot_v41_rom_elem_q_qxpq_w10_gb_split, 7ed95f56ac; bench
tools/dsrom_qelem_cl/tb_qxpq_split.sv lock-step vs the NB=2 element, mutants caught).  The two halves cover exactly the
old footprint, so no other block moves.  0 added cycles; the col parent gains one OR2 (fault).

Per instance (104 instances, 26 col_h9/h10 types):
  hard_cores  one gb entry -> hw + he entries (pins = the halves' declared pin contracts, LEF = the halves' kit
              abstracts (M5 ceiling; obs_max M5, the parent routes M6/M7 over them), lib = the halves' kit ETMs);
  clock.taps  the early core tap <inst>.ck -> <inst>.u_w.ck + <inst>.u_e.ck, each at the same relative x (and the same
              y) inside its half; insertion = DIE-S81-65 measured half io_reference (TT 465.39 / FF 361.26);
  collector_tree.core_resets  <inst> -> <inst>.u_w + <inst>.u_e on the same reset tap (one reset leaf drives both
              halves' rst_n, which the split wrapper ties together), pin_um / xy at each half's rst_n pin.
Bind (asbuilt): the 2 substitute_inst rows (qxpq_w10 leaf -> _gb) go; the col frame RTL instantiates the split wrapper
(dissolved) with OLAT 1 (the signed halves' parameter; IFN 1 is the wrapper default), the halves are the leaves;
instance_path_params moves from the qxpq_w10 leaf to the two halves.
The plan text is edited in place (each changed JSON value keeps its own line style), so the diff is only these blocks.
    python3 -I delta_romq_split_1106.py PLAN ASBUILT HALVES_JSON REPORT     (cwd = repo root)
"""
import copy
import json
import re
import sys
from pathlib import Path

M = "ot_v41_rom_elem_q_qxpq_w10_gb"
HW, HE = M + "_hw", M + "_he"
SPLIT = M + "_split"
W, H = 268.38, 221.4
# the second half sits 268.416 um east of the first (5592 M5 tracks of 0.048, a 0.036 um seam): 268.38 is not a
# whole number of tracks, so its pins would land off the plan tracks; the 8.64 lattice part goes in origin_um,
# the rest in track_offset_um (G0C hard_cores rule)
DX_E, DX_E_LAT = 268.416, 267.84
# added clock taps that the second clock sink pushes past the 200-um radius: (type base, tap) -> (old xy, new xy)
TAP_MOVES = {("col_h10_r0_p4__t1", "clk_t29"): ([1150.308, 980.6], [1150.344, 997.88]),
             ("col_h9_r0_p3__t1", "clk_t33"): ([1114.56, 505.44], [1114.56, 522.72])}
INS_TT, INS_FF = 465.39, 361.26
EV = "ROMQ-SPLIT-1106 DIE-S81-70 (COORD 13:0x (1) A)"


def spans(text):
    """{path tuple: (start, end)} for every JSON value of text (end exclusive)."""
    out, i = {}, 0
    ws = " \t\r\n"

    def skip(i):
        while i < len(text) and text[i] in ws:
            i += 1
        return i

    def val(i, path):
        i = skip(i)
        s = i
        c = text[i]
        if c == "{":
            i = skip(i + 1)
            if text[i] == "}":
                i += 1
            else:
                while True:
                    i = skip(i)
                    k, i = json.decoder.scanstring(text, i + 1)
                    i = skip(i)
                    assert text[i] == ":"
                    i = val(i + 1, path + (k,))
                    i = skip(i)
                    if text[i] == ",":
                        i += 1
                        continue
                    assert text[i] == "}"
                    i += 1
                    break
        elif c == "[":
            i = skip(i + 1)
            if text[i] == "]":
                i += 1
            else:
                n = 0
                while True:
                    i = val(i, path + (n,))
                    n += 1
                    i = skip(i)
                    if text[i] == ",":
                        i += 1
                        continue
                    assert text[i] == "]"
                    i += 1
                    break
        elif c == '"':
            _, i = json.decoder.scanstring(text, i + 1)
        else:
            m = re.compile(r"-?\d+(\.\d+)?([eE][-+]?\d+)?|true|false|null").match(text, i)
            i = m.end()
        out[path] = (s, i)
        return i

    val(0, ())
    return out


def render_like(old_text, objs, line_indent):
    """objs serialised in the style of old_text (compact one-line or indent-1 multi-line), joined as list items."""
    if "\n" not in old_text:
        sep = ", " if ", " in old_text or ": " in old_text else ","
        compact = (", ", ": ") if ": " in old_text else (",", ":")
        return ("," + ("\n" + line_indent)).join(json.dumps(o, separators=compact) for o in objs)
    # multi-line: indent-1 json, nested lines shifted by the item's indentation
    parts = []
    for o in objs:
        s = json.dumps(o, indent=1)
        parts.append(s.replace("\n", "\n" + line_indent))
    return ("," + "\n" + line_indent).join(parts)


def main():
    sys.path[:0] = ["tools/die_plan", "physical/die_plan/s81"]
    plan_p, ab_p, halves_p, rep_p = map(Path, sys.argv[1:5])
    text = plan_p.read_text()
    P = json.loads(text)
    halves = json.loads(halves_p.read_text())        # {hw|he: {pins_file, lef, lib, tap_dx_frac}}
    sp = spans(text)
    nudged, new_cores = [], {}
    edits, report = [], {"event": EV, "module": M, "halves": [HW, HE], "types": {}}
    for tn, t in P["partition_types"].items():
        hcs = t.get("hard_cores") or []
        idx = [i for i, h in enumerate(hcs) if h.get("module") == M]
        if not idx:
            continue
        taps = (t.get("clock") or {}).get("taps") or []
        lc = (t.get("clock") or {}).get("landing_contract") or {}
        cr = (lc.get("collector_tree") or {}).get("core_resets") or []
        rows = []
        for i in idx:
            h = hcs[i]
            assert h["outline_um"] == [2 * W, H] and h.get("orient", "R0") == "R0", (tn, h["inst"])
            I = h["inst"]
            (x, y), (tx, ty) = h["origin_um"], h.get("track_offset_um", [0.0, 0.0])
            new = []
            for half, mod, dx in (("hw", HW, 0.0), ("he", HE, DX_E)):
                e = {}
                for k, v in h.items():
                    e[k] = v
                e["inst"] = f"{I}.u_{half[1]}"
                e["module"] = mod
                e["lef"] = halves[half]["lef"]
                e["origin_um"] = [round(x + (DX_E_LAT if dx else 0.0), 4), y]
                if dx:
                    e["track_offset_um"] = [round(tx + dx - DX_E_LAT, 4), ty]
                e["outline_um"] = [W, H]
                e["pins_file"] = halves[half]["pins_file"]
                e["obs_max"] = "M5"
                e["note"] = (f"{EV}: {'first' if half == 'hw' else 'second'} half of the former {M} slot "
                             f"(was inst {I}, origin {h['origin_um']}); DIE-S81-65 split form, M5 ceiling")
                e["lib"] = halves[half]["lib"]
                new.append(e)
            new_cores.setdefault(tn, []).append(new)
            a, b = sp[("partition_types", tn, "hard_cores", i)]
            line0 = text.rfind("\n", 0, a) + 1
            edits.append((a, b, render_like(text[a:b], new, text[line0:a])))
            # clock core tap
            ti = [j for j, tp in enumerate(taps) if tp.get("kind") == "core" and tp.get("name") == I + ".ck"]
            assert len(ti) == 1, (tn, I, "core tap")
            tp = taps[ti[0]]
            rel = (tp["xy"][0] - x - tx) / (2 * W)
            nt = []
            for half, dx in (("w", 0.0), ("e", DX_E)):
                e = dict(tp)
                e["name"] = f"{I}.u_{half}.ck"
                e["xy"] = [round(x + tx + dx + rel * W, 4), tp["xy"][1]]
                e["insertion_ps"], e["insertion_ff_ps"] = INS_TT, INS_FF
                e["budget_owner"] = (f"{EV} PLAN UNCHECKED: DIE-S81-65 11-05 measured half io_reference "
                                     f"{INS_TT} TT / {INS_FF} FF (rom_q he/hw core.json clock_contract)")
                e["note"] = f"{EV}: early core tap of half u_{half} at the former gb tap's relative x"
                nt.append(e)
            a, b = sp[("partition_types", tn, "clock", "taps", ti[0])]
            line0 = text.rfind("\n", 0, a) + 1
            edits.append((a, b, render_like(text[a:b], nt, text[line0:a])))
            # reset leaf
            ri = [j for j, r in enumerate(cr) if r.get("inst") == I]
            rr = []
            if ri:
                assert len(ri) == 1
                r = cr[ri[0]]
                pins = {hf: {p["name"]: p for p in json.loads(Path("physical/die_plan/s81", halves[hf]["pins_file"]).read_text())["pins"]}
                        for hf in ("hw", "he")}
                for half, hf, dx in (("w", "hw", 0.0), ("e", "he", DX_E)):
                    pr = pins[hf][r["pin"]]
                    e = dict(r)
                    e["inst"] = f"{I}.u_{half}"
                    px, py = round(x + tx + dx + pr["x"], 4), round(y + ty + pr["y"], 4)
                    e["pin_um"] = [px, py]
                    e["xy"] = [px, r["xy"][1]]
                    rr.append(e)
                a, b = sp[("partition_types", tn, "clock", "landing_contract", "collector_tree", "core_resets", ri[0])]
                line0 = text.rfind("\n", 0, a) + 1
                edits.append((a, b, render_like(text[a:b], rr, text[line0:a])))
            rows.append(dict(inst=I, origin=h["origin_um"], taps=[e["name"] for e in nt], resets=[e["inst"] for e in rr]))
        # an added clock tap that sat exactly on the old slot's east halo edge is now 0.036 um inside the second
        # half's halo: move it east onto the new edge (same rule taps.py applies: on the halo edge is legal)
        ck = t.get("clock") or {}
        if ck.get("tap_mode") == "grid+explicit" and ck.get("added_taps"):
            import schema as S
            from placement_obstacles import placement_boxes
            t2 = copy.deepcopy(t)
            t2["hard_cores"] = [x for x in hcs if x.get("module") != M] + [e for r in new_cores[tn] for e in r]
            boxes = placement_boxes(t2, halo=S.TAP_CLEAR_UM)
            for j, ptap in enumerate(ck["added_taps"]):
                px, py = map(float, ptap["xy"])
                mv = TAP_MOVES.get((tn.split("__cl")[0], ptap["name"]))
                if mv is not None:
                    # the split adds a second clock sink 268 um east per core: this added tap's farthest sink went past
                    # the 200-um tap radius (taps.grid_explicit_sites); smallest legal move found by a 4.32-um search
                    assert [px, py] == mv[0], (tn, ptap, mv)
                    a, b = sp[("partition_types", tn, "clock", "added_taps", j, "xy", 1)]
                    edits.append((a, b, json.dumps(mv[1][1])))
                    if mv[1][0] != px:   # also off the second half's halo (east edge)
                        a, b = sp[("partition_types", tn, "clock", "added_taps", j, "xy", 0)]
                        edits.append((a, b, json.dumps(mv[1][0])))
                    nudged.append(dict(type=tn, tap=ptap["name"], xy_old=[px, py], xy_new=mv[1], why="radius"))
                    continue
                hit = [(k, b) for k, b in boxes.items() if b[0] + 1e-8 < px < b[2] - 1e-8 and b[1] + 1e-8 < py < b[3] - 1e-8]
                if not hit:
                    continue
                assert len(hit) == 1 and hit[0][0].endswith(".u_e") and hit[0][1][2] - px < 0.05, (tn, ptap, hit)
                nx = round(hit[0][1][2], 4)
                a, b = sp[("partition_types", tn, "clock", "added_taps", j, "xy", 0)]
                edits.append((a, b, json.dumps(nx)))
                nudged.append(dict(type=tn, tap=ptap["name"], x_old=px, x_new=nx, core=hit[0][0]))
        report["types"][tn] = rows
    edits.sort()
    for (a1, b1, _), (a2, _, _) in zip(edits, edits[1:]):
        assert b1 <= a2, "overlapping edits"
    out = text
    for a, b, s in sorted(edits, reverse=True):
        out = out[:a] + s + out[b:]
    Q = json.loads(out)
    # semantic check: the result equals the intended object edit
    want = copy.deepcopy(P)
    for tn, rows in report["types"].items():
        t = want["partition_types"][tn]
        got = Q["partition_types"][tn]
        n_old = sum(1 for h in t["hard_cores"] if h.get("module") == M)
        assert sum(1 for h in got["hard_cores"] if h.get("module") in (HW, HE)) == 2 * n_old
        assert not any(h.get("module") == M for h in got["hard_cores"])
        for k in t:
            if k not in ("hard_cores", "clock"):
                assert t[k] == got[k], (tn, k)
        for k in t["clock"]:
            if k not in ("taps", "landing_contract", "added_taps"):
                assert t["clock"][k] == got["clock"][k], (tn, k)
        for k in t["clock"].get("landing_contract", {}):
            if k != "collector_tree":
                assert t["clock"]["landing_contract"][k] == got["clock"]["landing_contract"][k], (tn, k)
    for k in P:
        if k != "partition_types":
            assert P[k] == Q[k], k
    for tn in P["partition_types"]:
        if tn not in report["types"]:
            assert P["partition_types"][tn] == Q["partition_types"][tn], tn
    plan_p.write_text(out)
    report["instances"] = sum(len(v) for v in report["types"].values())
    report["added_tap_nudges"] = nudged
    # asbuilt
    ab_text = ab_p.read_text()
    AB = json.loads(ab_text)
    sa = spans(ab_text)
    ab_edits = []
    subs = AB["substitute_inst"]
    gone = [j for j, r in enumerate(subs) if r["module"] == M]
    assert len(gone) == 2, gone
    # the gb rows are the list's tail: cut from the end of the last kept row to the end of the last row
    assert gone == list(range(len(subs) - len(gone), len(subs))) and len(gone) < len(subs), gone
    ab_edits.append((sa[("substitute_inst", gone[0] - 1)][1], sa[("substitute_inst", len(subs) - 1)][1], ""))
    ipp = AB["instance_path_params"]
    j = next(j for j, r in enumerate(ipp) if r["module"] == "ot_v41_rom_elem_q_qxpq_w10")
    a, b = sa[("instance_path_params", j)]
    ab_edits.append((a, b, json.dumps({"module": HW, "param": "INSTANCE"}) + ", " + json.dumps({"module": HE, "param": "INSTANCE"})))
    a, b = sa[("dissolve", len(AB["dissolve"]) - 1)]
    ab_edits.append((b, b, ", " + json.dumps(SPLIT)))
    gbf = "rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb.sv"
    fj = AB["files"].index(gbf)
    a, b = sa[("files", fj)]
    ab_edits.append((b, b, ", " + json.dumps("rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb_split.sv")))
    # hard_params sidecars: the frame kit stripped the #() of the qxpq_w10 leaf and bind_elab baked the hardened set
    # into its lib stub.  That leaf is gone (the split wrapper is a dissolved body whose parameter defaults ARE that
    # set, asserted below; the halves are leaves with explicit #() from the wrapper), so the sidecars this asbuilt reads
    # are copies without the qxpq_w10 master (bind_elab fails closed on a hardened master with no leaf stub)
    hp_new = []
    for j, f in enumerate(AB["hard_params"]):
        rec = json.loads(Path(f).read_text())
        hs = rec["masters"].pop("ot_v41_rom_elem_q_qxpq_w10")
        rec["sites"].pop("ot_v41_rom_elem_q_qxpq_w10", None)
        sp_src = Path("rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb_split.sv").read_text()
        hdr = sp_src[sp_src.index(f"module {SPLIT}"):sp_src.index(") (", sp_src.index(f"module {SPLIT}"))]
        dflt = dict(re.findall(r"parameter\s+(?:integer\s+)?(\w+)\s*=\s*([^,\s]+)", hdr))
        assert {k: v for k, v in hs.items() if k != "NB"} == {k: dflt[k] for k in hs if k != "NB"} and hs["NB"] == "2", hs
        rec["note"] += (" | DIE-S81-70 11-06 rom_q split event: ot_v41_rom_elem_q_qxpq_w10 dropped (now the dissolved "
                        f"{SPLIT} wrapper, defaults = that hardened set, NB 2 = the two NB 1 halves); copy of {f}")
        nf = f.replace(".hard_params.json", "_romq_split.hard_params.json")
        assert nf != f
        Path(nf).write_text(json.dumps(rec, indent=1) + "\n")
        a, b = sa[("hard_params", j)]
        ab_edits.append((a, b, json.dumps(nf)))
        hp_new.append(nf)
    report["hard_params"] = hp_new
    for a, b, s in sorted(ab_edits, reverse=True):
        ab_text = ab_text[:a] + s + ab_text[b:]
    AB2 = json.loads(ab_text)
    assert AB2["hard_params"] == hp_new
    assert [r for r in AB2["substitute_inst"]] == [r for r in subs if r["module"] != M]
    assert SPLIT in AB2["dissolve"] and "rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10_gb_split.sv" in AB2["files"]
    ab_p.write_text(ab_text)
    report["asbuilt"] = dict(removed_substitute_rows=[subs[j]["inst"][:60] + "..." for j in gone],
                             dissolve_add=SPLIT, instance_path_params=[HW, HE])
    # RTL: col frame sources
    rtl = {}
    for f in ("rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h10_l4_lp_plan_kit.sv",
              "rtl/dsrom_sys/s81_dv/frame_lp/plan/col_h9_l4_lp_plan_kit.sv"):
        src = Path(f).read_text()
        n_lines = src.count("\n")
        pat = re.compile(r"^(\s*)ot_v41_rom_elem_q_qxpq_w10 (u_e\d+ \()(.*)$", re.M)
        cnt = 0

        def fix(m):
            nonlocal cnt
            cnt += 1
            body, k = re.subn(r"\.xs_sv\(\{[^}]*\}\), ", "", m.group(3))
            assert k == 1, m.group(2)
            return f"{m.group(1)}{SPLIT} #(.OLAT(1)) {m.group(2)}{body}"

        src2 = pat.sub(fix, src)
        assert src2.count("\n") == n_lines and cnt == 16, (f, cnt)
        Path(f).write_text(src2)
        rtl[f] = cnt
    report["rtl"] = rtl
    Path(rep_p).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(dict(types=len(report["types"]), instances=report["instances"], rtl=rtl)))


if __name__ == "__main__":
    main()
