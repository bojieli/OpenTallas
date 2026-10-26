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
Flow (yosys in the ORFS image): read the core sources (repo paths at the commit), hierarchy -top, proc, flatten,
memory_collect -> pre.json; this script edits the netlist JSON -> post.json; write_verilog -> <core>.v (kit RTL).
Proof: memory_map both, equiv_make gold=pre gate=post (same-name macro cells merged, then exposed as free
ports: expose -evert), async2sync, equiv_simple -seq 2, equiv_induct -seq 2, equiv_status -assert (also on the emitted .v); a mutant
(one private copy's D inverted) must FAIL the same proof.
usage: hr_face_ports.py transform PRE.json POST.json REPORT.json --top MOD [--mutant]
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


def pbits(v, w):
    s = str(v)
    if set(s) <= set("01xz"):
        s = s.rjust(w, "0")[-w:]
        return s
    n = int(s)
    return format(n, f"0{w}b")[-w:]


def transform(J, top, mutant=False):
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
    for net in M["netnames"].values():
        if any(bit in init_by_bit for bit in net["bits"]):
            net.setdefault("attributes", {})["init"] = "".join(
                init_by_bit.get(bit, "x") for bit in reversed(net["bits"]))
    rep["added_ff_bits"] = len(rep["private_out"])
    for k in ("unregistered_out", "feedthrough", "dropped_in", "logic_in", "multi_in", "const_out"):
        rep["n_" + k] = len(rep[k])
    return J, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["transform"])
    ap.add_argument("pre")
    ap.add_argument("post")
    ap.add_argument("report")
    ap.add_argument("--top", required=True)
    ap.add_argument("--mutant", action="store_true")
    a = ap.parse_args()
    J, rep = transform(json.load(open(a.pre)), a.top, a.mutant)
    json.dump(J, open(a.post, "w"))
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k.startswith("n_") or k in ("added_ff_bits", "added_cycles")}))
    print("merged_in", len(rep["merged_in"]))


if __name__ == "__main__":
    main()
