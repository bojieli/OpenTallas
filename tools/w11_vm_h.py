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
import w11_vm_variant  # noqa: E402,F401  (VM-H / C_rotate sources and rules: rtl/w11crot)
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


class _ng:
    """Lay ops out with option H's rule for `ng` groups (rtl_hdc_v41x_vec_campaign.VMD_NG) inside the block."""

    def __init__(self, ng):
        self.ng = ng

    def __enter__(self):
        self.prev, C.VMD_NG = C.VMD_NG, self.ng

    def __exit__(self, *a):
        C.VMD_NG = self.prev


def layout_h(f, N, M, ng=None):
    with _ng(ng or N // 8):
        return C.layout(f, N, M)


def unpacked(f, N, M, ng=None):
    """Option H lays the op out one row a vector where the natural layout packs rows."""
    with _ng(0):
        n0 = C.layout(f, N, M)["nsh"]
    return layout_h(f, N, M, ng)["nsh"] != n0


def classify(f, N, M, ng=None):
    """Per class the RTL's decision on the H layout: L local, B broadcast (one element a vector), R one rotation
    a vector (the residual rotate), P the pair stream (C = A ^ 1: the rotate's xor-1 level), X anything else
    (gathered A, half streams, strides other than 0 / 1: the permutation network)."""
    ng = ng or N // 8
    lay = layout_h(f, N, M, ng)
    ls, nsh = lay["ls"], lay["nsh"]
    S = 1 << ls
    s_no, s_ni = (1, f["nout"] * f["nin"]) if lay["flat"] else (f["nout"], f["nin"])
    mk = ng - 1

    def unit(si):
        return si == 1 or s_ni == 1

    def fits(so):          # every row of a vector starts at the same rotation (or one row / one row a vector)
        return s_no == 1 or nsh == 0 or (((so - S) & MK24) & mk) == 0

    def loc(base, so, si):
        return unit(si) and (base & mk) == 0 and \
            (s_no == 1 or ((((so - S) & MK24) & mk) == 0 if nsh != 0 else (so & mk) == 0)) and \
            not (nsh == 0 and S < ng and s_ni > S)

    def bc(so, si):
        return si == 0 and (nsh == 0 or so == 0)

    def kind(base, so, si):
        if bc(so, si) and not unit(si):
            return "B"
        if loc(base, so, si):
            return "L"
        if bc(so, si):
            return "B"
        return "R" if unit(si) and fits(so) else "X"

    cl = {}
    if f["asrc"] == I.SRC_VM:
        cl["A"] = "X" if f["aind"] else kind(f["abase"], f["aso"], f["asi"])
    for s in "bd":
        if f[f"{s}src"] == I.SRC_VM:
            cl[s.upper()] = "X" if (f["bhalf"] and f[f"{s}si"] != 0) else \
                kind(f[f"{s}base"], f[f"{s}so"], f[f"{s}si"])
    if f["csrc"] == I.SRC_VM:
        cl["C"] = ("X" if cl.get("A") == "X" else "P") if f["cpair"] else kind(f["cbase"], f["cso"], f["csi"])
    if f["aind"] == I.IND_I:
        cl["G"] = kind(f["aibase"], 0, 1)
    elif f["aind"] == I.IND_O:
        cl["G"] = kind(f["aibase"], 1, 0)
    if f["dst"] == I.DST_VM:
        k = kind(f["obase"], f["oso"], f["osi"])
        cl["E"] = "X" if k == "B" else k        # a write of one element from many lanes: not a rotation
    return cl


def rule(f, N, M, ng=None):
    """(b, x, r, wr, wx): broadcast read, permutation read, rotate read (R / P), rotate write, permutation
    write -- the RTL's h_* flags."""
    cl = classify(f, N, M, ng)
    rd = [v for c, v in cl.items() if c != "E"]
    return ("B" in rd, "X" in rd, any(v in ("R", "P") for v in rd), cl.get("E") == "R", cl.get("E") == "X")


XI_ELEMS = 64         # elements a cycle through the class-X trees (ot_hdc_v41x_vec XI_ELEMS)


def xint(f, N, M, ng=None, flags=None):
    """Cycles between an op's vectors: an op with an X stream crosses the class-X trees XI_ELEMS a cycle."""
    fl = flags or rule(f, N, M, ng)
    if not (fl[1] or fl[4]):
        return 1
    lay = layout_h(f, N, M, ng)
    return max(1, -(-(1 << (lay["ls"] + lay["nsh"])) // XI_ELEMS))


def hold(flags, rot=17, gath=18, scal=8):
    b, x, r, wr, wx = flags
    return (scal if b else 0) + (gath if x else rot if r else 0) + (gath if wx else rot if wr else 0)


def truth(f, vm, N, M, ng=None, cl=None):
    """On the H layout, per class: non-local lanes, vectors that read more than one element (a broadcast
    class must read one), and vectors whose lanes do not all need one rotation (R) / one rotation then the
    pair swap (P) -- the rotate network could not serve them."""
    ng = ng or N // 8
    lay = layout_h(f, N, M, ng)
    cl = cl or {}
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
    rem, multi, norot = collections.Counter(), collections.Counter(), collections.Counter()
    for oo, ii in lay["vecs"]:
        e = C.elem_index(f, oo, ii)
        lanes = phys_lanes(f, lay, oo, ii)
        for cls, a in st.items():
            x = a[e] & MK24
            if len(np.unique(x)) > 1:
                multi[cls] += 1               # a vector that is not one element for every lane
            rem[cls] += int(np.count_nonzero((x % ng) != (lanes % ng)))
            if cl.get(cls) in ("R", "P"):
                g = (x % ng) ^ (1 if cl[cls] == "P" else 0)
                if len(np.unique((g - lanes) % ng)) > 1:
                    norot[cls] += 1
    return rem, multi, norot


def check(ops, N, M, ng=None):
    ng = ng or N // 8
    out = dict(ops=0, flagged=collections.Counter(), unsafe=[], unsafe_count=0, residual_ops=0, flagged_any=0,
               over_flagged=0, hold_cycles=0, holds=collections.Counter(), classes=collections.Counter(),
               unpacked_ops=0, vectors=0, vectors_packed=0, issue_cycles=0)
    for k, (tag, f, vm) in enumerate(ops):
        if f["nout"] == 0 or f["nin"] == 0:
            continue
        lay = layout_h(f, N, M, ng)
        with _ng(0):
            lay0 = C.layout(f, N, M)
        if lay["bad"]:
            continue
        out["ops"] += 1
        out["vectors"] += lay["nv"]
        out["issue_cycles"] += lay["nv"] * xint(f, N, M, ng)
        out["vectors_packed"] += lay0["nv"]
        out["unpacked_ops"] += int(lay["nsh"] != lay0["nsh"])
        cl = classify(f, N, M, ng)
        out["classes"].update(f"{c}{v}" for c, v in cl.items())
        fl = rule(f, N, M, ng)
        b, x, r, wr, wx = fl
        rem, multi, norot = truth(f, vm, N, M, ng, cl)
        # LOCAL: no non-local lane; BROADCAST: one element a vector; R / P: one rotation a vector
        bad = {c: v for c, v in cl.items()
               if (v == "L" and rem[c]) or (v == "B" and multi[c]) or (v in ("R", "P") and norot[c])}
        rd = any(rem[c] and cl.get(c) != "B" for c in "ABCDG")
        wrem = bool(rem["E"])
        out["residual_ops"] += int(rd or wrem)
        for nm, v in zip(("b", "x", "r", "wr", "wx"), fl):
            out["flagged"][nm] += int(v)
        net = x or r or wr or wx
        out["flagged_any"] += int(net)
        if bad:
            out["unsafe_count"] += 1
            if len(out["unsafe"]) < 20:
                out["unsafe"].append(dict(op=k, tag=tag, classes=cl, remote={c: rem[c] for c in rem if rem[c]},
                                          multi=dict(multi), norot=dict(norot)))
        if net and not (rd or wrem):
            out["over_flagged"] += 1
        h = hold(fl)
        out["hold_cycles"] += h
        out["holds"][h] += 1
    out["flagged"] = dict(out["flagged"])
    out["classes"] = dict(out["classes"])
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
