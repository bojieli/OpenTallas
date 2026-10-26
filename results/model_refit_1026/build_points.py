#!/usr/bin/env python3
"""MODEL-REFIT: assemble every measured core clock-insertion trial (all dies) into one table.
src: CBR = recomputed by this lane from raw run artifacts; NC = NUMBER-CHECK checked; LANE = lane receipt only (UNCHECKED).
basis: PL = placement RC, GRT = global-route RC estimate.  struct: cts = TritonCTS grown from the pin (plain);
rt = regional-tap / count H-tree (CTS below taps); trunk = MSCTS structured trunk from the pin; plan = fully plan-built tree
(core_infra_htree / MSCTS H-tree, TritonCTS not run)."""
import json, sys
from pathlib import Path

T = Path(__file__).resolve().parent


def far(w, h, x, y):
    return max(abs(cx - x) + abs(cy - y) for cx in (0, w) for cy in (0, h))


P = []


def add(**k):
    k.setdefault("tt_max", None); k.setdefault("ff_mean", None); k.setdefault("ff_max", None)
    k.setdefault("flag", ""); k.setdefault("L_sink", None)
    P.append(k)


# ---------------------------------------------------------------- HBM edge (B2l kits, PL, TritonCTS natural tree, TT)
b2l = json.loads((T / "hbm_b2l.json").read_text())
rc = {t["module"]: t for t in json.loads((T / "hbm_rootcause.json").read_text())["types"]}
by = {}
for v in b2l["views"]:
    if v.get("status") == "MEASURED" and v["module"] in rc:
        by.setdefault(v["module"], []).append(v)
for mod, vs in by.items():
    t = rc[mod]
    ports = {}
    for v in vs:
        for p, q in v["ports"].items():
            ports.setdefault(p, []).append(q)
    main = max(ports, key=lambda p: ports[p][0]["sinks"])          # port with the most sinks
    w, h = vs[0]["outline_um"]
    pins = {p: (x, y) for p, x, y in t["clk_pin_xy"]}
    flag = []
    if mod.endswith("kshare_splitstrap"):
        px, py = 354.2, 448.5                                      # NE corner (NUMBER-CHECK 11:18 item 2)
        flag.append("pin from NUMBER-CHECK")
    else:
        pin = pins.get(main) or pins.get("clk") or list(pins.values())[0]
        bw, bh = t["b2n_outline"]
        px, py = pin[0] * w / bw, pin[1] * h / bh                  # B2n pin placed on the measured B2l outline
        if [round(bw, 2), round(bh, 2)] != [round(w, 2), round(h, 2)]:
            flag.append("outline changed B2l->B2n: pin scaled")
    L = far(w, h, px, py)
    means = [q["mean_ps"] for q in ports[main]]
    add(die="HBM", core=mod.replace("ot_", "")[:34], trial="B2l natural (%d views)" % len(vs), src="LANE+CBR-geom",
        basis="PL", struct="cts", entry="edge", L=round(L, 1), sinks=ports[main][0]["sinks"],
        tt_mean=round(sum(means) / len(means), 1), tt_max=max(q["max_ps"] for q in ports[main]),
        tt_lane=t["tt_ps"], flag="; ".join(flag))

# ---------------------------------------------------------------- HBM centre (PATH-HBM b1d calibration, GRT, TritonCTS)
for k, r in json.loads((T / "hbm_centre.json").read_text())["types"].items():
    w, h = r["outline_um"]; x, y = r["entry_um"]
    add(die="HBM", core=k, trial="b1d centre M5 pin", src="LANE(NC-3 reproduced)", basis="GRT", struct="cts",
        entry="centre", L=round(far(w, h, x, y), 1), L_sink=r["lmax_entry_to_sink_um"], sinks=r["tt"]["sinks"],
        tt_mean=r["tt"]["mean_ps"], tt_max=r["tt"]["max_ps"], ff_mean=r["ff"]["mean_ps"], ff_max=r["ff"]["max_ps"])

# ---------------------------------------------------------------- QC SU (GRT RC lat probe)
for core, L, n, tt, ff in [("vmr", 406.08, None, 341.8, 271.8), ("prog", 436.32, 5291, 419.4, 337.1),
                           ("btab", 436.32, 5644, 384.9, 308.1)]:
    add(die="QC", core=core, trial="B (S-face pin, MSCTS SEG110 trunk)", src="LANE (master_plan CAL_POINTS)",
        basis="GRT", struct="trunk", entry="edge", L=L, sinks=n, tt_mean=tt, ff_mean=ff)
add(die="QC", core="rp1", trial="M (SW corner, MSCTS 4 stages)", src="LANE", basis="GRT", struct="trunk", entry="edge",
    L=405.0, sinks=2790, tt_mean=408.3, ff_mean=322.9)
raw = T / "raw"
sys.path.insert(0, str(T))
import re


def native(f):
    text = f.read_text(); out = {}
    for c in ("TT", "FF"):
        taps = {}
        for name, n, mean, lo, hi in re.findall(r"OT_MSCTS_TAP grt " + c + r" (\S+) n (\d+) mean ([-.\d]+) min ([-.\d]+) max ([-.\d]+)", text):
            taps[name] = (int(n), float(mean), float(lo), float(hi))      # last record per tap
        v = list(taps.values()); n = sum(a[0] for a in v)
        out[c] = dict(n=n, mean=round(sum(a * b for a, b, _, _ in v) / n, 1), max=max(a[3] for a in v),
                      win=round(max(a[1] for a in v) - min(a[1] for a in v), 1))
    return out


for core, log, trial, w, h, x, y, path, flag in [
        ("btab", "codex-qc-su-0733_kits_btab_r4b.log", "R4b plan H-tree depth 3", 354.24, 259.2, 177.12, 135.0, None, "window 80 (STRUCTURAL FAIL)"),
        ("prog", "codex-qc-su-0733_kits_prog_r4b.log", "R4b plan H-tree depth 3", 354.24, 259.2, 177.12, 129.6, None, "window 75; entry = outline centre (assumed)"),
        ("rp1", "codex-qc-su-0733_kits_rp1_r4b.log", "R4b plan H-tree depth 3", 259.2, 276.48, 129.6, 138.24, None, "window 99; entry = outline centre (assumed)"),
        ("btab", "qc-su-lat-r5_btab_r5.log", "R5 plan H-tree 4 islands star", 354.24, 259.2, 177.12, 135.0, 360.18, "window 41.8"),
        ("btab", "qc-su-lat-r6_btab_r6.log", "R6 plan H-tree W/E split", 354.24, 259.2, 177.12, 135.0, 286.74,
         "BAL pad plan logged, NOT applied: final tap means = pre-BAL means (T001 253.4 / T031 270.0)")]:
    m = native(raw / log)
    add(die="QC", core=core, trial=trial, src="CBR (cts_grt.log)", basis="GRT", struct="plan", entry="centre",
        L=far(w, h, x, y), path=path, sinks=m["TT"]["n"], tt_mean=m["TT"]["mean"], tt_max=m["TT"]["max"],
        ff_mean=m["FF"]["mean"], ff_max=m["FF"]["max"], flag=flag)
add(die="QC", core="btab", trial="R3 (Codex; equal-load plan lost)", src="LANE (raw log not found)", basis="GRT", struct="plan",
    entry="centre", L=312.1, sinks=5644, tt_mean=360.1, ff_mean=281.2, flag="UNCHECKED, structure broken (1..59 sinks/leaf)")

# ---------------------------------------------------------------- S81 gunit (centre M5 pin + count H-tree, OT_RT_WIN 1e6)
for core, trial, n, tt, ttx, ff, ffx in [("gunit_l0", "r3rt42 4x2", 3655, 294.74, 318.96, 240.52, 265.65),
                                        ("gunit_l0", "r3rt41 4x1", 3655, 299.90, 321.23, 247.81, 268.54),
                                        ("gunit_l2", "r3rt42 4x2", 3567, 297.51, 319.14, 243.92, 265.62)]:
    add(die="S81", core=core, trial=trial, src="CBR (ins_probe_*.json)", basis="GRT", struct="rt", entry="centre",
        L=259.2, sinks=n, tt_mean=tt, tt_max=ttx, ff_mean=ff, ff_max=ffx)
add(die="S81", core="gunit_l4", trial="cl26rt 4x1", src="NC 06:59", basis="GRT", struct="rt", entry="centre", L=207.36,
    sinks=12098, tt_mean=259.69, ff_mean=208.55)
add(die="S81", core="gunit_l4", trial="cl26rt 4x1 (PL)", src="LANE", basis="PL", struct="rt", entry="centre", L=207.36,
    sinks=12098, tt_mean=233.8, tt_max=242.1)
add(die="S81", core="gunit_l4", trial="cl26c plain CTS raw it0", src="LANE", basis="PL", struct="cts", entry="centre",
    L=207.36, sinks=12098, tt_mean=200.0, tt_max=226.0, flag="pre-balance raw tree")

# ---------------------------------------------------------------- KV (PL what-ifs)
for core, n, tt, ttx in [("head_e0", 39847, 244.1, 255.3), ("head_e1", 26614, 236.6, 248.6),
                         ("head_e2", 28964, 238.4, 248.0), ("head_e6", 28964, 236.3, 246.4)]:
    add(die="KV", core=core, trial="v5 centre pin, one TritonCTS tree", src="CBR (ins.tsv all sinks)", basis="PL",
        struct="cts", entry="centre", L=216.0, sinks=n, tt_mean=tt, tt_max=ttx)
add(die="KV", core="pv_pair", trial="v5 centre pin", src="CBR (ins.tsv)", basis="PL", struct="cts", entry="centre",
    L=285.12, sinks=29716, tt_mean=224.9, tt_max=249.0, flag="5 CTS balance bufs on SRAM-CK")
for core, tt, ff in [("ectlk_q0", 260.58, 215.07), ("ectlk_q1", 258.97, 213.03), ("ectlk_q3", 251.99, 207.02)]:
    add(die="KV", core=core, trial="N-face centre pin", src="LANE", basis="PL", struct="cts", entry="edge", L=280.8,
        sinks=10500, tt_mean=tt, ff_mean=ff)
add(die="KV", core="pv_join", trial="W-face mid pin", src="LANE", basis="PL", struct="cts", entry="edge", L=259.1,
    sinks=16200, tt_mean=212.39, ff_mean=172.82)

if __name__ == "__main__":
    (T / "points.json").write_text(json.dumps(P, indent=1))
    for p in P:
        print(f"{p['die']:4} {p['core'][:30]:30} {p['basis']:3} {p['struct']:5} {p['entry']:6} L={p['L']:7.1f} n={p['sinks']} "
              f"TT {p['tt_mean']}/{p['tt_max']} FF {p['ff_mean']}/{p['ff_max']} {p['src']} {p['flag']}")
    print(len(P))
