#!/usr/bin/env python3
"""W11 distributed VM, option H: the stream unit's per-op network rule, in Python, and its check.

rtl/hdc/v41x/ot_hdc_v41x_vec.sv (VMD_NG > 0) decides at set-up, from an op's fields and its layout, which
networks the op needs: the per-row scalar fetch (a BROADCAST stream), the permutation network (a gathered A),
the residual rotate network (a read stream that is neither local nor a broadcast), the rotate on the write
side (a non-local element write).  `rule` is that decision, line for line.  `truth` lays the op out as the
unit does (tools/rtl_hdc_v41x_vec_campaign.layout) and names, per class, the lanes whose element is not in the
lane's group.  The rule is SAFE when every op with a non-local access has the matching network flagged (an
unflagged non-local access would read through a network the op was never charged for); it is TIGHT to the
extent it flags nothing else.

    python3 tools/w11_vm_h.py [--n 1024 --m 256] [--align 128]   (prints the check on the reduced vehicle)
"""
from __future__ import annotations

import argparse
import collections
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I                    # noqa: E402
import rtl_hdc_v41x_vec_campaign as C      # noqa: E402

MK24 = (1 << 24) - 1


def phys_lanes(f, lay, oo, ii):
    """The physical lane of each live element of a vector: lane l takes element (o_v + l / S, i_v + l mod S)
    (ot_hdc_v41x_vec LAYOUT); dead lanes (i >= ni) are skipped by the layout's live mask, not compacted."""
    if len(oo) == 0:
        return np.zeros(0, dtype=np.int64)
    if lay["flat"]:
        g = oo * f["nin"] + ii
        return (g - g.min()).astype(np.int64)
    return ((oo - oo.min()) * lay["S"] + (ii - ii.min())).astype(np.int64)


def classify(f, N, M, ng=None):
    """Per class the RTL's decision: L local, B broadcast, R residual (rotate), G gathered."""
    ng = ng or N // 8
    lay = C.layout(f, N, M)
    ls, nsh = lay["ls"], lay["nsh"]
    S = 1 << ls
    s_no, s_ni = (1, f["nout"] * f["nin"]) if lay["flat"] else (f["nout"], f["nin"])
    mk = ng - 1

    def loc(base, so, si):
        return ((si == 1 or s_ni == 1) and (base & mk) == 0 and
                (s_no == 1 or ((((so - S) & MK24) & mk) == 0 if nsh != 0 else (so & mk) == 0)) and
                not (nsh == 0 and S < ng and s_ni > S))

    def bc(so, si):
        return si == 0 and (nsh == 0 or so == 0)

    cl = {}
    if f["asrc"] == I.SRC_VM:
        cl["A"] = "G" if f["aind"] else "B" if bc(f["aso"], f["asi"]) else \
            "L" if loc(f["abase"], f["aso"], f["asi"]) else "R"
    for s in "bd":
        if f[f"{s}src"] == I.SRC_VM:
            cl[s.upper()] = "B" if bc(f[f"{s}so"], f[f"{s}si"]) else \
                "R" if f["bhalf"] or not loc(f[f"{s}base"], f[f"{s}so"], f[f"{s}si"]) else "L"
    if f["csrc"] == I.SRC_VM:
        cl["C"] = "R" if f["cpair"] else "B" if bc(f["cso"], f["csi"]) else \
            "L" if loc(f["cbase"], f["cso"], f["csi"]) else "R"
    if f["aind"] == I.IND_I:
        cl["G"] = "L" if loc(f["aibase"], 0, 1) else "R"
    elif f["aind"] == I.IND_O:
        cl["G"] = "B" if bc(1, 0) else "R"
    if f["dst"] == I.DST_VM:
        cl["E"] = "L" if loc(f["obase"], f["oso"], f["osi"]) else "R"
    return cl


def rule(f, N, M, ng=None):
    """(b, g, r, w): broadcast read, gathered read, residual read, residual write -- the RTL's h_* flags."""
    cl = classify(f, N, M, ng)
    return (any(v == "B" for c, v in cl.items() if c != "E"), cl.get("A") == "G",
            any(v == "R" for c, v in cl.items() if c != "E"), cl.get("E") == "R")


def hold(flags, rot=17, gath=18, scal=8):
    b, g, r, w = flags
    return (scal if b else 0) + (gath if g else rot if r else 0) + (rot if w else 0)


def truth(f, vm, N, M, ng=None):
    """Per class: non-local lanes (a vector whose lanes all read one element is a broadcast, not counted),
    and the classes with a broadcast vector."""
    ng = ng or N // 8
    lay = C.layout(f, N, M)
    no, ni = f["nout"], f["nin"]
    idx = None
    if f["aind"]:
        cnt = ni if f["aind"] == I.IND_I else no
        idx = np.asarray(vm[f["aibase"]:f["aibase"] + cnt], dtype=np.int64)
    st = {}
    for s, name in zip("abcd", "ABCD"):
        if f[f"{s}src"] == I.SRC_VM:
            st[name] = C.addrs(f, s, no, ni, idx if s == "a" else None)
    if f["cpair"] and f["csrc"] == I.SRC_VM and "A" in st:
        st["C"] = st["A"] ^ 1
    if f["aind"]:
        o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
        st["G"] = (f["aibase"] + (i if f["aind"] == I.IND_I else o)).reshape(-1).astype(np.int64)
    if f["dst"] == I.DST_VM:
        st["E"] = C.out_addrs(f).astype(np.int64)
    rem, multi = collections.Counter(), collections.Counter()
    for oo, ii in lay["vecs"]:
        e = C.elem_index(f, oo, ii)
        lanes = phys_lanes(f, lay, oo, ii)
        for cls, a in st.items():
            x = a[e] & MK24
            if len(np.unique(x)) > 1:
                multi[cls] += 1               # a vector that is not one element for every lane
            rem[cls] += int(np.count_nonzero((x % ng) != (lanes % ng)))
    return rem, multi


def check(ops, N, M, ng=None):
    out = dict(ops=0, flagged=collections.Counter(), unsafe=[], residual_ops=0, flagged_any=0, over_flagged=0,
               hold_cycles=0, holds=collections.Counter())
    for k, (tag, f, vm) in enumerate(ops):
        if f["nout"] == 0 or f["nin"] == 0:
            continue
        lay = C.layout(f, N, M)
        if lay["bad"]:
            continue
        out["ops"] += 1
        cl = classify(f, N, M, ng)
        fl = rule(f, N, M, ng)
        b, g, r, w = fl
        rem, multi = truth(f, vm, N, M, ng)
        # a LOCAL class has no non-local lane; a BROADCAST class reads one element a vector
        bad = {c: v for c, v in cl.items() if (v == "L" and rem[c]) or (v == "B" and multi[c])}
        rd = any(rem[c] and cl.get(c) != "B" for c in "ABCDG")
        wr = bool(rem["E"])
        out["residual_ops"] += int(rd or wr)
        for nm, v in zip("bgrw", fl):
            out["flagged"][nm] += int(v)
        out["flagged_any"] += int(g or r or w)
        if bad:
            if len(out["unsafe"]) < 20:
                out["unsafe"].append(dict(op=k, tag=tag, classes=cl, remote={c: rem[c] for c in rem if rem[c]},
                                          multi={c: multi[c] for c in multi}))
            out.setdefault("unsafe_count", 0)
            out["unsafe_count"] = out.get("unsafe_count", 0) + 1
        if (g or r or w) and not (rd or wr):
            out["over_flagged"] += 1
        h = hold(fl)
        out["hold_cycles"] += h
        out["holds"][h] += 1
    out["unsafe_count"] = out.get("unsafe_count", 0)
    out["flagged"] = dict(out["flagged"])
    out["holds"] = {str(k): v for k, v in sorted(out["holds"].items())}
    return out


def vehicle_ops():
    recs, _, _, meta = C.vehicle_records()
    return [("vehicle", C.resolve(f0, dyn), np.asarray(vm, dtype=np.uint32)) for f0, dyn, vm, _ in recs], meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--m", type=int, default=256)
    a = ap.parse_args()
    ops, meta = vehicle_ops()
    r = check(ops, a.n, a.m)
    print(dict(meta=meta, align=os.environ.get("HDC_V41_VM_ALIGN", "32"), **r))


if __name__ == "__main__":
    main()
