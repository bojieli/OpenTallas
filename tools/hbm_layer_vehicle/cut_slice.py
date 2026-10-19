#!/usr/bin/env python3
"""LAYERBENCH-HBM (10-18): cut a slice top out of the GENERATED d4g die netlist.

The die netlist (tools/hbm_die_v16/contract_die_v.py output: one flat module of instances + wires, no assigns) names
every instance-output net <inst>__<port> and connects it bare; inputs connect as slices / concatenations / replications
of those nets, die pins or sized constants (straps).  Given an instance set S this tool writes a slice top that
instantiates the S instances VERBATIM (same master, parameters, connections, so the slice is the die's real bound RTL)
and turns every net that crosses the S boundary into a slice port:
  input  : net driven outside S (another quadrant, a central block, a die pin) and read inside S
  output : net driven inside S and read outside S (or a die output pin driven inside S)
Nets driven and read inside S stay wires; outputs no-one reads stay open wires (as on the die).
The boundary manifest (JSON) lists every port with width, the driving / reading die instance.port and the peer class
(quadrant, central block, die pin); the replay model drives the inputs and checks the outputs from it.

  cut_slice.py --die die.v --contract pre.json[.gz] --set sw --out DIR [--top hbm_v16_slice_sw]
  sets: sw/se/nw/ne (= the quadrant's instances + hb_ckgen), or --include REGEX (repeatable) [--exclude REGEX]
Writes DIR/slice.v, DIR/boundary.json, DIR/masters.txt (masters the slice instantiates).
"""
import argparse, gzip, json, re, sys
from pathlib import Path

ID = re.compile(r"\b([A-Za-z_]\w*)\b")
QUAD = re.compile(r"(?<![A-Za-z])(SW|SE|NW|NE)")


def parse_die(text):
    m = re.search(r"\bmodule\s+(\w+)\s*\((.*?)\);", text, re.S)
    top, body = m.group(1), text[m.end():text.rindex("endmodule")]
    ports, wires, insts = {}, {}, []
    lines = body.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        d = re.match(r"\s*(input|output)\s+wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)\s*;", ln)
        w = re.match(r"\s*wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)\s*;", ln)
        if d:
            ports[d.group(4)] = (d.group(1), int(d.group(2) or 0) + 1)
        elif w:
            wires[w.group(3)] = int(w.group(1) or 0) + 1
        elif re.match(r"\s*[A-Za-z_]\w*\s*(#\(.*\))?\s*[A-Za-z_]\w*\s*\(\s*$", ln):
            hdr = re.match(r"\s*([A-Za-z_]\w*)\s*(#\(.*\))?\s*([A-Za-z_]\w*)\s*\(\s*$", ln)
            conns, raw = [], [ln]
            i += 1
            while not re.match(r"\s*\);\s*$", lines[i]):
                raw.append(lines[i])
                c = re.match(r"\s*\.(\w+)\((.*)\),?\s*$", lines[i])
                if not c:
                    sys.exit(f"cut_slice: unparsed connection line {i + 1}: {lines[i]!r}")
                conns.append((c.group(1), c.group(2)))
                i += 1
            raw.append(lines[i])
            insts.append({"master": hdr.group(1), "params": hdr.group(2) or "", "name": hdr.group(3),
                          "conns": conns, "text": "\n".join(raw)})
        elif ln.strip() and not ln.strip().startswith(("//", "`")):
            sys.exit(f"cut_slice: unexpected die.v line {i + 1}: {ln!r} (netlist must be instances + wires only)")
        i += 1
    return top, ports, wires, insts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--die", required=True)
    ap.add_argument("--contract", help="die source contract (pre.json[.gz]): adds slot/region to the manifest")
    ap.add_argument("--set", choices=["sw", "se", "nw", "ne"])
    ap.add_argument("--include", action="append", default=[])
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--top")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    text = Path(a.die).read_text()
    top, ports, wires, insts = parse_die(text)
    names = {x["name"]: x for x in insts}
    inc = [re.compile(r) for r in a.include]
    if a.set:
        q = a.set.upper()
        inc.append(re.compile(rf"^hb_ckgen$"))
        quad_of = lambda n: (QUAD.search(n).group(1) if QUAD.search(n) else None)
        S = {n for n in names if quad_of(n) == q or any(r.search(n) for r in inc)}
    else:
        S = {n for n in names if any(r.search(n) for r in inc)}
    S -= {n for n in S if any(re.search(r, n) for r in a.exclude)}
    if not S:
        sys.exit("cut_slice: empty instance set")

    # drivers: <inst>__<port> bare connection, or a die input pin
    driver = {}
    for x in insts:
        for p, e in x["conns"]:
            e = e.strip()
            if e == f"{x['name']}__{p}" and e in wires:
                driver[e] = (x["name"], p)
            elif e in ports and ports[e][0] == "output":
                driver[e] = (x["name"], p)            # die output pin driven by this instance
    for pn, (d, _) in ports.items():
        if d == "input":
            driver[pn] = ("<die_pin>", pn)
    readers = {}
    for x in insts:
        for p, e in x["conns"]:
            for ref in set(ID.findall(re.sub(r"\d+'[bdhoBDHO][0-9a-fA-FxXzZ_]+", " ", e))):
                if (ref in wires or ref in ports) and driver.get(ref) != (x["name"], p):
                    readers.setdefault(ref, []).append((x["name"], p))
    undriven = sorted(n for n in readers if n not in driver)
    if undriven:
        sys.exit(f"cut_slice: {len(undriven)} read nets without a driver, e.g. {undriven[:5]}")

    width = lambda n: wires[n] if n in wires else ports[n][1]
    used = set()
    for n in S:
        for p, e in names[n]["conns"]:
            used |= {r for r in ID.findall(re.sub(r"\d+'[bdhoBDHO][0-9a-fA-FxXzZ_]+", " ", e)) if r in wires or r in ports}
    sp_in, sp_out, internal = [], [], []
    for net in sorted(used):
        dv = driver[net]
        inside_drv = dv[0] in S
        outside_rd = [r for r in readers.get(net, []) if r[0] not in S]
        if net in ports and ports[net][0] == "output":
            (sp_out if inside_drv else internal).append(net)
        elif not inside_drv:
            sp_in.append(net)
        elif outside_rd:
            sp_out.append(net)
        else:
            internal.append(net)

    con, eclk = {}, {}
    if a.contract:
        c = json.load((gzip.open if a.contract.endswith(".gz") else open)(a.contract, "rt"))
        con = c.get("instances", {})
        for e in c.get("edges", []):
            if e.get("clock"):
                eclk[(e["source"][0], e["source"][1])] = e["clock"]
                eclk[(e["sink"][0], e["sink"][1])] = e["clock"]
        for cr in c.get("clock_resets", []):
            eclk[(cr["source"][0], cr["source"][1])] = cr["domain"]

    def peer_class(inst):
        if inst == "<die_pin>":
            return "die_pin"
        qm = QUAD.search(inst)
        if qm:
            return f"quadrant_{qm.group(1)}"
        return f"central:{inst}"

    top_name = a.top or f"{top}_slice_{a.set or 'custom'}"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pl = sp_in + sp_out
    v = [f"// generated by tools/hbm_layer_vehicle/cut_slice.py from {Path(a.die).name} (die top {top}); "
         f"{len(S)} of {len(insts)} instances, verbatim", "`default_nettype none", f"module {top_name} ("]
    v.append(",\n".join(f"  {n}" for n in pl))
    v.append(");")
    for n in sp_in:
        v.append(f"  input wire [{width(n) - 1}:0] {n};")
    for n in sp_out:
        v.append(f"  output wire [{width(n) - 1}:0] {n};")
    for n in internal:
        v.append(f"  wire [{width(n) - 1}:0] {n};")
    for x in insts:
        if x["name"] in S:
            v.append(x["text"])
    v.append("endmodule\n`default_nettype wire\n")
    (out / "slice.v").write_text("\n".join(v))

    def ent(n, d):
        dv = driver[n]
        rd = readers.get(n, [])
        peer = dv[0] if d == "input" else None
        e = {"name": n, "dir": d, "width": width(n), "driver": f"{dv[0]}.{dv[1]}",
             "readers_inside": sorted(f"{r[0]}.{r[1]}" for r in rd if r[0] in S),
             "readers_outside": sorted(f"{r[0]}.{r[1]}" for r in rd if r[0] not in S)}
        clk = eclk.get(dv) or next((eclk[r] for r in rd if r in eclk), None)
        e["clock"] = clk or ("stream" if dv[0] != "<die_pin>" else None)
        e["clock_from_contract"] = bool(clk)
        if d == "input":
            e["peer_class"] = peer_class(dv[0])
            if dv[0] in con:
                e["peer_slot"] = con[dv[0]].get("slot")
        else:
            outs = sorted({r[0] for r in rd if r[0] not in S})
            e["peer_class"] = sorted({peer_class(r) for r in outs}) or (["die_pin"] if n in ports else [])
        return e

    bnd = {"schema": "opentallas.hbm_slice_boundary.v1", "die_v": str(a.die), "die_top": top, "slice_top": top_name,
           "instances": sorted(S), "instance_count": len(S), "die_instance_count": len(insts),
           "masters": sorted({names[n]["master"] for n in S}),
           "inputs": [ent(n, "input") for n in sp_in], "outputs": [ent(n, "output") for n in sp_out],
           "internal_nets": len(internal)}
    summ = {}
    for e in bnd["inputs"]:
        k = ("in", e["peer_class"])
        summ[k] = [summ.get(k, [0, 0])[0] + 1, summ.get(k, [0, 0])[1] + e["width"]]
    for e in bnd["outputs"]:
        for pc in e["peer_class"]:
            k = ("out", pc)
            summ[k] = [summ.get(k, [0, 0])[0] + 1, summ.get(k, [0, 0])[1] + e["width"]]
    bnd["summary"] = {f"{k[0]}:{k[1]}": {"ports": v_[0], "bits": v_[1]} for k, v_ in sorted(summ.items())}
    (out / "boundary.json").write_text(json.dumps(bnd, indent=1))
    (out / "masters.txt").write_text("\n".join(bnd["masters"]) + "\n")
    print(f"SLICE {top_name}: {len(S)} instances, {len(bnd['masters'])} masters, {len(sp_in)} in "
          f"({sum(width(n) for n in sp_in)} b), {len(sp_out)} out ({sum(width(n) for n in sp_out)} b), "
          f"{len(internal)} internal nets -> {out}")
    for k, v_ in bnd["summary"].items():
        print(f"  {k:40s} {v_['ports']:5d} ports {v_['bits']:8d} b")


if __name__ == "__main__":
    main()
