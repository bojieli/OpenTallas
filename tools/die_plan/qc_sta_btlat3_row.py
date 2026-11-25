#!/usr/bin/env python3
"""QC-STA-BTLAT3 11-25: two st_a rows for C1o (FABLE-RC-QC 00:14 'RC st_a' (b), COORD ruling).

Row STA-BTSEAT (all 11 st_a types): C1m/C1n already seat the btab SRAM stack (r10, y0 587.52) but carry 0 btab-keyed
relay_sites, so the read-side flops float: on the routed kits the unseated g_read q was pulled ~1 mm toward u_r0 and the
round trip failed on g_read.u_sel / g_read.q / SRAM r_addr, r_ce.  The row adds FIRM relay_sites (kit_istations
rs_place_all, flop-name keys without the u_bound. prefix) at the stack W face for
  * u_u_btab.u_bt.u_core.g_read[g].q[i]          16 x 16 flops, the bt_q capture (slot g = rd_out bits 16g..16g+15);
  * u_u_btab.u_bt.u_core.g_read[g].u_sel.q[j]    16 x 4 select copies (+ .m[j], the second stage, on OT_BTAB_S4R types).
Slot g sits at the mean height of its rd_out pins over the four banks (pins on the macro W edge, y = 1.632 + 0.096 b),
one 4 x 4 block of capture flops per slot, its select copies beside it, in the 0.8 um gap W of the SRAM halo.
0 cycles, no RTL change.

Row STA-BTLAT3 (st_a types already at BT_LAT 2: OT_BTAB_S4R + four region cores <m>_bt2, i.e. RC97-BT2 / RC97-V1 rows):
  * verilog_defines += OT_BTAB_RQ -> qfd_dv_s5_btab_s4 registers the request leg (bt_re, bt_word) and the table-write leg
    (rq_* flops) at the SRAM stack in front of the registered-read core: +1 edge, bt round trip +2 vs btab_safe;
  * region hard cores u_r0..u_r3 <m>_bt2 -> <m>_bt3, param_wrap BT_LAT 3 (every other param, outline, pins, origin
    unchanged; 494 pins), lef/lib -> --views-dir (NEEDS-BUILD until the private child kit signs off + LEC);
  * relay_sites for the request flops rq_re, rq_word[*], rq_we, rq_kind[*], rq_addr[2..8] at the midpoint of the u_r0
    bt_word pins and the far bank (both hops <= 405 um, asserted);
  * the paired st_b regions u_r4..u_r7 take BT_LAT 3 from the bind hook qc_fabric_transport (fail closed unless the st_a
    type has OT_BTAB_S4R + OT_BTAB_RQ and its region cores BT_LAT 3).
Latency: no lane, station, boundary or core_latency change (LATCHECK lane tables unchanged); in-slice bt round trip +1
edge over RC97-BT2 on each slice of a changed type, so the compiler table (stn_transport_params, hook record bt_lat 3)
moves result(s) and busy(s) by +2 against the as-built (was +1).

usage: qc_sta_btlat3_row.py BASE_PLAN OUT_PLAN --row seats|bt3 [--row ...] [--views-dir REL] [--delta OUT.json]
"""
import argparse
import copy
import hashlib
import json
import os

BASE = "qfd_dv_s8_station_tail1_nb0"
PRE = "u_u_btab.u_bt.u_core"
RQ = "u_u_btab.u_bt"
HALO_GAP = 0.8            # um between the SRAM halo and the seat column
PITCH_X, PITCH_Y = 1.08, 0.27
NOTE = ("QC-STA-BTLAT3 11-25: BT_LAT 3 master (request-leg register OT_BTAB_RQ + registered btab read OT_BTAB_S4R on this "
        "type; +2 edges on the bt round trip), NEEDS-BUILD until its private child kit signs off")


def stack(t, tn):
    rows = [h for h in t.get("hard_cores", []) if h["inst"].startswith(f"u_bound.{PRE}.g_btb[")]
    assert len(rows) == 4, (tn, len(rows))
    xs = {h["origin_um"][0] for h in rows}
    assert len(xs) == 1, (tn, xs)
    halo = {h.get("halo_um", 0.0) for h in rows}
    assert len(halo) == 1, (tn, halo)
    return xs.pop() - halo.pop() - HALO_GAP, sum(h["origin_um"][1] for h in rows) / 4.0


def r3(v):
    return [round(v[0], 3), round(v[1], 3)]


def seat_rows(t, tn):
    xw, yb = stack(t, tn)
    s4r = "OT_BTAB_S4R" in (t.get("verilog_defines") or [])
    out = {}
    for g in range(16):
        y0 = yb + 1.632 + 0.096 * 16 * g                       # bottom pin of slot g (bank-mean height)
        for i in range(16):
            out[f"{PRE}.g_read[{g}].q[{i}]"] = r3([xw - PITCH_X * (i % 4), y0 + PITCH_Y * (i // 4)])
        sel = [("q", j) for j in range(4)] + ([("m", j) for j in range(4)] if s4r else [])
        for n, (nm, j) in enumerate(sel):
            out[f"{PRE}.g_read[{g}].u_sel.{nm}[{j}]"] = r3([xw - PITCH_X * (4 + n % 4), y0 + PITCH_Y * (n // 4)])
    return out


def rq_rows(t, tn, pins_dir):
    """request flops on the u_r0 -> stack leg at the MIDPOINT of the u_r0 bt_word / bt_re pin centroid and the far bank's
    r_addr / r_ce pins, so both hops are <= 405 um (FABLE 405 rule on placed hops; at the stack face the first hop would be
    ~584 um)."""
    xw, yb = stack(t, tn)
    r0 = next(h for h in t["hard_cores"] if h["inst"] == "u_r0")
    pf = json.load(open(os.path.join(pins_dir, r0["pins_file"])))
    src = [(r0["origin_um"][0] + x["x"], r0["origin_um"][1] + x["y"]) for x in pf["pins"]
           if x["name"] == "bt_re" or x["name"].startswith("bt_word[")]
    sx, sy = sum(a for a, _ in src) / len(src), sum(b for _, b in src) / len(src)
    banks = [(h["origin_um"][0], h["origin_um"][1] + 0.9) for h in t["hard_cores"] if h["inst"].startswith(f"u_bound.{PRE}.g_btb[")]
    far = max(banks, key=lambda b: abs(b[0] - sx) + abs(b[1] - sy))
    q = ((sx + xw) / 2.0, (sy + far[1]) / 2.0)
    L = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])          # noqa: E731
    h1, h2 = L((sx, sy), q), max(L(q, b) for b in banks)
    assert h1 <= 405 and h2 <= 405, (tn, h1, h2)
    names = ["rq_re", "rq_we"] + [f"rq_word[{b}]" for b in range(9)] + [f"rq_kind[{b}]" for b in range(2)] + \
            [f"rq_addr[{b}]" for b in range(2, 9)]
    rows = {f"{RQ}.{n}": r3([q[0] - PITCH_X * (k % 5), q[1] + PITCH_Y * (k // 5)]) for k, n in enumerate(names)}
    return rows, (round(h1, 1), round(h2, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--row", action="append", choices=("seats", "bt3"), required=True)
    ap.add_argument("--views-dir", default="physical/die_plan/qwen_compute/qcviews_btlat3")
    ap.add_argument("--delta")
    ap.add_argument("--pins-dir", help="dir the plan pins_file paths resolve against (default: the base plan's dir)")
    a = ap.parse_args()
    raw = open(a.base, "rb").read()
    q = copy.deepcopy(json.loads(raw))
    delta = {"rows": a.row, "base_sha256": hashlib.sha256(raw).hexdigest(), "types": {}, "masters": {}}
    sta = sorted(tn for tn in q["partition_types"] if "_st_a_v" in tn)
    assert len(sta) == 11, sta
    for tn in sta:
        t = q["partition_types"][tn]
        ch = delta["types"].setdefault(tn, [])
        rs = t.setdefault("relay_sites", {})
        if "seats" in a.row:
            new = seat_rows(t, tn)
            clash = sorted(set(new) & set(rs))
            assert not clash, (tn, clash[:3])
            rs.update(new)
            ch.append(f"STA-BTSEAT relay_sites +{len(new)} (g_read q + u_sel at stack W face x {min(v[0] for v in new.values()):.2f}"
                      f"..{max(v[0] for v in new.values()):.2f}, y {min(v[1] for v in new.values()):.2f}"
                      f"..{max(v[1] for v in new.values()):.2f})")
        if "bt3" in a.row:
            d = list(t.get("verilog_defines") or [])
            regs = [h for h in t.get("hard_cores", []) if (h.get("param_wrap") or {}).get("base") == BASE]
            if "OT_BTAB_S4R" not in d:
                assert not any((h["param_wrap"]["params"].get("BT_LAT", 1)) != 1 for h in regs), tn
                ch.append("STA-BTLAT3 skipped: not at BT_LAT 2 (no OT_BTAB_S4R; needs the RC97-V1 row first)")
                continue
            assert len(regs) == 4 and "OT_BTAB_RQ" not in d, (tn, len(regs), d)
            for h in regs:
                pr = h["param_wrap"]["params"]
                m0 = h["module"]
                assert pr["BT_LAT"] == 2 and m0.endswith("_bt2") and h["physical_master"] == m0, (tn, h["inst"], m0, pr)
                m = m0[:-4] + "_bt3"
                pr["BT_LAT"] = 3
                h["module"] = h["physical_master"] = m
                h["lef"] = f"{a.views_dir}/{m}/{m}.lef"
                h["lib"] = f"{a.views_dir}/{m}/{m}_tt.lib"
                h["note"] = (h.get("note", "") + " | " + NOTE).lstrip(" |")
                delta["masters"].setdefault(m, {"from": m0, "params": dict(sorted(pr.items())), "pins_file": h["pins_file"],
                                                "outline_um": h["outline_um"], "rows": []})["rows"].append(f"{tn}.{h['inst']}")
                ch.append(f"STA-BTLAT3 {h['inst']}: {m0} -> {m} (BT_LAT 2 -> 3)")
            t["verilog_defines"] = d + ["OT_BTAB_RQ"]
            new, hops = rq_rows(t, tn, a.pins_dir or os.path.dirname(os.path.abspath(a.base)))
            assert not set(new) & set(rs), tn
            rs.update(new)
            ch.append(f"STA-BTLAT3 verilog_defines += OT_BTAB_RQ; relay_sites +{len(new)} request flops; "
                      f"hops u_r0 bt_word -> rq {hops[0]} um, rq -> far bank {hops[1]} um")
    bt3 = {tn for tn, c in delta["types"].items() if any("OT_BTAB_RQ" in x for x in c)}
    delta["slices"] = {pp["name"].split("_")[1]: pp["type"] for pp in q["partitions"] if pp["type"] in bt3}
    delta["latency"] = {"lanes_changed": 0, "core_latency_changed": 0,
                        "in_slice_edges_vs_btab_safe": {s: 2 for s in sorted(delta["slices"])},
                        "compiler": "stn_transport result(s) +2, busy(s) +2 on these slices (hook record bt_lat 3; was +1)"}
    out = json.dumps(q, indent=1, sort_keys=False) + "\n"
    open(a.out, "w").write(out)
    delta["out_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    if a.delta:
        open(a.delta, "w").write(json.dumps(delta, indent=1) + "\n")
    print(json.dumps({"rows": a.row, "types": {k: len(v) for k, v in delta["types"].items()},
                      "masters": {k: len(v["rows"]) for k, v in delta["masters"].items()}, "slices": delta["slices"],
                      "base": delta["base_sha256"][:12], "out": delta["out_sha256"][:12]}))


if __name__ == "__main__":
    main()
