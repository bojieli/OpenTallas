#!/usr/bin/env python3
"""KV-FT 10-24 (owner decision 12 plan item: cut KV feedthrough crossings; hub row = star).  Plan v3.8x -> v3.9ft
CANDIDATE.  Structural moves that turn star / far-tail lanes into neighbour-only collectives (accelerator principles:
neighbour-only hops, tree collectives, no star hubs).  Same-outline origin/orient swaps were searched first
(ft_swap_search_v39.py: 3,149 swaps, none lowers the crossing count): the v3.x lattice is already traffic-ordered, the
crossings come from the RTL connection pattern, so every move below changes connectivity (RTL change, listed per move).

  MA  PV flag reduction chain (replaces 128 1-bit pvw fault / y_valid lanes = 448 crossings).  hub_C's
      ot_qwen_tp8_pv_wide_ctl_tbf only uses |col_fault, (&col_valid || !|col_valid) and col_valid[0] (== &col_valid when
      all equal), so each pv row folds its 4 slices into 3 chain bits {f = OR fault, a = AND valid, o = OR valid} and
      passes them to the next row toward the hub (neighbour hop); pv_N_7 / pv_S_7 deliver 3 bits to hub_C.  The chain
      reuses the windows of 3 deleted row-0 lanes per half; each row's in->out traversal keeps the deleted slot's
      stations as internal_stations (FIRM regs) and as the hop lane's fixed_cycles.  RTL: new leaf ot_dp_pvflag_red per
      pv row (+ per-slice alignment = the old d# pads), pv ctl takes the 3 reduced bits (FLAG_D = chain depth).
  MD  kvs_ctl -> hroot broadcast trunk.  o_hroot_{EN,ES,WN,WS} (1118 b each) share 967 bits (fanr_h 784, boot
      group/controller data+addr, lprg layer/epoch/ctx/go); only 151 per quadrant differ (ectl_a_cfg slice + decoded
      boot we/last).  One 1269-b trunk per side (967 + 2 x 151) hub_C -> hub_Ei/Wi slot -> a registered fan leaf
      (qkd_hroot_fan) in hub_Eo/Wo, which drives the two 1118-b hroot ports as neighbour lanes.  Removes the 1118-b
      ft30/ft31 (hub_Eo) and ft2/ft3 (hub_Wo) corridors = the TRIAL-QK die-GRT overflow site (3349 overflow, all in
      hub_Eo/Wo gcells).  RTL: kvs_ctl output regroup + the fan leaf.
  MB  Fault / reset chains run TOWARD their collector (tail adjacent): fch_hg (hg_X_7 .. hg_X_0 -> hub_C, 9 crossings),
      fch_pc (pc_X_7 .. pc_X_0 -> hroot, 7), fch_pv (pv_7,5,3,1,0 -> hub_C, 7) are OR chains whose order is free; the
      head (efault only) moves to row 0, the tail (row 7) feeds the collector.  host_hbm_rst_n reaches phy_X_0 from
      pc_X_0 (end of its own pc chain) instead of a 7-crossing lane from hroot.  RTL: chain order + u_fch moves row 0 ->
      row 7 types; pc row-0 type forwards hbm_rst_n.

    python3 post_v39_ft.py IN.json PLANDIR OUTDIR      (writes OUTDIR/die_plan.json, OUTDIR/census/*, OUTDIR/r8/bus_groups.json,
                                                       OUTDIR/post_v39_ft.json = move log)
"""
import copy
import gzip
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("OT_DIE_PLAN_TOOLS", os.path.join(HERE, "..", "..", "..", "tools", "die_plan")))
import schema as S  # noqa: E402

STMAX = 400.0            # decision 12: registered station every <= 405 um (25-um legalisation slack like reset relays)
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
LOG = []


def idx(raw):
    return ({x["id"]: x for x in raw["ports"]}, {x["id"]: x for x in raw["lanes"]},
            {x["name"]: x for x in raw["partitions"]}, raw["partition_types"])


def bus_of(t, name):
    return next((b for b in t["buses"] if b["name"] == name), None)


def add_bus(t, name, d, w, note=None):
    b = bus_of(t, name)
    if b:
        assert b["dir"] == d and b["width"] == w, (name, b)
        return
    b = dict(name=name, dir=d, width=w, kind="data")
    if note:
        b["note"] = note
    t["buses"].append(b)


def drop_buses(t, names):
    t["buses"] = [b for b in t["buses"] if b["name"] not in names]


def drop_lanes(raw, lids):
    P, L, _, _ = idx(raw)
    pids = {pid for lid in lids for pid in L[lid]["ports"]}
    raw["lanes"] = [x for x in raw["lanes"] if x["id"] not in lids]
    raw["ports"] = [x for x in raw["ports"] if x["id"] not in pids]


def even_regs(a, b, k):
    """k station points evenly on the L route a -> b (x first), type frame."""
    L = abs(a[0] - b[0]) + abs(a[1] - b[1])
    out = []
    for j in range(1, k + 1):
        t = L * j / (k + 1)
        dx = abs(b[0] - a[0])
        if t <= dx:
            out.append([round(a[0] + math.copysign(t, b[0] - a[0]), 3), round(a[1], 3)])
        else:
            out.append([round(b[0], 3), round(a[1] + math.copysign(t - dx, b[1] - a[1]), 3)])
    return out


def pin_pt(P, pid, part):
    """centre of port pid's window, type frame of `part`."""
    return [round(v, 3) for v in P.to_type(part, P.port_point(pid))]


def drop_unused_slots(raw):
    P = S.Plan(raw)
    used = {}
    for lid in P.lanes:
        for part, slot, _, _ in P.lane_crossings(lid):
            if slot:
                used.setdefault(P.parts[part]["type"], set()).add(slot)
    n = 0
    for tn, t in raw["partition_types"].items():
        keep = [s for s in t.get("ft_slots", []) if s["name"] in used.get(tn, set())]
        n += len(t.get("ft_slots", [])) - len(keep)
        if "ft_slots" in t:
            t["ft_slots"] = keep
    return n


# ----------------------------------------------------------------------------------------------- MA: pv flag chain
FLAG = re.compile(r"^o_pvw__u_sN_j_(fault|y_valid)(_d\d+)?$")
TEMPL = {"f": ("o_pvw__u_sN_j_fault", "OR fault"), "a": ("o_pvw__u_sN_j_y_valid", "AND y_valid"),
         "o": ("o_pvw__u_sN_j_fault_d1", "OR y_valid")}


def move_ma(raw, census):
    P = S.Plan(raw)
    ports, lanes, parts, T = idx(raw)
    flag = []
    for lid, ln in lanes.items():
        a, b = ports[ln["ports"][0]], ports[ln["ports"][-1]]
        if a["src"]["part"].startswith("pv_") and FLAG.match(a["src"]["bus"]) and b["dst"]["part"] == "hub_C":
            flag.append(lid)
    assert len(flag) == 128, len(flag)
    new_ports, new_lanes, ist = [], [], {}
    hub_new = []
    for half in ("N", "S"):
        rows = [f"pv_{half}_{k}" for k in range(8)]
        for bit, (tbus, what) in TEMPL.items():
            tl = next(l for l in flag if ports[lanes[l]["ports"][0]]["src"]["part"] == rows[0]
                      and ports[lanes[l]["ports"][0]]["src"]["bus"] == tbus)
            tp = lanes[tl]["ports"]
            assert len(tp) == 8, (tl, tp)
            xs = P.lane_crossings(tl)              # (part, slot, in_port, out_port) for rows 1..7
            for k, pid in enumerate(tp):
                old = ports[pid]
                src = rows[k]
                dst = rows[k + 1] if k < 7 else "hub_C"
                assert old["src"]["part"] == src and old["dst"]["part"] == dst, (pid, old)
                dbus = f"i_pvf_{bit}" if k < 7 else f"i_pvf_{half}_{bit}"
                np_ = dict(old, id=f"PVF_{half}_{bit}_{k}", src=dict(part=src, bus=f"o_pvf_{bit}"),
                           dst=dict(part=dst, bus=dbus), width=1)
                new_ports.append(np_)
                fixed = 0
                if k > 0:                          # row k's in->out traversal = the deleted slot's stations
                    part, slot, pin, pout = xs[k - 1]
                    assert part == src
                    s = P.slot(part, slot)
                    st = int(s.get("stations", 1))
                    fixed = st
                    a_ = pin_pt(P, pin, part)
                    b_ = pin_pt(P, pout, part)
                    regs = [list(r) for r in s["regs_um"]] if s.get("regs_um") else even_regs(a_, b_, st)
                    ist.setdefault(parts[part]["type"], {})[f"bus:o_pvf_{bit}"] = dict(
                        conn=f"bus:o_pvf_{bit}", from_um=a_, to_um=b_, regs_um=regs, bits=1,
                        launch=f"face:i_pvf_{bit}", capture=f"face:o_pvf_{bit}",
                        note=f"KV-FT v3.9 MA: pv flag chain ({what}) in->out, stations of the deleted slot {slot}")
                new_lanes.append(dict(id=f"LPVF_{half}_{bit}_{k}", ports=[np_["id"]], fixed_cycles=fixed,
                                      note=f"KV-FT v3.9 MA: pv flag reduction chain {half} {what}, hop {src}->{dst}"
                                           + (f" (+{fixed} internal stations in {src})" if fixed else "")))
                if k == 7:
                    hub_new.append((f"i_pvf_{half}_{bit}", what))
    old_hub = {ports[lanes[l]["ports"][-1]]["dst"]["bus"] for l in flag}
    old_pv = {b["name"] for tn in {parts[f"pv_{h}_{k}"]["type"] for h in "NS" for k in range(8)}
              for b in T[tn]["buses"] if FLAG.match(b["name"])}
    drop_lanes(raw, set(flag))
    raw["ports"] += new_ports
    raw["lanes"] += new_lanes
    for h in "NS":
        for k in range(8):
            tn = parts[f"pv_{h}_{k}"]["type"]
            t = T[tn]
            drop_buses(t, old_pv)
            for bit in TEMPL:
                add_bus(t, f"o_pvf_{bit}", "out", 1)
                if k > 0:
                    add_bus(t, f"i_pvf_{bit}", "in", 1)
            if not any(c["inst"] == "u_pvf" for c in t["contents"]):
                t["contents"].append(dict(inst="u_pvf", module="ot_dp_pvflag_red", status="new", note=(
                    "KV-FT v3.9 MA: folds the row's 4 slice flags (per-slice alignment = the old d# pads) with the "
                    "incoming chain: f |= fault, a &= y_valid, o |= y_valid; row 0 has no chain input")))
            for conn, e in ist.get(tn, {}).items():
                t.setdefault("internal_stations", [])
                t["internal_stations"] = [x for x in t["internal_stations"] if x.get("conn") != conn] + [e]
    hc = T["kv3_hub_C"]
    drop_buses(hc, old_hub)
    for name, what in hub_new:
        add_bus(hc, name, "in", 1, note=f"KV-FT v3.9 MA: reduced pv flag ({what}) -> pv wide ctl")
    for c in hc["contents"]:
        if c["module"] == "ot_qwen_tp8_pv_wide_ctl_tbf_p":
            c["note"] = (c.get("note", "") + " | KV-FT v3.9 MA: col_valid/col_fault[31:0] -> 3 reduced chain bits "
                         "(cbad = f | (a != o) | (!idle & a != out_slot)); FLAG_D = chain depth").strip(" |")
    # census: the 128 slice-flag rows -> chain rows
    rows, mp = census
    keep = []
    for r in rows:
        if re.match(r"pvw_[01]__u_s\d+_j$", r[0]) and r[1] in ("fault", "y_valid") and r[3] in ("col_fault", "col_valid"):
            continue
        keep.append(r)
    ctl = {"N": "pvw_1__u_ctl", "S": "pvw_0__u_ctl"}
    for h in "NS":
        for k in range(8):
            mp["parts"][f"pvf_{h}_{k}"] = f"pv_{h}_{k}"
            for bit in TEMPL:
                if k < 7:
                    keep.append([f"pvf_{h}_{k}", f"o_{bit}", f"pvf_{h}_{k + 1}", f"i_{bit}", "data", "1"])
                else:
                    keep.append([f"pvf_{h}_{k}", f"o_{bit}", ctl[h], f"pvf_{bit}", "data", "1"])
    rows[:] = keep
    LOG.append(dict(move="MA", removed_lanes=len(flag), added_lanes=len(new_lanes),
                    removed_hub_C_buses=len(old_hub), removed_pv_buses=len(old_pv)))
    return set(flag)


# ------------------------------------------------------------------------------------------ MD: hroot broadcast trunk
SHARED, PERQ = 967, 151


def move_md(raw, census):
    ports, lanes, parts, T = idx(raw)
    P = S.Plan(raw)
    gone = set()
    for side, (la, lb) in (("E", ("L1447", "L1448")), ("W", ("L1449", "L1450"))):
        A, B = lanes[la], lanes[lb]
        pa, pb = [ports[x] for x in A["ports"]], [ports[x] for x in B["ports"]]
        assert len(pa) == 3 and len(pb) == 3 and pa[0]["src"]["part"] == "hub_C", (la, lb)
        inner, outer = pa[0]["dst"]["part"], pa[1]["dst"]["part"]      # hub_Ei/Wi (slot), hub_Eo/Wo (fan)
        q = {pa[2]["dst"]["part"]: pa[2], pb[2]["dst"]["part"]: pb[2]}
        w = SHARED + 2 * PERQ
        trunk = []
        for k in range(2):
            lo = min(pa[k]["window_um"][0], pb[k]["window_um"][0])
            hi_free = max(pa[k]["window_um"][1], pb[k]["window_um"][1])
            hi = S.window_for(lo, w, pa[k]["layers"])
            assert hi <= hi_free + 1e-6, (la, k, lo, hi, hi_free)
            pr = dict(pa[k], id=f"HT_{side}_{k}", width=w, window_um=[lo, hi])
            trunk.append(pr)
        trunk[0]["src"] = dict(part="hub_C", bus=f"o_kvs_ctl_o_hroot_{side}")
        trunk[1]["dst"] = dict(part=outer, bus=f"i_kvs_ctl_hroot_{side}")
        slot = trunk[0]["dst"]["bus"][:-2]
        s = next(x for x in T[parts[inner]["type"]]["ft_slots"] if x["name"] == slot)
        s["width"] = w
        to = parts[outer]["type"]
        fan_in = pin_pt(P, pa[1]["id"], outer)          # old slot in-port = the trunk landing on the fan
        new_lanes = [dict(id=f"LHT_{side}", ports=[t["id"] for t in trunk], fixed_cycles=0,
                          note=f"KV-FT v3.9 MD: kvs_ctl -> hroot {side} broadcast trunk ({SHARED} shared + 2 x {PERQ}"
                               f" per-quadrant b) -> {outer} fan")]
        new_ports = list(trunk)
        for dpart, old in sorted(q.items()):
            qn = dpart.split("_")[1]
            np_ = dict(old, id=f"HF_{qn}", src=dict(part=outer, bus=f"o_kvs_ctl_hroot_{qn}"))
            new_ports.append(np_)
            fan_out = pin_pt(P, old["id"], outer)
            L = abs(fan_in[0] - fan_out[0]) + abs(fan_in[1] - fan_out[1])
            st = max(0, math.ceil(L / STMAX) - 1)
            T[to].setdefault("internal_stations", []).append(dict(
                conn=f"bus:o_kvs_ctl_hroot_{qn}", from_um=fan_in, to_um=fan_out,
                regs_um=even_regs(fan_in, fan_out, st), bits=1118, launch=f"face:i_kvs_ctl_hroot_{side}",
                capture=f"face:o_kvs_ctl_hroot_{qn}",
                note=f"KV-FT v3.9 MD: fan {side} -> hroot_{qn}, {L:.0f} um, {st} FIRM stations <= {STMAX:g} um"))
            lid = la if old is pa[2] else lb
            new_lanes.append(dict(id=lid, ports=[np_["id"]], fixed_cycles=st,
                                  note=f"KV-FT v3.9 MD: {outer} fan -> {dpart} (1118 b; {st} internal stations)",
                                  **({"param": lanes[lid]["param"]} if "param" in lanes[lid] else {})))
        # buses
        hc = T["kv3_hub_C"]
        drop_buses(hc, {pa[0]["src"]["bus"], pb[0]["src"]["bus"]})
        add_bus(hc, f"o_kvs_ctl_o_hroot_{side}", "out", w,
                note=f"KV-FT v3.9 MD: {SHARED} shared + 2 x {PERQ} per-quadrant bits")
        add_bus(T[to], f"i_kvs_ctl_hroot_{side}", "in", w)
        for dpart in q:
            add_bus(T[to], f"o_kvs_ctl_hroot_{dpart.split('_')[1]}", "out", 1118)
        T[to]["contents"].append(dict(inst=f"u_hfan_{side}", module="qkd_hroot_fan", status="new", note=(
            f"KV-FT v3.9 MD: registered fan of the kvs_ctl {side} broadcast trunk to the two hroots of this side")))
        for c in hc["contents"]:
            if c["inst"] == "kvs_ctl":
                c["note"] = (c.get("note", "") + f" | KV-FT v3.9 MD: o_hroot_{side} = shared + per-quadrant fields "
                             "(one trunk per side)").strip(" |")
        gone |= {la, lb}
        drop_lanes(raw, {la, lb})
        raw["ports"] += new_ports
        raw["lanes"] += new_lanes
        ports, lanes, parts, T = idx(raw)
        P = S.Plan(raw)
        # census
        rows, mp = census
        mp["parts"][f"hfan_{side}"] = outer
        keep = []
        for r in rows:
            if r[0] == "kvs_ctl" and r[1] in (pa[0]["src"]["bus"].replace("o_kvs_ctl_", ""),
                                              pb[0]["src"]["bus"].replace("o_kvs_ctl_", "")):
                keep.append([f"hfan_{side}", "o_" + r[1].split("_")[-1], r[2], r[3], r[4], r[5]])
                continue
            keep.append(r)
        keep.append(["kvs_ctl", f"o_hroot_{side}", f"hfan_{side}", "i_trunk", "data", str(w)])
        rows[:] = keep
    LOG.append(dict(move="MD", trunk_bits=SHARED + 2 * PERQ, replaced=sorted(gone)))
    return gone


# ------------------------------------------------------------------------------------------------------- main
def main():
    src, pdir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    moves = (sys.argv[4] if len(sys.argv) > 4 else "MA,MD").split(",")
    raw = json.load(open(src))
    cen = raw["census"][0]
    with gzip.open(os.path.join(pdir, cen["rows"]), "rt") as f:
        hdr, *rows = [ln.rstrip("\n").split("\t") for ln in f if ln.strip()]
    mp = json.load(open(os.path.join(pdir, cen["map"])))
    census = (rows, mp)
    gone = set()
    if "MA" in moves:
        gone |= move_ma(raw, census)
    if "MD" in moves:
        gone |= move_md(raw, census)
    if "MB" in moves:
        import post_v39_mb
        gone |= post_v39_mb.move_mb(raw, census, LOG)
    n = drop_unused_slots(raw)
    live = {x["id"] for x in raw["lanes"]}
    raw.setdefault("latency", {})["lanes"] = {k: v for k, v in raw.get("latency", {}).get("lanes", {}).items()
                                              if k in live and k not in gone}   # gen.py latency rewrites the table
    LOG.append(dict(dropped_slots=n))
    raw["latency_groups"] = [g for g in raw.get("latency_groups", []) if not set(g["lanes"]) & gone]
    os.makedirs(os.path.join(out, "census"), exist_ok=True)
    with gzip.open(os.path.join(out, "census", "census_rows_v39ft.tsv.gz"), "wt") as f:
        f.write("\t".join(hdr) + "\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    json.dump(mp, open(os.path.join(out, "census", "census_map_v39ft.json"), "w"), indent=1)
    raw["census"] = [dict(cen, rows="census/census_rows_v39ft.tsv.gz", map="census/census_map_v39ft.json",
                          note=cen.get("note", "") + " | KV-FT v3.9ft: planned-RTL census (MA/MD/MB rows replaced: "
                          "see post_v39_ft.py)")]
    if cen.get("bitcon"):
        raw["census"][0]["bitcon"] = "census/" + os.path.basename(cen["bitcon"])
    # R8 bus groups: drop groups whose members ride a replaced lane (the reduced / regrouped buses have no as-built group)
    bg = json.load(open(os.path.join(pdir, "r8", "bus_groups.json")))
    n0 = len(bg["landing"])
    bg["landing"] = [g for g in bg["landing"] if not {m.get("lane") for m in g["members"]} & gone
                     and not any(re.match(r"pvw_[01]__u_s\d+_j\.(fault|y_valid)$", m.get("source", ""))
                                 for m in g["members"])
                     and not any(m.get("source", "").startswith("kvs_ctl.o_hroot_") for m in g["members"])]
    bg["note"] = bg.get("note", "") + f" | KV-FT v3.9ft: {n0 - len(bg['landing'])} groups of replaced buses dropped"
    os.makedirs(os.path.join(out, "r8"), exist_ok=True)
    json.dump(bg, open(os.path.join(out, "r8", "bus_groups.json"), "w"))
    LOG.append(dict(r8_groups_dropped=n0 - len(bg["landing"])))
    raw["note"] = raw.get("note", "") + " | v3.9ft CANDIDATE (KV-FT 10-24, NOT on main): " + ", ".join(moves) + \
        " (post_v39_ft.py)"
    json.dump(raw, open(os.path.join(out, "die_plan.json"), "w"), indent=1)
    json.dump(LOG, open(os.path.join(out, "post_v39_ft.json"), "w"), indent=1)
    print(json.dumps(LOG))


if __name__ == "__main__":
    main()
