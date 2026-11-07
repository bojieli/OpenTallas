#!/usr/bin/env python3
"""DIE-HBM-82 d44v part 50: clock pin sites = the plan clock pin points for 3 cores (p45 pattern, scan cmp_clk 11-06).

gen_core_kit_hbm.py --clock-pin-entry on places the entry's clock pins (port + merged_clock_ports) by spreading them every
2nd M5 track around the clock_entries xy unless the entry carries clock_pin_sites_um.  The DIE-HBM-82-P40 scan of all d44v
views (io.tcl vs pin table, release_tree_plan pin_compare) found 3 more cores whose kits miss their table that way:
  ot_hbm_static_cfg_collar_idx256r  clk_in 43.32 vs table 44.664          -> sites = table (counted DB matches the table)
  ot_pdie_serdes_rx_bm3_rest        rck_clk 42.408 vs table 42.936        -> sites = table
  ot_hbm_idx_qctl_static            table clk_program/_mem on the S face (191.736/192.648, 0.24) but the plan entry and
        the die clock taps are the core centre (99.36, 64.8) and the counted DB sits there (release_tree_plan
        APPROVED_PIN_EVENTS 'HBM centre clock entry', COORD 11-03 00:1x, "DIE-HBM-59 lands the event in the HBM POR")
        -> the event lands here: new table = d35a table with the two clock pins at the generator's entry points
        (99.384, 64.8) / (99.48, 64.8), the 4 instances point to it, sites = those points.
Not touched: ot_hbm_sm_vm_wr_q_t_lanes4 (its 6 clock pins are M4 E-face pins; the site form is M5-only), reported.
    mk_p50.py D44V_DIR POR_DIR   (tables missing from d44v/cores are read from POR_DIR/*/cores, d35a first)"""
import gzip, json, re, sys
from pathlib import Path
D, POR = Path(sys.argv[1]), Path(sys.argv[2])
ld = lambda p: json.loads(gzip.decompress(p.read_bytes()) if p.name.endswith(".gz") else p.read_text())
def wgz(p, obj):
    with open(p, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
        g.write((json.dumps(obj) + "\n").encode())
def tab_of(pf):
    for d in [D] + [POR / x for x in ("d35a", "d35b")]:
        for q in (d / pf, Path(str(d / pf) + ".gz")):
            if q.exists():
                return ld(q)
    raise SystemExit(f"no table {pf}")
name = lambda q: q.get("name") or (q["bus"] if q.get("bit") is None else f"{q['bus']}[{q['bit']}]")
base = lambda n: re.sub(r"\[\d+\]$", "", n)
P = ld(D / "die_plan.json.gz")
CE = ld(D / "clock_entries.json.gz")
QCTL = "ot_hbm_idx_qctl_static"
QOLD = "cores/ot_hbm_idx_qctl_static__194.832x82.08__canon__d16f__codex_g21.json"
QNEW = "cores/ot_hbm_idx_qctl_static__194.832x82.08__d44v_centry_p50.json"
QPTS = {"clk_program": [99.384, 64.8], "clk_program_mem": [99.48, 64.8]}
log = []
# qctl: new table with the centre entry points, instances repointed
t = tab_of(QOLD)
rows = t["pins"] if isinstance(t, dict) else t
hit = 0
for q in rows:
    if name(q) in QPTS:
        assert q["layer"] == "M5", q
        q["x"], q["y"] = QPTS[name(q)]
        hit += 1
assert hit == 2, hit
(D / QNEW).write_text(json.dumps(t, indent=1) + "\n")
n_inst = 0
for T in P["partition_types"].values():
    for h in T.get("hard_cores", []):
        if h.get("module") == QCTL:
            assert h["pins_file"] == QOLD, h["pins_file"]
            h["pins_file"] = QNEW; n_inst += 1
assert n_inst == 4, n_inst
log.append(("qctl table", QNEW, "instances", n_inst))
SITES = {QCTL: QPTS}
for m in ("ot_hbm_static_cfg_collar_idx256r", "ot_pdie_serdes_rx_bm3_rest"):
    pf = {h["pins_file"] for T in P["partition_types"].values() for h in T.get("hard_cores", []) if h.get("module") == m}
    assert len(pf) == 1, (m, pf)
    tb = tab_of(pf.pop()); tb = tb["pins"] if isinstance(tb, dict) else tb
    SITES[m] = {name(q): [q["x"], q["y"]] for q in tb if q["layer"] == "M5" and base(name(q)) in {"clk", "clk_in", "rck_clk"}}
for m, sites in SITES.items():
    ents = [e for b in CE.values() if isinstance(b, dict) for e in b.values() if isinstance(e, dict) and e.get("module") == m]
    sigs = {json.dumps([e.get("xy_um"), e.get("port"), sorted(e.get("merged_clock_ports") or [])]) for e in ents}
    assert ents and len(sigs) == 1, (m, sigs)
    assert all(e.get("clock_pin_sites_um") is None for e in ents), m
    named = set(ents[0].get("merged_clock_ports") or []) | ({ents[0]["port"]} if ents[0].get("port") else set())
    assert set(sites) == named, (m, sites, named)
    assert all(abs((x - 0.024) / 0.048 - round((x - 0.024) / 0.048)) < 1e-6 for x, _ in sites.values()), (m, sites)
    assert len({tuple(v) for v in sites.values()}) == len(sites), (m, sites)
    for e in ents:
        e["clock_pin_sites_um"] = dict(sorted(sites.items()))
    log.append((m, "entries", len(ents), json.dumps(dict(sorted(sites.items())))))
wgz(D / "die_plan.json.gz", P)
wgz(D / "clock_entries.json.gz", CE)
for x in log:
    print("P50", *x)
