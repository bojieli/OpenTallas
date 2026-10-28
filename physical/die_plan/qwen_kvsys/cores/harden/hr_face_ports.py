#!/usr/bin/env python3
"""CORES-KITS/KVHR2 10-26: zero-cycle face recut of the KV hub_Wi host cores qkd_hr_* (--hr-face-ports).

The hr cores are raw cuts of u_host member boundaries (kv_core_rtl.py --hr-elab), so some face flops also feed core
logic (face_guard 'shared').  Industry fix, 0 added cycles (register duplication / private port flops, as
kvspc_copy_outputs.py / ectlk_face_ports.py):
  * OUTPUT bit driven by a flop Q that also loads core logic (or a 2nd port): a private copy of that flop bit
    (same D, clock, reset/enable, reset value; (* keep *)) drives the pin; the original keeps the internal loads.
  * INPUT bit captured by several flops whose D is the pin itself with identical control: merged into one capture flop
    (equal next state on every edge = equivalent, 0 cycles); other loads (logic before the flop) are NOT touched.
Everything else (output through logic = needs +1 cycle, dropped input, feedthrough) is only LISTED in the report.
DIE-KV-3/CORETX 10-27 (opt-in --retime-in PIN[i], e.g. core_tx u_ctrl__package_abort[0]): an INPUT bit whose whole
fan-out is one combinational cone into ONE flop bit F.D (abort_q <= package_abort with a sync clear: pin -> AND2 -> F)
gets a face capture flop, 0 added cycles (Shannon retime of the cone across F): P <= pin, H <= cone(pin=0),
G <= cone(pin=1) (same clock/reset/enable as F, H/G reset to F's value, P to 0) and F.Q := P ? G : H.  The pin then has
exactly one load, a flop D; the proof (equiv_simple/equiv_induct) covers it like the other edits.
Flow (yosys in the ORFS image): read the core sources (repo paths at the commit), hierarchy -top, proc, flatten,
memory_collect -> pre.json; this script edits the netlist JSON -> post.json; write_verilog -> <core>.v (kit RTL).
Proof: memory_map both, equiv_make gold=pre gate=post (same-name macro cells merged, then exposed as free
ports: expose -evert), async2sync, equiv_simple -seq 2, equiv_induct -seq 2, equiv_status -assert (also on the emitted .v); a mutant
(one private copy's D inverted) must FAIL the same proof.
usage: hr_face_ports.py transform PRE.json POST.json REPORT.json --top MOD [--mutant] [--retime-in PIN[i] ...]
"""
import argparse
import copy
import json
import re
import sys
from collections import defaultdict

FF = {"$dff", "$adff", "$dffe", "$adffe", "$sdff", "$sdffe", "$sdffce", "$aldff", "$aldffe", "$dffsr", "$dffsre",
      "$_DFF_P_", "$_DFF_N_"}
WIDE = ("D", "Q", "SET", "CLR", "AD")
CTRL = ("CLK", "ARST", "EN", "SRST", "ALOAD")
VAL = ("ARST_VALUE", "SRST_VALUE")
CLKRST = re.compile(r"(^|__)(ck|ck_\w+|clk\w*|rst_n|arst_n|hrst_n|[rw]rst_n|[a-z0-9_]*_rst_n|por_n)$")
ONE = "00000000000000000000000000000001"
# flop types the retime can replicate bit-wise (no per-bit SET/CLR/AD vectors)
RETIME_FF = {"$dff", "$adff", "$dffe", "$adffe", "$sdff", "$sdffe", "$sdffce"}


def pbits(v, w):
    s = str(v)
    if set(s) <= set("01xz"):
        s = s.rjust(w, "0")[-w:]
        return s
    n = int(s)
    return format(n, f"0{w}b")[-w:]


def transform(J, top, mutant=False, retime_in=()):
    M = J["modules"][top]
    cells, ports = M["cells"], M["ports"]
    # Plan pin tables use p[0] even for width-one ports. Preserve that physical
    # identity through write_verilog; scalar clocks otherwise become ck rather
    # than ck[0] and OpenROAD rejects the planned pin (PPL-0061).
    for pn, port in ports.items():
        if len(port["bits"]) == 1:
            M["netnames"][pn].setdefault("attributes", {})["single_bit_vector"] = ONE
    init_by_bit = {}
    for net in M["netnames"].values():
        if "init" not in net.get("attributes", {}):
            continue
        vals = pbits(net["attributes"]["init"], len(net["bits"]))[::-1]
        for bit, val in zip(net["bits"], vals):
            if val not in "01":
                continue
            if bit in init_by_bit and init_by_bit[bit] != val:
                raise ValueError(f"conflicting initial values on net bit {bit}")
            init_by_bit[bit] = val
    nid = [max([b for c in cells.values() for v in c["connections"].values() for b in v if isinstance(b, int)] +
               [b for p in ports.values() for b in p["bits"] if isinstance(b, int)] +
               [b for n in M["netnames"].values() for b in n["bits"] if isinstance(b, int)] + [1])]

    def new():
        nid[0] += 1
        return nid[0]
    drv, loads = {}, defaultdict(list)
    for cn, c in cells.items():
        for p, bits in c["connections"].items():
            d = c.get("port_directions", {}).get(p, "input")
            for i, b in enumerate(bits):
                if not isinstance(b, int):
                    continue
                if d == "output":
                    drv[b] = (cn, p, i)
                else:
                    loads[b].append((cn, p, i))
    pin_of = defaultdict(list)
    for pn, p in ports.items():
        for i, b in enumerate(p["bits"]):
            pin_of[b].append((pn, i))
    rep = dict(top=top, private_out=[], merged_in=[], unregistered_out=[], const_out=[], feedthrough=[],
               dropped_in=[], logic_in=[], multi_in=[], added_ff_bits=0, added_cycles=0, mutant=mutant)
    retime_in = list(dict.fromkeys(retime_in))
    if retime_in:
        rep["retimed_in"] = []
    nm = 0

    def ffcopy(cn, i, tag):
        c = cells[cn]
        w = len(c["connections"]["Q"])
        nc = copy.deepcopy(c)
        nc["parameters"]["WIDTH"] = format(1, "032b")
        for k in VAL:
            if k in nc["parameters"]:
                nc["parameters"][k] = pbits(c["parameters"][k], w)[::-1][i]
        for p in WIDE:
            if p in nc["connections"]:
                nc["connections"][p] = [c["connections"][p][i]]
        q = new()
        nc["connections"]["Q"] = [q]
        nc["attributes"] = {"keep": ONE, "src": "hr_face_ports.py private port flop"}
        cells[f"hrfp_{tag}"] = nc
        # keep the original too: else synth opt_merge folds it into the kept copy (shared again, host_qm 1st build)
        c.setdefault("attributes", {})["keep"] = ONE
        # Preserve the actual Q nets across write_verilog/proc round trips.
        # A kept alias of the output produces a real buffer load on the face.
        original_q = c["connections"]["Q"][i]
        for net in M["netnames"].values():
            if original_q in net["bits"]:
                net.setdefault("attributes", {})["keep"] = ONE
        if original_q in init_by_bit:
            init_by_bit[q] = init_by_bit[original_q]
            # The original initialized name may be the output port that is
            # about to move to the private Q. Keep its internal state init too.
            M["netnames"][f"hrfp_{tag}_internal_init"] = dict(
                hide_name=0, bits=[original_q],
                attributes=dict(keep=ONE, init=init_by_bit[original_q]))
        return q, nc

    for pn, p in ports.items():
        if CLKRST.search(pn):
            continue
        for i, b in enumerate(p["bits"]):
            nm_ = f"{pn}[{i}]"
            if p["direction"] == "output":
                if not isinstance(b, int):
                    rep["const_out"].append(nm_)
                    continue
                inp = [x for x in pin_of[b] if ports[x[0]]["direction"] == "input"]
                if inp:
                    rep["feedthrough"].append(f"{nm_} <- {inp[0][0]}[{inp[0][1]}]")
                    continue
                d = drv.get(b)
                if d is None or cells[d[0]]["type"] not in FF or d[1] != "Q":
                    rep["unregistered_out"].append(f"{nm_}: {cells[d[0]]['type'] if d else 'undriven'}")
                    continue
                # Two distinct output registers with equal next state may
                # currently be private yet merge during later synthesis.
                # Preserve every registered output, including existing ones.
                cells[d[0]].setdefault("attributes", {})["keep"] = ONE
                M["netnames"][pn].setdefault("attributes", {})["keep"] = ONE
                occ = [x for x in pin_of[b] if ports[x[0]]["direction"] == "output"]
                internal = len(loads[b])
                if internal == 0 and len(occ) == 1:
                    continue
                if internal == 0 and occ[0] == (pn, i):
                    continue                     # first of several ports keeps the original flop
                tag = re.sub(r"\W", "_", f"{pn}_{i}")
                q, nc = ffcopy(d[0], d[2], tag)
                if mutant and nm == 0:
                    # inject: private copy samples the inverse of D (the proof must catch it)
                    nb = new()
                    cells["hrfp_mutant_not"] = {"hide_name": 0, "type": "$not", "parameters": {
                        "A_SIGNED": "0" * 32, "A_WIDTH": format(1, "032b"), "Y_WIDTH": format(1, "032b")},
                        "attributes": {}, "port_directions": {"A": "input", "Y": "output"},
                        "connections": {"A": nc["connections"]["D"], "Y": [nb]}}
                    nc["connections"]["D"] = [nb]
                p["bits"][i] = q
                M["netnames"][pn]["bits"][i] = q          # read_json takes the wire from netnames
                M["netnames"][pn].setdefault("attributes", {})["keep"] = ONE
                nm += 1
                rep["private_out"].append(dict(pin=nm_, orig_ff=d[0], orig_bit=d[2], internal_loads=internal,
                                               other_ports=len(occ) - 1, cycles=0))
            else:
                if not isinstance(b, int):
                    continue
                if nm_ in retime_in:
                    continue                     # handled after the port loop (retime_input)
                ld = loads[b]
                if not ld:
                    rep["dropped_in"].append(nm_)
                    continue
                if len(ld) == 1:
                    cn, pp, _ = ld[0]
                    if not (cells[cn]["type"] in FF and pp == "D"):
                        rep["logic_in"].append(f"{nm_}: {cells[cn]['type']}.{pp}")
                    continue
                if all(cells[cn]["type"] in FF and pp == "D" for cn, pp, _ in ld):
                    def key(x):
                        c = cells[x[0]]
                        w = len(c["connections"]["Q"])
                        return (c["type"], tuple((k, tuple(c["connections"][k])) for k in CTRL if k in c["connections"]),
                                tuple((k, v) for k, v in sorted(c["parameters"].items()) if k.endswith("POLARITY")),
                                tuple((k, c["connections"][k][x[2]]) for k in WIDE if k not in ("D", "Q") and k in c["connections"]),
                                init_by_bit.get(c["connections"]["Q"][x[2]]),
                                tuple(pbits(c["parameters"][k], w)[::-1][x[2]] for k in VAL if k in c["parameters"]))
                    if len({key(x) for x in ld}) == 1:
                        keep = ld[0]
                        kq = cells[keep[0]]["connections"]["Q"][keep[2]]
                        for cn, pp, j in ld[1:]:
                            oq = cells[cn]["connections"]["Q"][j]
                            for c in cells.values():
                                for k, v in c["connections"].items():
                                    if c.get("port_directions", {}).get(k) != "output":
                                        c["connections"][k] = [kq if x == oq else x for x in v]
                            for pn2, p2 in ports.items():
                                if p2["direction"] == "output":
                                    p2["bits"] = [kq if x == oq else x for x in p2["bits"]]
                                    M["netnames"][pn2]["bits"] = list(p2["bits"])
                            for nn in M["netnames"].values():           # names of the merged capture -> kept net
                                nn["bits"] = [kq if x == oq else x for x in nn["bits"]]
                            cells[cn]["connections"]["Q"][j] = new()     # merged bit: dead, removed by opt
                        rep["merged_in"].append(dict(pin=nm_, kept=keep[0], merged=[x[0] for x in ld[1:]], cycles=0))
                        continue
                rep["multi_in"].append(f"{nm_}: " + ", ".join(f"{cells[cn]['type']}.{pp}" for cn, pp, _ in ld[:4]))
    for nm_ in retime_in:
        mut = mutant and nm == 0
        rep["retimed_in"].append(retime_input(M, ports, cells, drv, loads, pin_of, init_by_bit, new, nm_, mut))
        nm += int(mut)
    for net in M["netnames"].values():
        if any(bit in init_by_bit for bit in net["bits"]):
            net.setdefault("attributes", {})["init"] = "".join(
                init_by_bit.get(bit, "x") for bit in reversed(net["bits"]))
    rep["added_ff_bits"] = len(rep["private_out"]) + sum(r["added_ff_bits"] for r in rep.get("retimed_in", []))
    for k in ("unregistered_out", "feedthrough", "dropped_in", "logic_in", "multi_in", "const_out"):
        rep["n_" + k] = len(rep[k])
    return J, rep


def retime_input(M, ports, cells, drv, loads, pin_of, init_by_bit, new, nm_, mutant=False):
    """--retime-in: face capture flop for input bit nm_ (port[i]) whose fan-out is one combinational cone into one flop
    bit F.D[j]; 0 added cycles (Shannon: F' = P ? G : H, P <= pin, G/H <= cone with pin = 1/0).  SystemExit if the pin
    does not have that shape (the option is an explicit per-core request, so a mismatch must be loud)."""
    m = re.fullmatch(r"(.+)\[(\d+)\]", nm_)
    if not m or m[1] not in ports or ports[m[1]]["direction"] != "input" or int(m[2]) >= len(ports[m[1]]["bits"]):
        raise SystemExit(f"--retime-in {nm_}: not an input port bit of the top")
    b = ports[m[1]]["bits"][int(m[2])]
    if not isinstance(b, int):
        raise SystemExit(f"--retime-in {nm_}: constant port bit")
    cone, cone_bits, work, sink = [], {b}, [b], None
    while work:
        x = work.pop()
        for cn, pp, j in loads[x]:
            c = cells[cn]
            if c["type"] in FF:
                if pp != "D" or (sink is not None and sink != (cn, j)):
                    raise SystemExit(f"--retime-in {nm_}: cone reaches flop {cn}.{pp}[{j}] beside {sink} (one D bit only)")
                sink = (cn, j)
                continue
            if not c["type"].startswith("$") or re.search(r"dff|latch|^\$mem|^\$_", c["type"], re.I):
                raise SystemExit(f"--retime-in {nm_}: cone cell {cn} type {c['type']} is not combinational logic")
            if cn in cone:
                continue
            cone.append(cn)
            for p2, bits in c["connections"].items():
                if c.get("port_directions", {}).get(p2) == "output":
                    for y in bits:
                        if isinstance(y, int) and y not in cone_bits:
                            cone_bits.add(y)
                            work.append(y)
    if sink is None:
        raise SystemExit(f"--retime-in {nm_}: the cone reaches no flop")
    if any(y != b and pin_of.get(y) for y in cone_bits):
        raise SystemExit(f"--retime-in {nm_}: the cone drives a top port")
    fn, j = sink
    F = cells[fn]
    if F["type"] not in RETIME_FF:
        raise SystemExit(f"--retime-in {nm_}: sink flop {fn} type {F['type']} not supported")
    if F["connections"]["Q"][j] in init_by_bit:
        raise SystemExit(f"--retime-in {nm_}: sink flop {fn} bit {j} has an initial value")
    w = len(F["connections"]["Q"])
    tag = re.sub(r"\W", "_", nm_)

    def copy_cone(v):
        mp = {b: v}
        cc = {}
        for cn in cone:
            nc = copy.deepcopy(cells[cn])
            for p2, bits in nc["connections"].items():
                if nc.get("port_directions", {}).get(p2) == "output":
                    for y in bits:
                        if isinstance(y, int):
                            mp[y] = new()
            cc[cn] = nc
        for cn, nc in cc.items():
            nc["connections"] = {p2: [mp.get(x, x) if isinstance(x, int) else x for x in bits]
                                 for p2, bits in nc["connections"].items()}
            nc["attributes"] = {"src": f"hr_face_ports.py retime cone {nm_}={v}"}
            cells[f"hrrt_{tag}_c{v}_{len(cells)}"] = nc
        return mp.get(F["connections"]["D"][j], F["connections"]["D"][j])

    def flop(d, rv, name, keep=False):
        nc = copy.deepcopy(F)
        nc["parameters"]["WIDTH"] = format(1, "032b")
        for k in VAL:
            if k in nc["parameters"]:
                nc["parameters"][k] = rv if rv is not None else pbits(F["parameters"][k], w)[::-1][j]
        for p2 in WIDE:
            if p2 in nc["connections"]:
                nc["connections"][p2] = [nc["connections"][p2][j]]
        nc["connections"]["D"] = [d]
        q = new()
        nc["connections"]["Q"] = [q]
        nc["attributes"] = {"src": f"hr_face_ports.py retime {name} {nm_}"}
        if keep:
            nc["attributes"]["keep"] = ONE
        cells[f"hrrt_{tag}_{name}"] = nc
        return q, nc
    h, g = copy_cone("0"), copy_cone("1")
    pq, _ = flop(b, "0", "p", keep=True)          # the face capture flop: D = pin, reset 0 (selects H = F's reset value)
    hq, _ = flop(h, None, "h")
    gq, gc = flop(g, None, "g")
    if mutant:
        gc["connections"]["D"] = [h]     # mutant: G samples the pin=0 cone -> F' ignores the pin (proof must FAIL)
    orig_q = F["connections"]["Q"][j]
    F["connections"]["Q"][j] = new()     # old F bit: dead (removed by opt)
    F["connections"]["D"][j] = "0"
    if w == 1:
        F.get("attributes", {}).pop("keep", None)   # whole F is dead now; let opt remove it
    cells[f"hrrt_{tag}_mux"] = {"hide_name": 0, "type": "$mux", "parameters": {"WIDTH": format(1, "032b")},
                                "attributes": {"src": f"hr_face_ports.py retime mux {nm_}"},
                                "port_directions": {"A": "input", "B": "input", "S": "input", "Y": "output"},
                                "connections": {"A": [hq], "B": [gq], "S": [pq], "Y": [orig_q]}}
    return dict(pin=nm_, sink_ff=fn, sink_bit=j, cone_cells=len(cone), added_ff_bits=3, cycles=0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["transform"])
    ap.add_argument("pre")
    ap.add_argument("post")
    ap.add_argument("report")
    ap.add_argument("--top", required=True)
    ap.add_argument("--mutant", action="store_true")
    ap.add_argument("--retime-in", action="append", default=[], metavar="PIN[i]",
                    help="input bit to give a face capture flop by a 0-cycle retime of its cone into one flop (opt-in)")
    a = ap.parse_args()
    J, rep = transform(json.load(open(a.pre)), a.top, a.mutant, a.retime_in)
    json.dump(J, open(a.post, "w"))
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k.startswith("n_") or k in ("added_ff_bits", "added_cycles")}))
    print("merged_in", len(rep["merged_in"]))


if __name__ == "__main__":
    main()
