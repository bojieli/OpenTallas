#!/usr/bin/env python3
"""FABLE-UNC-QC STA-BTW-0 (rc96): 0 cycles, plan relay_sites only.
The 29 stn_cfg bits of b_tw_data_i (q[28:0] of the in-boundary bank u_bin_b_tw_data_i; ot_dp_st = one plain flop per bit) are read
by the cfg_*_p pins of u_r0..u_r3, stacked over ~1010 um.  The bank sits at the landing macro, so the bank -> u_r3 arc is ~940 um.
Row: FIRM sites u_bin_b_tw_data_i/q[0..28] at the L1 centre T of the four cfg pin groups (pushed out of the hard cores + halo), so
the one bank flop is the mid station: landing q pin -> bank and bank -> farthest pin are both ~half the run.  Family form of the
QC-PLAN-R3 N4.6e5 11-19 fix that 2 of the 11 st_a types carry (bits 0..28 FIRM (490,580)).
usage (cwd = launch tree): btw0_rows.py PLAN ROWS.json TABLE.tsv     |   btw0_rows.py --apply PLAN ROWS.json OUT_PLAN"""
import sys, json, re, hashlib
from pathlib import Path
def apply(plan, rows, out):
    raw = json.load(open(plan)); R = json.load(open(rows)); n = 0
    for tn, d in R["relay_sites"].items():
        rs = raw["partition_types"][tn].setdefault("relay_sites", {})
        for k, v in d.items(): rs[k] = v; n += 1
        t = raw["partition_types"][tn]; t["note"] = (t.get("note", "") + " | " if t.get("note") else "") + R["note"]
    Path(out).write_text(json.dumps(raw, separators=(",", ":")) + "\n")
    print("STA-BTW-0 applied", n, "sites on", len(R["relay_sites"]), "types ->", out, hashlib.sha256(Path(out).read_bytes()).hexdigest()[:12])
if sys.argv[1] == "--apply": apply(*sys.argv[2:5]); sys.exit(0)
sys.path.insert(0, "tools/die_plan")
import bind_pad_tail_split as TS
plan, prow, ptsv = sys.argv[1:4]
raw = json.load(open(plan)); PD = Path("physical/die_plan/qwen_compute/plan_of_record")
PORTS = [("cfg_kcm1_p", 8, 0), ("cfg_sbase_p", 9, 8), ("cfg_nwords_p", 8, 17), ("cfg_wsrc_p", 1, 25), ("cfg_mode_p", 2, 26), ("cfg_v_p", 1, 28)]
CELL = (1.404, 0.27); COLS = 2; out = {}; tsv = []
for tn, ty in raw["partition_types"].items():
    if not re.match(r"sl[ew]_st_a", tn): continue
    hcs = ty["hard_cores"]; tab = TS.pin_table(hcs, PD); boxes = TS.core_boxes(hcs)
    bands = [v["rect_um"] for v in (((ty.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}).values() if v.get("rect_um")]
    cores = [c for c in ("u_r0", "u_r1", "u_r2", "u_r3") if "cfg_kcm1_p" in tab.get(c, {})]
    assert len(cores) == 4, (tn, cores)
    pins = {}
    for pn, w, lo in PORTS:
        for i in range(w):
            pins[lo + i] = [TS.pin_xy(tab, c, pn, i, w)[1] for c in cores]
    allp = [p for v in pins.values() for p in v]
    T = TS.push_out(TS.l1_centre(allp), boxes + [tuple(b) for b in bands])
    q = tab["cl_b_tw_data_i"]["q"]
    rs = ty.get("relay_sites") or {}
    sites = {}
    x0 = round(T[0] - CELL[0] * COLS / 2, 3); y0 = round(T[1] - 15 * 2 * CELL[1] / 2, 3)
    for j in range(29):
        sites[f"u_bin_b_tw_data_i/q[{j}]"] = [round(x0 + (j % COLS) * 2.16, 3), round(y0 + (j // COLS) * 2 * CELL[1], 3)]
    def arcs(site_of):
        a = b = 0.0
        for j in range(29):
            s = site_of(j); a = max(a, TS.md(q[str(j)], s)); b = max(b, max(TS.route_len(s, p, boxes)[0] for p in pins[j]))
        return a, b
    old = lambda j: tuple(rs.get(f"u_bin_b_tw_data_i/q[{j}]") or (q[str(j)][0] - 25.0, q[str(j)][1]))     # unsited: the bank sits beside the landing q pins
    new = lambda j: tuple(sites[f"u_bin_b_tw_data_i/q[{j}]"])
    oa, ob = arcs(old); na, nb = arcs(new)
    inside = [k for k, (x, y) in sites.items() if any(b[0] < x < b[2] and b[1] < y < b[3] for b in boxes + [tuple(b) for b in bands])]
    out[tn] = sites
    tsv.append((tn, "FIRM(%.0f,%.0f)" % tuple(rs["u_bin_b_tw_data_i/q[0]"]) if "u_bin_b_tw_data_i/q[0]" in rs else "unsited", round(oa), round(ob), "(%.1f,%.1f)" % T, round(na), round(nb), len(inside)))
note = "STA-BTW-0 11-23 (FABLE-UNC-QC rc96): u_bin_b_tw_data_i q[0..28] (stn_cfg) FIRM at the L1 centre of the u_r0..u_r3 cfg pins; the bank flop is the mid station of the landing -> region run, 0 cycles"
json.dump(dict(row="STA-BTW-0", lane="FABLE-UNC-QC", item="rc96", base_sha=hashlib.sha256(open(plan, "rb").read()).hexdigest()[:12], key="partition_types.<type>.relay_sites (29 keys per type)", note=note, relay_sites=out), open(prow, "w"), indent=0)
with open(ptsv, "w") as f:
    f.write("type\tbank_bits_0_28_now\tlanding_to_bank_um\tbank_to_far_pin_um\tT\tnew_landing_to_bank_um\tnew_bank_to_far_pin_um\tsites_in_core_or_band\n")
    for r in tsv: f.write("\t".join(map(str, r)) + "\n")
for r in tsv: print("\t".join(map(str, r)))
print("STA-BTW-0 types", len(out), "sites", sum(len(v) for v in out.values()), "worst arc now", max(max(r[2], r[3]) for r in tsv), "-> after", max(max(r[5], r[6]) for r in tsv))
