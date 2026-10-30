#!/usr/bin/env python3
"""Preserve zero-cycle HR face copies through JSON -> Verilog -> synthesis.

Only explicitly kept dff/adff cells are wrapped, one bit per kept hierarchy.
An optional combinational output is retimed across its existing same-clock,
same-reset source flops, so the observable edge does not move.
"""
import argparse
import copy
import json

ONE = "0" * 31 + "1"


def transform(design, top, retime=(), mutant=False):
    out = copy.deepcopy(design)
    m = out["modules"][top]
    cells = m["cells"]
    all_bits = [b for c in cells.values() for v in c["connections"].values() for b in v if isinstance(b, int)]
    next_bit = max(all_bits) + 1

    def fresh():
        nonlocal next_bit
        b = next_bit
        next_bit += 1
        return b

    driver = {}
    for name, c in cells.items():
        for port, direction in c["port_directions"].items():
            if direction == "output":
                for i, b in enumerate(c["connections"][port]):
                    driver[b] = (name, port, i)
    retimed = []
    for port in retime:
        p = m["ports"][port]
        if p["direction"] != "output" or len(p["bits"]) != 1:
            raise ValueError("retime requires a scalar output")
        old_q = p["bits"][0]
        cache = {}
        domains = set()
        reset_value = {}

        def advance(b):
            if isinstance(b, str):
                return b
            if b in cache:
                return cache[b]
            name, op, index = driver[b]
            c = cells[name]
            if c["type"] in ("$dff", "$adff"):
                if c["type"] != "$adff":
                    raise ValueError("retimed output must have a common explicit reset")
                par = c["parameters"]
                domains.add((tuple(c["connections"]["CLK"]), par["CLK_POLARITY"],
                             tuple(c["connections"]["ARST"]), par["ARST_POLARITY"]))
                rv = par["ARST_VALUE"][::-1][index]
                if rv != "0":
                    raise ValueError("only zero-reset reduction outputs are supported")
                reset_value[b] = rv
                cache[b] = c["connections"]["D"][index]
                return cache[b]
            if c["type"] not in ("$reduce_or", "$reduce_bool", "$logic_or", "$or"):
                raise ValueError("unsupported retime cone " + c["type"])
            if c["type"] == "$or" and any(len(v) != 1 for v in c["connections"].values()):
                raise ValueError("only scalar bitwise OR can be retimed as a reduction")
            nc = copy.deepcopy(c)
            for ip, direction in nc["port_directions"].items():
                nc["connections"][ip] = ([advance(x) for x in nc["connections"][ip]]
                                         if direction == "input" else [fresh() for _ in nc["connections"][ip]])
            cells["hrface_next_" + str(len(cells))] = nc
            for j, ob in enumerate(c["connections"][op]):
                cache[ob] = nc["connections"][op][j]
            return cache[b]

        d = advance(old_q)
        if len(domains) != 1 or not reset_value:
            raise ValueError("retime cone has mixed clock/reset or no registers")
        ck, cp, rn, rp = domains.pop()
        new_q = fresh()
        cells["hrface_retime_" + port] = dict(hide_name=0, type="$adff",
            parameters=dict(WIDTH=ONE, CLK_POLARITY=cp, ARST_POLARITY=rp, ARST_VALUE="0"),
            attributes=dict(keep=ONE), port_directions=dict(CLK="input", ARST="input", D="input", Q="output"),
            connections=dict(CLK=list(ck), ARST=list(rn), D=[d], Q=[new_q]))
        p["bits"] = [new_q]
        # The old internal signal keeps its own name; only the public alias moves.
        m["netnames"][port] = copy.deepcopy(m["netnames"][port])
        m["netnames"][port]["bits"] = [new_q]
        m["netnames"][port].setdefault("attributes", {})["keep"] = ONE
        retimed.append(port)

    wrappers = {}
    count = 0
    public_bits = {b for p in m["ports"].values() if p["direction"] == "output" for b in p["bits"]}
    mutated = False
    for name, c in list(cells.items()):
        if c["type"] not in ("$dff", "$adff") or not int(c.get("attributes", {}).get("keep", "0"), 2):
            continue
        par = c["parameters"]
        width = len(c["connections"]["Q"])
        for i in range(width):
            sig = (c["type"], par["CLK_POLARITY"], par.get("ARST_POLARITY", ""),
                   par.get("ARST_VALUE", "0" * width)[::-1][i])
            wn = "ot_hr_face_" + ("ar" if sig[0] == "$adff" else "d") + "_" + "_".join(sig[1:])
            if wn not in wrappers:
                con = dict(CLK=[2], D=[3], Q=[4])
                pp = dict(CLK_POLARITY=sig[1], WIDTH=ONE)
                pd = dict(CLK="input", D="input", Q="output")
                if sig[0] == "$adff":
                    con["ARST"] = [5]
                    pp.update(ARST_POLARITY=sig[2], ARST_VALUE=sig[3])
                    pd["ARST"] = "input"
                wrappers[wn] = dict(attributes={"keep_hierarchy": ONE},
                    ports={k: dict(direction=pd[k], bits=v) for k, v in con.items()},
                    netnames={k: dict(hide_name=0, bits=v, attributes={}) for k, v in con.items()},
                    cells={"u_ff": dict(hide_name=0, type=sig[0], parameters=pp,
                        attributes={"keep": ONE}, port_directions=pd, connections=con)})
            cn = {p: ([b[i]] if p in ("D", "Q") else list(b)) for p, b in c["connections"].items()}
            if mutant and not mutated and cn["Q"][0] in public_bits:
                nb = fresh()
                cells["hrface_mutant"] = dict(hide_name=0, type="$not", parameters=dict(A_SIGNED="0", A_WIDTH=ONE, Y_WIDTH=ONE),
                    attributes={}, port_directions=dict(A="input", Y="output"), connections=dict(A=cn["D"], Y=[nb]))
                cn["D"] = [nb]
                mutated = True
            cells[name + "_facebit_" + str(i)] = dict(hide_name=0, type=wn, parameters={},
                attributes={"keep": ONE, "keep_hierarchy": ONE}, port_directions=c["port_directions"], connections=cn)
            count += 1
        del cells[name]
    out["modules"].update(wrappers)
    if mutant and not mutated:
        raise ValueError("no observable private output flop for mutant")
    return out, dict(top=top, wrapped_ff_bits=count, retimed_outputs=retimed, added_cycles=0, mutant=mutant)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("output")
    p.add_argument("--top", required=True)
    p.add_argument("--retime-output", action="append", default=[])
    p.add_argument("--mutant", action="store_true")
    a = p.parse_args()
    result, report = transform(json.load(open(a.source)), a.top, a.retime_output, a.mutant)
    with open(a.output, "w") as f:
        json.dump(result, f)
    print(json.dumps(report))
