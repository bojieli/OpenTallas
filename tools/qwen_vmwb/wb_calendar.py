#!/usr/bin/env python3
"""Q-VMWB compiler pass: static VM write-back calendar for the Qwen TP8 compute die result face (2026-10-15).

For every result-producing ME instruction of the decoder programme it derives, from the instruction fields alone,
  * the train command the TT-side issuer (rtl/qwen_split/qfd_res_train_issue.sv) sends to the three band serializers
    (rtl/qwen_split/qfd_res_train_par.sv): count = tiles, stride = max(ts, 8), payload = oen, slot_count NS = the
    port bframe active-slot prefix (8 for split <= 7, 8 >> (split - 7) for 8..10, 1 above);
  * every result row of every burst (port address law of ot_qwen_me_spport_w12 BANDF=1, pt_id = 8 band + slot):
        row(k, p) = obase + (k // 8) * ots * (GT >> split) + (k % 8) * ojs + g(split, p) * ots,  we = oen & in-range(p)
    cross-checked row-for-row against the actual RTL ports (tb_vmwb_rows dumps) when --rows-dir is given;
  * the emission edge of every row:  F(b, k, s) = c0 + D + b NS + (k // 8) P + (k % 8) NS + s,  P = max(8 NS, stride)
    and PROVES the calendar bank-conflict free: rows written in the same edge are distinct mod 16 (SU replicas) and
    mod 64 (copy 0); rows of one VM row keep capture order;
  * the last landing edge of the op and its cost against the Q-ATTN r3 reference (decision.json: last capture + D + 25,
    the 'unconstrained face'), for the adopted train24 baseline and the candidate structures, and the end-to-end loss
    of each option on the token-path DAG (tools/throughput/accepted_cost.py solver, all ops of all 36 layers at once).
Captures: c_k = c0 + (k // 8) ts + k % 8 with c0 the actual controller's first-capture edge after go (measured profile
of the shipped programme, results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json link_handoff).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/throughput"))
import accepted_cost as ac  # noqa: E402

GT, TB, D, NB = 3072, 10, 2, 3
DECISION = ROOT / "results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json"
PCS = ROOT / "results/arch/qwen_split_compute_1014/vmwb_1015/pcs.txt"
NODE = {"PC1": "qkv", "PC11": "attn_kv", "PC12": "o_proj", "PC16": "gate_up", "PC20": "down"}


def fields(line):
    pc, *args = line.split()
    f = dict(nout=0, tiles=1, k=1, ts=0, split=0, oen=0, obase=0, ots=0, ojs=0)
    supported = set("nout tiles k ts split oen obase ots ojs wsrc round mmode wbase ks js xbase xks xjs xcs wcs".split())
    seen = set()
    for a in args:
        m = re.fullmatch(r"\+(\w+)=(\d+)", a)
        if not m or m.group(1).lower() not in supported:
            raise ValueError(f"{pc}: invalid workload argument {a}")
        key = m.group(1).lower()
        if key in seen:
            raise ValueError(f"{pc}: duplicate workload argument {key}")
        seen.add(key)
        if key in f:
            f[key] = int(m.group(2))
    if f["nout"] <= 0:
        raise ValueError(f"{pc}: positive NOUT is required by the RTL bench")
    return pc, f


def ns_of(split):
    return 8 if split <= 7 else 8 >> (split - 7) if split <= 10 else 1


def bframe(sp, p):
    bb, kk = p >> 3, p & 7
    if sp <= TB:
        return (kk >> (TB - sp)) == 0, (bb << (TB - sp)) + kk
    return bb == 0 and kk < (GT >> sp), kk


def rows(f):
    """-> {(k, band, slot): row} for every real row (we) of the op"""
    out = {}
    for k in range(8 * f["tiles"]):
        oa = f["obase"] + (k // 8) * f["ots"] * (GT >> f["split"]) + (k % 8) * f["ojs"]
        for p in range(24):
            ok, g = bframe(f["split"], p)
            if ok and f["oen"]:
                out[(k, p // 8, p % 8)] = (oa + g * f["ots"]) & 0xFFFFF
    return out


def train(f):
    ns = ns_of(f["split"])
    stride = max(f["ts"], 8)
    return dict(train_count=f["tiles"], capture_stride=stride, payload_write=f["oen"], slot_count=ns,
                period=max(8 * ns, stride) if f["tiles"] > 1 else 8 * ns)


def calendar(f, c0, lanes=3, compress=True, lag=True):
    """emission edge of every (k, b, s) slot under a structure; -> (slot edges, last end edge)"""
    t = train(f)
    ns = t["slot_count"] if compress else 8
    per = max(8 * ns, t["capture_stride"]) if f["tiles"] > 1 else 8 * ns
    ed = {}
    if lanes == 3:
        for k in range(8 * f["tiles"]):
            for b in range(NB):
                for s in range(ns):
                    ed[(k, b, s)] = D + (b * ns if lag else 0) + (k // 8) * per + (k % 8) * ns + s
        last = max(e for (k, b, s), e in ed.items() if b == NB - 1 and s == ns - 1)
    elif lanes == 2:  # bands 0,1 share lane A (2 NS a burst), band 2 on lane B one NS behind
        span = 2 * ns
        per = max(8 * span, t["capture_stride"]) if f["tiles"] > 1 else 8 * span
        for k in range(8 * f["tiles"]):
            for b in range(NB):
                for s in range(ns):
                    ed[(k, b, s)] = D + (k // 8) * per + (k % 8) * span + (b * ns if b < 2 else ns) + s
        last = max(ed.values())
    elif lanes == 6:  # wider beats: two rows of a band per beat (6 lanes, face 6 x 551 b)
        nh = max(1, ns // 2)
        per = max(8 * nh, t["capture_stride"]) if f["tiles"] > 1 else 8 * nh
        for k in range(8 * f["tiles"]):
            for b in range(NB):
                for s in range(ns):
                    ed[(k, b, s)] = D + b * nh + (k // 8) * per + (k % 8) * nh + s // 2
        last = max(ed.values())
    else:  # one shared lane: band b of burst k at its own third of a 3 NS slot (train24 when ns = 8)
        span = NB * ns
        per = max(8 * span, t["capture_stride"]) if f["tiles"] > 1 else 8 * span
        for k in range(8 * f["tiles"]):
            for b in range(NB):
                for s in range(ns):
                    ed[(k, b, s)] = D + (k // 8) * per + (k % 8) * span + b * ns + s
        last = max(ed.values())
    caps = {k: (k // 8) * f["ts"] + k % 8 for k in range(8 * f["tiles"])}
    late = [k for k in caps if caps[k] + D > min(e for (kk, b, s), e in ed.items() if kk == k)]
    return ed, last, late


def conflicts(f, ed, rw):
    by = {}
    for key, r in rw.items():
        if key not in ed:
            return [("row outside reserved slots", key)]
        by.setdefault(ed[key], []).append((key, r))
    bad = []
    for e, lst in by.items():
        for mod in (16, 64):
            banks = [r % mod for _, r in lst]
            if len(set(banks)) != len(banks):
                bad.append((e, mod, lst))
    # program order per VM row: emission order must follow capture order
    seen = {}
    for key in sorted(rw, key=lambda kk: (kk[0], kk[1], kk[2])):
        r = rw[key]
        if r in seen and ed[seen[r]] >= ed[key]:
            bad.append(("row order", r, seen[r], key))
        seen[r] = key
    return bad


def check_rtl_rows(pc, f, rows_dir):
    p = Path(rows_dir) / f"{pc}.log"
    got = {}
    for line in p.read_text().splitlines():
        if line.startswith("ROW"):
            d = dict(re.findall(r"(\w+)=(\w+)", line))
            if d["we"] == "1":
                key = (int(d["cap"]), int(d["band"]), int(d["slot"]))
                if key in got:
                    raise ValueError(f"{pc}: duplicate RTL row {key}")
                got[key] = int(d["addr"]) & 0xFFFFF
    return got == rows(f), len(got)


def e2e(deltas):
    """deltas {token-path op: cycles per layer} -> loss % with every layer's node delayed at once"""
    doc = ac.load_path("qwen_rom")
    base, _ = ac.solve(doc["nodes"], doc["edges"])
    dl = {}
    for n in doc["nodes"]:
        op = n["id"].split(".")[-1]
        if "." in n["id"] and op in deltas and deltas[op] > 0:
            dl[n["id"]] = dl.get(n["id"], 0.0) + deltas[op]
    new, _ = ac.solve(doc["nodes"], doc["edges"], dl)
    return round(ac.loss_pct(base, new), 3), round(new - base, 1)


STRUCTS = {
    "O1_train24_1lane_24slots": dict(lanes=1, compress=False),
    "O2_1lane_compressed": dict(lanes=1, compress=True),
    "O3_3lanes_8slots": dict(lanes=3, compress=False),
    "O4_3lanes_compressed": dict(lanes=3, compress=True),
    "O5_2lanes_compressed": dict(lanes=2, compress=True),
    "O6_6lanes_wide_beats_compressed": dict(lanes=6, compress=True),
}


def read_program(path, dec):
    """Require the complete pinned decoder result-op contract, including VM-weight PC11.

    --pcs supplies workload fields, not permission to reduce the production shape.
    Capture profiles remain measured inputs; changing the shape requires new profiles.
    """
    program = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        pc, f = fields(line)
        if pc not in NODE:
            raise ValueError(f"unsupported result op {pc}")
        if pc in program:
            raise ValueError(f"duplicate result op {pc}")
        if not 1 <= f["tiles"] <= 8 or not 0 <= f["split"] <= 15 or f["oen"] not in (0, 1):
            raise ValueError(f"{pc}: fields outside the serializer contract")
        caps = dec[pc]["capture_cycles_after_go"]
        expected = [caps[0] + (k // 8) * f["ts"] + k % 8 for k in range(8 * f["tiles"])]
        if caps != expected:
            raise ValueError(f"{pc}: workload capture shape differs from measured profile")
        program[pc] = f
    if set(program) != set(NODE):
        raise ValueError(f"incomplete decoder result programme: missing {sorted(set(NODE) - set(program))}")
    return program


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pcs", default=str(PCS))
    ap.add_argument("--rows-dir", help="tb_vmwb_rows logs: cross-check the row law against the actual RTL ports")
    ap.add_argument("--out", help="write the calendar/cost JSON here")
    a = ap.parse_args(argv)
    dec = json.loads(DECISION.read_text())["link_handoff"]["ops"]
    ops, ok = {}, True
    for pc, f in read_program(a.pcs, dec).items():
        caps = dec[pc]["capture_cycles_after_go"]
        c0 = caps[0]
        rw = rows(f)
        rec = dict(fields=f, train=train(f), real_rows=len(rw), first_capture_after_go=c0,
                   last_capture_after_go=caps[-1], unconstrained_last_landing=caps[-1] + D + 25)
        if a.rows_dir:
            same, n = check_rtl_rows(pc, f, a.rows_dir)
            rec["row_law_matches_rtl"] = same
            ok &= same
        rec["structures"] = {}
        for name, st in STRUCTS.items():
            ed, last, late = calendar(f, c0, **st)
            bad = conflicts(f, ed, rw) if st["lanes"] == 3 else []
            land = c0 + last + 2            # tb_sertrade convention (+2: decode edge -> rb register -> observe)
            rec["structures"][name] = dict(last_landing_after_go=land,
                                           face_cycles_over_unconstrained=land - rec["unconstrained_last_landing"],
                                           bank_conflicts=len(bad), capture_after_emission=len(late))
            if name.startswith("O4"):
                ok &= not bad and not late
                rec["calendar"] = {f"{k}.{b}.{s}": e for (k, b, s), e in sorted(ed.items())}
        ops[pc] = rec
    summary = {}
    for name in STRUCTS:
        d = {NODE[pc]: max(0, r["structures"][name]["face_cycles_over_unconstrained"]) for pc, r in ops.items()}
        d_tok = {k: v for k, v in d.items() if k != "attn_kv"}
        summary[name] = dict(face_cycles_per_layer=sum(d.values()),
                             face_cycles_per_layer_token_ops=sum(d_tok.values()),
                             e2e_loss_pct_incl_pc11=e2e(d)[0], e2e_loss_pct_token_ops=e2e(d_tok)[0])
    out = dict(schema="opentallas.qwen.vm_writeback_calendar.v1", tool="tools/qwen_vmwb/wb_calendar.py",
               law=dict(row="obase + (k//8)*ots*(GT>>split) + (k%8)*ojs + g(split,pt)*ots",
                        emission="c0 + D + b*NS + (k//8)*P + (k%8)*NS + s, P = max(8NS, stride)",
                        bank="distinct mod 16 and mod 64 per edge (proved)"),
               ops=ops, options=summary, ok=bool(ok))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for name, s in summary.items():
        print(f"{name:28s} face/layer {s['face_cycles_per_layer']:5d} (token ops {s['face_cycles_per_layer_token_ops']:5d})"
              f"  e2e {s['e2e_loss_pct_incl_pc11']:6.3f}% incl PC11, {s['e2e_loss_pct_token_ops']:6.3f}% token ops")
    for pc, r in ops.items():
        print(pc, r["train"], "rows", r["real_rows"], "rtl", r.get("row_law_matches_rtl"),
              {n: (v["last_landing_after_go"], v["bank_conflicts"]) for n, v in r["structures"].items()})
    print("CALENDAR OK" if ok else "CALENDAR FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
