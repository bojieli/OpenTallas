#!/usr/bin/env python3
"""TYPE-SAFE-2 11-08: core connectivity sidecar (check.py core_conns.json format) from a native BOUND module.

The S81 native bind joins face buses to hard-core ports through wiring only (concatenations / bit selects in
`assign` statements, kept transport chains ot_dp_dly, lane pads u_lpad_*).  None of that is visible to the plan, so
check.py R3-INTERNAL (pin-to-pin reach of bus window -> core port) is blind for those types.  This tool reads the bound
module and writes, per hard core inst (plan name) and port, the face buses and other cores it reaches by WIRING ONLY
(no logic operator in between), plus the existing stages on that wire path (lane pad / kept chain depth), so a plan
event can (1) site existing stages first (0 cycles) and (2) add internal_stations only for the remainder.

usage: core_conns_from_bind.py PLAN.json TYPE BOUND.sv OUT.json
OUT = {"core_conns": {TYPE: {core_inst: {port: ["bus:<bus>", "core:<inst>.<port>", ...]}}},
       "paths": [{core, port, dir, bus|partner, stages_existing, via}]}"""
import json
import re
import sys
from collections import defaultdict

ID = r"[A-Za-z_][A-Za-z0-9_$]*"
PURE = re.compile(r"^[\s{}\[\]:,0-9A-Za-z_$']*$")     # concatenation / bit select only (no ?:, &, |, ^, ~, +, ==)


def strip_comments(txt):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", txt, flags=re.S))


def idents(expr):
    out = []
    for m in re.finditer(ID, expr):
        s = m.group(0)
        # skip sized-literal pieces like 1'b0 / 595
        if re.match(r"^[0-9]", s) or s in ("b", "d", "h"):
            continue
        out.append(s)
    return out


def parse(txt):
    txt = strip_comments(txt)
    assigns = {}                            # lhs id -> (rhs ids, pure)
    for m in re.finditer(rf"\bassign\s+({ID})\s*(\[[^\]]*\])?\s*=\s*(.*?);", txt, flags=re.S):
        lhs, rhs = m.group(1), m.group(3)
        pure = bool(PURE.match(rhs.replace("'b", "").replace("'d", "").replace("'h", "")))
        prev = assigns.get(lhs)
        ids = idents(rhs)
        if prev:                            # several partial assigns: union, pure only if all pure
            assigns[lhs] = (prev[0] + ids, prev[1] and pure)
        else:
            assigns[lhs] = (ids, pure)
    insts = []                              # (module, inst, {port: expr})
    for m in re.finditer(rf"\n\s*({ID})\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*({ID})\s*\((.*?)\)\s*;", txt, flags=re.S):
        mod, inst, body = m.group(1), m.group(3), m.group(4)
        if mod in ("module", "assign", "wire", "reg", "input", "output", "always", "if", "for"):
            continue
        ports = {}
        for pm in re.finditer(rf"\.({ID})\s*\(", body):
            # balanced parens from pm.end()
            i, depth = pm.end(), 1
            while i < len(body) and depth:
                depth += {"(": 1, ")": -1}.get(body[i], 0)
                i += 1
            ports[pm.group(1)] = body[pm.end():i - 1]
        params = m.group(2) or ""
        dm = re.search(r"\.D\s*\(\s*(\d+)\s*\)", params)
        insts.append((mod, inst, ports, int(dm.group(1)) if dm else None))
    return assigns, insts


def trace(plan, tn, text):
    """-> {core_conns: {tn: {core: {port: [..]}}}, paths: [...], ...} for the bound module text of type tn"""
    t = plan["partition_types"][tn]
    def flat(inst):          # plan "u_c.u_xf.g_cp[3].u_e" -> bound suffix "u_xf_g_cp_3_u_e" (first scope dropped)
        parts = inst.split(".")
        parts = parts[1:] if len(parts) > 1 else parts
        return re.sub(r"\[(\d+)\]", r"_\1", "_".join(parts))
    hcs = {flat(hc["inst"]): hc["inst"] for hc in t.get("hard_cores", [])}
    buses = {b["name"]: b for b in t.get("buses", [])}
    assigns, insts = parse(text)
    # wire producers: dly/st chains and face in flops
    chain = {}                              # q id -> (d ids, stages, inst)
    bus_of_q = {}                           # id -> bus (in buses: <bus>_q after u_bin / u_lpad)
    bout_in = defaultdict(list)             # id -> [out bus] that read it in their .d
    core_in = defaultdict(list)             # id -> [(core, port)] read by a core input
    core_out = {}                           # id -> (core, port) driven by a core output
    # wires driven by an assign or a stage are never a core OUTPUT (a core input wire may share the w_<core>_<port> form)
    driven = set(assigns) | {i for mod, _, ports, _ in insts if mod in ("ot_dp_st", "ot_dp_dly")
                             for i in idents(ports.get("q", ""))}
    for mod, inst, ports, D in insts:
        if mod == "ot_dp_st" and inst.startswith("u_bin_"):
            q = idents(ports.get("q", ""))
            if q:
                bus_of_q[q[0]] = inst[len("u_bin_"):]
                chain[q[0]] = ([f"@bus:{inst[len('u_bin_'):]}"], 0, inst)
        elif mod == "ot_dp_st" and inst.startswith("u_bout_"):
            for i in idents(ports.get("d", "")):
                bout_in[i].append(inst[len("u_bout_"):])
        elif mod == "ot_dp_dly":
            q = idents(ports.get("q", ""))
            for qq in q:
                chain[qq] = (idents(ports.get("d", "")), D or 0, inst)
        else:
            core = None
            for k in sorted(hcs, key=len, reverse=True):
                if inst.endswith("_" + k) or inst == k:
                    core = hcs[k]
                    break
            if core is None:
                continue
            for p, e in ports.items():
                ids = idents(e)
                if len(ids) == 1 and ids[0].startswith("w_") and ids[0] not in driven and \
                        (ids[0].endswith("_" + p) or ids[0].endswith(p)):
                    core_out[ids[0]] = (core, p)
                for i in ids:
                    core_in[i].append((core, p))
    # backward trace from a core input id to bus / core outputs through pure assigns and chains
    paths = []
    conns = defaultdict(lambda: defaultdict(set))

    def back(i, stages, via, seen):
        if i in seen:
            return []
        seen.add(i)
        res = []
        if i in core_out:
            res.append(("core", core_out[i], stages, via))
        if i in chain:
            d, st, inst = chain[i]
            for j in d:
                if j.startswith("@bus:"):
                    res.append(("bus", j[5:], stages, via))
                else:
                    res += back(j, stages + st, via + [inst], seen)
        if i in assigns:
            ids, pure = assigns[i]
            if pure:
                for j in ids:
                    res += back(j, stages, via, seen)
        return res
    for i, users in core_in.items():
        for core, p in users:
            if core_out.get(i) == (core, p):
                continue                    # the port's own output wire
            for kind, what, st, via in back(i, 0, [], set()):
                if kind == "bus":
                    conns[core][p].add(f"bus:{what}")
                    paths.append(dict(core=core, port=p, dir="in", bus=what, stages_existing=st, via=via))
                elif kind == "core" and what[0] != core:
                    conns[core][p].add(f"core:{what[0]}.{what[1]}")
                    paths.append(dict(core=core, port=p, dir="in", partner=f"{what[0]}.{what[1]}",
                                      stages_existing=st, via=via))
    # forward trace from core outputs to out buses (through pure assigns and chains)
    fwd = defaultdict(list)                 # id -> ids that read it purely
    for lhs, (ids, pure) in assigns.items():
        if pure:
            for j in ids:
                fwd[j].append((lhs, 0, None))
    for q, (d, st, inst) in chain.items():
        for j in d:
            if not j.startswith("@"):
                fwd[j].append((q, st, inst))
    for w, (core, p) in core_out.items():
        stack, seen = [(w, 0, [])], set()
        while stack:
            i, st, via = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            for ob in bout_in.get(i, ()):
                conns[core][p].add(f"bus:{ob}")
                paths.append(dict(core=core, port=p, dir="out", bus=ob, stages_existing=st, via=via))
            for j, s2, inst in fwd.get(i, ()):
                stack.append((j, st + s2, via + ([inst] if inst else [])))
    return dict(core_conns={tn: {c: {p: sorted(v) for p, v in ps.items()} for c, ps in conns.items()}},
                paths=paths, n_insts=len(insts), n_assigns=len(assigns), cores=sorted(hcs.values()),
                buses=len(buses))


def main(argv):
    plan_path, tn, bound, out = argv[1:5]
    res = trace(json.load(open(plan_path)), tn, open(bound).read())
    json.dump(res, open(out, "w"), indent=1)
    conns = res["core_conns"][tn]
    print(f"{tn}: {len(res['paths'])} wiring paths, {sum(len(ps) for ps in conns.values())} core ports connected, "
          f"cores {len(conns)}/{len(res['cores'])}")


if __name__ == "__main__":
    main(sys.argv)
