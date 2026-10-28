#!/usr/bin/env python3
"""DIE-HEAD-5: real-netlist die GRT for the HEAD part map (die-local, opt-in; nothing shared changes).

The die_trial kit (FB1 clock variant) routes only ft feedthroughs, channel ports and an arst_n spine on abstracts that
carry only the plan bus pins + clock taps.  NC-HEAD-PART (3): that GRT holds no landing ring pins, no start/fault
monitor nets and no forwarded clocks.  This tool rebuilds, inside an existing die_trial kit dir:

  abstracts/<module>.lef   every pin the partition kit places (gen_phys.plan_pin_records: plan bus pins, native
                           infrastructure ports, clock/reset taps, reset/start wavefront outs, landing contract pins),
                           same OBS / PG as die_trial.abstract_lef
  grt/route.v              EVERY partition<->partition net of the generated die top (gen rtl --clock-landing:
                           abutment wires w_<port>, cland_mon_* ready/fault, clock_landing_fwd_* forwarded clocks,
                           reset/start wavefront nets), joined with die_trial's in-partition ft feedthrough nets;
                           clock tap pins (driven by the die clock tree in the combo run) and die IO-only nets are left
                           out (counted in the report).

    head_die_grt_real.py PLAN.json TOP.sv KITDIR [--estimate-only] --report OUT.json
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path


def parse_top(text):
    """-> (wires {name: width}, insts [(module, inst, {formal: expr})], top ports {name: width})."""
    wires, ports = {}, {}
    for m in re.finditer(r"^\s*(input|output|inout)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)\s*,?", text, re.M):
        ports[m.group(3)] = int(m.group(2) or 0) + 1
    for m in re.finditer(r"^\s*wire\s+(?:\[(\d+):0\]\s+)?([\w\s,]+);", text, re.M):
        for n in m.group(2).split(","):
            wires[n.strip()] = int(m.group(1) or 0) + 1
    insts = []
    for m in re.finditer(r"^    (\w+)\s+(\w+)\s*\((.*?)\n    \);", text, re.M | re.S):
        conns = {}
        for c in re.finditer(r"\.(\w+)\(([^()]*)\)", m.group(3)):
            conns[c.group(1)] = c.group(2).strip()
        insts.append((m.group(1), m.group(2), conns))
    return wires, insts, ports


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("top")
    ap.add_argument("kit")
    ap.add_argument("--tools", required=True, help="repo tools/die_plan")
    ap.add_argument("--report", required=True)
    ap.add_argument("--estimate-only", action="store_true")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.tools)
    import schema as S
    import gen_phys
    import die_trial as DT
    P = S.Plan(json.loads(Path(a.plan).read_text()), Path(a.plan))
    smod = DT.standin_module_names(P)
    wires, insts, ports = parse_top(Path(a.top).read_text())
    assert len(insts) == len(P.parts), (len(insts), len(P.parts))
    # pin table per type: name -> (layer, x, y, face|None)
    tpins, clockpins = {}, {}
    for tn in P.types:
        if not any(p["type"] == tn for p in P.parts.values()):
            continue
        tp = gen_phys.type_pins(P, tn)
        d = {}
        for r in gen_phys.plan_pin_records(P, tn, tp):
            d[r["name"]] = [r["layer"], r["x"], r["y"], None]
        for bus, bit, ln, x, y, f in tp:
            d[f"{bus}[{bit}]"] = [ln, x, y, f]
        # landing-contract input clock pins (edge clocks) are placed by edge_clock_pins -> already in tap_pins
        tpins[tn] = d
        clockpins[tn] = {n for n, *_ in gen_phys.clock_pins(P, tn)} | {n for n, *_ in gen_phys.core_tap_pins(P, tn)}
    # nets: union-find over (inst, pin)
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(x, y):
        x, y = find(x), find(y)
        if x != y:
            parent[max(x, y)] = min(x, y)
    members = collections.defaultdict(list)
    st = collections.Counter()
    missing = collections.Counter()
    pdir = {}
    for mod, inst, conns in insts:
        tn = P.parts[inst]["type"]
        for formal, expr in conns.items():
            if not expr:
                st["open_pins"] += 1
                continue
            if re.match(r"\d+'", expr):
                st["tied_conns"] += 1
                continue
            if formal in clockpins[tn] or expr.startswith("clk_region_"):
                st["clock_tap_conns"] += 1
                continue
            w = wires.get(expr) or ports.get(expr)
            if w is None:
                raise SystemExit(f"{inst}.{formal}: unknown net {expr}")
            for b in range(w):
                pn = f"{formal}[{b}]" if (f"{formal}[{b}]" in tpins[tn] or w > 1) else formal
                if pn not in tpins[tn]:
                    missing[(tn, formal)] += 1
                    continue
                net = f"{expr}[{b}]" if w > 1 else expr
                members[net].append((inst, pn))
    # in-partition ft feedthrough joins (die_trial.route_netlist model: S_i[b] and S_o[b] are one route)
    nft = 0
    for n, p in P.parts.items():
        tn = p["type"]
        for s_ in P.types[tn].get("ft_slots", []) or []:
            b = 0
            while f"{s_['name']}_i[{b}]" in tpins[tn] and f"{s_['name']}_o[{b}]" in tpins[tn]:
                union((n, f"{s_['name']}_i[{b}]"), (n, f"{s_['name']}_o[{b}]"))
                b += 1
                nft += 1
    for net, ms in members.items():
        for m in ms[1:]:
            union(ms[0], m)
        parent.setdefault(ms[0], ms[0])
    groups = collections.defaultdict(set)
    for net, ms in members.items():
        for m in ms:
            groups[find(m)].add(m)
    for x in list(parent):
        groups[find(x)].add(x)
    # classify + HPWL estimate
    def die_xy(inst, pn):
        ln, x, y, f = tpins[P.parts[inst]["type"]][pn]
        return ln, P.to_die(inst, (x, y))
    nets = []
    cls = collections.Counter()
    hp_by = collections.defaultdict(float)
    hist = collections.Counter()
    longest = []
    for root, ms in groups.items():
        ms = sorted(ms)
        if len({i for i, _ in ms}) < 2:
            cls["single_instance(io/ft-only)"] += 1
            continue
        pts = [die_xy(i, p)[1] for i, p in ms]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        hp = (max(xs) - min(xs)) + (max(ys) - min(ys))
        pn = ms[0][1]
        kind = ("landing_mon" if pn.startswith("cland_") else "fwd_clock" if pn.startswith("fclk_") else
                "ft" if any("ft" in p and ("_i[" in p or "_o[" in p) for _, p in ms) and len(ms) > 2 else
                "reset_start" if any(k in pn for k in ("rst", "arst", "start", "wf_")) else "data")
        cls[kind] += 1
        hp_by[kind] += hp
        hist["0" if hp < 1e-3 else "<10" if hp < 10 else "<100" if hp < 100 else "<405" if hp < 405 else ">=405"] += 1
        longest.append((round(hp, 1), kind, ms[0][0], pn, len(ms)))
        nets.append((root, ms, kind, hp))
    longest.sort(reverse=True)
    rep = dict(instances=len(insts), nets_multi_instance=len(nets), by_kind=dict(cls),
               hpwl_um_by_kind={k: round(v, 1) for k, v in hp_by.items()}, hpwl_hist=dict(hist),
               longest=longest[:25], missing_pins={f"{k[0]}.{k[1]}": v for k, v in missing.items()},
               conn_stats=dict(st), ft_bit_joins=nft)
    if not a.estimate_only:
        kit = Path(a.kit)
        # abstracts: die_trial LEF with the pin section replaced by every plan pin
        top = P.layer_budget["partition_signal_max"]
        for tn, d in tpins.items():
            mod = smod[tn]
            f = kit / "abstracts" / f"{mod}.lef"
            old = f.read_text()
            head, rest = old.split("  PIN ", 1)
            pg = rest[rest.index("  PIN VDD"):]
            dirs = {}
            for b in P.types[tn].get("buses", []):
                dirs[b["name"]] = "INPUT" if b["dir"] == "in" else "OUTPUT"
            out = [head.rstrip("\n")]
            for name, (ln, x, y, fc) in sorted(d.items()):
                lw = gen_phys.LAYER_W.get(ln, 0.04) / 2
                pl = gen_phys.PIN_LEN_UM
                if fc:
                    r = {"E": (x - pl, y - lw, x, y + lw), "W": (x, y - lw, x + pl, y + lw),
                         "N": (x - lw, y - pl, x + lw, y), "S": (x - lw, y, x + lw, y + pl)}[fc]
                else:
                    r = (x - lw, y - 2 * pl, x + lw, y + 2 * pl)
                bus = name.split("[")[0]
                dr = dirs.get(bus, "OUTPUT" if bus.endswith("_o") else "INPUT")
                use = "CLOCK" if name in clockpins[tn] or name.startswith("fclk_") else "SIGNAL"
                out += [f"  PIN {name}", f"    DIRECTION {dr} ;", f"    USE {use} ;", "    PORT",
                        f"      LAYER {ln} ;", f"        RECT {r[0]:.4f} {r[1]:.4f} {r[2]:.4f} {r[3]:.4f} ;",
                        "    END", f"  END {name}"]
            f.write_text("\n".join(out) + "\n" + pg)
        # route.v
        rv = (kit / "grt" / "route.v").read_text()
        mh = re.match(r"\s*module\s+(\w+)\s*\(", rv)
        conns = collections.defaultdict(dict)
        v = [f"module {mh.group(1)} (rst_n);", "  input rst_n;"]
        for k, (root, ms, kind, hp) in enumerate(sorted(nets, key=lambda q: q[0])):
            w = f"n{k}_{kind}"
            v.append(f"  wire {w};")
            for i, p in ms:
                conns[i][p] = w
        nopen = 0
        for n, p in sorted(P.parts.items()):
            tn = p["type"]
            buses = collections.defaultdict(dict)
            scal = []
            for pn in tpins[tn]:
                m = re.match(r"(\w+)\[(\d+)\]$", pn)
                if m:
                    buses[m.group(1)][int(m.group(2))] = conns[n].get(pn)
                elif pn in conns[n]:
                    scal.append(f".{pn}({conns[n][pn]})")
            cc = []
            for bus, bits in sorted(buses.items()):
                if not any(bits.values()):
                    continue
                el = []
                for b in range(max(bits), -1, -1):
                    if bits.get(b):
                        el.append(bits[b])
                    else:
                        nopen += 1
                        ow = f"open_{nopen}"
                        v.append(f"  wire {ow};")
                        el.append(ow)
                cc.append(f".{bus}({{{', '.join(el)}}})")
            v.append(f"  {smod[tn]} {DT.sv(n)} ({', '.join(cc + scal)});")
        rep["open_bus_bits"] = nopen
        v.append("endmodule")
        (kit / "grt" / "route_dietrial.v").write_text(rv)
        (kit / "grt" / "route.v").write_text("\n".join(v) + "\n")
        rep["route_v_nets"] = len(nets)
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("instances", "nets_multi_instance", "by_kind", "hpwl_um_by_kind", "hpwl_hist",
                                          "missing_pins", "conn_stats")}, indent=1))
    print("longest", rep["longest"][:10])


if __name__ == "__main__":
    sys.exit(main())
