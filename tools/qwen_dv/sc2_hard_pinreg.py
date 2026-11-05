#!/usr/bin/env python3
"""DIE-QC-71 11-04 (QC SC event, chain-end leaves): the SC HARD_PINREG capture-sharing rewrite as a rule, so the chain-end
netlists qfd_dv_s5_sc2_k79_up0 / _dn0 get the same form the base k79 got by hand-derived candidate (Codex 98bbbbd8184).

Every input-pin bit that drives more than one capture flop becomes one pin register:
  * plain class (N >= 2 dff_p, same C, same D = the pin bit): first flop keeps D and drives sc_pin_cap_<i>; under
    HARD_PINREG=1 every member output is that capture through a NOT-NOT pair, and the other flops do not exist;
  * reset class (N >= 2 dff_pn0 on one pin bit): each member keeps its flag flop (D=1 under HARD_PINREG=1, own R), output
    = shared un-reset capture & flag.  Same cycle behaviour; 0 added cycles.
HARD_PINREG=0 elaborates the original flops (legacy branch); a plain class leader drives its output through sc_pin_cap.
Proof that the rule is the candidate: run on the base k79 at 051340895d9 this reproduces 98bbbbd8184 byte for byte
(sha256 9d943818a85c..., source_event.json).  A pin bit with both plain and multi-flop reset captures stops the tool.
usage: sc2_hard_pinreg.py IN.sv OUT.sv"""
import collections
import json
import re
import sys

ATTR = '(* keep=1, keep_hierarchy="yes" *) '
P = re.compile(r'^\(\* keep=1, keep_hierarchy="yes" \*\) qfd_s2_bmath_dff_p #\(\.ID\(0\)\) (u_\d+)\(\.C\((n_\d+)\),\.D\((n_\d+)\),\.Q\((n_\d+)\)\);$')
R = re.compile(r'^\(\* keep=1, keep_hierarchy="yes" \*\) qfd_s2_bmath_dff_pn0 #\(\.ID\(0\)\) (u_\d+)\(\.C\((n_\d+)\),\.D\((n_\d+)\),\.Q\((n_\d+)\),\.R\((n_\d+)\)\);$')
PORTS = re.compile(r'^(input|output) wire \[(\d+):0\] (\w+);$')


def pin_bits(lines):
    inputs = {m.group(3) for x in lines[:60] for m in [PORTS.match(x)] if m and m.group(1) == "input"}
    bit = {}
    for x in lines:
        m = re.match(r'^assign \{(.*)\} = (\w+);$', x)
        if m and m.group(2) in inputs:
            ns = m.group(1).split(",")
            for k, n in enumerate(ns):
                bit[n] = f"{m.group(2)}[{len(ns) - 1 - k}]"
        m = re.match(r'^assign (n_\d+) = (\w+);$', x)
        if m and m.group(2) in inputs:
            bit[m.group(1)] = f"{m.group(2)}[0]"
    return bit


def rewrite(text):
    lines = text.split("\n")
    bit = pin_bits(lines)
    plain, rst = collections.OrderedDict(), collections.OrderedDict()
    for x in lines:
        m = P.match(x)
        if m and m.group(3) in bit:
            plain.setdefault(m.group(3), []).append(m.group(1))
        m = R.match(x)
        if m and m.group(3) in bit:
            rst.setdefault(m.group(3), []).append(m.group(1))
    both = [bit[n] for n in plain if n in rst and len(rst[n]) > 1]
    assert not both, f"pin bit with plain and reset captures: {both}"
    plain = collections.OrderedDict((n, v) for n, v in plain.items() if len(v) >= 2)
    rst = collections.OrderedDict((n, v) for n, v in rst.items() if len(v) >= 2)
    capi = {n: i for i, n in enumerate(plain)}
    rsti = {n: i for i, n in enumerate(rst)}
    pos = {u: k for n, v in plain.items() for k, u in enumerate(v)}
    # NOT pair IDs: two per plain member, class by class
    ids, nid = {}, 1000000
    for n, v in plain.items():
        for u in v:
            ids[u] = nid
            nid += 2
    out = []
    header_done = False
    for k, x in enumerate(lines):
        if k < 60 and x.startswith("module "):
            x, c = re.subn(r'^module (\w+)\(', r'module \1 #(parameter integer HARD_PINREG=0) (', x)
            assert c == 1
        if k < 60 and not header_done and k > 1 and not PORTS.match(x):
            header_done = True
            out.append("// Declare shared pin captures before every generate use (slang lexical scope).")
            out += [f"wire sc_pin_cap_{i};" for i in range(len(plain))]
            out += [f"wire sc_pin_rstcap_{i};" for i in range(len(rst))]
        m = P.match(x)
        if m and m.group(3) in plain:
            u, c, d, q = m.groups()
            i = capi[d]
            if pos[u] == 0:
                out.append(f"{ATTR}qfd_s2_bmath_dff_p #(.ID(0)) {u}(.C({c}),.D({d}),.Q(sc_pin_cap_{i}));")
            out += [f"generate if (HARD_PINREG) begin : g_sc_pin_{u}",
                    f"wire sc_pin_inv_{u};",
                    f"{ATTR}qfd_s2_bmath_not #(.ID({ids[u]})) u_b0 (.A(sc_pin_cap_{i}),.Y(sc_pin_inv_{u}));",
                    f"{ATTR}qfd_s2_bmath_not #(.ID({ids[u] + 1})) u_b1 (.A(sc_pin_inv_{u}),.Y({q}));",
                    f"end else begin : g_sc_legacy_{u}"]
            out.append(f"assign {q} = sc_pin_cap_{i};" if pos[u] == 0 else x)
            out.append("end endgenerate")
            continue
        m = R.match(x)
        if m and m.group(3) in rst:
            u, c, d, q, r = m.groups()
            i = rsti[d]
            out += [f"wire sc_pin_flag_{u};",
                    f"{ATTR}qfd_s2_bmath_dff_pn0 #(.ID(0)) {u}(.C({c}),.D(HARD_PINREG ? 1'b1 : {d}),.Q(sc_pin_flag_{u}),.R({r}));",
                    f"assign {q} = HARD_PINREG ? (sc_pin_rstcap_{i} & sc_pin_flag_{u}) : sc_pin_flag_{u};"]
            continue
        if x == "endmodule":
            ck = next(m.group(2) for y in lines for m in [P.match(y)] if m)
            out += ["", "// Optional registered hard-boundary specialization; zero added arithmetic edges."]
            for n, i in rsti.items():
                out += [f"generate if (HARD_PINREG) begin : g_sc_shared_rst_{i}",
                        f"{ATTR}qfd_s2_bmath_dff_p #(.ID({nid + i})) u_pin (.C({ck}),.D({bit[n]}),.Q(sc_pin_rstcap_{i}));",
                        f"end else begin : g_sc_no_shared_rst_{i}",
                        f"assign sc_pin_rstcap_{i}=1'b0;",
                        "end endgenerate"]
        out.append(x)
    rep = dict(plain_classes=len(plain), plain_members=sum(map(len, plain.values())), reset_classes=len(rst),
               reset_members=sum(map(len, rst.values())), ffs_removed_hard=sum(len(v) - 1 for v in plain.values()),
               ffs_added_hard=len(rst), reset_pins=[bit[n] for n in rst])
    return "\n".join(out), rep


if __name__ == "__main__":
    out, rep = rewrite(open(sys.argv[1]).read())
    open(sys.argv[2], "w").write(out)
    print(json.dumps(rep))
