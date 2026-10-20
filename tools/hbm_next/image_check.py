#!/usr/bin/env python3
"""HBM-NEXT-CMTP: static checker for the WHOLE-TOKEN HGI-1R IMAGE form (emitter.py --whole output).

static_check.py proves the compiled programme's S2 timeline (C1-C5).  The image adds data-dependent spans and a
token-wide VM map; this checker reads the image bytes (+ its emitter.json) and FAILS on any of:

  I1 decode     every record decodes, re-encodes byte-identical, and is legal (isa_rows.check).
  I2 frame      exactly one CTL.END, last; users images start with CTL.USERS; MTP ends CTL.ACCEPT -> CTL.TOKX -> END,
                users / AR end CTL.TOKX -> END; no record after END.
  I3 union      CTL.LOOP / ENDLOOP balanced, never nested.  Every VM-count loop (param [17]) reads its count at the
                D[0] word of the LAST IDX.UNION before it in the same segment, and no record between them writes that
                word.  The bound is structural: the IDX.UNION takes A = N rows x 6 ids, so U <= 6 N (and <= E), and
                its list O and row table R hold >= 6 N entries -- the loop can never run past the tables, and the
                calendar reserves U_max = 6 N iterations (plane_compiler meas --union-bound prices that).  Every loop
                body record is rsel = 1 with rtab = that IDX.UNION's R, ROWX n = N.
  I4 ATT plan   every IDX.KVUNION: line budget param [24:16] = ATT_BUDGET (128) <= 256, lanes NL <= P, R holds 32 SM
                blocks of PLAN_WORDS.  Every plan-mode ATT record (rsel = 1, rtab = a KVUNION's R) follows that
                KVUNION in the same segment.  The static span = fixed + budget beats (a plan over budget = E_RANGE).
  I5 VM bounds  every VM operand's rows (base + r x rs, r < N, + its descriptor extent) stay below 2^19 words.
  I6 one map    emitter.json token: every compiled record emitted (0 emit errors), no live-ins, every pinned interval at one base in every segment, no host-preloaded
                word; aux tables inside 2^19 and disjoint.
  I7 FUSED      native FUSED bank-phase, operand-space, alignment and gain-broadcast rules (F1-F4).

    PYTHONPATH=tools python3 tools/hbm_next/image_check.py --dir results/arch/hbm_next_1019/cmtp/emitter/whole/mtp_N6
    PYTHONPATH=tools python3 tools/hbm_next/image_check.py --selftest DIR      (mutants must FAIL)
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
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hbm_next"))

import isa_rows as IR  # noqa: E402
from fused_phase_check import check_fused  # noqa: E402

VM_LIMIT = 1 << 19
ATT_BUDGET = 128
TOPK = 6
EXPERTS = 384


def decode_all(img: bytes):
    out, off = [], 0
    while off < len(img):
        r, rx, nxt = IR.decode_one(img, off)
        out.append((off, r, rx, img[off:nxt]))
        off = nxt
    return out


def seg_of(table, off):
    seg = None
    for t in table:
        if t["offset"] <= off:
            seg = t["segment"]
    return seg


def vm_extent(d, rows, rs):
    """highest VM word + 1 an operand touches over its rows (row r at base + r rs; a negative rs counts too)"""
    span = d.n if d.m <= 1 else (d.m - 1) * d.stride + d.n
    lo = min(d.base, d.base + (rows - 1) * rs)
    hi = max(d.base, d.base + (rows - 1) * rs) + span
    return lo, hi


def check_image(recs, table, meta, mode, N, P=4):
    V = []

    def bad(kind, at, msg):
        V.append(dict(check=kind, offset=at, segment=seg_of(table, at), msg=msg))

    # I1 decode / legality
    for off, r, rx, b in recs:
        try:
            if IR.encode(r, rx) != b:
                bad("I1", off, f"{r.unit}.{r.op} re-encode differs")
            IR.check(r, rx)
        except Exception as e:                                           # noqa: BLE001
            bad("I1", off, f"{r.unit}.{r.op}: {type(e).__name__}: {e}"[:200])
        for rule, msg in check_fused(r, rx):
            bad("I7", off, f"{r.unit}.{r.op} {rule}: {msg}")
    # I2 frame
    ends = [n for n, (_, r, _, _) in enumerate(recs) if r.unit == "CTL" and r.op == "END"]
    if ends != [len(recs) - 1]:
        bad("I2", recs[ends[0]][0] if ends else 0, f"CTL.END at {ends}, records {len(recs)}")
    tail = [f"{r.unit}.{r.op}" for _, r, _, _ in recs[-3:]]
    want = ["CTL.ACCEPT", "CTL.TOKX", "CTL.END"] if mode == "mtp" else ["CTL.TOKX", "CTL.END"]
    if tail[-len(want):] != want:
        bad("I2", recs[-1][0], f"tail {tail} != {want}")
    if mode == "mu" and not (recs[0][1].unit == "CTL" and recs[0][1].op == "USERS"):
        bad("I2", 0, "users image does not start with CTL.USERS")
    # I3 union loops / I4 ATT plan / I5 VM bounds
    loops, plans = [], {}
    cur_seg, last_union, open_loop = None, None, None
    for n, (off, r, rx, _) in enumerate(recs):
        sg = seg_of(table, off)
        if sg != cur_seg:
            cur_seg, last_union, plans_seg = sg, None, set()
            if open_loop is not None:
                bad("I3", off, "CTL.LOOP open across a segment boundary")
                open_loop = None
            plans = {}
        rows = rx.n if rx is not None else 1
        for k, d in r.desc.items():
            if d.space == "VM":
                lo, hi = vm_extent(d, rows, (rx.rs.get(k, 0) if rx is not None else 0))
                if lo < 0 or hi > VM_LIMIT:
                    bad("I5", off, f"{r.unit}.{r.op} {k} VM [{lo}, {hi}) outside 2^19")
        if r.unit == "IDX" and r.op == "UNION":
            A, O, D, R = (r.desc.get(k) for k in "AODR")
            cap = A.n * max(1, A.m) if A is not None else 0
            if A is None or A.n != TOPK or max(1, A.m) != N:
                bad("I3", off, f"IDX.UNION A {A and (A.n, A.m)} != {TOPK} ids x N {N} rows")
            if O is None or O.n < min(cap, EXPERTS):
                bad("I3", off, f"IDX.UNION list O.n {O and O.n} < U_max {cap}")
            if R is None or max(1, R.m) < min(cap, EXPERTS) or R.n < IR.TABLE_ROW_WORDS:
                bad("I3", off, f"IDX.UNION row table R {R and (R.n, R.m)} < U_max {cap} rows")
            last_union = dict(off=off, count=D.base if D is not None else None, tab=R.base if R is not None else None,
                              umax=min(cap, EXPERTS), clobbered=False)
            continue
        if last_union is not None and last_union["count"] is not None:
            for k, d in r.desc.items():
                wd = r.unit == "IDX" and (r.op in ("UNION", "KVUNION") or (r.op == "INDEX" and (r.param >> 12) & 1))
                if d.space == "VM" and (k in ("O", "R") or (k == "D" and wd)):
                    lo, hi = vm_extent(d, rows, (rx.rs.get(k, 0) if rx is not None else 0))
                    if lo <= last_union["count"] < hi:
                        last_union["clobbered"] = True
        if r.unit == "CTL" and r.op == "LOOP":
            if open_loop is not None:
                bad("I3", off, "nested CTL.LOOP")
            open_loop = dict(off=off, vm=bool(r.param & (1 << 17)), imm_a=r.imm_a, body=0)
            if open_loop["vm"]:
                if last_union is None:
                    bad("I3", off, "VM-count CTL.LOOP with no IDX.UNION before it in the segment")
                elif r.imm_a != last_union["count"]:
                    bad("I3", off, f"CTL.LOOP count word {r.imm_a} != IDX.UNION D[0] {last_union['count']}")
                elif last_union["clobbered"]:
                    bad("I3", off, "the union count word is overwritten between IDX.UNION and CTL.LOOP")
                open_loop["umax"] = last_union["umax"] if last_union else None
            continue
        if r.unit == "CTL" and r.op == "ENDLOOP":
            if open_loop is None:
                bad("I3", off, "CTL.ENDLOOP without CTL.LOOP")
            else:
                if open_loop["body"] == 0:
                    bad("I3", off, "empty CTL.LOOP body")
                loops.append(dict(segment=cur_seg, offset=open_loop["off"], body=open_loop["body"],
                                  u_max=open_loop.get("umax")))
            open_loop = None
            continue
        if open_loop is not None:
            open_loop["body"] += 1
            if open_loop["vm"]:
                if rx is None or rx.rsel != 1 or rx.n != N or last_union is None or rx.rtab != last_union["tab"]:
                    bad("I3", off, f"loop body {r.unit}.{r.op}: rsel {rx and rx.rsel} n {rx and rx.n} rtab "
                                   f"{rx and rx.rtab} != IDX.UNION R {last_union and last_union['tab']}")
        if r.unit == "IDX" and r.op == "KVUNION":
            bud, nl = (r.param >> 16) & 0x1FF, (r.param & 0xF) + 1
            R = r.desc.get("R")
            if bud != ATT_BUDGET or bud > 256:
                bad("I4", off, f"KVUNION line budget {bud} != {ATT_BUDGET}")
            if nl > P:
                bad("I4", off, f"KVUNION lanes {nl} > P {P}")
            if R is None or R.n * max(1, R.m) < IR.NSM_ATT * IR.PLAN_WORDS:
                bad("I4", off, f"KVUNION plan R {R and (R.n, R.m)} < {IR.NSM_ATT} x {IR.PLAN_WORDS}")
            else:
                plans[R.base] = off
            continue
        if r.unit == "ATT" and rx is not None and rx.rsel == 1:
            if rx.rtab not in plans:
                bad("I4", off, f"plan-mode ATT.{r.op} rtab {rx.rtab} has no IDX.KVUNION before it in the segment")
    if open_loop is not None:
        bad("I3", open_loop["off"], "CTL.LOOP never closed")
    # I6 one map
    tok = meta.get("token", {})
    nerr = sum(len(sg.get("errors") or ()) for sg in meta.get("segments", {}).values())
    if nerr or tok.get("errors"):
        bad("I6", 0, f"{nerr} records failed to emit (missing from the image)")
    if tok.get("liveins"):
        bad("I6", 0, f"live-ins {list(tok['liveins'])}")
    if not tok.get("pinned_one_base", False):
        bad("I6", 0, f"pinned intervals not at one base: {tok.get('pinned_bases')}")
    if tok.get("host_preloaded"):
        bad("I6", 0, f"host-preloaded words {tok['host_preloaded'][:4]}")
    for k, s in meta.get("segments", {}).items():
        items = sorted((a, a + w, nm) for nm, (a, w) in (s.get("aux") or {}).items())
        for (a0, b0, n0), (a1, b1, n1) in zip(items, items[1:]):
            if a1 < b0:
                bad("I6", 0, f"segment {k}: aux {n0} [{a0}, {b0}) overlaps {n1}")
        if items and items[-1][1] > VM_LIMIT:
            bad("I6", 0, f"segment {k}: aux top {items[-1][1]} > 2^19")
    return V, loops


def run_dir(d: Path):
    meta = json.loads((d / "emitter.json").read_text())
    img = (d / meta["token"]["image"]).read_bytes()
    recs = decode_all(img)
    V, loops = check_image(recs, meta["token"]["segments"], meta, meta["mode"], meta["N"], meta.get("P", 4))
    return meta, img, recs, V, loops


def mutants(recs, meta):
    """witnesses: each mutant must FAIL the checker"""
    out = {}

    def remake(fn):
        rs = [list(x) for x in recs]
        fn(rs)
        img = b"".join(IR.encode(r, rx) for _, r, rx, _ in rs)
        return decode_all(img)
    ix = lambda op: next(n for n, (_, r, _, _) in enumerate(recs) if f"{r.unit}.{r.op}" == op)

    def m_loopcount(rs):                                  # the loop reads the wrong count word
        n = ix("CTL.LOOP")
        r = copy.copy(rs[n][1])
        r.imm_a += 1
        rs[n][1] = r

    def m_budget(rs):                                     # KVUNION plans more than the calendar reserved
        n = ix("IDX.KVUNION")
        r = copy.copy(rs[n][1])
        r.param = (r.param & ~(0x1FF << 16)) | (256 << 16)
        rs[n][1] = r

    def m_rtab(rs):                                       # a loop body record points at another table
        n = ix("CTL.LOOP") + 1
        rx = copy.deepcopy(rs[n][2])
        rx.rtab += 32
        rs[n][2] = rx

    def m_noend(rs):                                      # the END is lost
        rs.pop()

    def m_vm(rs):                                         # a VM operand pushed past 2^19
        n = ix("CTL.LOOP") + 1
        r = copy.copy(rs[n][1])
        r.desc = {k: copy.copy(d) for k, d in r.desc.items()}
        k = next(k for k, d in r.desc.items() if d.space == "VM")
        r.desc[k].base = VM_LIMIT - 4
        rs[n][1] = r
    for name, fn in (("loop_count_word", m_loopcount), ("kv_budget_256", m_budget), ("loop_rtab", m_rtab),
                     ("no_end", m_noend), ("vm_past_2p19", m_vm)):
        try:
            rr = remake(fn)
            # segment table offsets shift with sizes: rebuild by record index ratio (sizes are unchanged except noend)
            V, _ = check_image(rr, meta["token"]["segments"], meta, meta["mode"], meta["N"], meta.get("P", 4))
            # A pre-existing FUSED failure cannot witness an unrelated mutant.
            expected = {"loop_count_word": "I3", "kv_budget_256": "I4", "loop_rtab": "I3",
                        "no_end": "I2", "vm_past_2p19": "I5"}[name]
            matched = [v for v in V if v["check"] == expected]
            out[name] = dict(fails=bool(matched), expected_check=expected,
                             first=matched[0] if matched else None)
        except StopIteration:
            out[name] = dict(fails=None, note="record kind absent in this image")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, action="append", required=True, help="emitter --whole output dir(s)")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    res = dict(schema="opentallas.hbm_next_1019.cmtp.image_check.v1", generated_utc=datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rule=__doc__, isa_version=IR.VERSION, images={})
    ok = True
    for d in a.dir:
        meta, img, recs, V, loops = run_dir(d)
        ent = dict(image=meta["token"]["image"], sha256=hashlib.sha256(img).hexdigest(), records=len(recs),
                   mode=meta["mode"], N=meta["N"], PASS=not V, violations=V[:20], n_violations=len(V),
                   union_loops=len(loops), union_u_max=sorted({x["u_max"] for x in loops if x["u_max"]}),
                   kvunion=sum(1 for _, r, _, _ in recs if r.unit == "IDX" and r.op == "KVUNION"),
                   carried=meta.get("carried", {}).get("pinned"))
        if a.selftest:
            ent["mutants"] = mutants(recs, meta)
            ent["mutants_all_fail"] = all(m["fails"] in (True, None) for m in ent["mutants"].values())
            ok &= ent["mutants_all_fail"]
        ok &= ent["PASS"]
        res["images"][d.name] = ent
        print(d.name, "PASS" if ent["PASS"] else f"FAIL {len(V)}: {V[:2]}", f"loops {len(loops)} U_max "
              f"{ent['union_u_max']} kvunion {ent['kvunion']}",
              ("mutants " + json.dumps({k: v["fails"] for k, v in ent.get("mutants", {}).items()})), flush=True)
    res["PASS"] = ok
    res["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                             for p in ("tools/hbm_next/image_check.py", "tools/hbm_next/isa_rows.py",
                                       "tools/hbm_next/fused_phase_check.py")}
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=1, default=str) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
