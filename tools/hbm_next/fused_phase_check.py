#!/usr/bin/env python3
"""HBM-NEXT FUSED bank-phase image check (LH-P3UNITS/FUSHUB 2026-10-19; DECISION LEAD-HBM/LH-P3UNITS: the compiler
allocator bank-aligns FUSED HC_PRE_NORM operands, ph = 0, so the die's fixed neighbour-hop csum tree is exactly the
golden chunk8 reduction order; no runtime reorder).

Every FUSED.HC_PRE_NORM / FUSED.HC_POST record of an HGI-1R image must satisfy what the RTL hub
(ot_hnx_fused_hub job_ok, rtl/hbm_next/fused/ot_hnx_fused_tree.sv) accepts; otherwise the record FAULTs on the die:

  F1 space    A, O (and B) in VM; C in VM.  HC_PRE_NORM's gain B is read by the lanes from VM (an HBM gain needs a
              DMA.LOAD to VM first).
  F2 lane-local  word addresses of A / B / O sector aligned (x 8) and at ONE bank phase ph = addr[7:3]; row strides
              rs_A / rs_B / rs_O multiples of 256 words (a row stays on its lane's bank); C and rs_C multiples of 8.
  F3 PHASE    HC_PRE_NORM: ph = 0 (A, B, O at word addresses = 0 mod 256).  The 32 chunk sums of a block meet in the
              fixed tree pair (lane 2c, 2c + 1) -> groups -> quadrants -> hub; chunk u is lane (u + ph) mod 32, so only
              ph = 0 is the golden pairing.  HC_POST has no cross-lane reduction: ph is free (F2 still binds).
  F4 gain     HC_PRE_NORM: rs_B = 0 (one gain vector broadcast to every row).

    PYTHONPATH=tools python3 tools/hbm_next/fused_phase_check.py --img X.hgi1r [--img ...] [--dir D (every *.hgi1r)]
    PYTHONPATH=tools python3 tools/hbm_next/fused_phase_check.py --selftest     (synthetic records; mutants must FAIL)
Exit 0 only when every FUSED record passes (and, with --selftest, every mutant fails).
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hbm_next"))

import isa_rows as IR  # noqa: E402
from hgi_sim import records as RC  # noqa: E402

FUSED_OPS = ("HC_PRE_NORM", "HC_POST")


def phase(w):
    return (w >> 3) & 31


def check_fused(r, rx):
    """violations of one FUSED HC record: [(rule, msg)]"""
    if r.unit != "FUSED" or r.op not in FUSED_OPS:
        return []
    V = []
    pre = r.op == "HC_PRE_NORM"
    rs = (rx.rs if rx is not None else {}) or {}
    D = {k: r.desc.get(k) for k in "ABCO"}
    for k, d in D.items():
        if d is None or d.space != "VM":
            V.append(("F1", f"{k} in {getattr(d, 'space', 'absent')}, not VM"))
    lane = [k for k in "ABO" if D[k] is not None and D[k].space == "VM"]
    for k in lane:
        if D[k].base % 8:
            V.append(("F2", f"{k} word {D[k].base} not sector aligned"))
        if rs.get(k, 0) % 256:
            V.append(("F2", f"rs_{k} {rs.get(k, 0)} not a multiple of 256 words"))
    phs = {k: phase(D[k].base) for k in lane}
    if len(set(phs.values())) > 1:
        V.append(("F2", f"bank phases differ {phs} (lane-local rule: one phase)"))
    if D["C"] is not None and D["C"].space == "VM" and (D["C"].base % 8 or rs.get("C", 0) % 8):
        V.append(("F2", f"C word {D['C'].base} / rs_C {rs.get('C', 0)} not sector aligned"))
    if pre:
        bad = {k: p for k, p in phs.items() if p != 0}
        if bad:
            V.append(("F3", f"HC_PRE_NORM bank phase {bad} != 0 (fixed csum tree = golden order only at ph = 0)"))
        if rs.get("B", 0) != 0:
            V.append(("F4", f"HC_PRE_NORM rs_B {rs.get('B')} != 0 (gain is a broadcast)"))
    return V


def decode_all(img: bytes):
    out, off = [], 0
    while off < len(img):
        r, rx, nxt = IR.decode_one(img, off)
        out.append((off, r, rx))
        off = nxt
    return out


def check_image(path: Path):
    img = path.read_bytes()
    recs = decode_all(img)
    viol, n = [], 0
    for off, r, rx in recs:
        if r.unit == "FUSED" and r.op in FUSED_OPS:
            n += 1
            for rule, msg in check_fused(r, rx):
                viol.append(dict(offset=off, op=f"{r.unit}.{r.op}", rule=rule, msg=msg))
    return dict(image=str(path), sha256=hashlib.sha256(img).hexdigest(), records=len(recs), fused=n,
                PASS=not viol, n_violations=len(viol),
                by_rule={k: sum(1 for v in viol if v["rule"] == k) for k in ("F1", "F2", "F3", "F4")},
                violations=viol[:12])


def selftest():
    MD = RC.MDesc
    D = 5120

    def pre(ph=0):
        o = 8 * ph
        r = RC.Rec("FUSED", "HC_PRE_NORM", desc=dict(A=MD(space="VM", base=0 + o, n=4 * D, m=1),
                                                     B=MD(space="VM", base=131072 + o, n=D, m=1),
                                                     C=MD(space="VM", base=196608, n=4, m=1),
                                                     O=MD(space="VM", base=163840 + o, n=D, m=1)))
        return r, IR.RowX(n=4, rs=dict(A=4 * D, C=8, O=D))

    def post(ph=0):
        o = 8 * ph
        r = RC.Rec("FUSED", "HC_POST", desc=dict(A=MD(space="VM", base=0 + o, n=D, m=1),
                                                 B=MD(space="VM", base=32768 + o, n=4 * D, m=1),
                                                 C=MD(space="VM", base=327680, n=20, m=1),
                                                 O=MD(space="VM", base=196608 + o, n=4 * D, m=1)))
        return r, IR.RowX(n=4, rs=dict(A=D, B=4 * D, C=24, O=4 * D))

    def mut(fn, base):
        r, rx = base
        r = copy.copy(r)
        r.desc = {k: copy.copy(d) for k, d in r.desc.items()}
        rx = copy.deepcopy(rx)
        fn(r, rx)
        return r, rx

    def b_hbm(r, rx):
        r.desc["B"].space = "HBM"

    def o_off(r, rx):
        r.desc["O"].base += 48                          # O at another bank phase than A

    def c_mis(r, rx):
        r.desc["C"].base += 4

    def rs_mis(r, rx):
        rx.rs["A"] += 8

    def rsb(r, rx):
        rx.rs["B"] = 256
    cases = {
        "pre_ph0": (pre(0), True), "post_ph0": (post(0), True), "post_ph5": (post(5), True),
        "pre_ph3": (pre(3), False), "pre_ph1": (pre(1), False),
        "pre_gain_hbm": (mut(b_hbm, pre(0)), False), "pre_o_phase": (mut(o_off, pre(0)), False),
        "post_o_phase": (mut(o_off, post(0)), False), "post_c_unaligned": (mut(c_mis, post(0)), False),
        "pre_rsA_8": (mut(rs_mis, pre(0)), False), "pre_rsB_nonzero": (mut(rsb, pre(0)), False),
    }
    out, ok = {}, True
    for name, ((r, rx), want) in cases.items():
        # round-trip through the binary encoding, as an image record
        r2, rx2, _ = IR.decode_one(IR.encode(r, rx), 0)
        V = check_fused(r2, rx2)
        good = (not V) == want
        ok &= good
        out[name] = dict(expect="PASS" if want else "FAIL", got="PASS" if not V else "FAIL",
                         rules=sorted({v[0] for v in V}), ok=good)
        print(f"selftest {name:18s} expect {'PASS' if want else 'FAIL'} got {'PASS' if not V else 'FAIL'} "
              f"{sorted({v[0] for v in V})} {'ok' if good else 'WRONG'}")
    return ok, out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--img", type=Path, action="append", default=[])
    ap.add_argument("--dir", type=Path, action="append", default=[])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    res = dict(schema="opentallas.hbm_next_1019.fused_phase_check.v1", generated_utc=datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rule=__doc__, isa_version=IR.VERSION, images={})
    ok = True
    if a.selftest:
        st_ok, st = selftest()
        res["selftest"] = dict(PASS=st_ok, cases=st)
        ok &= st_ok
    imgs = list(a.img) + [p for d in a.dir for p in sorted(d.glob("*.hgi1r"))]
    for p in imgs:
        e = check_image(p)
        res["images"][str(p)] = e
        ok &= e["PASS"]
        print(f"{p}: {'PASS' if e['PASS'] else 'FAIL'} fused {e['fused']} violations {e['n_violations']} {e['by_rule']}"
              + (f" first {e['violations'][0]}" if e["violations"] else ""))
    res["PASS"] = ok
    res["sources_sha256"] = {p: hashlib.sha256((TOOLS.parent / p).read_bytes()).hexdigest()
                             for p in ("tools/hbm_next/fused_phase_check.py", "tools/hbm_next/isa_rows.py")
                             if (TOOLS.parent / p).exists()}
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=1, default=str) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
