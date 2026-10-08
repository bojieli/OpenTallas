#!/usr/bin/env python3
"""DS-ROM field wire re-price on the wired S81 die r8 (CLAUDE DS-REPRICE, 2026-10-06).

The composition charged every ROM-field phase 80 wire cycles: 2 x 41 stages at 504 um (the r7 floorplan's
`trunk_stages.stages_at_504.field_one_way`) less the 2 spine broadcast stages already in the field vehicle.  The wired
r8 die (tools/dsrom_s81_fulldie.py --gen r8, main 5841260ac) instantiates every forwarded stage at <= 430.56 um (SS,
1.2 GHz) and counts the field round trip PER FRAME: x trunk stations to the frame's tap + entry meso 2 + one slot
station per slot + the column return register + return-tree root stages + return trunk stations + hub meso 2.  The
farthest frame is 139 (scan die) / 140 (1-stack layer die); the hub slabs are joined by direct wires with no stages.

This tool
  geometry  builds the r8 die (layer = scan die, layer1 = 1-stack die) at an element frame height and pair count and
            writes, per frame (= S81 return region), the round-trip stage components, and, per hub-internal bus
            (VM / SU / HC / gather / capture / collective slabs), the longest bit's driver -> load Manhattan length
            and the stages it needs at 430.56 um.                            (12 s, 0.2 GB a die: run on a compute host)
  regions   reads the field vehicle's per-region run results (go -> last row write, go -> idle, rows) of one field
            record's work dir and writes them compactly, so the re-price is reproducible from committed data.
  record    composes, per field record (as-built field.json, field_spine baseline PQ=0, field_spine_pq PQ=1) and
            per geometry, every node's wire as the MAX over the regions that hold the node's rows of
            (region's measured cycles + region's round trip - 2 vehicle broadcast stages) + the hub-bus stages on
            the field return path (gather -> capture -> VM).  It writes reprice.json and re-prices the two
            field_spine lever records (conditional; the as-built field.json is re-priced by the composition
            adapter from reprice.json).
  compose   AR / MTP with tools/three_machine_compose.py semantics for every geometry (current frame + the three
            taller q-element frames, with their extra layer dies -> extra stage hops at the measured full-FEC hop).

    python3 tools/dsrom_field_reprice_r8.py geometry --die layer --elem-h 157.68 --out G.json
    python3 tools/dsrom_field_reprice_r8.py regions --work W --plan-dir P --config asbuilt|baseline|pq --out R.json.gz
    python3 tools/dsrom_field_reprice_r8.py record
    python3 tools/dsrom_field_reprice_r8.py compose
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

OUT = ROOT / "results/rtl/dsrom_field_reprice_r8_20261006"
STAGE_UM = 430.56                 # one forwarded stage at SS 1.2 GHz (the HBM die pricing rule; LINK_STAGE_UM)
BST_IN_VEHICLE = 2                # spine broadcast stages already inside the field vehicle (tools/dsrom_1m_field.py)
OLD_WIRE_PER_PHASE = 80           # r7 floorplan: 2 x 41 stages at 504 um - 2
CLK = 1.2e9
# element frame (um) -> (q-element frame name, max pairs per layer die at that slot, from the r8 README capacity
# table / capacity_report()); the frame is the q element's FH + 6.48 um
GEOMS = {
    "f157.68": dict(elem_h=157.68, fh=151.2, pairs=2417, q_lef=None, label="current frame (FH 151.2, 12 slots)"),
    "f183.60": dict(elem_h=183.60, fh=177.12, pairs=2304, q_lef="results/rtl/dsrom_qz_20261004/Z20/Z20c/routed_element.lef.gz",
                    label="Z20c FH 177.12 (QX=10 CLOSED, 11 slots)"),
    "f198.72": dict(elem_h=198.72, fh=192.24, pairs=2050, q_lef=None, label="Z20b FH 192.24 (10 slots)"),
    "f216.00": dict(elem_h=216.00, fh=209.52, pairs=1798, q_lef=None, label="Z20a FH 209.52 (9 slots)"),
    # CLAUDE S81-RERUN (item 10): the owner's 192.24 um frame on the r9 die (hub-bus stations, q-element boundary
    # banks, column relays, 425 um station step); q abstract Z20c until QELEM posts the 192.24 um (Z22) abstract
    "r9f198.72": dict(elem_h=198.72, fh=192.24, pairs=2050, rev="r9",
                      q_lef="results/rtl/dsrom_qz_20261004/Z20/Z20c/routed_element.lef.gz",
                      label="S81-RERUN r9 die, FH 192.24 (10 slots; hub stations + q banks + column relays)"),
    # MARGIN-FIRST (owner rule 2026-10-06): every common-clock hop (hub-bus / end-block stations, column relays) capped
    # at 215 um -- a synchronous 440 um span measured SS -330 ps (meso_fifo verdict fwd_hop2_synchronous_counterfactual)
    "r9m215f198.72": dict(elem_h=198.72, fh=192.24, pairs=2050, rev="r9", cc_reach=215.0,
                          q_lef="results/rtl/dsrom_qz_20261004/Z20/Z20c/routed_element.lef.gz",
                          label="S81-RERUN r9 MARGIN-FIRST: common-clock hops <= 215 um (FH 192.24)"),
    # S81-RERUN v6 die case: + VCH / corridor interleave, link fix, a station on every hop over reach (budget sheets
    # 2026-10-06: column relays / hub stations / forwarded stations), meso FIFOs DEPTH 8 (+1 cycle a crossing)
    "r9m215v6f198.72": dict(elem_h=198.72, fh=192.24, pairs=2050, rev="r9", cc_reach=215.0,
                            opts="--vch-interleave --corr-interleave --link-fix --hop-fix --meso-d8 --cfifo-v2",
                            q_lef="results/rtl/dsrom_qz_20261004/Z20/Z20c/routed_element.lef.gz",
                            label="S81-RERUN v6: r9m215 + hop stations (budget sheets) + meso depth 8 (FH 192.24)"),
    # s81-fieldphase (2026-10-07): the actual legal 1,792-pair mixed geometry (77ffa0428 mixed221: q frame 221.4 um, BF
    # frame 198.72 um, 4 BF a region; tools/s81/mixed_geometry.py BASE options = the current S81 die revision) for the
    # 2d811aafb mappings: m221bf = a BF-flavour die (4 BF a region), m221q = a q-only die (HALF dedicated's q stages)
    "m221bf": dict(elem_h=198.72, fh=192.24, pairs=1792, rev="r9", cc_reach=215.0, q_lef=None,
                   opts="--vch-interleave --link-fix --corr-interleave --hop-fix --meso-d8 --cfifo-v2 --hc-xface "
                        "--link-split --sel-xstg --pin-relay --ch-heights 259.2,302.4,388.8,388.8,302.4,259.2,259.2 "
                        "--bf-per-region 4 --geometry-fix --vch-w 1641.6 --hc-corr 1512 --hub-column-width 1728 "
                        "--su-mm2 25.61188 --pairs 1792 --q-elem-h 221.4",
                   label="actual 1,792 mixed221 BF die (current S81 die options, 77ffa0428)"),
    "m221q": dict(elem_h=198.72, fh=192.24, pairs=1792, rev="r9", cc_reach=215.0, q_lef=None,
                  opts="--vch-interleave --link-fix --corr-interleave --hop-fix --meso-d8 --cfifo-v2 --hc-xface "
                       "--link-split --sel-xstg --pin-relay --ch-heights 259.2,302.4,388.8,388.8,302.4,259.2,259.2 "
                       "--bf-per-region 0 --geometry-fix --vch-w 1641.6 --hc-corr 1512 --hub-column-width 1728 "
                       "--su-mm2 25.61188 --pairs 1792 --q-elem-h 221.4",
                  label="actual 1,792 mixed221 q-only die (HALF dedicated q stages)"),
}
LAYER_PAIRS_TOTAL = 81 * 4 * 2417          # 783,108 layer-field pairs (S81 decision)
TP = 4
BASE_LAYER_DIES = 324                      # 81 stages x TP4
# hub-internal buses on the field return path and on the SU / HC / collective paths (tools/dsrom_s81_fulldie.py r8
# 'hub' class: adjacent slabs joined directly)
FIELD_RETURN_BUSES = ("hb_gather_capture", "hb_capture_vm")
FIELD_FWD_BUSES = ()                        # x leaves the VM through the ratio CDC end blocks inside the x trunk count
SU_BUSES = ("hb_vm_su_s", "hb_vm_su_n", "hb_su_s_hc_s", "hb_su_n_hc_n", "hb_hc_s_hc_n", "hb_hc_n_hc_s", "hb_hc_n_vm",
            "hb_vm_hc_s")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def stages(um: float) -> int:
    return math.ceil(um / STAGE_UM - 1e-9) if um > 0 else 0


# ------------------------------------------------------------------------------------------------ geometry
def cmd_geometry(a):
    import os
    g = GEOMS[a.geom]
    if g["q_lef"]:
        os.environ["OT_S81_Q_LEF"] = g["q_lef"]
    import dsrom_s81_fulldie as S
    import die_top_lint as L
    S.REV = g.get("rev", "r8")
    S.set_cc_reach(g.get("cc_reach"))
    S.Q_LEF = os.environ.get("OT_S81_Q_LEF", S.Q_LEF)
    if g.get("opts"):                       # die options of a recorded case (tools/dsrom_s81_fulldie.py die_options)
        import shlex
        S.apply_options(S.die_options(argparse.ArgumentParser()).parse_args(
            shlex.split(g["opts"]) + ["--gen", "r8", "--rev", g.get("rev", "r8"), "--die", a.die,
                                     "--cc-reach-um", str(g.get("cc_reach") or 430.56)]))
    S.configure(a.die, "r8")
    S.slot_geometry(g["elem_h"])
    if a.die == "layer":
        S.set_pairs(g["pairs"])
    else:                                   # layer1 keeps the scan die's field (r8 README): same pair count
        S.set_pairs(g["pairs"])
    m = S.build()
    S.finalize_r8(m)
    fr, xs, rs = m["frames"], m.get("x_stages", {}), m.get("r_stages", {})
    frames = {}
    for r, f in fr.items():
        mc = 4 if getattr(S, "MESO_D8", False) else 2
        comp = dict(x_trunk=xs.get(r, 0), entry_meso=mc, slot_stations=f["last_slot"] + 1, column_return_reg=1,
                    root_stages=f.get("ret_stages", 0), return_trunk=rs.get(r, 0), hub_meso=mc)
        if m.get("hop_fix"):
            comp["hop_fwd"] = m["hop_fix"].get("fwd_rt_add", 0)
        if getattr(S, "CFIFO_V2", False):
            comp["cfifo_v2_regs"] = 2
        if f.get("bank_stages") is not None:          # r9: q-element boundary banks and column relays
            comp.update(q_banks=f.get("bank_stages", 0), column_relays_x=f.get("relay_x", 0),
                        column_relays_return=f.get("relay_ret", 0))
        frames[int(r)] = dict(rt=sum(comp.values()), half=f.get("half"), tier=f.get("tier"), col=f.get("col"), **comp)
    rec_fp = S.plan_record_r8(m)
    far = rec_fp["field_round_trip_cycles"]
    assert frames[far["farthest_frame"]]["rt"] == far["cycles"], (far, frames[far["farthest_frame"]])
    # hub-internal buses: per bit, driver pin -> load pin Manhattan length (die coordinates)
    die = f"s81r8_{a.die}"
    L.R8[die] = m
    L.R8_ACTIVE[0] = True
    M = S.masters(m, 1)
    pw = S.port_widths(m, 1)
    tab = L.pin_table(die, m, M, pw, {})       # generated masters only (the hub slabs); no real-block binding needed
    by = {it.name: it for it in m["insts"]}
    hub_names = {it.name: k for k, it in m["hub"].items()}
    buses = {}
    for bid, cls, bits, eps in m["buses"]:
        if not any(e[0] in hub_names for e in eps) or len(eps) < 2:
            continue
        if cls in ("clock", "reset", "col_clock", "col_reset", "fclk", "top_in"):
            continue
        (di, dp), loads = eps[0], eps[1:]
        dpts = tab.get((by[di].master, dp)) if di in by else None
        best = 0.0
        cen = 0.0
        for li, lp in loads:
            if li not in by:
                continue
            lpts = tab.get((by[li].master, lp))
            if not dpts or not lpts:
                continue
            n = min(bits, len(dpts), len(lpts))
            D = [L.to_die(by[di], *dpts[i]) for i in range(n) if dpts[i] is not None]
            Q = [L.to_die(by[li], *lpts[i]) for i in range(n) if lpts[i] is not None]
            for (x0, y0), (x1, y1) in zip(D, Q):
                best = max(best, abs(x1 - x0) + abs(y1 - y0))
            cx = lambda P: (sum(p[0] for p in P) / len(P), sum(p[1] for p in P) / len(P))
            (ax, ay), (bx, by_) = cx(D), cx(Q)
            cen = max(cen, abs(ax - bx) + abs(ay - by_))
        if best == 0.0:
            continue
        buses[bid] = dict(cls=cls, bits=bits, driver=hub_names.get(di, di), loads=[hub_names.get(x, x) for x, _ in loads],
                          max_bit_um=round(best, 1), centroid_um=round(cen, 1), stages_430=stages(best),
                          stages_430_centroid=stages(cen))
    hub = {k: dict(x=round(it.x, 2), y=round(it.y, 2), w=round(it.w, 2), h=round(it.h, 2)) for k, it in m["hub"].items()}
    extra = dict(hub_stations=m["hub_stations"], column_relays=m.get("col_relays")) if m.get("hub_stations") else {}
    out = dict(schema="opentallas.dsrom-field-reprice-r8.geometry.v1", die=a.die, geom=a.geom, **g,
               q_lef_used=S.Q_LEF, slot=rec_fp["slot"], forwarded=rec_fp["forwarded"],
               field_round_trip_farthest=far, frames=frames, hub_slabs=hub, hub_buses=buses, **extra,
               stage_um=STAGE_UM, generator=dict(tool="tools/dsrom_s81_fulldie.py --gen r8",
                                                 sha256=sha(ROOT / "tools/dsrom_s81_fulldie.py")))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    rts = [f["rt"] for f in frames.values()]
    print(a.die, a.geom, "slots", rec_fp["slot"]["slots_per_column"], "far", far["cycles"], "rt min/mean/max",
          min(rts), round(sum(rts) / len(rts), 1), max(rts), "hub",
          {k: (v["max_bit_um"], v["stages_430"]) for k, v in buses.items() if v["cls"] == "hub"})
    return 0


# ------------------------------------------------------------------------------------------------ regions
def cmd_regions(a):
    """Per phase, per region: rows, go->last row write, go->idle (sequential runs) or the node run's per-op drains
    (PQ node runs).  Sources: tools/dsrom_1m_field.py work dir (asbuilt), tools/dsrom_field_spine.py work dirs."""
    work, pdir = a.work.resolve(), a.plan_dir.resolve()
    plan = json.loads((pdir / "plan.json").read_text())
    out = dict(schema="opentallas.dsrom-field-reprice-r8.regions.v1", config=a.config, work=str(work),
               plan_dir=str(pdir), plan_sha256=sha(pdir / "plan.json"), phases={}, nodes={})
    if a.config.startswith("asbuilt"):
        for ph in plan["phases"]:
            rows = {}
            for reg in ph["regions"]:
                f = work / "runs" / ph["phase"] / f"r{reg:03d}" / "result.json"
                r = json.loads(f.read_text())
                rows[reg] = [r["rows"], r["go_to_last_w"], r["go_to_idle"], int(r["pass_"])]
            out["phases"][ph["phase"]] = dict(layer=ph["layer"], node=ph["node"], stage=ph["stage"], regions=rows)
    else:
        import dsrom_field_spine as FS
        import dsrom_recovery_field as F
        groups = FS.groups_all(plan)
        for key, phs in sorted(groups.items()):
            L_, node, st = key
            if a.config.startswith("pq") and len(phs) > 1:
                regs = sorted({r for ph in phs for r in ph["regions"]})
                runs = {}
                for reg in regs:
                    r = FS.load(work, key, reg)
                    runs[reg] = dict(rows=r["rows"], pass_=int(r["pass_"]),
                                     ops=[[o["phase"], o["go"], o["end"], o.get("accept"),
                                           o["last_w"] if o["last_w"] is not None else None] for o in r["ops"]])
                out["nodes"][f"{L_}|{node}|{st}"] = dict(layer=L_, node=node, stage=st, mode="pq",
                                                        phases=[ph["phase"] for ph in phs], regions=runs)
            else:
                pl = []
                for i, ph in enumerate(phs):
                    rows = {}
                    for reg in ph["regions"]:
                        r = FS.load(work, FS.phase_key(key, i), reg)
                        nd = r["node"]
                        rows[reg] = [r["rows"], (nd["last_w"] - nd["go"]) if nd and nd["last_w"] >= 0 else None,
                                     (nd["idle"] - nd["go"]) if nd else None, int(r["pass_"])]
                    pl.append(dict(phase=ph["phase"], regions=rows))
                out["nodes"][f"{L_}|{node}|{st}"] = dict(layer=L_, node=node, stage=st, mode="seq", phases=pl)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(a.out, "wt") as f:
        json.dump(out, f, separators=(",", ":"))
    print("wrote", a.out)
    return 0


# ------------------------------------------------------------------------------------------------ node composition
def load_regions(p):
    with gzip.open(p, "rt") as f:
        return json.load(f)


def seq_cycles(phases, wire):
    """as-built rule with a per-region wire: phase i < last ends when the farthest BUSY region's last row is back
    (idle_r + wire_r; an idle region only gates by its own idle), + 1; the last phase at max(last_r + wire_r).
    wire: region -> cycles (constant dict for the old 80-cycle charge)."""
    tot, ok = 0, True
    for i, ph in enumerate(phases):
        R = ph["regions"]
        ok &= all(v[3] for v in R.values())
        if i < len(phases) - 1:
            tot += max(max(v[2] + (wire(int(r)) if v[0] > 0 else 0) for r, v in R.items()),
                       max(v[2] for v in R.values())) + 1
        else:
            tot += max(v[1] + wire(int(r)) for r, v in R.items() if v[1] is not None)
    return tot, ok


def seq_cycles_noloc(phases):
    """the measured part alone (old record definition): sum (max idle + 1) + max last"""
    tot = 0
    for i, ph in enumerate(phases):
        R = ph["regions"].values()
        tot += (max(v[2] for v in R) + 1) if i < len(phases) - 1 else max(v[1] for v in R if v[1] is not None)
    return tot


def spine_rule(nodes):
    import dsrom_recovery_field as F
    rs = [[dict(ops=[dict(phase=o[0], go=o[1], end=o[2], accept=o[3], last_w=o[4]) for o in r["ops"]])
           for r in n["regions"].values()] for n in nodes.values() if n["mode"] == "pq"]
    return F.spine_rule(rs)


def pq_cycles(node, k, wire):
    """tools/dsrom_recovery_field.compose with every (region, op) drain shifted by that region's wire"""
    phs = node["phases"]
    idx = {p: i for i, p in enumerate(phs)}
    n = len(phs)
    s = [0] * n
    drains = []
    for r, rr in node["regions"].items():
        for ph, go, end, acc, lw in rr["ops"]:
            i = idx[ph]
            s[i] = max(s[i], end - go)
            if lw is not None:
                drains.append((i, lw - go, int(r)))
    go = [0] * n
    end = [0] * n
    go[0] = k["c_first"]
    for i in range(n):
        if i:
            go[i] = max(end[i - 1] + k["c_gap"], (end[i - 2] + k["c_guard"]) if i >= 2 else 0, go[i - 1] + k["c_cfg"])
        end[i] = go[i] + s[i]
    meas = max(go[i] + d for i, d, r in drains)
    tot = max(go[i] + d + wire(r) for i, d, r in drains)
    return meas, tot, all(rr["pass_"] for rr in node["regions"].values())


def node_table(reg, wire, per_phase_extra=0):
    """{(layer, node, stage): dict(meas, total, phases, exact)} for one regions file; wire(r) -> cycles;
    per_phase_extra: cycles added once per wire crossing (hub buses on the return path, not region-dependent)."""
    out = {}
    if reg["config"].startswith("asbuilt"):
        grp = {}
        for name, ph in reg["phases"].items():
            grp.setdefault((ph["layer"], ph["node"], ph["stage"]), []).append(ph)
        items = [(k, dict(mode="seq", phases=v)) for k, v in grp.items()]
    else:
        items = [((n["layer"], n["node"], n["stage"]), n) for n in reg["nodes"].values()]
        k = spine_rule(reg["nodes"]) if reg["config"].startswith("pq") else None
    for key, n in items:
        if n["mode"] == "seq":
            w = lambda r: wire(r) + per_phase_extra
            tot, ok = seq_cycles(n["phases"], w)
            meas = seq_cycles_noloc(n["phases"])
            out[key] = dict(meas=meas, total=tot, phases=len(n["phases"]), exact=ok, mode="seq")
        else:
            meas, tot, ok = pq_cycles(n, k, lambda r: wire(r) + per_phase_extra)
            out[key] = dict(meas=meas, total=tot, phases=len(n["phases"]), exact=ok, mode="pq")
    return out


def cmd_check(a):
    """reproduce a committed field record's node cycles from the regions file with the old constant wire"""
    reg = load_regions(a.regions)
    rec = json.loads(a.record.read_text())
    tab = node_table(reg, lambda r: 0)
    bad, n = 0, 0
    for nd in rec["nodes"]:
        key = (nd["layer"], nd["node"].split(".", 1)[1] if nd["node"].startswith("L") else nd["node"], nd["die_stage"])
        t = tab.get(key)
        if t is None:
            print("missing", key)
            bad += 1
            continue
        n += 1
        if t["meas"] != nd["measured_cycles"]:
            bad += 1
            if bad < 10:
                print("diff", key, t["meas"], nd["measured_cycles"])
    print(f"{a.regions}: {n} nodes, {bad} differ")
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ record
DIES = ("layer", "layer1")
PROXY_REF = "f198.72"                  # scan die (4 stacks, 32 of the rack) and 1-stack layer die (292)
CONFIGS = dict(asbuilt=("regions/asbuilt.json.gz", "results/rtl/dsrom_1m_allmeasured_20261004/field.json"),
               # as-built field with the closed DS q-element QX 10 on the FP8/FP4 pairs (the headline field since the
               # owner's go, 2026-10-06; tools/dsrom_1m_field.py --qelem 10)
               asbuilt_qelem10=("regions/asbuilt_qelem10.json.gz", "results/rtl/dsrom_field_qelem_20261005/field_qelem_qx10.json"),
               baseline=("regions/baseline.json.gz", "results/rtl/dsrom_field_spine_20261004/field_baseline.json"),
               pq=("regions/pq.json.gz", "results/rtl/dsrom_field_spine_20261004/field_pq.json"),
               # PQ spine x DS q-element (2026-10-06, GAP 32 / GUARD 202 / GSLACK 32; tools/dsrom_combined_l20.py qelem-lever)
               # (margin-first QM = 2 lanes + tree, 2026-10-06; the QM = 0 measurement: regions/pq_qelem.json.gz, field_pq_qelem.json)
               pq_qelem=("regions/pq_qelem_qm2.json.gz", "results/rtl/dsrom_qelem_pq_20261006/field_pq_qelem_qm2.json"))
LEVER_CONFIG = dict(field_spine="baseline", field_spine_pq="pq", qelem_pq="pq_qelem")
# SU hub traverse already charged (stages): fused 1.2 GHz units HUB_IN 33 / HUB_OUT 23; unfused wired SU (0.9 GHz)
# BCAST 22 / RET 15 slow stages (tools/dsrom_1m_su.py, la6_inputs/dsrom_su_norm.py)
SU_CHARGED_NS = dict(fused=dict(inp=33 / 1.2, out=23 / 1.2), wired=dict(inp=22 / 0.9, out=15 / 0.9))


def added(um):
    """forwarded stations a direct register-to-register wire of `um` needs at 430.56 um a stage"""
    return max(0, math.ceil(um / STAGE_UM - 1e-9) - 1)


def geo_path(die, geom):
    return OUT / "geometry" / f"{die}_{geom}.json"


def load_geo(geom):
    out = {}
    for d in DIES:
        p = geo_path(d, geom)
        if p.exists():
            out[d] = json.loads(p.read_text())
    return out


def stage_count(pairs):
    dies = math.ceil(LAYER_PAIRS_TOTAL / pairs)
    return dies, math.ceil(dies / TP)


def hub_terms(geo):
    """per die kind: field-return hub stations (end block -> gather by tier-half, gather -> capture -> VM), the
    collective -> VM stations, and the SU in/out path against the charged hub traverse"""
    out = {}
    for d, g in geo.items():
        B = g["hub_buses"]
        hs = g.get("hub_stations")
        lb = (lambda k: hs[k]["path_um"]) if hs else (lambda k: B[k]["max_bit_um"])
        hr = {k[3:5]: added(v["max_bit_um"]) for k, v in B.items() if k.startswith("hr_")}
        su = {}
        for half, sl, path_out in (("s", "su_s", ("hb_su_s_hc_s", "hb_hc_s_hc_n", "hb_hc_n_vm")),
                                   ("n", "su_n", ("hb_su_n_hc_n", "hb_hc_n_vm"))):
            slab = g["hub_slabs"][sl]
            span = slab["h"] / 2 + slab["w"]           # face-centre entry -> farthest lane corner
            l_in = lb(f"hb_vm_{sl}") + span
            l_out = span + sum(lb(b) for b in path_out)
            need_in, need_out = math.ceil(l_in / STAGE_UM) / 1.2, math.ceil(l_out / STAGE_UM) / 1.2   # ns
            su[sl] = dict(in_um=round(l_in, 1), out_um=round(l_out, 1), need_in_ns=round(need_in, 3),
                          need_out_ns=round(need_out, 3), out_path=list(path_out),
                          excess_ns={k: round(max(0.0, need_in - c["inp"]) + max(0.0, need_out - c["out"]), 3)
                                     for k, c in SU_CHARGED_NS.items()})
        if hs:                      # r9: the stations the generator actually placed (hub buses and end block -> gather)
            hr = {k[3:5]: v["stations"] for k, v in hs.items() if k.startswith("hr_")}
            out[d] = dict(hr_added_by_tier_half=hr, gather_capture_added=hs["hb_gather_capture"]["stations"],
                          capture_vm_added=hs["hb_capture_vm"]["stations"],
                          collective_vm_added=hs["hb_collective_vm"]["stations"], su=su,
                          buses={k: dict(um=v["path_um"], added=v["stations"]) for k, v in hs.items()},
                          basis="r9 generator stations (hub_stations)")
            continue
        out[d] = dict(hr_added_by_tier_half=hr,
                      gather_capture_added=added(B["hb_gather_capture"]["max_bit_um"]),
                      capture_vm_added=added(B["hb_capture_vm"]["max_bit_um"]),
                      collective_vm_added=added(B["hb_collective_vm"]["max_bit_um"]),
                      su=su, buses={k: dict(um=v["max_bit_um"], added=added(v["max_bit_um"])) for k, v in B.items()
                                    if k.startswith("hb_")})
    return out


def wire_fn(geo, hub):
    """region -> wire cycles beyond the vehicle: max over die kinds of (round trip - 2 vehicle broadcast stages +
    end-block -> gather + gather -> capture + capture -> VM stations) for that frame"""
    W = {}
    for d, g in geo.items():
        h = hub[d]
        for r, f in g["frames"].items():
            w = f["rt"] - BST_IN_VEHICLE + h["hr_added_by_tier_half"][f"{f['half']}{f['tier']}"] \
                + h["gather_capture_added"] + h["capture_vm_added"]
            W[int(r)] = max(W.get(int(r), 0), w)
    return W


def summarise(tab):
    """(layer, node, stage) -> totals  =>  node name -> the slowest die's entry (as node_summary)"""
    by = {}
    for (L, node, st), t in tab.items():
        name = node if node.startswith("E1.") else f"L{L}.{node}"
        if name not in by or t["total"] > by[name]["total_cycles"]:
            by[name] = dict(total_cycles=t["total"], meas_cycles=t["meas"], phases=t["phases"], mode=t["mode"],
                            wire_cycles=t["total"] - t["meas"], die_stage=st, exact=t["exact"],
                            us=round(t["total"] / CLK * 1e6, 6))
    return by


def cmd_record(a):
    regs = {c: load_regions(OUT / p) for c, (p, _) in CONFIGS.items()}
    geoms = {}
    for gk, gd in GEOMS.items():
        geo = load_geo(gk)
        proxy = None
        if "layer" not in geo:
            # the scan die does not build at this frame (generator: no station spot on chain coSW; record
            # geometry/layer_<geom>.FAILED.log): proxy = the 1-stack die's frames + the scan - 1-stack per-frame
            # difference and the scan die's hub buses at the next shorter frame (hub slabs do not depend on the frame)
            ref = load_geo(PROXY_REF)
            geo["layer"] = copy.deepcopy(ref["layer"])
            for r, f in geo["layer"]["frames"].items():
                d_ = ref["layer"]["frames"][r]["rt"] - ref["layer1"]["frames"][r]["rt"]
                f.update(geo["layer1"]["frames"][r], rt=geo["layer1"]["frames"][r]["rt"] + d_)
            far = max(geo["layer"]["frames"], key=lambda r: geo["layer"]["frames"][r]["rt"])
            geo["layer"]["field_round_trip_farthest"] = dict(farthest_frame=int(far),
                                                            cycles=geo["layer"]["frames"][far]["rt"], proxy=True)
            geo["layer"]["slot"] = geo["layer1"]["slot"]
            proxy = dict(die="layer", from_die="layer1", delta_and_hub_from=PROXY_REF,
                         reason="scan die not buildable at this frame with the default field margin "
                                "(geometry/layer_" + gk + ".FAILED.log)")
        hub = hub_terms(geo)
        W = wire_fn(geo, hub)
        dies, st = stage_count(gd["pairs"])
        cfgs = {}
        for c, reg in regs.items():
            new = summarise(node_table(reg, lambda r: W[r]))
            old = summarise(node_table(reg, lambda r: OLD_WIRE_PER_PHASE)) if not c.startswith("pq") else None
            if c.startswith("pq"):  # PQ: old charge was 80 once per node (pipelined) -- recompute that way
                old = {}
                for key, t in node_table(reg, lambda r: 0).items():
                    w = OLD_WIRE_PER_PHASE * (1 if t["mode"] == "pq" else t["phases"])
                    name = key[1] if key[1].startswith("E1.") else f"L{key[0]}.{key[1]}"
                    if name not in old or t["meas"] + w > old[name]["total_cycles"]:
                        old[name] = dict(total_cycles=t["meas"] + w)
            for n, v in new.items():
                v["old_total_cycles"] = old[n]["total_cycles"]
            cfgs[c] = new
        rts = {d: dict(min=min(f["rt"] for f in g["frames"].values()), max=max(f["rt"] for f in g["frames"].values()),
                       mean=round(sum(f["rt"] for f in g["frames"].values()) / len(g["frames"]), 2),
                       farthest=g["field_round_trip_farthest"], slots=g["slot"]["slots_per_column"])
               for d, g in geo.items()}
        geoms[gk] = dict(gd, layer_dies=dies, stages=st, extra_layer_dies=dies - BASE_LAYER_DIES,
                         extra_stage_hops=st - BASE_LAYER_DIES // TP, round_trip=rts,
                         dies_built=sorted(d for d in DIES if geo_path(d, gk).exists()), scan_die_proxy=proxy, hub=hub,
                         wire_per_region=dict(sorted(W.items())),
                         wire_per_region_stats=dict(min=min(W.values()), max=max(W.values()),
                                                    mean=round(sum(W.values()) / len(W), 2)),
                         configs=cfgs)
    rec = dict(
        schema="opentallas.dsrom-field-reprice-r8.v1",
        rule=("field phase wire = max over the regions holding the phase's rows of (region's measured cycles + "
              "frame round trip on the r8 die - 2 spine broadcast stages inside the vehicle + end block -> gather + "
              "gather -> capture + capture -> VM forwarded stations); round trip and stations at 430.56 um a stage "
              "(SS 1.2 GHz); per frame the max over the scan die and the 1-stack layer die; PQ nodes: the measured "
              "pipelined composition with every (region, op) drain shifted by its region's wire"),
        old_rule=f"{OLD_WIRE_PER_PHASE} cycles a phase (PQ: once a node) = 2 x 41 stages at 504 um (r7 floorplan "
                 "trunk_stages) - 2",
        stage_um=STAGE_UM, bst_in_vehicle=BST_IN_VEHICLE, old_wire_per_phase=OLD_WIRE_PER_PHASE,
        default_geom="f157.68", geoms=geoms,
        inputs={**{rel(OUT / p): sha(OUT / p) for p, _ in CONFIGS.values()},
                **{r_: sha(ROOT / r_) for _, r_ in CONFIGS.values()},
                **{rel(geo_path(d, gk)): sha(geo_path(d, gk)) for gk in GEOMS for d in DIES if geo_path(d, gk).exists()}},
        tool_sha256={rel(Path(__file__)): sha(Path(__file__))})
    (OUT / "reprice.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("wrote", rel(OUT / "reprice.json"))
    for gk, g in geoms.items():
        print(gk, g["round_trip"], "wire/region", g["wire_per_region_stats"], "stages", g["stages"])
    if a.levers:
        relever()
    return 0


def relever():
    """re-price the field_spine / field_spine_pq lever records' node times (default geometry) through the adapter"""
    import dsrom_1m_allmeasured_adapters as AD
    import dsrom_1m_measure as M
    g, _, _ = M.s58_graph()
    lev_dir = ROOT / "results/rtl/dsrom_recovery_20261004/levers"
    for lever, cfg in LEVER_CONFIG.items():
        f = lev_dir / f"{lever}.json"
        lr = json.loads(f.read_text())
        rec = json.loads((ROOT / lr["measurement"]["record"]).read_text())
        old_rows = AD.field_rows(g, rec, geom=None)
        new_rows = AD.field_rows(g, rec, geom="f157.68")
        tag = lr["nodes"][next(iter(lr["nodes"]))]["source"].split(": ", 1)[0]
        for name, (sec, src, cls, _m) in new_rows.items():
            cur = lr["nodes"][name]["us"]          # the record before (old 80 charge) or already re-priced
            assert min(abs(cur - round(old_rows[name][0] * 1e6, 6)), abs(cur - round(sec * 1e6, 6))) < 1e-5, name
            lr["nodes"][name] = dict(us=round(sec * 1e6, 6), cls=cls, source=f"{tag}: " + src)
        lr["field_wire_reprice"] = dict(
            record=rel(OUT / "reprice.json"), sha256=sha(OUT / "reprice.json"), geom="f157.68",
            note="CLAUDE DS-REPRICE 2026-10-06: node times re-priced from the r8 die's per-frame round trip (was 80 "
                 "cycles a phase / once a PQ node); measured cycles unchanged")
        f.write_text(json.dumps(lr, indent=1) + "\n")
        print("re-priced", rel(f), len(new_rows), "nodes")


# ------------------------------------------------------------------------------------------------ compose
def cmd_compose(a):
    """AR / MTP for every geometry: headline (ADOPT + exact levers) and all PENDING_SSFF flipped (alternatives
    resolved as tools/three_machine_compose.py does), against main's published composition before this re-price."""
    import tempfile
    import dsrom_1m_allmeasured as D
    import dsrom_1m_allmeasured_adapters as AD
    import three_machine_compose as TM
    levers = TM.read_levers(TM.RECOVERY / "levers")
    cond = sorted(k for k, v in levers.items() if v["cls"] == "conditional")
    tm = json.loads((ROOT / "results/arch/three_machine_compose/compose.json").read_text())["ds_rom"]
    joint_levers = tm["conditional_all"]["levers"]
    rp = json.loads((OUT / "reprice.json").read_text())
    rows = {}
    geom0 = AD.FIELD_GEOM
    try:
        for gk in ["old80"] + list(GEOMS):
            AD.FIELD_GEOM = None if gk == "old80" else gk
            base = TM._row(D.compose(TM._args(TM.RECOVERY), write_output=False))
            with tempfile.TemporaryDirectory() as td:
                joint = TM._row(TM._with_flipped(TM.RECOVERY, Path(td), joint_levers))
            g = rp["geoms"].get(gk, {})
            rows[gk] = dict(label=g.get("label", "r7 floorplan charge: 80 cycles a field phase, no hub stations "
                                                 "(main before this re-price)"),
                            elem_h=g.get("elem_h"), fh=g.get("fh"), pairs_per_layer_die=g.get("pairs"),
                            layer_dies=g.get("layer_dies", BASE_LAYER_DIES),
                            extra_layer_dies=g.get("extra_layer_dies", 0), stages=g.get("stages", 81),
                            extra_stage_hops=g.get("extra_stage_hops", 0),
                            farthest_round_trip=({d: v["farthest"]["cycles"] for d, v in g["round_trip"].items()}
                                                 if g else None),
                            wire_per_region=g.get("wire_per_region_stats"), headline=base, conditional_all=joint)
            print(gk, "AR", base["AR_tok_s"], "MTP", base["MTP_tok_s"], "| cond AR", joint["AR_tok_s"], "MTP",
                  joint["MTP_tok_s"], flush=True)
    finally:
        AD.FIELD_GEOM = geom0
    ref = rows["old80"]
    for gk, r in rows.items():
        for k in ("headline", "conditional_all"):
            r[k + "_delta_vs_old80"] = TM._delta(r[k], ref[k])
        if gk != "old80":
            r["headline_delta_vs_current_frame"] = TM._delta(r["headline"], rows["f157.68"]["headline"])
            r["conditional_delta_vs_current_frame"] = TM._delta(r["conditional_all"], rows["f157.68"]["conditional_all"])
    out = dict(schema="opentallas.dsrom-field-reprice-r8.compose.v1",
               rule="tools/dsrom_1m_allmeasured.compose (recovery baseline, full-FEC links) with the field wire, hub "
                    "stations and stage count of each geometry; conditional = " + ", ".join(joint_levers) +
                    " flipped together (tools/three_machine_compose.py alternatives rule)",
               main_before=dict(AR_tok_s=1798.5, MTP_tok_s=5184.4, source="results/arch/three_machine_compose/table.txt "
                                                                           "at main 0a490f77c"),
               unvalidated=["taller frames: field cycles per region kept at the current S81 placement's measurement "
                            "(fewer pairs per die -> a new placement, not re-measured; QELEM measured QX10 = QX9 node "
                            "cycles)",
                            "taller frames: extra stage hops at the measured full-FEC stage hop + the rack's mean "
                            "cable flight per stage hop; the per-stage busy time (MTP II) is kept (fewer layers per "
                            "die would only shorten it)",
                            "Z20a (FH 209.52): the scan die does not build at the default field margin; its round "
                            "trip is a proxy (1-stack die + scan/1-stack difference at FH 192.24)",
                            "Z20b / Z20a: the head die holds 1,450 / 1,282 pairs (< 1,471 content pairs), so 13 / 14 "
                            "head dies instead of 12 -- not priced (no serial hop added by a wider head group)",
                            "SU hub traverse: intra-slab span assumed face-centre entry to the farthest lane corner"],
               rows=rows, tool_sha256={rel(Path(__file__)): sha(Path(__file__))},
               inputs={rel(OUT / "reprice.json"): sha(OUT / "reprice.json")})
    (OUT / "compose.json").write_text(json.dumps(out, indent=1) + "\n")
    L = [f"{'geometry':10s} {'FH um':>7s} {'pairs':>6s} {'+dies':>6s} {'+hops':>6s} {'far rt':>8s} "
         f"{'AR tok/s':>9s} {'dAR%':>7s} {'MTP tok/s':>10s} {'dMTP%':>7s} | {'cond AR':>8s} {'cond MTP':>9s}"]
    for gk, r in rows.items():
        h, c = r["headline"], r["conditional_all"]
        rt = "/".join(str(v) for v in r["farthest_round_trip"].values()) if r["farthest_round_trip"] else "82@504*"
        L.append(f"{gk:10s} {str(r['fh'] or '-'):>7s} {str(r['pairs_per_layer_die'] or 2417):>6s} "
                 f"{r['extra_layer_dies']:>+6d} {r['extra_stage_hops']:>+6d} {rt:>8s} {h['AR_tok_s']:>9,.1f} "
                 f"{100 * (h['AR_tok_s'] / ref['headline']['AR_tok_s'] - 1):>+7.2f} {h['MTP_tok_s']:>10,.1f} "
                 f"{100 * (h['MTP_tok_s'] / ref['headline']['MTP_tok_s'] - 1):>+7.2f} | {c['AR_tok_s']:>8,.1f} "
                 f"{c['MTP_tok_s']:>9,.1f}")
    L.append("far rt = farthest frame field round trip, scan die / 1-stack die (stages); * old charge 80 a phase "
             "(2 x 41 at 504 um - 2)")
    (OUT / "table.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("geometry")
    p.add_argument("--die", default="layer", choices=["layer", "layer1"])
    p.add_argument("--geom", default="f157.68", choices=sorted(GEOMS))
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("regions")
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--plan-dir", type=Path, required=True)
    p.add_argument("--config", required=True, choices=["asbuilt", "asbuilt_qelem10", "baseline", "pq", "pq_qelem"])
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("record")
    p.add_argument("--levers", action="store_true", help="also re-price the field_spine lever records")
    sub.add_parser("compose")
    p = sub.add_parser("check")
    p.add_argument("--regions", type=Path, required=True)
    p.add_argument("--record", type=Path, required=True)
    a = ap.parse_args()
    sys.exit(dict(geometry=cmd_geometry, regions=cmd_regions, check=cmd_check, record=cmd_record, compose=cmd_compose)[a.cmd](a))
