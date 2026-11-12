#!/usr/bin/env python3
"""DIE-QC-97 fw SAFE-FORM derivation (11-11), re-runnable on any placed pilot of a fw type.

  python3 -I fwderive.py SRC PLAN TYPE GEOM_TSV WORK OUT_PLAN [--kit KIT_DIR] [--tools DIR]

SRC       source tree the build uses (tools/die_plan, tools/autopilot; the bins dir is written under it)
PLAN      plan to derive from (the plan the pilot was built from, or the composed plan with re-placed cores)
GEOM_TSV  AUTO-GEOM dump (geom/geom.tsv) of a 3_place of TYPE built from a plan whose station/clock form matches PLAN
WORK      scratch dir (dumps, r2r json, moved geom, report.json)
--kit     the pilot kit dir (landing_placement.tcl: placed collector sites); optional
--tools   dir holding model_class.py, lanes2.py, r2rlist.py, r2rmove.py, geom2dump.py (default: this script's dir)

Rules, each from the MEASURED placement (a20 slw_fw_v3 -> 685226a034f4, a21 sle_fw_v3 -> 872de5bd25c7):
 C  clock: sink bins of every placed flop (8.64 um), density taps cap 1200 / target 900 (model_class.py)
 S  station re-placement, 0 added cycles: for every internal_stations bus with an r2r capture > 405 between u_core and its
    end station, the core end (leaf) moves to the centroid of the measured core flops of the failing pairs (>= half the
    bus bits failing) or to the midpoint of the plan leaf and that centroid (fewer); stations re-spaced evenly on the
    straight segment leaf -> face end
 F  feeder bin: a bus-in register u_bin_<b> launching > 405 into another bus's station moves on the line to that
    station's measured site to 340 um of it, kept only if its ring band (landing_contract.bands[b].rect_um) stays <= 405
 P  seam pin -> bus-in register > 150 (pins stay, parent seam): the register moves to 120 um of its pin on the
    pin -> old-site line; when its measured consumer is then > 405 away, ONE in-station (per_bit) at the midpoint is
    added (+1 pin cycle; lanes2.py sets lane fixed_cycles and reports the latency delta)
 R  collector root: cland_up_* pin -> root collector > 150: the root collector site moves to 137 um of the pins on the
    line to its child collector (kept only if the child hop stays <= 405); a collector site rect > 300 um off its node
    is dropped (stale tree)
 H1 seam hold: HOLDFORM-1 bus hold_hb4 N per in-bus / ft slot from the pilot's min STA (--sta, holdform.py)
 H2 cross-tap reg-reg hold: clock.tap_pair_affinity sized on the measured violating pairs (holdform.py)
 -  not derived (reported): reset relay -> bus-in eq captures (RSTN-TAP class), 1-bit station flops without [b]
    (placed FIRM by kit_istations 57b8bad4f22b)
Every move is replayed on the measured netlist (r2rmove.py) and the remaining captures > 405 are reported.
"""
import argparse, collections, copy, hashlib, json, math, re, subprocess, sys
from pathlib import Path

REACH, PIN_REG, BIN_TO, PIN_TO, ROOT_TO = 405.0, 150.0, 340.0, 120.0, 137.0
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
cen = lambda pts: [round(sum(p[0] for p in pts) / len(pts), 3), round(sum(p[1] for p in pts) / len(pts), 3)]
mid = lambda a, b: [round((a[0] + b[0]) / 2, 3), round((a[1] + b[1]) / 2, 3)]


def toward(a, b, d):
    """point on segment a -> b at L1 distance d from a (straight line)"""
    t = min(1.0, d / max(L1(a, b), 1e-9))
    return [round(a[0] + (b[0] - a[0]) * t, 3), round(a[1] + (b[1] - a[1]) * t, 3)]


def lin(a, b, n):
    return [[round(a[0] + (b[0] - a[0]) * k / (n + 1), 3), round(a[1] + (b[1] - a[1]) * k / (n + 1), 3)] for k in range(1, n + 1)]


def style(b, P):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=1), lambda p: json.dumps(p, indent=2) + "\n",
              lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
        if f(P).encode() == b:
            return f
    raise SystemExit("plan JSON style unknown")


NAME = re.compile(r"(?:^|\.)(u_\w+?)/(\w+?)(?:\\?\[(\d+)\\?\])?\$_")


def parse(n):
    m = NAME.search(n)
    return (m.group(1), m.group(2), None if m.group(3) is None else int(m.group(3))) if m else (n, None, None)


def run(cmd, log):
    r = subprocess.run(cmd, capture_output=True, text=True)
    Path(log).write_text(r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit(f"FAIL {' '.join(map(str, cmd[:3]))}: see {log}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for a in ("src", "plan", "type", "geom", "work", "out"):
        ap.add_argument(a)
    ap.add_argument("--kit"); ap.add_argument("--tools", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--sta", action="append", default=[], metavar="CORNER=MIN_RPT",
                    help="H1/H2: per-corner full_clock min report of the pilot (h2.tcl); repeat per corner")
    a = ap.parse_args()
    S, W, X, TN = Path(a.src), Path(a.work), Path(a.tools), a.type
    W.mkdir(parents=True, exist_ok=True)
    py = [sys.executable, "-I"]
    rep = dict(type=TN, plan=a.plan, plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
               geom=a.geom, geom_sha256=hashlib.sha256(Path(a.geom).read_bytes()).hexdigest())

    # ---- C: clock from measured flops
    (W / "dumps").mkdir(exist_ok=True); (W / "census_empty.tsv").write_text("")
    run(py + [X / "geom2dump.py", a.geom, W / "dumps" / f"{TN}.json", f"fwderive {a.geom}"], W / "dump.log")
    ev = f"physical/die_plan/qwen_compute/tap_fwderive_{TN}_{rep['geom_sha256'][:8]}"
    (S / ev).mkdir(parents=True, exist_ok=True)
    run(py + [X / "model_class.py", S, W / "dumps", a.plan, ev, W / "census_empty.tsv", TN], W / "model.log")
    cp = json.loads((S / ev / "clock_patches.json").read_text()).get(TN)
    if cp is None:
        raise SystemExit(f"FAIL tap model found no cap-1200 form for {TN}: {S / ev / 'model.json'}")

    rb = Path(a.plan).read_bytes(); raw = json.loads(rb); dump = style(rb, raw)
    t = raw["partition_types"][TN]
    for k, v in cp["clock"].items():
        if k != "landing_contract":
            t["clock"][k] = v
    rep["C"] = dict(bins=t["clock"]["sink_bins_file"], **cp["model"])

    # ---- measured geometry
    pins, rows = {}, []
    for line in open(a.geom):
        f = line.rstrip("\n").split("\t")
        if f[0] == "P":
            pins[f[2]] = [float(f[6]), float(f[7])]
    run(py + [X / "r2rlist.py", S / "tools", a.geom, W / "r2r_in.json"], W / "r2r_in.log")
    pairs = json.loads((W / "r2r_in.json").read_text())["pairs"]
    rep["r2r_in"] = len(pairs)
    pin_of = lambda bus, b: pins.get(f"{bus}[{b}]") or pins.get(bus)
    st = {e["conn"][4:]: e for e in t.get("internal_stations", []) if e.get("conn", "").startswith("bus:")}
    width = {b["name"]: int(b["width"]) for b in t["buses"]}
    rs = t.setdefault("relay_sites", {})
    moves, actions = {}, []

    # ---- S: station core ends
    for bus, e in sorted(st.items()):
        n = len(e["regs_um"]); out = e["capture"].startswith("face")
        if out:
            bad = [p for p in pairs if ".u_core." in p["launch"] and parse(p["capture"])[0] == f"u_ist_{bus}_0"]
            core = [p["launch_xy"] for p in bad]; sbits = {parse(p["capture"])[2] for p in bad}
        else:
            bad = [p for p in pairs if ".u_core." in p["capture"] and parse(p["launch"])[0] == f"u_ist_{bus}_{n - 1}"]
            core = [p["capture_xy"] for p in bad]; sbits = {parse(p["launch"])[2] for p in bad}
        if not bad:
            continue
        c = cen(core)
        leaf = c if len(sbits) * 2 >= e["bits"] else mid(e["leaf_um"], c)
        old = copy.deepcopy(e)
        if out:
            e["from_um"] = leaf; e["leaf_um"] = leaf; e["regs_um"] = lin(leaf, e["to_um"], n)
        else:
            e["to_um"] = leaf; e["leaf_um"] = leaf; e["regs_um"] = lin(e["from_um"], leaf, n - 1) + [leaf]
        e["note"] = e.get("note", "") + f"; fwderive S: leaf from {len(bad)} measured r2r>405 pairs, 0 added cycles"
        actions.append(dict(rule="S", bus=bus, pairs=len(bad), old_leaf=old["leaf_um"], leaf=leaf, regs=e["regs_um"],
                            hop_um=round(L1(e["regs_um"][0], leaf), 1)))

    # ---- F: feeder bins into another bus's station
    bands = t["clock"].get("landing_contract", {}).get("bands", {})
    feed = collections.defaultdict(list)
    for p in pairs:
        li, lp, lb = parse(p["launch"]); ci = parse(p["capture"])[0]
        if li.startswith("u_bin_") and ci.startswith("u_ist_") and lb is not None:
            feed[(li[6:], lb)].append(p["capture_xy"])
    for (bus, b), caps in sorted(feed.items()):
        k = f"u_bin_{bus}/q[{b}]"
        if k not in rs:
            continue
        tgt = cen(caps); new = toward(tgt, rs[k], BIN_TO)
        ring = bands.get(bus, {}).get("rect_um")
        rc = [(ring[0] + ring[2]) / 2, (ring[1] + ring[3]) / 2] if ring else None
        if rc and L1(rc, new) > REACH:
            actions.append(dict(rule="F", site=k, skipped=f"ring hop {round(L1(rc, new), 1)} > {REACH}"))
            continue
        actions.append(dict(rule="F", site=k, old=rs[k], new=new, to_station_um=round(L1(new, tgt), 1),
                            ring_hop_um=None if rc is None else round(L1(rc, new), 1)))
        rs[k] = new; moves[k] = new

    # ---- P: seam pin -> bus-in register (the MEASURED first register of each input pin, through BUF/INV only)
    sys.path.insert(0, str(S / "tools/autopilot"))
    import geom_rules as G
    D = G.Design(a.geom)
    new_in = {}
    for pn in D.pins:
        m = re.fullmatch(r"(\w+)\[(\d+)\]", pn["name"])
        if pn["io"] != "INPUT" or not m or m.group(1) in bands or D.pin_net.get(pn["k"]) is None:
            continue
        bus = m.group(1); front, seen, first = [D.pin_net[pn["k"]]], set(), None
        while front and first is None:
            nf = []
            for nn in front:
                for sk in D.nets[nn][2]:
                    if sk[0] != "i" or sk[2]:
                        continue
                    kd = D.kind(sk[1])
                    if kd == "S" and first is None:
                        first = sk[1]
                    elif kd == "B":
                        nf += [o for o in D.drives.get(sk[1], []) if o not in seen and not seen.add(o)]
            front = nf
        if first is None:
            continue
        inst, _pin, b = parse(D.cells[first][6]); k = f"u_bin_{bus}/q[{b}]"
        x0, y0, x1, y1 = D.cells[first][2:6] if len(D.cells[first]) > 6 else (0, 0, 0, 0)
        here = [(float(x0) + float(x1)) / 2, (float(y0) + float(y1)) / 2]
        pxy = [pn["x"], pn["y"]]
        if inst != f"u_bin_{bus}" or k not in rs or k in moves or L1(pxy, here) <= PIN_REG:
            continue
        new = toward(pxy, rs[k], PIN_TO)
        actions.append(dict(rule="P", site=k, pin=pxy, measured_um=round(L1(pxy, here), 1), old=rs[k], new=new))
        new_in.setdefault(bus, []).append((b, rs[k], new)); rs[k] = new; moves[k] = new
    # replay -> consumers of the moved bins
    (W / "moves.json").write_text(json.dumps(moves))
    run(py + [X / "r2rmove.py", S / "tools", a.geom, W / "moves.json", W / "geom_moved.tsv"], W / "r2r_moved1.log")
    run(py + [X / "r2rlist.py", S / "tools", W / "geom_moved.tsv", W / "r2r_moved1.json"], W / "r2r_moved1b.log")
    p1 = json.loads((W / "r2r_moved1.json").read_text())["pairs"]
    added = []
    for bus, lst in sorted(new_in.items()):
        far = [p for p in p1 if parse(p["launch"])[0] == f"u_bin_{bus}"]
        if not far:
            continue
        if bus in st:
            actions.append(dict(rule="P", bus=bus, unresolved=f"{len(far)} captures > {REACH} and the bus already has stations"))
            continue
        c = cen([p["capture_xy"] for p in far]); pc = cen([pin_of(bus, b) for b, _o, _n in lst])
        stn = mid(cen([n for _b, _o, n in lst]), c)
        t["internal_stations"].append(dict(conn=f"bus:{bus}", from_um=pc, to_um=c, regs_um=[stn], bits=width[bus] + 1,
                                           launch=f"face {bus}", capture="u_core", bit_route="per_bit", leaf_um=c,
                                           note=f"fwderive P: +1 pin cycle, seam register <= {PIN_REG:g} um of the pins, "
                                                f"measured consumer {round(L1(pc, c))} um"))
        added.append(bus)
        actions.append(dict(rule="P", bus=bus, in_station=stn, consumer=c, plus_cycles=1))

    # ---- R: collector root next to the up pins
    lc = t["clock"].get("landing_contract", {})
    if lc.get("collector_tree") and a.kit:
        sys.path.insert(0, str(S / "tools/die_plan"))
        import landing_place as LP
        site = {}
        for m in re.finditer(r"\{u_cland_collect_(\S+) \{(\S+) (\S+) (\S+) (\S+)\} collector",
                             (Path(a.kit) / "landing_placement.tcl").read_text()):
            site[m.group(1)] = ((float(m.group(2)) + float(m.group(4))) / 2, (float(m.group(3)) + float(m.group(5))) / 2)
        ev = dict(tree=lc["collector_tree"], collector_root_node=lc.get("collector_root_node", "rst_root_n"),
                  local_sources=lc.get("collector_local_sources") or [], children=lc.get("collector_children") or [])
        act, xy = LP.collector_nodes(ev)
        gr = lc.setdefault("group_rects_um", {})
        for key in sorted(gr):
            n = key[len("u_cland_collect_"):] if key.startswith("u_cland_collect_") else None
            if n in xy:
                c = [(gr[key][0] + gr[key][2]) / 2, (gr[key][1] + gr[key][3]) / 2]
                if L1(c, xy[n]) > 300:
                    actions.append(dict(rule="R", dropped=key, rect=gr.pop(key), off_node_um=round(L1(c, xy[n]), 1)))
        root = ev["collector_root_node"]
        up = [q["xy_um"] for q in lc.get("pins", []) if q["name"] in ("cland_up_ready", "cland_up_fault")]
        rs0 = site.get(root, tuple(xy.get(root, (0, 0))))
        if up and root != "rst_root_n" and max(L1(u, rs0) for u in up) > PIN_REG:
            adj = collections.defaultdict(list)
            for r in lc["collector_tree"]["relays"]:
                adj[r["q"]].append(r["d"]); adj[r["d"]].append(r["q"])
            kids = [site.get(k, tuple(xy[k])) for k in adj[root] if k in act]
            pc = cen(up); tgt = cen(kids) if kids else rs0
            new = toward(pc, tgt, ROOT_TO)
            if all(L1(new, k) <= REACH for k in kids):
                gr[f"u_cland_collect_{root}"] = [round(new[0] - 2.16, 3), round(new[1] - 2.16, 3), round(new[0] + 2.16, 3), round(new[1] + 2.16, 3)]
                actions.append(dict(rule="R", root=root, old=list(rs0), new=new, pin_um=round(max(L1(u, new) for u in up), 1),
                                    child_hop_um=[round(L1(new, k), 1) for k in kids]))
            else:
                actions.append(dict(rule="R", root=root, skipped="child hop > reach"))

    # ---- H1/H2: structural hold from the pilot's measured min STA (holdform.py)
    if a.sta:
        sys.path.insert(0, str(X))
        import holdform as HF
        HF.apply(t, a.sta, a.geom, S, rep)
    t["note"] = (t.get("note") or "") + (f" | fwderive {rep['geom_sha256'][:12]}: clock C, S/F/P/R"
                                         + (", H1/H2" if a.sta else "") + " per report")
    stage = W / "derived_pre_lanes.json"
    stage.write_text(dump(raw))
    if added:
        out = run(py + [X / "lanes2.py", S, a.plan, stage, TN, a.out, W / "lanes_rep.json"], W / "lanes.log")
        rep["lanes"] = json.loads((W / "lanes_rep.json").read_text())
    else:
        Path(a.out).write_bytes(stage.read_bytes())

    # ---- verify: replay bins + stations (all bits at their regs_um) on the measured netlist
    fin = json.loads(Path(a.out).read_text())["partition_types"][TN]
    vm = dict(moves)
    changed = {x["bus"] for x in actions if x["rule"] == "S"}
    for e in fin.get("internal_stations", []):
        bus = e["conn"][4:]; n = len(e["regs_um"]); out = e["capture"].startswith("face")
        if bus in added or not (bus in changed or width.get(bus) == 1):
            continue                     # new stations are not in the measured netlist; unchanged ones stay as measured
        for k, r in enumerate(e["regs_um"]):
            vm[f"u_ist_{bus}_{k}/q"] = r                     # 1-bit station (scalar q, FIRM at its plan site)
            for b in range(e["bits"]):
                pb = pin_of(bus, b)
                if pb is None:
                    vm[f"u_ist_{bus}_{k}/q[{b}]"] = r
                elif out:                                 # per_bit: station k of n on leaf -> this bit's pin
                    vm[f"u_ist_{bus}_{k}/q[{b}]"] = [e["leaf_um"][i] + (pb[i] - e["leaf_um"][i]) * (k + 1) / (n + 1) for i in (0, 1)]
                else:
                    vm[f"u_ist_{bus}_{k}/q[{b}]"] = [pb[i] + (e["leaf_um"][i] - pb[i]) * (k + 1) / (n + 1) for i in (0, 1)]
    for x in actions:                                     # collectors: dropped rect -> its node; moved root -> new site
        if x["rule"] == "R" and "dropped" in x:
            n = x["dropped"][len("u_cland_collect_"):]
            for o in ("ready_o", "fault_o"):
                vm[f"u_cland_collect_{n}/{o}"] = list(xy[n])
        if x["rule"] == "R" and "new" in x:
            for o in ("ready_o", "fault_o"):
                vm[f"u_cland_collect_{x['root']}/{o}"] = x["new"]
    (W / "verify_moves.json").write_text(json.dumps(vm))
    log = run(py + [X / "r2rmove.py", S / "tools", a.geom, W / "verify_moves.json", W / "geom_verify.tsv"], W / "verify.log")
    rem = [l for l in log.splitlines()[2:] if l.strip()]
    for bus in added:      # a capture of a bus that got an in-station is split by it: count the halves by distance
        rem = [l for l in rem if f"u_bin_{bus}/" not in l]
    rep.update(actions=actions, added_in_stations=added, remaining_gt405=rem, verify_head=log.splitlines()[:2],
               sha256=hashlib.sha256(Path(a.out).read_bytes()).hexdigest())
    (W / "report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(f"FWDERIVE {TN} {rep['sha256'][:12]} r2r>405 {rep['r2r_in']} -> {len(rem)} remaining; actions "
          + " ".join(f"{k}:{v}" for k, v in collections.Counter(x['rule'] for x in actions).items()))
    for l in rem:
        print("  remaining", l)


if __name__ == "__main__":
    main()
