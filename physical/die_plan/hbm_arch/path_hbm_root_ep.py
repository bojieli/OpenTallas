#!/usr/bin/env python3
"""PATH-HBM/ROOTEP (COORD ruling (2) 2026-10-25 14:44: root vertical cut 0.70-0.76 -> re-route the root endpoints, not
width).  Replaces the B2o name-based CARTESIAN placeholder of core_conns['root'] for the nine root<->hub lanes
L12/L12m/L13/L13m/L62/L62m/L74m/L89/L89m (every idx-cluster port listed against ALL of them, outputs against input
buses) by a typed, direction-correct endpoint graph:

  * every bus bit-range is attributed to ONE real root core port bit-range (outputs only on *_o, inputs only on *_i);
  * SOURCE = the r18h5 as-built die netlist (physical/die_plan/hbm/bind/inputs/die_r18h5.v.gz, top hbm_v16_die), traced
    through the hbfd_rly/pad/lh/lh0/land transport stages by root_ep_trace.py: each row names the as-built partner it
    was traced to.  Fold rule of the B die (census note): as-built SW/NW partners -> NW_hub (q_hub_nw, L*),
    SE/NE -> NE_hub (q_hub, L*m).  TKM return L13_o[571:0] = PATH-HBM/HUBNW q_hub_nw L13_i bit map.
  * bits with no real driver/consumer stay OPEN (not invented); real root inputs with no hub->root lane left are
    UNLANED (COORD width/lane question);
  * exactly the root internal_stations of those nine buses are regenerated (b2o R3-INTERNAL rule: cores_b2.RelayRouter,
    hops <= 360 um, 405-um fallback in narrow corridors, never a register inside a hard core); capture = the core end
    (check.py R3-INTERNAL key); the note says dir in/out; outputs run core -> face window.
  * lanes / latency untouched (asserted).

    python3 path_hbm_root_ep.py --src <plan dir> --out <new plan dir> [--trace trace.json]
"""
import argparse, collections, json, os, re, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import schema as S  # noqa: E402
import check as CK  # noqa: E402
import b2n as B  # noqa: E402
import b2o as BO  # noqa: E402
import cores_b2 as CB  # noqa: E402
import path_hbm_b2p as PB  # noqa: E402

BUSES = ["L12_o", "L12m_o", "L13_o", "L13m_o", "L62_o", "L62m_o", "L74m_i", "L89_i", "L89m_i"]
NW, NE = ("SW", "NW"), ("SE", "NE")
SIDES = ("SW", "SE", "NW", "NE")
TKM = "u_tkm_SW_root"


def R(core, port, plo, phi, dirn, hub, asb, side=None, note=""):
    return dict(core=core, port=port, plo=plo, phi=phi, dir=dirn, hub=hub, asb=asb, side=side, note=note)


def link(side):
    return [R("u_hb_idx__link", "tx", 0, 2179, "out", "u_cij_Q.idx_tx_{r0,r1,h} (+_r1 copies)", ["cij_"], side,
              "idx_launch_data 2180 (ot_hgi_coll_idx_tkm_join: staging tx -> collective ingress vm_d)"),
            R("u_hb_idx__link", "tx_v", 0, 3, "out", "u_cij_Q.idx_tx_v (+_v_r1)", ["cij_"], side)]


def coll_cfg(side):
    return [R("u_col_idx", "pw_we", 0, 0, "out", "u_hb_idx__qctl_Q.program_we", ["hb_idx__qctl_"], side),
            R("u_col_idx", "pw_addr", 0, 7, "out", "u_hb_idx__qctl_Q.program_addr", ["hb_idx__qctl_"], side),
            R("u_col_idx", "pw_data", 0, 255, "out", "u_hb_idx__qctl_Q.program_data", ["hb_idx__qctl_"], side),
            R("u_col_idx", "start_v", 0, 0, "out", "u_hb_idx__qctl_Q.start", ["hb_idx__qctl_"], side),
            R("u_col_idx", "prm", 0, 11, "out", "u_hb_idx__qctl_Q.length", ["hb_idx__qctl_"], side),
            R("u_col_idx", "prm", 12, 43, "out", "u_hb_idx__op_Q.{weight,query}_sector", ["hb_idx__op_"], side),
            R("u_col_idx", "prm", 52, 65, "out", "u_hb_idx__qctl_Q.nkeys", ["hb_idx__qctl_"], side)]


TKMRET = [R(TKM, "w_v", 0, 0, "out", "q_hub_nw L13_i[0] -> vm writer_tkw (HUBNW)", ["hb_coll_SW"], NW),
          R(TKM, "w_addr", 0, 39, "out", "L13_i[40:1] w_addr", ["hb_coll_SW"], NW),
          R(TKM, "w_mask", 0, 15, "out", "L13_i[56:41] w_mask", ["hb_coll_SW"], NW),
          R(TKM, "w_data", 0, 511, "out", "L13_i[568:57] w_data", ["hb_coll_SW"], NW),
          R(TKM, "busy", 0, 0, "out", "L13_i[569] body_core tkx_busy", ["hb_coll_SW"], NW),
          R(TKM, "done", 0, 0, "out", "L13_i[570] body_core tkx_done", ["hb_coll_SW"], NW),
          R(TKM, "fault", 0, 0, "out", "L13_i[571] body_core tkx_fault", ["hb_coll_SW"], NW)]

# bus -> ordered rows (LSB first).  Placement by geometry: the 2.2-kb idx launch + vm/vms requests take L12 (window
# y~712, next to the idx cluster); the TKM return + index_rr take the direct 2-cycle L13 (window y~2196, above TKM root).
MAP = {
    "L12_o": link(NW) + [
        R("u_hb_idx__ctl", "cq", 0, 337, "out", "u_hb_vms_Q.cq[675:338]", ["hb_vms_SW"], NW),
        R("u_hb_argmax", "cq", 0, 337, "out", "u_hb_vms_Q.cq[337:0]", ["hb_vms_SW"], NW),
        R("u_hb_idx__ctl", "vm_rq", 0, 135, "out", "u_vmb_Q0..7.rq4 (17 b each)", ["vmb_SW"], NW)],
    "L12m_o": link(NE),
    "L13_o": TKMRET + [R("u_hb_idx__ctl", "index_rr", 0, 2055, "out", "u_hb_idx__op_Q.vm_rr", ["hb_idx__op_SW"], NW)],
    "L13m_o": [],
    "L62_o": coll_cfg(NW),
    "L62m_o": coll_cfg(NE) + [
        R("u_col_idx", "ready", 0, 0, "out", "u_hleaf_Q.t_ready", ["hleaf_SE"], NE),
        R("u_col_idx", "active", 0, 0, "out", "u_hleaf_Q.t_active", ["hleaf_SE"], NE),
        R("u_col_idx", "fault", 0, 0, "out", "u_hleaf_Q.t_fault", ["hleaf_SE"], NE),
        R("u_hb_argmax", "nan_flag", 0, 0, "out", "u_fr_Q.in", ["fr_NE"], NE),
        R("u_hc_eng_tail0_sk_steady", "fault", 0, 0, "out", "u_hleaf_Q.t_fault (hc_eng.fault)", None, NE,
          "UNVERIFIED split-piece attribution: as-built hc_eng.fault -> hleaf_SE.t_fault; B2o put this piece port on "
          "the m lanes only"),
        R("u_hc_eng_tail1_sk_steady", "fault", 0, 0, "out", "u_hleaf_Q.t_fault (hc_eng.fault)", None, NE,
          "UNVERIFIED split-piece attribution (see tail0)")],
    "L89_i": [R("u_hb_idx__ctl", "qfault", 0, 0, "in", "u_hb_idx__qctl_Q.fault", ["hb_idx__qctl_SW"], NW,
                "fans out in root to qfault[0] (SW) and qfault[2] (NW): one folded NW qctl"),
              R("u_col_idx", "c_fault", 4, 4, "in", "u_hb_idx__nwsh.fault", ["hb_idx__nwsh"], NW)],
    "L89m_i": [R("u_hb_idx__ctl", "qfault", 1, 1, "in", "u_hb_idx__qctl_Q.fault", ["hb_idx__qctl_SE"], NE,
                 "fans out in root to qfault[1] (SE) and qfault[3] (NE)")],
    "L74m_i": [R("u_col_idx", "cfg_v", 0, 0, "in", "u_hleaf_Q.a_cfg_v", ["hleaf_SE"], NE),
               R("u_col_idx", "cfg_target", 0, 7, "in", "u_hleaf_Q.a_cfg_target", ["hleaf_SE"], NE),
               R("u_col_idx", "cfg_addr", 0, 11, "in", "u_hleaf_Q.a_cfg_addr", ["hleaf_SE"], NE),
               R("u_col_idx", "cfg_data", 0, 255, "in", "u_hleaf_Q.a_cfg_data", ["hleaf_SE"], NE),
               R("u_col_idx", "desc_v", 0, 0, "in", "u_hleaf_Q.a_desc_v", ["hleaf_SE"], NE),
               R("u_col_idx", "launch_v", 0, 0, "in", "u_hleaf_Q.a_launch_v", ["hleaf_SE"], NE)],
}
# extra fan-out bits on the root side (same lane bit, second port bit)
FANOUT = {("L89_i", "u_hb_idx__ctl", "qfault", 0): 2, ("L89m_i", "u_hb_idx__ctl", "qfault", 1): 3}
# real NW_hub -> root inputs of the idx cluster with no lane: L74 is TKM-only (HUBNW), L89 is 66 b.
UNLANED = [R("u_hb_idx__ctl", "cr", 0, 273, "in", "u_hb_vms_Q.cr[547:274]", ["hb_vms_SW"], NW),
           R("u_hb_argmax", "cr", 0, 273, "in", "u_hb_vms_Q.cr[273:0]", ["hb_vms_SW"], NW),
           R("u_hb_idx__ctl", "index_rq", 0, 135, "in", "u_hb_idx__op_Q.vm_rq", ["hb_idx__op_SW"], NW),
           R("u_hb_idx__ctl", "vm_rr", 0, 2055, "in", "u_vmb_Q0..7.rr4 (257 b each)", ["vmb_SW"], NW)]


def asb_name(core):
    return core[2:] if core.startswith("u_") else core


def verify(trace):
    """every mapped bit: as-built direction and partner match the table (root_ep_trace.py output)."""
    bad, n = [], 0
    amap = {"u_tkm_SW_root": "tkm_SW"}
    for bus, rows in list(MAP.items()) + [("UNLANED", UNLANED)]:
        for r in rows:
            if r["asb"] is None:
                continue
            key = f"{amap.get(r['core'], asb_name(r['core']))}.{r['port']}"
            if key not in trace:
                bad.append(f"{bus} {key}: not in trace"); continue
            for b in range(r["plo"], r["phi"] + 1):
                row = trace[key]["rows"][b]
                n += 1
                if row["dir"] != r["dir"]:
                    bad.append(f"{bus} {key}[{b}] dir {row['dir']}"); continue
                names = [p[0] for p in row["partners"]] if r["dir"] == "out" else [row["partner"]]
                hit = []
                for x in names:
                    inst = x.split(".")[0]
                    for a in r["asb"]:
                        if not inst.startswith(a):
                            continue
                        if (r["side"] is None or a.rstrip("_").endswith(SIDES) or not any(s in inst for s in SIDES)
                                or any(re.search(rf"_{s}\d*$", inst) for s in r["side"])):
                            hit.append(x)
                if not hit:
                    bad.append(f"{bus} {key}[{b}] partners {names[:3]} != {r['asb']} {r['side']}")
    return n, bad


def apply(plan, out, cc, trace=None):
    T = plan["partition_types"]["root"]
    lat0 = json.dumps({k: plan["latency"]["lanes"].get(k) for k in ("L12", "L12m", "L13", "L13m", "L62", "L62m",
                                                                     "L74m", "L89", "L89m")}, sort_keys=True)
    bw = {b["name"]: b for b in T["buses"]}
    rep = dict(buses={}, unlaned=[], removed_targets=0)
    hcs = {h["inst"]: h for h in T["hard_cores"]}
    pins = {}
    for k, h in hcs.items():
        o = h.get("orient", "R0")
        cw, ch = h["outline_um"]
        d = collections.defaultdict(dict)
        f = collections.defaultdict(list)
        for p in json.loads((out / h["pins_file"]).read_text()):
            m = re.match(r"^(.*?)(?:\[(\d+)\])?$", p["name"])
            rx, ry = BO.opt(o, p["x"], p["y"], cw, ch)
            d[m.group(1)][int(m.group(2) or 0)] = (h["origin_um"][0] + rx, h["origin_um"][1] + ry)
            f[m.group(1)].append(BO.oface(o, CK._core_face("R0", p["x"], p["y"], cw, ch)))
        pins[k] = (d, f)
    # --- bit maps + checks
    groups = collections.defaultdict(list)     # (core, port, bus) -> port bits
    for bus in BUSES:
        rows, at, tab = MAP[bus], 0, []
        want = "out" if bus.endswith("_o") else "in"
        for r in rows:
            if r["dir"] != want:
                raise ValueError(f"{bus}: {r['core']}.{r['port']} dir {r['dir']}")
            d = pins[r["core"]][0].get(r["port"])
            if d is None or any(b not in d for b in range(r["plo"], r["phi"] + 1)):
                raise ValueError(f"{bus}: {r['core']}.{r['port']}[{r['phi']}:{r['plo']}] has no pins")
            w = r["phi"] - r["plo"] + 1
            tab.append(dict(bits=f"[{at + w - 1}:{at}]", port=f"{r['core']}.{r['port']}[{r['phi']}:{r['plo']}]",
                            dir=r["dir"], hub=r["hub"], asbuilt=r["asb"], fold=r["side"], note=r["note"]))
            groups[(r["core"], r["port"], bus)] += list(range(r["plo"], r["phi"] + 1))
            fx = FANOUT.get((bus, r["core"], r["port"], r["plo"]))
            if fx is not None:
                groups[(r["core"], r["port"], bus)].append(fx)
                tab[-1]["fanout_port_bit"] = fx
            at += w
        if at > bw[bus]["width"]:
            raise ValueError(f"{bus}: {at} b > width {bw[bus]['width']}")
        rep["buses"][bus] = dict(width=bw[bus]["width"], used=at, open=bw[bus]["width"] - at,
                                 open_bits=(f"[{bw[bus]['width'] - 1}:{at}]" if at < bw[bus]["width"] else None),
                                 map=tab)
    for r in UNLANED:
        rep["unlaned"].append(dict(port=f"{r['core']}.{r['port']}[{r['phi']}:{r['plo']}]", bits=r["phi"] - r["plo"] + 1,
                                   hub=r["hub"], asbuilt=r["asb"]))
    if trace is not None:
        n, bad = verify(trace)
        rep["trace_verify"] = dict(bits=n, mismatches=bad[:20], n_bad=len(bad))
        if bad:
            raise ValueError(f"trace mismatches: {bad[:5]}")
    # --- core_conns: drop the nine placeholder buses, add the typed ones
    rc = cc["root"]
    for core, ports in rc.items():
        for port in list(ports):
            n0 = len(ports[port])
            ports[port] = [x for x in ports[port] if x[4:] not in BUSES]
            rep["removed_targets"] += n0 - len(ports[port])
            if not ports[port]:
                del ports[port]
    for (core, port, bus) in groups:
        rc.setdefault(core, {}).setdefault(port, []).append(f"bus:{bus}")
    # --- internal stations: regenerate exactly the nine buses
    W, H = T["outline_um"]
    geo = {h["inst"]: (h["origin_um"][0], h["origin_um"][1], h["outline_um"][0], h["outline_um"][1]) for h in T["hard_cores"]}
    boxes = list(geo.values())
    # the TKM tile array is one routing obstacle: its 8.64-um inter-column gaps are the per-column clock spine
    # channels (PATH-HBM TKMCLK), so endpoint chains use the W / E edge channels, never the gaps.
    tl = [g for k, g in geo.items() if k.startswith("u_tkm_SW_tile")]
    arr = (min(g[0] for g in tl), min(g[1] for g in tl), max(g[0] + g[2] for g in tl) - min(g[0] for g in tl),
           max(g[1] + g[3] for g in tl) - min(g[1] for g in tl))
    r0 = CB.RelayRouter(boxes + [arr], W, H, B.HOP)
    r1 = CB.RelayRouter(boxes + [arr], W, H, B.REACH - 1.0)

    def router(a, b):
        try:
            return r0(a, b)
        except ValueError:
            return r1(a, b)
    bt = CK._bus_targets(S.Plan(plan), "root")
    old = T.get("internal_stations", [])
    keep = [e for e in old if e.get("conn", "")[4:] not in BUSES]
    rep["stations_removed"] = len(old) - len(keep)
    added, short = [], []
    for (core, port, bus), bl in sorted(groups.items()):
        d, f = pins[core]
        pp = [d[port][b] for b in bl]
        A = (sum(p[0] for p in pp) / len(pp), sum(p[1] for p in pp) / len(pp))
        Bp = tuple(bt[bus][1])
        dist = abs(A[0] - Bp[0]) + abs(A[1] - Bp[1])
        nbits = len(set(bl)) if bus.endswith("_o") else len(bl)
        if dist <= B.HOP:
            short.append(dict(port=f"{core}.{port}", bus=bus, um=round(dist, 1)))
            continue
        f_ = collections.Counter(f[port]).most_common(1)[0][0]
        nc = CB.free_point((A[0] + BO.NRM[f_][0] * 4 * BO.LAT, A[1] + BO.NRM[f_][1] * 4 * BO.LAT), boxes, W, H)
        regs = router(Bp, nc) + [nc]
        r3 = lambda p: [round(p[0], 3), round(p[1], 3)]  # noqa: E731
        if bus.endswith("_o"):
            ent = dict(conn=f"bus:{bus}", from_um=r3(A), to_um=r3(Bp), regs_um=[r3(p) for p in reversed(regs)],
                       bits=nbits, launch=f"{core}.{port}", capture=f"{core}.{port}")
            dn = f"dir out: {core}.{port} drives face bus {bus}"
        else:
            ent = dict(conn=f"bus:{bus}", from_um=r3(Bp), to_um=r3(A), regs_um=[r3(p) for p in regs],
                       bits=nbits, launch=f"face bus {bus}", capture=f"{core}.{port}")
            dn = f"dir in: face bus {bus} -> {core}.{port}"
        ent["note"] = (f"PATH-HBM/ROOTEP 10-25 typed endpoint ({dn}; capture = core end), {dist:.0f} um, "
                       f"{len(regs)} station(s), hops <= {B.HOP:g} um (b2o R3-INTERNAL rule)")
        added.append(ent)
    for e in added:
        for p in e["regs_um"]:
            for (x, y, w, h) in boxes:
                if x < p[0] < x + w and y < p[1] < y + h:
                    raise ValueError(f"register inside a hard core: {e['conn']} {e['capture']} {p}")
    T["internal_stations"] = keep + added
    hop = lambda e: max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in  # noqa: E731
                        zip([e["from_um"]] + e["regs_um"], e["regs_um"] + [e["to_um"]]))
    rep["stations"] = dict(before=len(old), after=len(T["internal_stations"]), added=len(added),
                           regs_added=sum(len(e["regs_um"]) for e in added),
                           worst_new_hop_um=round(max(hop(e) for e in added), 2), within_hop=short)
    lat1 = json.dumps({k: plan["latency"]["lanes"].get(k) for k in ("L12", "L12m", "L13", "L13m", "L62", "L62m",
                                                                     "L74m", "L89", "L89m")}, sort_keys=True)
    assert lat0 == lat1
    rep["lane_cycles"] = json.loads(lat1)
    rep["lane_cycle_delta"] = 0
    return rep


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--src", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--trace")
    x = a.parse_args()
    src, out = Path(x.src), Path(x.out)
    if out.exists():
        raise ValueError("new output directory required")
    out.mkdir(parents=True)
    for p in src.iterdir():
        if p.name.startswith("g0") or p.name.startswith("gates") or p.name in ("die_plan.json", "core_conns.json") \
                or p.suffix in (".log", ".exit"):
            continue
        if p.is_symlink():
            os.symlink(os.readlink(p), out / p.name)
        elif p.is_dir():
            shutil.copytree(p, out / p.name, symlinks=True)
        else:
            shutil.copy2(p, out / p.name)
    plan = json.loads((src / "die_plan.json").read_text())
    cc = json.loads((src / "core_conns.json").read_text())
    trace = json.loads(Path(x.trace).read_text()) if x.trace else None
    rep = apply(plan, out, cc, trace)
    plan["note"] = plan.get("note", "") + (" | PATH-HBM ROOTEP: root L12/L13/L62/L74m/L89 (+m) typed endpoint graph "
                                           "(as-built r18h5 trace), placeholder chains regenerated")
    S.Plan(plan, out / "die_plan.json")
    (out / "die_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    (out / "core_conns.json").write_text(json.dumps(cc, indent=1) + "\n")
    rep.update(src=str(src), src_plan_sha256=PB.sha(src / "die_plan.json"), out_plan_sha256=PB.sha(out / "die_plan.json"))
    (out / "root_ep_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("stations", "removed_targets", "lane_cycle_delta")}, indent=1))
    for b, v in rep["buses"].items():
        print(b, "width", v["width"], "used", v["used"], "OPEN", v["open_bits"])
    print("UNLANED", sum(u["bits"] for u in rep["unlaned"]), [u["port"] for u in rep["unlaned"]])


if __name__ == "__main__":
    main()
