#!/usr/bin/env python3
"""HBM-BIND-7: expose the actual hub collective bodies (hb_coll_NE / hb_coll_NW) in the strict-bind netlist without
re-elaborating the die (HBM-BIND-5 splice_qhub.py precedent: a die re-elab renumbers Yosys primitives die-wide).

Base = the bound die netlist (normalized Yosys JSON, hb_coll_NE/NW are blackbox leaves ot_hfd_coll_q2_hard_v8g_s /
ot_hfd_coll_q3_hard_v8x with the actual parameters NLINK 2/3, VM_RT 3, TP 192, ROWS 256, AR_ITER 1).  Donor = Codex's
exact outer-wrapper probe elaboration (codex-hbm-bind-1355 probe_body/asbuilt.json, bind.py elab, top coll_exact_probe:
same two instances, same parameters, every terminal net / constant of the die top preserved), with the parents and
their bodies (ot_hfd_coll_q_hard_v8g_body / _body_s) elaborated and the coll leaves as library leaves.
Only the blackbox type of the two base top cells is replaced by the donor's elaborated parent module; the donor
modules they reach are copied.  Checks (fail closed): same hdlname as the base master, identical port names / widths /
directions, connections bit-identical under one consistent donor->base bit map (constants equal), the base cell's
parameters equal the donor's specialised parameter values, copied module names new to the base or with an identical
port signature and blackbox status, the base top's other cells / nets / ports and every other module byte-identical.
No logic, cycle or constant change.
usage: splice_coll.py BASE.json DONOR.json OUT.json RECEIPT.json [--top T] [--donor-top coll_exact_probe]"""
import argparse, copy, hashlib, json
from pathlib import Path

MASTERS = {"hb_coll_NE": "ot_hfd_coll_q2_hard_v8g_s", "hb_coll_NW": "ot_hfd_coll_q3_hard_v8x"}


def sha(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()


def sig(m):
    return {p: (v["direction"], len(v["bits"])) for p, v in m.get("ports", {}).items()}


def splice(B, D, top, dtop, insts=tuple(MASTERS), mutate=None):
    bt, dt = B["modules"][top], D["modules"][dtop]
    before = {k: sha(v) for k, v in B["modules"].items()}
    other_before = {k: sha(v) for k, v in bt["cells"].items() if k not in insts}
    nets_before, ports_before = sha(bt["netnames"]), sha(bt["ports"])
    copied, types, checked = set(), set(), {}
    for inst in insts:
        bc, dc = bt["cells"][inst], dt["cells"][inst]
        bm = B["modules"][bc["type"]]
        assert "blackbox" in bm.get("attributes", {}), (inst, "base cell is not a blackbox leaf")
        assert bc["type"] == MASTERS[inst], (inst, bc["type"])
        dtyp = dc["type"]; dm = D["modules"][dtyp]
        assert "blackbox" not in dm.get("attributes", {}) and dm.get("cells"), (inst, "donor body missing")
        assert dm.get("attributes", {}).get("hdlname") == MASTERS[inst], (inst, dm.get("attributes", {}).get("hdlname"))
        bdir = {p: v["direction"] for p, v in bm["ports"].items()}
        assert {p: (bdir[p], len(bs)) for p, bs in bc["connections"].items()} == sig(dm), (inst, "port signature differs")
        assert set(bc["connections"]) == set(dc["connections"]), inst
        m, nbits = {}, 0
        for p in bc["connections"]:
            xs, ys = bc["connections"][p], dc["connections"][p]
            assert len(xs) == len(ys), (inst, p)
            for x, y in zip(xs, ys):
                nbits += 1
                if isinstance(x, str) or isinstance(y, str):
                    assert x == y, (inst, p, "constant differs", x, y)
                else:
                    assert m.setdefault(y, x) == x, (inst, p, "donor bit maps to two base bits")
        assert len(set(m.values())) == len(m), (inst, "two donor bits map to one base bit")
        for k, v in bc.get("parameters", {}).items():
            dv = dm.get("parameter_default_values", {}).get(k)
            assert dv is not None and int(dv, 2) == int(v, 2), (inst, "parameter differs", k, v, dv)
        checked[inst] = dict(base_type=bc["type"], donor_type=dtyp, ports=len(bc["connections"]), bits=nbits,
                             parameters={k: int(v, 2) for k, v in bc.get("parameters", {}).items()})
        types.add(dtyp)
        bc["type"] = dtyp
        bc["parameters"] = {}
    todo = list(types)
    while todo:
        t = todo.pop()
        if t in copied:
            continue
        dm = D["modules"][t]
        if t in B["modules"] and t not in types:
            assert sig(B["modules"][t]) == sig(dm), (t, "existing module signature differs")
            assert ("blackbox" in B["modules"][t].get("attributes", {})) == ("blackbox" in dm.get("attributes", {})), t
            continue
        assert t not in B["modules"], (t, "name clash")
        B["modules"][t] = copy.deepcopy(dm); copied.add(t)
        for c in dm.get("cells", {}).values():
            if c["type"] in D["modules"]:
                todo.append(c["type"])
    if mutate:
        mutate(B)
    after = {k: sha(v) for k, v in B["modules"].items()}
    changed = sorted(k for k in before if before[k] != after[k])
    assert changed == [top], changed
    assert {k: sha(v) for k, v in bt["cells"].items() if k not in insts} == other_before
    assert sha(bt["netnames"]) == nets_before and sha(bt["ports"]) == ports_before
    return dict(schema="hbm.bind7.splice_coll.v1", instances=checked, new_types=sorted(types),
                copied_modules=sorted(copied), top_cells_changed=list(insts),
                other_top_cells_identical=len(other_before), other_modules_identical=len(before) - 1)


def main():
    ap = argparse.ArgumentParser()
    for x in ("base", "donor", "out", "receipt"):
        ap.add_argument(x, type=Path)
    ap.add_argument("--top", default="hbm_current_native_top")
    ap.add_argument("--donor-top", default="coll_exact_probe")
    a = ap.parse_args()
    raw_b, raw_d = a.base.read_bytes(), a.donor.read_bytes()
    B, D = json.loads(raw_b), json.loads(raw_d)
    rec = splice(B, D, a.top, a.donor_top)
    rec.update(base=str(a.base), base_sha256=hashlib.sha256(raw_b).hexdigest(), donor=str(a.donor),
               donor_sha256=hashlib.sha256(raw_d).hexdigest())
    txt = json.dumps(B)
    a.out.write_text(txt)
    rec["out_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    a.receipt.write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: v for k, v in rec.items() if k != "instances"})[:1500])


if __name__ == "__main__":
    main()
