#!/usr/bin/env python3
"""Die STA top with the plan's clock-landing network (HEAD-DIE-R 11-16; die-agnostic).

gen_rtl.die_top() (the die_trial kit/sta/die_top.v) wires the clock spine, resets and abutment nets but not the
clock-landing network: forwarded fclk_out -> fclk_in, cland_up/dn/fstart/tstart and rst_start nets.  A real-view
die STA on that top leaves every capture ring clocked by an fclk_in port undriven, so every landed seam is untimed
(HEAD NF15c: 379 / 1182 seams).  This tool adds exactly the nets landing_route.network(P) defines (the set
die_trial --landing-infra puts in the route target) to a die top:
  * one `wire` per landing net, `.pin(net)` on every instance whose part netlist module has that port;
  * the explicit START boundary nets (clock.landing_network.start_tree) as top inputs / outputs, aliases as assigns;
  * a binding whose part module lacks the pin (a stand-in without landing pins) is NOT connected and is listed per
    instance in the report, so a seam left untimed by it is attributable; --fail-on-real-drop TYPES fails closed when
    a part of a type not in the given stand-in list drops a binding.

usage: sta_landing_top.py PLAN TOP_IN PARTS_DIR TOP_OUT [--report R.json] [--standin-types a,b,...] [--fail-on-real-drop]
PARTS_DIR/<module>/6_final.v is the netlist die_sta.py run --parts reads."""
import argparse
import json
import re
import sys
from pathlib import Path

PORT = re.compile(r"^\s*(input|output|inout)\s+(?:wire\s+)?(?:\[[^\]]*\]\s*)?([^;]+);", re.M)
INST = re.compile(r"^\s+([A-Za-z_]\w*)(?:\s+#\(.*\))?\s+(\S+)\s*\($")
PIN = re.compile(r"^\s*\.(\w+)\s*\(")


def module_ports(text, module):
    """port names of module in a structural netlist (ANSI or non-ANSI declarations); None if absent"""
    m = re.search(r"\bmodule\s+" + re.escape(module) + r"\b(.*?)\bendmodule", text, re.S)
    if not m:
        return None
    res, body = set(), m.group(1)
    hdr = re.match(r"\s*\((.*?)\)\s*;", body, re.S)
    if hdr:
        body = body[hdr.end():]
        for d in re.finditer(r"\b(?:input|output|inout)\s+(?:wire\s+)?(?:\[[^\]]*\]\s*)?([A-Za-z_]\w*)", hdr.group(1)):
            res.add(d.group(1))
    for _d, names in PORT.findall(body):
        res.update(n.strip() for n in names.split(",") if n.strip())
    return res


def apply(top, network, ports_of):
    """top text + landing network dict + ports_of(module) -> (new top text, report dict)"""
    if network.get("monitor_relays"):
        raise ValueError("STA landing monitor relays require the actual mapped and clocked relay cells")
    lines = top.splitlines()
    mi = next(i for i, l in enumerate(lines) if re.match(r"\s*module\s+\w+\s*\($", l))
    out, cur, start = [], None, 0
    connected, dropped, already, used = {}, {}, {}, set()
    for line in lines:
        m = INST.match(line) if len(out) > mi else None
        if m and cur is None:
            cur = (m.group(1), m.group(2).lstrip("\\")); start = len(out); out.append(line); continue
        if cur is not None and line.strip() == ");":
            mod, inst = cur
            b = network["bindings"].get(inst, {})
            if b:
                have = ports_of(mod)
                if have is None:
                    raise SystemExit(f"STA_LANDING_TOP module {mod} (instance {inst}) not in parts")
                bound = {PIN.match(l).group(1) for l in out[start + 1:] if PIN.match(l)}
                add = []
                for pin, w in sorted(b.items()):
                    if pin in bound:
                        already.setdefault(inst, []).append(pin)
                    elif pin in have:
                        add.append(f"        .{pin}({w})"); used.add(w)
                    else:
                        dropped.setdefault(inst, []).append(pin)
                if add:
                    if not out[-1].rstrip().endswith(","):
                        out[-1] = out[-1].rstrip() + ","
                    out.extend(a + ("," if k < len(add) - 1 else "") for k, a in enumerate(add))
                    connected[inst] = len(add)
            out.append(line); cur = None; continue
        out.append(line)
    bnd_in = [n for n in network["boundary_inputs"] if n in used]
    bnd_out = [n for n in network["boundary_outputs"] if n in used or n in network["boundary_aliases"]]
    ports = [f"    input  wire {n}," for n in bnd_in] + [f"    output wire {n}," for n in bnd_out]
    out[mi + 1:mi + 1] = ports
    end = next(i for i in range(mi + 1, len(out)) if out[i].strip() == ");")
    bnd = set(network["boundary_inputs"]) | set(network["boundary_outputs"])
    decl = ["    // clock-landing network (tools/die_plan/sta_landing_top.py, landing_route.network)"]
    decl += [f"    wire {w};" for w in sorted(used | set(network["boundary_aliases"].values())) if w not in bnd]
    decl += [f"    assign {n} = {w};" for n, w in sorted(network["boundary_aliases"].items())]
    out[end + 1:end + 1] = decl
    rep = dict(edges=network.get("edges"), nets=len(network["wires"]), connected_bindings=sum(connected.values()),
               dropped_bindings=sum(len(v) for v in dropped.values()),
               dropped_by_instance={k: len(v) for k, v in sorted(dropped.items())},
               dropped_examples={k: v[:6] for k, v in sorted(dropped.items())},
               already_connected=sum(len(v) for v in already.values()),
               boundary_inputs=len(bnd_in), boundary_outputs=len(bnd_out))
    return "\n".join(out) + "\n", rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan"); ap.add_argument("top"); ap.add_argument("parts"); ap.add_argument("out")
    ap.add_argument("--report")
    ap.add_argument("--standin-types", default="", help="comma list of plan types that are stand-ins in PARTS")
    ap.add_argument("--fail-on-real-drop", action="store_true",
                    help="exit 2 when an instance of a type NOT in --standin-types drops a landing binding")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import schema as S
    import landing_route
    P = S.Plan(S.load(a.plan), Path(a.plan))
    net = landing_route.network(P)
    cache = {}

    def ports_of(mod):
        if mod not in cache:
            v = Path(a.parts) / mod / "6_final.v"
            cache[mod] = module_ports(v.read_text(errors="replace"), mod) if v.is_file() else None
        return cache[mod]
    text, rep = apply(Path(a.top).read_text(), net, ports_of)
    Path(a.out).write_text(text)
    stand = {t for t in a.standin_types.split(",") if t}
    real_drop = {i: n for i, n in rep["dropped_by_instance"].items() if P.parts.get(i, {}).get("type") not in stand}
    rep.update(plan=a.plan, top_in=a.top, parts=a.parts, standin_types=sorted(stand), real_drop=real_drop)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print("STA_LANDING_TOP", json.dumps({k: rep[k] for k in ("edges", "connected_bindings", "dropped_bindings",
                                                             "already_connected", "boundary_inputs")}),
          "real_drop", len(real_drop))
    if a.fail_on_real_drop and real_drop:
        print("STA_LANDING_TOP FAIL real (non-stand-in) instances drop landing pins:", dict(list(real_drop.items())[:8]))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
