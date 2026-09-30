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


def rule(f, N, M, ng=None):
    """(b, g, r, w): broadcast read, gathered read, residual read, residual write -- the RTL's h_* flags."""
    ng = ng or N // 8
    lay = C.layout(f, N, M)
    ls, nsh = lay["ls"], lay["nsh"]
    S = 1 << ls
    if lay["flat"]:
        s_no, s_ni = 1, f["nout"] * f["nin"]
    else:
        s_no, s_ni = f["nout"], f["nin"]
    mk = ng - 1

    def loc(base, so, si):
        return (si == 1 and (base & mk) == 0 and
                ((((so - S) & MK24) & mk) == 0 if nsh != 0 else (s_no == 1 or (so & mk) == 0)) and
                not (nsh == 0 and S < ng and s_ni > S))

    def bc(so, si):
        return si == 0 and (nsh == 0 or so == 0)

    b = g = r = w = False
    if f["asrc"] == I.SRC_VM:
        if f["aind"]:
            g = True
        elif bc(f["aso"], f["asi"]):
            b = True
        elif not loc(f["abase"], f["aso"], f["asi"]):
            r = True
    for s in "bd":
        if f[f"{s}src"] == I.SRC_VM:
            if bc(f[f"{s}so"], f[f"{s}si"]):
                b = True
            elif f["bhalf"] or not loc(f[f"{s}base"], f[f"{s}so"], f[f"{s}si"]):
                r = True
    if f["csrc"] == I.SRC_VM:
        if f["cpair"]:
            r = True
        elif bc(f["cso"], f["csi"]):
            b = True
        elif not loc(f["cbase"], f["cso"], f["csi"]):
            r = True
    if f["aind"] == I.IND_I:
        if not loc(f["aibase"], 0, 1):
            r = True
    elif f["aind"] == I.IND_O:
        if bc(1, 0):
            b = True
        else:
            r = True
    if f["dst"] == I.DST_VM and not loc(f["obase"], f["oso"], f["osi"]):
        w = True
    return b, g, r, w


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
    rem, bcv = collections.Counter(), set()
    for oo, ii in lay["vecs"]:
        e = C.elem_index(f, oo, ii)
        lanes = np.arange(len(e))
        for cls, a in st.items():
            x = a[e] & MK24
            if len(x) > 1 and len(np.unique(x)) == 1:
                bcv.add(cls)
                continue
            rem[cls] += int(np.count_nonzero((x % ng) != (lanes % ng)))
    return rem, bcv


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
        fl = rule(f, N, M, ng)
        b, g, r, w = fl
        rem, bcv = truth(f, vm, N, M, ng)
        rd = any(rem[c] for c in "ABCDG")
        wr = bool(rem["E"])
        out["residual_ops"] += int(rd or wr)
        for nm, v in zip("bgrw", fl):
            out["flagged"][nm] += int(v)
        out["flagged_any"] += int(g or r or w)
        if (rd and not (g or r)) or (wr and not w):
            if len(out["unsafe"]) < 20:
                out["unsafe"].append(dict(op=k, tag=tag, remote={c: rem[c] for c in rem if rem[c]}, flags=fl))
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
