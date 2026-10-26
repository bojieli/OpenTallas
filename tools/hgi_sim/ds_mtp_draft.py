#!/usr/bin/env python3
"""H-MTP2 decision 4: the DSpark DRAFT lowered as R-row batches by the compiler (DeepSeek-V4.1-Flash, generic HBM die,
1M context, DSpark gamma 5: block of R = 5 rows, 3 stages).

As lowered (ds_mtp_kernels, spec=True) the draft is ROW-SERIAL: each stage runs its dsa body (hc mixes .. q RoPE, the
block row's FP8 KV row into DSKX) and its dsb body (attention over DSKX rows 0 .. n_win + 4, no mask .. FFN hc_post)
once per block row, with the row's column swap around each launch; DHEAD runs once per row (LM head into DLOG row i),
MARKOV gamma times (d_{i+1} depends on d_i: serial by construction).  ds_mtp_rows had a RATIO MODEL for the batched
draft (dsa + dsb + dhead x verify(P = 5, layer 0) / (5 x AR layer 0)).  This module replaces the ratio by a COMPILE:

  BODIES: the rank-0 kernel bodies as the simulator builds and prices them (Kernels(m, spec=True).body[0]; `dump`
    writes them, records bit-encoded + tag / family / region names / source op, with the w19 ops they price from).
  COMPILER: each body is rewritten as ONE R-row programme by the batched-verify compiler pass
    (ds_mtp_verify.compile_verify: classify(), shared / per-position / P-row record forms, row_ii(), sm_mode,
    sm_k, att_k, the per-segment column swaps) under the SAME item configuration as the verify (ds_mtp_rows.cfg_of):
      * dsa: the R block rows are independent (each its own h / PRE, KV row into DSKX at n_win + i, q / mixes saved
        by row): every per-row record becomes R rows or R records (the configuration decides), weights / tables
        are shared (SM: serial / one line-held read / k slot sets), un-indexed SU rows x R in one record;
      * dsb: the R rows attend the SAME DSKX rows (0 .. n_win + 4, no mask), so the option-B attention as a P-row
        record ("ATT" item) streams the KV lines once (fixed spans once, the measured component span x
        ceil(R / att_k)); without the item, R attention records; the routed experts (128, top 3): as-built SM
        serial = every row its own 3 experts; SM slot modes read the UNION of the rows' top-3 (U slots, R x 3 / U
        rows a slot; U = R x 3 = 15 unless --union: the no-sharing bound, conservative), + the per-die union record;
      * dhead: the R rows' LM-head rows share the head weight stream (SM slot modes), per-row norm / DLOG store;
      * seed: the P = 6 verify columns' SEED bodies, the same pass at P = 6 (main_proj / wkv weights shared);
      * markov: NOT batched (d_{i+1} = argmax(DLOG_i + markov_head(embed(d_i)))): gamma x the P = 1 body;
      * demb: the R embedding launches kept serial (5 x 326 cycles, as in the ratio model).
    Column swaps: as built (VM swap) every R-row segment swaps its R columns in (and out: dsa / dsb; DHEAD in only)
    -- the same swap count as the row-serial launches; with the VM item (swap=False) the R rows stay resident (the
    5 x 20,484-word draft rows fit the VM growth sized for the 6 verify columns, which are not live during the draft).
  COST of a draft record = the simulator's pricing of the launch bodies (ds_mtp_kernels sim --price-pos 1048575
    --att-b b_measured_model.json exposed): DT.NativeCost over the kernel ops, the TU collective model for the
    kernels' own collectives (no w19 op), the measured SM attention spans (option B, by selection class) for ATT;
    timing.schedule S2 with the MTP doorbell DYN (WIN = min(pos + 1, 128)) at position 1,048,575.  The scale tables
    ('fixed', 'sens_current', 'sens_1010') apply per record exactly as on the verify (ds_mtp_verify.cost_fn).
  VALIDATION: at P = 1 the compiled bodies reproduce the row-serial per-launch s2_cycles of the sim's launches.json.

    python3 -m hgi_sim.ds_mtp_draft dump --out BODIES.json            (needs the checkpoint; ~3 min)
    python3 -m hgi_sim.ds_mtp_draft validate --out REC.json            (from tools/; seconds)
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import datetime
import hashlib
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from hgi_sim import timing as T  # noqa: E402
from hgi_sim import ds_mtp_verify as V  # noqa: E402

BODIES = ROOT / "results/arch/hbm_mtp_1015/draft_rows/draft_bodies.json"
LAUNCHES = ROOT / "results/arch/hbm_mtp_1015/sim1M_B/launches.json"
R = 5                      # DSpark block rows (gamma 5)
TOPK = 3                   # DSpark stage MoE: 128 experts, top 3 (+ the shared expert slot 3)
NAMES = ("dsa0", "dsa1", "dsa2", "dsb0", "dsb1", "dsb2", "dhead", "markov", "seed", "demb", "swapin", "swapout")
KEYS = dict(dsa0=(7, 0), dsa1=(7, 1), dsa2=(7, 2), dsb0=(8, 0), dsb1=(8, 1), dsb2=(8, 2), dhead=(9, 0),
            markov=(10, 0), seed=(5, 0), demb=(6, 0), swapin=(0, 0), swapout=(1, 0))


# ---- bodies ------------------------------------------------------------------------------------------------------
def dump(a):
    """Kernels(m, spec=True) as the sim builds it (released checkpoint), rank 0 (the die the sim prices): the draft
    bodies + the w19 ops their records price from -> JSON"""
    import os
    os.environ.setdefault("HDC_V41_ARITH", "chunk8")
    sys.path.insert(0, str(TOOLS / "gpu_sys"))
    from hgi_sim import ds_mtp_kernels as KM
    KM.npy_check()
    import rtl_v41_fullshape_layer_campaign as LC
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    K = KM.Kernels(m, spec=True)
    bodies, used = {}, set()
    for nm in NAMES:
        recs = []
        for x in K.body[0][KEYS[nm]]:
            src = getattr(x, "src", None)
            if src and isinstance(src, tuple):
                used.add(f"{src[0]}:{src[1]}")
                used.update(f"{src[0]}:{e}" for e in (src[2] if len(src) > 2 else ()))
            recs.append(dict(hex=x.encode().hex(), tag=x.tag, family=x.family,
                             reads=list(x.reads) if hasattr(x, "reads") else None,
                             writes=list(x.writes) if hasattr(x, "writes") else None,
                             src=list(src) if isinstance(src, tuple) else None,
                             implicit=[[k_, list(iv)] for k_, iv in getattr(x, "implicit", ())] or None))
        bodies[nm] = recs
    ops = {k: K.ops[k] for k in sorted(used) if k in K.ops}
    rec = dict(schema="opentallas.hgi_sim.ds_mtp_draft_bodies.v1", rank=0, kernel_keys=KEYS, bodies=bodies, ops=ops,
               fused_hll=int(K.DN.FUSED_HLL),
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               source_sha256={p_: hashlib.sha256((TOOLS / p_).read_bytes()).hexdigest() for p_ in (
                   "hgi_sim/ds_mtp_kernels.py", "hgi_sim/ds_native.py", "hgi_sim/records.py")})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, default=_jsonable) + "\n")
    print(f"{a.out}: {sum(len(v) for v in bodies.values())} records, {len(ops)} ops")
    return 0


def _jsonable(o):
    if hasattr(o, "item"):
        return o.item()
    if isinstance(o, (set, tuple)):
        return list(o)
    raise TypeError(f"not JSON: {type(o)}")


def load_bodies(path=BODIES):
    from hgi_sim.records import decode_one
    d = json.loads(Path(path).read_text())
    out = {}
    for nm, xs in d["bodies"].items():
        recs = []
        for x in xs:
            r, _ = decode_one(bytes.fromhex(x["hex"]), 0)
            r.tag, r.family = x["tag"], x["family"]
            if x["reads"] is not None:
                r.reads, r.writes = x["reads"], x["writes"]
            if x["implicit"]:
                r.implicit = [(k_, tuple(iv)) for k_, iv in x["implicit"]]
            r.src_key0 = None if not x["src"] else f"{x['src'][0]}:{x['src'][1]}"
            recs.append(r)
        out[nm] = recs
    return d, out


# ---- cost: the simulator's launch-body pricing --------------------------------------------------------------------
def body_cost(ops, body, att_b):
    """ds_mtp_kernels.sim's per-launch cost function (C, 'timing'), for one body: DT.NativeCost over the kernel ops;
    the kernels' own collectives (no w19 op, or a size the measured table lacks) by the TU collective model; ATT by
    the measured SM attention span of its selection class (option B)"""
    from hgi_sim.ds_native_timing import NativeCost
    from hgi_sim.perf import coll_cycles
    for r in body:
        r.src_key = r.src_key0 if r.src_key0 in ops else None
        r.src_extra = []
    nc = NativeCost(ops, body)

    def model(r):
        n = r.desc["A"].n if "A" in r.desc else 1
        nb = 8 * 96 if r.op == "ARGMAX_MERGE" else 4 * n
        c, _, _ = coll_cycles("ALL_GATHER", nb, 96)
        return c, "measured_tu_budget", f"{r.op} {nb} B over 96 (TU collective model; no measured class)"

    def cf(r, dyn, L):
        if r.unit == "COLL" and r.src_key is None:
            return model(r)
        if r.unit == "ATT" and att_b:
            T_ = r.desc["O"].n if r.op == "QK" else r.desc["A"].n
            cls = "640" if T_ > 128 + 64 else "128"
            return float(att_b[cls][r.op.lower()]), "measured_component+model", f"SM attention option B T{cls}"
        try:
            return nc(r, dyn, L)
        except KeyError:
            if r.unit == "COLL":
                return model(r)
            raise
    return cf


@contextlib.contextmanager
def mtp_dyn():
    """the MTP doorbell DYN (ds_mtp_kernels.patch_timing_dyn: v[15] = POS + 1, v[16] = WIN) for the draft bodies'
    timing only; the AR / verify program keeps the plain timing.Dyn"""
    old = T.Dyn

    class Dyn(old):
        def __init__(self, pos, token=0, rank=0):
            super().__init__(pos, token, rank)
            self.v[15], self.v[16] = pos + 1, min(pos + 1, 128)
    T.Dyn = Dyn
    try:
        yield
    finally:
        T.Dyn = old


_C = {}


def ctx():
    if "bodies" not in _C:
        d, b = load_bodies()
        bm = json.loads(V.BMODEL.read_text())
        _C.update(ops=d["ops"], bodies=b, bex={T_: dict(qk=v["qk"], pv=v["pv"]) for T_, v in bm["exposed"]["per_record"].items()},
                  bcomp=bm["measured_comp"])
    return _C


def undeclared_raw(body):
    """RAW hazards on VM the body's wait masks miss: Kernels.mv adds an SM.MATVEC with NO region-name read of its x
    operand (b.add(rec, [], [out])), so the Builder sets no wait on x's producer and the S2 dispatch issues the matvec
    while the producer is still writing x (dhead.lm_head after dhead.norm, markov.head after markov.embed, seed
    main_proj / wkv0 after seed.mh / main_norm.y; the sim's launch prices carry these races).  -> [(i, mask, producer
    tags)]: the wait bits record i needs (a producer of an overlapping VM interval on another unit, not drained by a
    wait of a record in between)"""
    from hgi_sim.records import wait_mask
    with mtp_dyn():
        dyn = T.Dyn(V.DT.POS)
        fps = [T.footprint(r, dyn, 0) for r in body]
    out = []
    for i, r in enumerate(body):
        need, who = 0, []
        for j in range(i):
            u = body[j].unit
            if u == r.unit or u == "CTL":
                continue
            if not any(T.overlap(a_, w) and a_[0] == "VM" for a_ in fps[i][0] for w in fps[j][1]):
                continue
            bit = wait_mask(u)
            if any(body[k].wait & bit for k in range(j + 1, i + 1)):
                continue
            need |= bit
            who.append(body[j].tag)
        if need:
            out.append((i, need, who))
    return out


def compile_body(name, P, cfg, union=None, fix_waits=True):
    """one draft body as a P-row programme (compile_verify) under the item configuration cfg (ds_mtp_rows.cfg_of);
    fix_waits: add the wait bits the body's undeclared SM reads miss (undeclared_raw; False = the bodies exactly as
    the sim priced them)"""
    c = ctx()
    body = [copy.copy(r) for r in c["bodies"][name]]
    fix = {i: m_ for i, m_, _ in undeclared_raw(body)} if fix_waits else {}
    for i, r in enumerate(body):
        r.layer = 0                  # one segment; the sim prices the bodies with L = 0
        r.wait_floor = r.wait | fix.get(i, 0)    # the kernel compiler's explicit waits (+ the missing RAW waits)
        if not hasattr(r, "reads"):
            r.reads, r.writes = [], []
    cf = body_cost(c["ops"], body, c["bex"])
    swap_out = "none" if name == "dhead" else "all"
    swap = bool(cfg.get("swap", True)) and P > 1 and name[:3] in ("dsa", "dsb", "dhe")     # (the row-serial launches swap these only)
    with mtp_dyn():
        prog, st = V.compile_verify(body, lambda r, dyn, L: cf(r, dyn, L), P,
                                    sm_mode=cfg.get("sm_mode", "serial") if P > 1 else "pport", att="B",
                                    bmodel=c["bex"], bcomp=c["bcomp"], swap=swap, rows=tuple(cfg.get("rows", ())),
                                    sm_k=cfg.get("sm_k"), att_k=cfg.get("att_k"), topk=TOPK,
                                    union=union if union is not None else TOPK * P, swap_out=swap_out)
    return prog, st


def time_prog(prog, scale=None):
    with mtp_dyn():
        r = V.run(prog, scale)
    return r


def draft_step(cfg, scale=None, union=None):
    """the draft + seed cycles of one DSpark step, R-row compiled under cfg and the scale table:
    dsa / dsb (3 stages, R rows each, swaps inside), dhead (R rows), seed (P = 6 columns), demb (R serial), markov
    (gamma serial)"""
    out, rec = {}, {}
    for nm in ("dsa0", "dsa1", "dsa2", "dsb0", "dsb1", "dsb2", "dhead"):
        prog, st = compile_body(nm, R, cfg, union)
        r = time_prog(prog, scale)
        rec[nm] = dict(cycles=r["cycles"], records=r["records"], compile=st)
    prog, st = compile_body("seed", V.GAMMA + 1, cfg, union)
    r = time_prog(prog, scale)
    rec["seed"] = dict(cycles=r["cycles"], records=r["records"], compile=st)
    for nm in ("markov", "demb"):
        prog, st = compile_body(nm, 1, cfg)
        rec[nm] = dict(cycles=time_prog(prog, scale)["cycles"], records=len(prog))
    out["dsa"] = sum(rec[f"dsa{s}"]["cycles"] for s in range(3))
    out["dsb"] = sum(rec[f"dsb{s}"]["cycles"] for s in range(3))
    out["dhead"] = rec["dhead"]["cycles"]
    out["markov"] = R * rec["markov"]["cycles"]
    out["demb"] = R * rec["demb"]["cycles"]
    out = {k: round(v, 1) for k, v in out.items()}
    return dict(draft_cycles=round(sum(out.values()), 1), draft_by_kind=out, seed_cycles=rec["seed"]["cycles"],
                bodies=rec)


# ---- validation: P = 1 against the row-serial launch trace --------------------------------------------------------
def validate(a):
    L = json.loads(LAUNCHES.read_text())
    i0 = next(i for i, x in enumerate(L) if x["kind"] == "seed")
    trace = {}
    for x in L[i0 + 1:]:
        nm = x["kind"] + (str(x["Lp"]) if x["kind"] in ("dsa", "dsb") else "")
        if x["kind"] in ("swapin", "swapout") and x["token"] < 8:
            continue
        trace.setdefault(nm, []).append(x["s2_cycles"])
    cfg = dict(sm_mode="serial", swap=True, rows=())
    rows = {}
    for nm in ("dsa0", "dsa1", "dsa2", "dsb0", "dsb1", "dsb2", "dhead", "markov", "seed", "demb", "swapin", "swapout"):
        r = time_prog(compile_body(nm, 1, cfg, fix_waits=False)[0], None)
        rf = time_prog(compile_body(nm, 1, cfg)[0], None)
        sim = trace[nm]
        rows[nm] = dict(compiled_p1=r["cycles"], sim_launch=sim[0], sim_launches=len(sim), sim_all_equal=len(set(sim)) == 1,
                        rel_err=round(r["cycles"] / sim[0] - 1, 5), compiled_p1_waits_fixed=rf["cycles"])
    kinds = {}
    for k in ("dsa", "dsb"):
        c = sum(rows[f"{k}{s}"]["compiled_p1"] for s in range(3)) * R
        s_ = sum(sum(trace[f"{k}{s}"]) for s in range(3))
        kinds[k] = dict(compiled_p1_x_rows=round(c, 1), sim=round(s_, 1), rel_err=round(c / s_ - 1, 5))
    for k in ("dhead", "markov", "demb", "swapin", "swapout"):
        c = rows[k]["compiled_p1"] * len(trace[k])
        s_ = sum(trace[k])
        kinds[k] = dict(compiled_p1_x_launches=round(c, 1), sim=round(s_, 1), rel_err=round(c / s_ - 1, 5))
    seeds = [x["s2_cycles"] for x in L if x["kind"] == "seed"][-(V.GAMMA + 1):]
    kinds["seed"] = dict(compiled_p1_x_columns=round(rows["seed"]["compiled_p1"] * len(seeds), 1), sim=round(sum(seeds), 1),
                         rel_err=round(rows["seed"]["compiled_p1"] * len(seeds) / sum(seeds) - 1, 5))
    c = ctx()
    rec = dict(schema="opentallas.hgi_sim.ds_mtp_draft_validate.v1", launches=str(LAUNCHES.relative_to(ROOT)),
               note="compiled_p1 = the bodies exactly as the sim priced them (fix_waits off); compiled_p1_waits_fixed "
                    "= with the wait bits of the undeclared SM reads (the R-row ladder uses these)",
               undeclared_raw={nm: [dict(record=c["bodies"][nm][i].tag, wait_bits=hex(m_), producers=w)
                                    for i, m_, w in undeclared_raw(c["bodies"][nm])] for nm in NAMES},
               bodies=str(BODIES.relative_to(ROOT)), per_body=rows, per_kind=kinds)
    print(json.dumps(rec, indent=1))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    d = sp.add_parser("dump")
    d.add_argument("--out", default=str(BODIES))
    v = sp.add_parser("validate")
    v.add_argument("--out")
    a = ap.parse_args()
    return dict(dump=dump, validate=validate)[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
