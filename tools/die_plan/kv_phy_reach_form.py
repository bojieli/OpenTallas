#!/usr/bin/env python3
"""KV-PHY-REACH (DIE-KV-100, RULEBOOK-1113 R-REACH): the PHY reach form of kv3_phy / kv3_phy_v1.

usage: phy_form.py PLAN_IN PLAN_OUT [--report R.json] [--repo TREE] [--no-taps]

WHY.  The vN2 re-face put the E-face po/pi windows straight opposite the PHY core pins (window y = core pin y within
4 um; rhN 74 um), but the type kept the registers of the old face: the four po input words had ONE register, FIRM by
relay_sites at 0.6 of the old route (x 527, y 321-693: 572 um from the pins, AUTO-GEOM pin_reg_p90 572), the pi
stations ran on the old slanted lines (last hop 447 um, relay_collapse 123) and the reset relays rg0..rg4 sat on the
old sites (relay -> epoch flop 709 um, r2r).  No pin moves: the windows are already at the core pins.

THE FORM (type frame; core E face x 306.72, tile E face x 864; all rows straight, core pin row -> window):
  column  x        registers
  CORE    330.72   pi stage 0 (register at the core output, 24 um) | po stage 1 (register at the core input)
  A       508.48   pi stage 1
  B       620.00   po stage 0
  C       686.24   pi stage 2
  FACE    ~857     u_bout (pi) and u_bin (po) face registers at their pins (the po relay_sites are removed)
  pi (6 out buses): depth 3, unchanged (0 cycles); hops 24 / 178 / 178 / 178.
  po (4 in buses):  +2 stations (internal_stations, bind native stations as on the pi side), hops 237 / 289 / 24;
                    DECLARED +2 data cycles on every po lane (pc -> phy), priced by reach_fix.sync_fixed_cycles.
  reset (reset.port_relays, relays FIRM by relay_sites; every hop <= 340 um):
      pe depth 1  (770, 820)                         face registers + column C
      pm depth 2  (697, 770) (558, 780)              columns A + B
      pw depth 2  (611, 765) (380, 770)              column CORE (+ u_ft_ft0_o_1 on kv3_phy_v1)
      ps depth 3  (516, 760) (432, 518) (432, 193)   kv3_phy_v1: u_ft_ft0_o_2 / _3 (was depth 2 from a relay 524 um away)
    Release rule kept: stage k of a chain is released no later than the epoch reaches it (depth_k <= depth_0 + k) and
    stage 0 of every observable chain keeps its depth (pi stage 0: 2; ft0 stage 0: rg5, untouched), so no output epoch
    moves.  The po epochs are read by nothing (the core takes po data only).  Rows without a po/pi register (hrst, rg5)
    and every other relay_sites key are kept byte-identical.
  clock taps: the registers moved, so the type's taps are re-solved by the fixed script
      reach_fix.py fix --types '^kv3_phy(_v1)?$' --classes 1,2,3   (hard-wrapper taps, KV-KITFIX-1)
    run from --repo (default: this source repository) unless --no-taps.
    Plain internal station banks are absent from taps.planned_sinks, so the form publishes
    their payload+epoch counts in clock.sink_sites_um before re-solving the taps.

IDEMPOTENT: the output is a pure function of the windows / core of the input; a second run returns the same bytes.
Touches only partition_types[kv3_phy|kv3_phy_v1].{internal_stations, relay_sites, reset.port_relays, note, clock taps}.
Lane cycles are NOT edited here: run this form before the chain's `sync` step with the pre-form plan as its base.
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TYPES = ("kv3_phy", "kv3_phy_v1")
REPO = str(Path(__file__).resolve().parents[2])
REACH = 405.0
PLAN_HOP = 340.0                # RULEBOOK R-REACH planning step
GAP = 24.0                      # CORE column: um east of the core E edge (KV-TYPES-5 stage 0)
X_A, X_B, X_C = 508.48, 620.0, 686.24   # B clear of the die clock islands at x 580-585 and 741-744
FACE_IN = 7.0                   # face register column, um inside the E edge (placed face flops x 855-858)
PI = ("o_phy_Q__sN_fhN", "o_phy_Q__sN_piN", "o_phy_Q__sN_piN_d1", "o_phy_Q__sN_piN_d2", "o_phy_Q__sN_piN_d3",
      "o_phy_Q__sN_rhN")
PO = ("i_kvpc_Q_N_pc__po", "i_kvpc_Q_N_pc__po_d1", "i_kvpc_Q_N_pc__po_d2", "i_kvpc_Q_N_pc__po_d3")
PO_PIN0_Y, PO_PITCH, PO_W, PO_WORD = 510.924, 0.192, 328, 120.0   # qkd_hbm3e_phy_pc4.lef: po<k>[b] y (macro frame)
PI_DEPTH = 3
MARK = "KV-PHY-REACH 11-13"
# reset rows: name -> (depth, relay sites); sinks are assigned by column below
RESET = {"pe": (1, [[770.0, 820.0]]),
         "pm": (2, [[697.0, 770.0], [558.0, 780.0]]),
         "pw": (2, [[611.0, 765.0], [380.0, 770.0]]),
         "ps": (3, [[516.0, 760.0], [432.0, 518.0], [432.0, 193.0]])}
FOREIGN = {"u_ft_ft0_o_1": "pw", "u_ft_ft0_o_2": "ps", "u_ft_ft0_o_3": "ps"}   # kv3_phy_v1 ft stations that shared rg1/rg3


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def r3(p):
    return [round(float(p[0]), 3), round(float(p[1]), 3)]


def type_y(part, H, die_y):
    return die_y - part["origin_um"][1] if part.get("orient", "R0") in ("R0", "MY") else H - (die_y - part["origin_um"][1])


def type_face(part, face):
    o = part.get("orient", "R0")
    if face in ("E", "W") and o in ("MY", "R180"):
        return {"E": "W", "W": "E"}[face]
    if face in ("N", "S") and o in ("MX", "R180"):
        return {"N": "S", "S": "N"}[face]
    return face


def windows(raw, tn):
    """{bus: (y0, y1)} E-face window of every po/pi bus in the type frame, identical on every instance"""
    t = raw["partition_types"][tn]
    H = t["outline_um"][1]
    parts = {p["name"]: p for p in raw["partitions"]}
    ports = {p["id"]: p for p in raw["ports"]}
    n_inst = sum(1 for p in raw["partitions"] if p["type"] == tn)
    acc = {}
    for ln in raw["lanes"]:
        for pid, side in ((ln["ports"][0], "src"), (ln["ports"][-1], "dst")):
            pr = ports[pid]
            e = pr[side]
            part = parts.get(e.get("part"))
            if part is None or part["type"] != tn or e["bus"] not in PI + PO:
                continue
            # port faces are given on the source side
            f = pr["face"] if side == "src" else {"E": "W", "W": "E", "N": "S", "S": "N"}[pr["face"]]
            assert type_face(part, f) == "E", f"{tn}.{e['bus']}: window not on the type E face ({e['part']})"
            ys = tuple(round(v, 2) for v in sorted(type_y(part, H, v) for v in pr["window_um"]))
            acc.setdefault(e["bus"], []).append(ys)
    out = {}
    for bus in PI + PO:
        v = acc.get(bus) or []
        assert len(v) == n_inst, f"{tn}.{bus}: {len(v)} windows for {n_inst} instances"
        assert max(abs(a - b) for w in v for a, b in zip(w, v[0])) <= 0.05, f"{tn}.{bus}: windows differ {set(v)}"
        out[bus] = v[0]
    return out


def station_sinks(t):
    """Weighted sites for plain pi/po station banks omitted by taps.planned_sinks.

    The placer firms every payload/epoch flop near regs_um.  Publish those
    banks explicitly rather than letting only face registers size the taps.
    """
    widths = {b["name"]: int(b["width"]) for b in t.get("buses", [])}
    return [[float(x), float(y), float(widths[e["conn"][4:]] + 1)]
            for e in t.get("internal_stations", [])
            if e.get("conn", "").startswith("bus:") and e["conn"][4:] in PI + PO
            for x, y in e.get("regs_um", [])]


def form_type(raw, tn):
    t = raw["partition_types"][tn]
    W, H = t["outline_um"]
    clock = t.setdefault("clock", {})
    # Drop only exact matching previously published pi/po bank rows, then
    # rebuild after re-siting.  This keeps the constructor idempotent and
    # preserves unrelated internal sink rows.
    old_banks = {tuple(r) for r in station_sinks(t)}
    clock["sink_sites_um"] = [r for r in clock.get("sink_sites_um", [])
                                if tuple(r) not in old_banks]
    mac = next(c for c in t["contents"] if c.get("physical_inst") == "u_bound.u_core")
    assert mac.get("orient", "R0") == "R0" and mac["physical_master"] == "qkd_hbm3e_phy_pc4", f"{tn}: core changed"
    mx0, my0 = mac["origin_um"]
    core_e = mx0 + mac["outline_um"][0]
    x_core = round(core_e + GAP, 3)
    x_face = W - FACE_IN
    assert core_e < x_core < X_A < X_B < X_C < x_face
    win = windows(raw, tn)
    st = t.setdefault("internal_stations", [])
    by = {e.get("conn"): e for e in st}
    rep = dict(buses={}, reset={})
    sink_xy = {}                 # reset sink (ot_dp_st instance) -> epoch flop xy
    chains = []                  # [(observable, [instances stage 0..n])]
    for bus in PI:
        e = by.get(f"bus:{bus}")
        assert e is not None and len(e["regs_um"]) == PI_DEPTH, f"{tn}.{bus}: expected {PI_DEPTH} source stations"
        src = e["from_um"]
        assert abs(src[0] - core_e) < 0.5, f"{tn}.{bus}: from_um is not the core E face"
        y0, y1 = win[bus]
        end = (W, (y0 + y1) / 2)
        f = lambda x: src[1] + (end[1] - src[1]) * (x - src[0]) / (end[0] - src[0])
        regs = [(x, f(x)) for x in (x_core, X_A, X_C)]
        hops = [man(a, b) for a, b in zip([tuple(src)] + regs, regs + [(x_face, end[1])])]
        worst_face = max(man(regs[-1], (x_face, y)) for y in (y0, y1))
        e["to_um"] = r3(end)
        e["regs_um"] = [r3(p) for p in regs]
        if MARK not in e.get("note", ""):
            e["note"] = (e.get("note", "") + f" | {MARK}: stations re-sited on the straight core pin row -> vN2 "
                         "window line (columns x 330.72 / 508.48 / 686.24), same depth, 0 cycles").strip(" |")
        names = [f"u_ist_{bus}_{j}" for j in range(PI_DEPTH)] + [f"u_bout_{bus}"]
        for nm, p in zip(names, regs + [(x_face, y1)]):
            sink_xy[nm] = p
        chains.append((True, names))
        rep["buses"][bus] = dict(dir="out", stations=PI_DEPTH, cycles_added=0, hops_um=[round(h, 1) for h in hops],
                                 worst_bit_last_hop_um=round(worst_face, 1), window_y=[y0, y1])
    for k, bus in enumerate(PO):
        y0, y1 = win[bus]
        src = (W, (y0 + y1) / 2)
        cy = my0 + PO_PIN0_Y + k * PO_WORD + PO_PITCH * (PO_W - 1) / 2      # po<k> pin row centre
        end = (round(core_e - 0.096, 3), cy)
        f = lambda x: src[1] + (end[1] - src[1]) * (x - src[0]) / (end[0] - src[0])
        regs = [(X_B, f(X_B)), (x_core, f(x_core))]
        hops = [man(a, b) for a, b in zip([(x_face, src[1])] + regs, regs + [end])]
        ent = dict(conn=f"bus:{bus}", from_um=r3(src), to_um=r3(end), regs_um=[r3(p) for p in regs],
                   launch="face flop", capture=f"u_core.po{k}",
                   note=(f"{MARK}: po word {k} face register at its pins (the 0.6-route relay_sites are removed), "
                         "+2 stations on the straight window -> core pin row (column B x 620, core-face column "
                         "x 330.72); +2 data cycles (pre-approved R-REACH-2 class), hops 237 / 289 / 24"))
        if f"bus:{bus}" in by:
            i = st.index(by[f"bus:{bus}"])
            st[i] = ent
        else:
            st.append(ent)
        names = [f"u_bin_{bus}"] + [f"u_ist_{bus}_{j}" for j in range(2)]
        for nm, p in zip(names, [(x_face, y1)] + regs):
            sink_xy[nm] = p
        chains.append((False, names))
        rep["buses"][bus] = dict(dir="in", stations=2, cycles_added=2, hops_um=[round(h, 1) for h in hops],
                                 window_y=[y0, y1], core_pin_y=round(cy, 3))
    for b_, r_ in rep["buses"].items():
        assert max(r_["hops_um"]) <= PLAN_HOP, f"{tn}.{b_}: hop {max(r_['hops_um'])} > {PLAN_HOP}"
    # ---- po face registers back at their pins
    rs = t.setdefault("relay_sites", {})
    drop = [k for k in rs if any(k.startswith(f"u_bin_{b}/") for b in PO)]
    for k in drop:
        del rs[k]
    rep["po_relay_sites_removed"] = len(drop)
    # ---- reset rows
    rows = t["reset"].get("port_relays") or []
    mine = set(sink_xy)
    keep, foreign = [], []
    for row in rows:
        if row["name"] in RESET or mine & set(row["sinks"]):     # the old rg rows and this form's own rows
            foreign += [s for s in row["sinks"] if s not in mine]
            for j in range(int(row["depth"])):
                rs.pop(f"u_prl_{row['name']}_{j}/q", None)
        else:
            keep.append(row)
    assert not (set(RESET) & {r["name"] for r in keep}), f"{tn}: a kept reset row uses a form name"
    assert set(foreign) <= set(FOREIGN), f"{tn}: unplanned reset sinks {sorted(set(foreign) - set(FOREIGN))}"
    if foreign:
        ft = next(f for f in t["ft_slots"] if f["name"] == "ft0")
        assert len(ft["regs_um"]) == 4
        for s in foreign:
            j = int(s.rsplit("_", 1)[1])
            sink_xy[s] = tuple(ft["regs_um"][j + 1][:2]) if j < 3 else (ft["regs_um"][0][0], 0.0)
    col = lambda x: ("pw" if x < 400 else "pm" if x < 650 else "pe")
    grp = {n: [] for n in RESET}
    for s in sorted(sink_xy):
        grp[FOREIGN[s] if s in FOREIGN else col(sink_xy[s][0])].append(s)
    tap = t["reset"]["tap_um"]
    new = []
    for name, (depth, sites) in RESET.items():
        if not grp[name]:
            continue
        assert len(sites) == depth
        pts = [tuple(tap)] + [tuple(s) for s in sites]
        tr = [man(a, b) for a, b in zip(pts, pts[1:])]
        leaf = {s: round(man(pts[-1], sink_xy[s]), 1) for s in grp[name]}
        assert max(tr + list(leaf.values())) <= PLAN_HOP, f"{tn}: reset row {name} hop {max(tr + list(leaf.values()))}"
        for (cx0, cy0, cw, ch) in [(mx0, my0, *mac["outline_um"])]:
            assert all(not (cx0 - 3 <= x <= cx0 + cw + 3 and cy0 <= y <= cy0 + ch) for x, y in sites), "relay on core"
        new.append(dict(name=name, depth=depth, sinks=grp[name]))
        for j, s in enumerate(sites):
            rs[f"u_prl_{name}_{j}/q"] = r3(s)
        rep["reset"][name] = dict(depth=depth, relays_um=sites, trunk_hops_um=[round(h, 1) for h in tr],
                                  leaf_max_um=max(leaf.values()), sinks=len(leaf))
    depth_of = {s: r["depth"] for r in new for s in r["sinks"]}
    for observable, names in chains:
        d0 = depth_of[names[0]]
        assert all(depth_of[n] <= d0 + k for k, n in enumerate(names)), f"{tn}: reset release order {names}"
        if observable:
            assert d0 == 2, f"{tn}: {names[0]} reset depth {d0} != 2 (the pi epoch would move)"
    t["reset"]["port_relays"] = keep + new
    if MARK not in t.get("note", ""):
        t["note"] = (t.get("note", "") + f" | {MARK} PHY reach form (dkv100/phy/phy_form.py): po/pi registers in "
                     "columns at the face pins, x 686 / 620 / 508 and the core face x 330.72 on straight pin rows; po "
                     "+2 stations (+2 cycles, relay_sites 0.6-route form withdrawn); reset rows pe/pm/pw/ps").strip(" |")
    rep["hop_max_um"] = max(max(r_["hops_um"]) for r_ in rep["buses"].values())
    rep["stations"] = sum(r_["stations"] for r_ in rep["buses"].values())
    banks = station_sinks(t)
    clock["sink_sites_um"].extend(banks)
    rep["station_clock_sinks"] = int(sum(r[2] for r in banks))
    return rep


def taps(plan_out, repo, report):
    """re-solve the hard-wrapper clock taps of the two types (reach_fix classes 1-3) in place"""
    d = os.path.dirname(os.path.abspath(plan_out))
    with tempfile.TemporaryDirectory(dir=d) as td:
        ev, new = os.path.join(td, "ev.json"), os.path.join(td, "p.json")
        cmd = [sys.executable, "-I", "tools/die_plan/reach_fix.py", "fix", os.path.abspath(plan_out), "--repo", ".",
               "--types", "^kv3_phy(_v1)?$", "--classes", "1,2,3", "--out-plan", new, "--event", ev]
        r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
        sys.stdout.write(r.stdout[-2000:])
        if r.returncode not in (0,) or not os.path.exists(ev):
            sys.stderr.write(r.stderr[-4000:])
            raise SystemExit(f"phy_form: reach_fix tap stage failed rc {r.returncode}")
        e = json.load(open(ev))
        report["taps"] = [dict(type=x["type"], applied=x["applied"], worse=x["worse"], before=x["before"],
                               after=x["after"]) for x in e["rows"]]
        report["taps_summary"] = dict(before=e["summary_before"], after=e["summary_after"])
        a = json.load(open(plan_out))
        b = json.load(open(new))
        for tn in a["partition_types"]:          # only the two types may differ
            if tn not in TYPES:
                assert a["partition_types"][tn] == b["partition_types"][tn], f"tap stage touched {tn}"
        for k in a:
            if k != "partition_types":
                assert a[k] == b[k], f"tap stage touched plan key {k}"
        os.replace(new, plan_out)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    opt = {a.split("=", 1)[0]: (a.split("=", 1) + [""])[1] for a in argv if a.startswith("--")}
    if len(args) != 2 or set(opt) - {"--report", "--repo", "--no-taps"}:
        raise SystemExit(__doc__)
    raw = json.load(open(args[0]))
    Q = copy.deepcopy(raw)
    report = dict(form=MARK, types={})
    for tn in TYPES:
        report["types"][tn] = form_type(Q, tn)
    a, b = copy.deepcopy(raw), copy.deepcopy(Q)
    for tn in TYPES:
        a["partition_types"].pop(tn)
        b["partition_types"].pop(tn)
    assert a == b, "phy_form: a key outside the two types changed"
    with open(args[1], "w") as f:
        json.dump(Q, f, indent=1)
        f.write("\n")
    if "--no-taps" not in opt:
        taps(args[1], opt.get("--repo") or REPO, report)
    # reach_fix may append a few control sinks after our bank rows.  On the
    # next application they predate those rows, so canonicalise this unordered
    # inventory to keep byte-idempotence without dropping any sink.
    final = json.load(open(args[1]))
    for tn in TYPES:
        rows = final["partition_types"][tn]["clock"].get("sink_sites_um", [])
        rows.sort(key=lambda r: tuple(float(v) for v in r))
    with open(args[1], "w") as f:
        json.dump(final, f, indent=1)
        f.write("\n")
    report["cycles"] = {"po lanes (pc -> phy, 4 buses x 32 instances)": "+2 data cycles each",
                        "pi lanes": "0", "boot": "0 on every observable epoch"}
    report["out_md5"] = hashlib.md5(open(args[1], "rb").read()).hexdigest()
    if opt.get("--report"):
        json.dump(report, open(opt["--report"], "w"), indent=1)
    for tn in TYPES:
        r = report["types"][tn]
        print(f"phy_form: {tn}: stations {r['stations']} hop max {r['hop_max_um']} um, po relay_sites removed "
              f"{r['po_relay_sites_removed']}, reset rows {{{', '.join(f'{k}: d{v['depth']} leaf {v['leaf_max_um']}' for k, v in r['reset'].items())}}}")
    print("phy_form: out md5", report["out_md5"])


if __name__ == "__main__":
    main(sys.argv[1:])
