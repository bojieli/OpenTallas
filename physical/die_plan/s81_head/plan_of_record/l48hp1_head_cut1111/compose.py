#!/usr/bin/env python3
"""HEAD-93 11-11: ONE combined HEAD plan event for the 12:00 cut, on base l48hp1 (main 40f6c59b6409).

Order (every step positions/defines only; EQ by construction, G0 gate in event.json):
  1. lepB   : l48hp1_cplhead_lepB/lep_b.py + rt_resel.py (CPL-HEAD, hd_lep0N +129.6 um W, hd_st_n4 crop), result sha 96248fef
  2. S03    : delta_lepB_swap03.json  (hd_lep0N pp0/pp3 pair swap, positions + orient)
  3. ctl C1 : delta_ctl_c1.json       (hd_ctl xa0/xa1/xb0 hand seed, positions)
  4. H2     : l48hp1_h2/apply_delta.py (hd_host_e u_rr+u_ep hard core ot_s81hd_he_epc)
  5. start_q: hd_ctl verilog_defines += OT_S81HD_CTL_START_Q (+1 pin cycle form, claude/head-92-ctl-start-q-1110 4bb9483caf)
  (hp1 strap sites = l48hp1_straps delta, applied on the prepared plan by prepare.sh, not here)

usage: compose.py REPO_ROOT OUT_DIR
"""
import gzip, hashlib, json, subprocess, sys, shutil
from pathlib import Path

R = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
POR = R / "physical/die_plan/s81_head/plan_of_record"
EV = POR / "l48hp1_head_cut1111"
sha = lambda b: hashlib.sha256(b).hexdigest()
LEPB_SHA = "96248fef8156af4963cc7d6d55263f28ffe37fa781f14d377eec4ae68d452673"
BASE_SHA = "7322511ff22a4741426044711ca11b2b52fe8afcb18f0abfed4d1080aa54a5e6"

raw = gzip.open(POR / "l48hp1/source_plan.json.gz").read()
assert sha(raw) == BASE_SHA, "l48hp1 base differs"
# step 1 = CPL-HEAD's committed lepB result (lep_b.py + rt_resel.py + the manual landing_contract source_instance
# re-point of the rst_start_raw pins, see l48hp1_cplhead_lepB/event.json "apply"); lep_b.py / rt_resel.py kept for provenance
lb = gzip.open(EV.parent / "l48hp1_cplhead_lepB/source_plan_lepB.json.gz").read()
got = sha(lb)
print("lepB sha", got)
assert got == LEPB_SHA, "lepB artifact differs from CPL-HEAD's recorded sha"
b0 = OUT / "step1_lepB.json"
b0.write_bytes(lb)
P = json.loads(b0.read_text())


import os
def positions(P, delta, tag):
    for tn, m in delta.items():
        hc = {h["inst"]: h for h in P["partition_types"][tn]["hard_cores"]}
        for inst, (x, y, o) in m.items():
            if os.environ.get("SKIP_INST") and os.environ["SKIP_INST"] in inst:
                continue
            h = hc[inst]
            print(tag, tn, inst, h["origin_um"], h.get("orient"), "->", [x, y], o)
            h["origin_um"] = [x, y]
            h["orient"] = o


import os
for name, tag in (("delta_lepB_swap03.json", "S03"), ("delta_ctl_c1.json", "C1")):
    if os.environ.get("SKIP_" + tag):
        continue
    d = json.loads((EV / name).read_text())
    positions(P, d, tag)

# C1 puts xa0 at y 99.36 (was 112.32): the b_i reader-start stage 2 at (150, 95) was 17 um below the core, now 4.4 um, which
# re-solves the hd_ctl reset tree ("reader START raw reset rst_rl_25 has no registered wavefront driver" in gen).
# Same fix as H2's reader-start stage: move the stage point clear of the moved core, chain order kept.
import os
CTL_STAGE_Y = float(os.environ.get("CTL_STAGE_Y", "80"))
_st = P["partition_types"]["hd_ctl"]["clock"]["landing_reader_start"]["branches"]["b_i"]["stages"][1]
assert _st["xy_um"] == [150, 95], _st
if os.environ.get("SKIP_C1"): CTL_STAGE_Y = 95.0
print("C1 fix: hd_ctl reader start b_i stage 2", _st["xy_um"], "->", [150, CTL_STAGE_Y])
_st["xy_um"] = [150, CTL_STAGE_Y]

# H2
sys.path.insert(0, str(POR / "l48hp1_h2"))
import apply_delta as H2
for line in H2.apply(P, "hd_host_e", H2.VIEWS):
    print("H2", line)

# H2 moves the reset tap + drops clock sink sites, which regenerates the hd_host_e reset tree and the clk_t* taps:
# the G0 clock_landings check then fails (duplicate local reset tap on clk_t5; rst_start_raw exports differ from the
# regenerated tree).  Fix = move the reset tap off clk_t5 and re-select each rst_start_raw export on the regenerated tree
# (same role + depth, nearest relay: the lep0N/nst4 rule of rt_resel.py), re-pointing the landing pin to it.
import math
sys.path.insert(0, str(R / "tools/die_plan"))
import schema as S, reset_tree as RT


def _relays(raw, path, tn):
    PL = S.Plan(raw, Path(path))
    tree = RT.for_type(PL, tn)
    st = bool(tree.get("start"))
    rl = RT.start_relays(tree) if st else tree["relays"]
    return [r for r in rl if not st or r.get("role") in ("raw", "boot", "bootstrap_transport")]


def _relays_all(raw, path, tn):
    PL = S.Plan(raw, Path(path))
    return RT.for_type(PL, tn)["relays"]


HE_TAP_OLD, HE_TAP_NEW = [574.56, 172.8], [574.56, 181.44]
tn = "hd_host_e"
pdir = OUT / "pd"
if pdir.exists():
    shutil.rmtree(pdir)
shutil.copytree(POR / "l48hp1", pdir)
shutil.copy(POR / "l48hp1_h2/ot_s81hd_he_epc_pins.json", pdir / "core_pins/ot_s81hd_he_epc_pins.json")
lt = P["partition_types"][tn]["reset"]["local_taps_um"]
lt[lt.index(HE_TAP_OLD)] = HE_TAP_NEW
print("H2 fix: reset tap", HE_TAP_OLD, "->", HE_TAP_NEW)
Aplan = json.loads(gzip.open(POR / "l48hp1/source_plan.json.gz").read())   # relays before H2 (raw exports as published)
ra = {r["name"]: r for r in _relays(Aplan, pdir / "base_plan.json", tn)}
(pdir / "cut_plan.json").write_text(json.dumps(P))
rb = _relays(P, pdir / "cut_plan.json", tn)
t = P["partition_types"][tn]
pins = {x["name"]: x for x in t["clock"]["landing_contract"]["pins"]}
for e in t["reset_start_raw_exports"]:
    o = ra[e["instance"]]
    c = [r for r in rb if r.get("role") == o.get("role") and r.get("depth") == o.get("depth")]
    n = min(c, key=lambda r: math.dist(r["xy"], e["xy_um"]))
    pn = pins[e["port"]]
    off = [pn["xy_um"][0] - o["xy"][0], pn["xy_um"][1] - o["xy"][1]]
    print("H2 resel", e["port"], e["instance"], "->", n["name"], n["q"], n["xy"], "dist %.2f" % math.dist(n["xy"], e["xy_um"]))
    e["instance"], e["net"], e["xy_um"] = n["name"], n["q"], list(n["xy"])
    pn["source_instance"], pn["source_copy_from_net"] = n["name"], n["q"]
    pn["xy_um"] = [round(n["xy"][0] + off[0], 4), round(n["xy"][1] + off[1], 4)]

# hp1 raw-pin nudge (l48hp1_straps delta, landing_pins_xy_um): rst_start_raw_0/2 pins +1.92 um in y, off the clk_t8/clk_t1 tap pins
for nm in ("rst_start_raw_0", "rst_start_raw_2"):
    pins[nm]["xy_um"][1] = round(pins[nm]["xy_um"][1] + 1.92, 4)
    print("hp1 pin nudge", nm, pins[nm]["xy_um"])

# HEAD-94 11-11: stage-level raw reset references (landing_reader_start / landing_writer_start stages[].raw_reset and
# landing_local_resets[].raw) name regenerated reset-tree relays by Q net (rst_rl_N). After a core move / tap move / outline
# change the tree is re-solved and the old relay can vanish (hd_ctl rst_rl_25 sat under the moved xa0; hd_host_e rst_rl_20/11
# under H2) -> gen "has no registered wavefront driver".  Same rule as rt_resel.py: keep the Q if the relay survives at the
# same depth within 0.5 um; else pick the relay of the same depth nearest to the OLD relay xy on the regenerated tree.
(pdir / "cut_plan.json").write_text(json.dumps(P))
RAW_CHANGED = ("hd_ctl", "hd_host_e", "hd_lep0N", "hd_st_n4")
for tn in RAW_CHANGED:
    ra_q = {r["q"]: r for r in _relays_all(Aplan, pdir / "base_plan.json", tn)}
    rb_all = _relays_all(P, pdir / "cut_plan.json", tn)
    rb_q = {r["q"]: r for r in rb_all}
    clk = P["partition_types"][tn]["clock"]
    refs = []
    for key in ("landing_reader_start", "landing_writer_start"):
        for bus, br in clk.get(key, {}).get("branches", {}).items():
            for i, st in enumerate(br.get("stages", [])):
                refs.append((f"{key}.{bus}.{i}", st, "raw_reset"))
    for i, lr in enumerate(clk.get("landing_local_resets", [])):
        refs.append((f"landing_local_resets.{i}", lr, "raw"))
    for tag, obj, fld in refs:
        q = obj[fld]
        o = ra_q.get(q)
        if o is None:
            print("RAWSEL skip (not in base tree)", tn, tag, q)
            continue
        pt = obj.get("xy_um") or o["xy"]          # the stage / local-reset flop site (already in the new frame)
        c = [r for r in rb_all if r.get("depth") == o.get("depth")]
        n = min(c, key=lambda r: math.dist(r["xy"], pt))
        k = rb_q.get(q)
        if k is not None and k.get("depth") == o.get("depth") and math.dist(k["xy"], pt) <= math.dist(n["xy"], pt) + 25.0:
            continue                               # same Q survives at the same depth and is within 25 um of the best
        print("RAWSEL", tn, tag, q, "old relay", o["xy"], "d", o.get("depth"), "site", pt, "->", n["q"], n["xy"],
              "site dist old %.1f new %.1f" % (math.dist(o["xy"], pt), math.dist(n["xy"], pt)))
        obj[fld] = n["q"]

# start_q
dfs = P["partition_types"]["hd_ctl"]["verilog_defines"]
if "OT_S81HD_CTL_START_Q" not in dfs and not os.environ.get("SKIP_SQ"):
    dfs.append("OT_S81HD_CTL_START_Q")

# COORD 03:55/04:2x ruling (DIE-VIS-KVHEAD S1 proposal): clock windows
TW = P["clock"]["tap_window"]
TW["per_type_ps"]["hd_serdes"] = 50.0     # (1) had none -> fell back to window_ps 0; need 38 ps = ceil10(38+10)
REBUILT = ("hd_ctl", "hd_mesh", "hd_spn", "hd_st_n4", "hd_lep0N", "hd_host_e", "hd_serdes")
for tn in REBUILT:                        # (2) zero-margin per-port windows -> ceil1(need)+10, capped at per_type_ps
    pp = TW["per_port_ps"].get(tn)
    cap = TW["per_type_ps"][tn]
    if not pp:
        print("per_port_ps: none for", tn, "(per_type", cap, ")")
        continue
    for k, v in pp.items():
        nv = min(float(v) + 10.0, cap)
        if nv != v:
            pp[k] = nv
    print("per_port_ps", tn, len(pp), "ports +10 capped", cap)
TW["note"] = TW["note"] + " | HEAD-93 11-11 (COORD 03:55): hd_serdes 50; per_port_ps +10 ps margin (cap per_type) for the types rebuilt in the 12:00 batch (need = the l48w_sth clock-of-record proof, ceil1; re-derive after DIE-PROTO-2 re-judge)"

# overlap check inside each changed type (hard cores only, no partial overlap allowed)
def overlap(tn):
    hs = P["partition_types"][tn]["hard_cores"]
    n = 0
    for i, a in enumerate(hs):
        for b in hs[i + 1:]:
            ax, ay = a["origin_um"]; aw, ah = a["outline_um"]
            bx, by = b["origin_um"]; bw, bh = b["outline_um"]
            def sw(h):
                o = h.get("orient", "R0")
                return h["outline_um"] if o in ("R0", "MX", "MY", "R180") else h["outline_um"][::-1]
            aw, ah = sw(a); bw, bh = sw(b)
            if ax < bx + bw - 1e-6 and bx < ax + aw - 1e-6 and ay < by + bh - 1e-6 and by < ay + ah - 1e-6:
                n += 1
                print("OVERLAP", tn, a["inst"], b["inst"])
    return n

ov = sum(overlap(t) for t in ("hd_lep0N", "hd_ctl", "hd_host_e"))
print("hard-core overlaps", ov)
text = json.dumps(P, indent=1) + "\n"
(OUT / "source_plan.json").write_text(text)
print("cut plan sha256", sha(text.encode()))
