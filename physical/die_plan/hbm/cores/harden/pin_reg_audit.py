"""CORE-HBM register-on-every-pin audit (OpenROAD python) on a synthesized / placed ODB.

    ODB=<1_synth.odb|...> OUT=<json> [SKIP_RE='^(clk|rst_n)$'] openroad -python -exit pin_reg_audit.py

For every signal port: an INPUT passes when its net reaches a flop D (any flop input pin except clock / async reset)
through at most 2 buffers/inverters and feeds NOTHING else (no logic before the register); an OUTPUT passes when it
is driven by a flop through at most 2 buffers/inverters.  Tie-driven outputs are listed separately (constants).
Output: {ports, bits, ok, unreg_in, unreg_out, const_out, unreg_in_buses{bus: n}, unreg_out_buses{bus: n}, cells, ffs}.
"""
import collections
import json
import os
import re

import odb  # noqa: E402

BUF = re.compile(r"^(BUF|INV|HB)")
CLKPIN = {"CLK", "CK", "SETN", "RESETN", "SN", "RN"}


def is_ff(m):
    return "DFF" in m or "DHL" in m or "DLL" in m or "SDF" in m


def main():
    db = odb.dbDatabase.create()
    db = odb.read_db(db, os.environ["ODB"])
    blk = db.getChip().getBlock()
    skip = re.compile(os.environ.get("SKIP_RE", r"^(clk|clk_[a-z0-9_]+|rst_n|arst_n|rst)$"))

    def fwd(net, depth):
        """(reaches_ff_D, feeds_logic)"""
        ok, logic = False, False
        for it in net.getITerms():
            mt = it.getMTerm()
            if mt.getIoType() != "INPUT":
                continue
            m = it.getInst().getMaster().getName()
            if is_ff(m):
                if mt.getName() in CLKPIN:
                    logic = True
                else:
                    ok = True
            elif BUF.match(m) and depth < 2:
                for o in it.getInst().getITerms():
                    if o.getMTerm().getIoType() == "OUTPUT" and o.getNet():
                        a, b = fwd(o.getNet(), depth + 1)
                        ok |= a
                        logic |= b
            else:
                logic = True
        return ok, logic

    def back(net, depth):
        for it in net.getITerms():
            if it.getMTerm().getIoType() != "OUTPUT":
                continue
            m = it.getInst().getMaster().getName()
            if is_ff(m):
                return "ff"
            if m.startswith("TIE"):
                return "const"
            if BUF.match(m) and depth < 2:
                for i in it.getInst().getITerms():
                    if i.getMTerm().getIoType() == "INPUT" and i.getNet():
                        return back(i.getNet(), depth + 1)
            return "logic"
        return "none"

    res = dict(bits=0, ok=0, unreg_in=0, unreg_out=0, const_out=0, unconnected=0)
    ub_in, ub_out = collections.Counter(), collections.Counter()
    for bt in blk.getBTerms():
        if bt.getSigType() != "SIGNAL" or skip.match(bt.getName()):
            continue
        res["bits"] += 1
        n = bt.getNet()
        bus = re.sub(r"\[\d+\]$", "", bt.getName())
        if n is None:
            res["unconnected"] += 1
            continue
        if bt.getIoType() == "INPUT":
            ok, logic = fwd(n, 0)
            if ok and not logic:
                res["ok"] += 1
            elif not ok and not logic and not n.getITerms():
                res["unconnected"] += 1
            else:
                res["unreg_in"] += 1
                ub_in[bus] += 1
        else:
            k = back(n, 0)
            if k == "ff":
                res["ok"] += 1
            elif k == "const":
                res["const_out"] += 1
            else:
                res["unreg_out"] += 1
                ub_out[bus] += 1
    ffs = sum(1 for i in blk.getInsts() if is_ff(i.getMaster().getName()))
    res.update(cells=len(blk.getInsts()), ffs=ffs, unreg_in_buses=dict(ub_in.most_common()),
               unreg_out_buses=dict(ub_out.most_common()),
               verdict="PASS" if res["unreg_in"] == 0 and res["unreg_out"] == 0 else "FAIL")
    json.dump(res, open(os.environ["OUT"], "w"), indent=1)
    print(f"PIN_REG_AUDIT {res['verdict']} bits {res['bits']} ok {res['ok']} unreg_in {res['unreg_in']} "
          f"unreg_out {res['unreg_out']} const_out {res['const_out']} unconnected {res['unconnected']} "
          f"cells {res['cells']} ffs {ffs}")


main()
