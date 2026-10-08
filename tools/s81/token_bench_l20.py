#!/usr/bin/env python3
"""S81 DS-ROM (DeepSeek-V4.1-Flash, 1,792 HALF-dedicated + router K-split mapping) ONE-LAYER TOKEN BENCH at the 1M token
(gaps-design 2026-10-08; owner rule "simulate the minimum component: per-stage RTL + analytic composition").

Layer 20 (a ratio-1 + compressor + indexer + candidates layer, the golden record's own 1M-token layer) of TP rank 0 is
run op by op as a CHAIN through the layer's vector memory (VM):

  stage FIELD    every ROM-field matvec phase of the layer (attention a_proj FP8 / BF16, wq_b, cmp.wk, wo_a groups,
                 wo_b, router, shared gate/up/down, the six routed experts' gate/up/down) on the field vehicle of
                 tools/dsrom_1m_field.py (pinned spine + VM + field, q element QX 10 on FP8/FP4 pairs, BF16-capable
                 pairs on the W10 BF16 slots), EVERY region of the die at full shape, placed by the 1,792 binding
                 (tools/dsrom_bf_geometry_alloc.py --pbf 1792 --pq 1792 --nbf-reg 4 --ksplit gate, sha256-checked
                 against results/uarch/dsrom_s81_field_phases_1792_20261007/binding/half_dedicated_ksplit.sha256).
  stage SELECT   the S81 die selector's streaming exact top-k (ot_hdc_v41x_sel, Q 4 / W 16 / IW 20 / K 512 / AW 8, the
                 module the dsfd_bk_selector slab instantiates unchanged) on the layer's 1,048,576 golden index scores in
                 four contiguous quarters, line-memory replays included; checked against the golden top-512.
  CHAIN          starting from the golden VM before the layer's first op, every op in program order rewrites the VM:
                 a FIELD op writes the RTL's own row words (not the golden rows), every other op (HC / norms / RoPE /
                 compressor / indexer scoring / sparse attention and its softmax / SwiGLU / combine: the units without a
                 field-vehicle stage here) applies the golden executor's VM delta of that op.  Before each FIELD op its
                 x is read from the CHAIN VM and must equal the x the RTL ran on; after EVERY op the whole chain VM must
                 equal the golden VM; at the end it must equal the golden layer output (expect_vm.hex).
PASS = every field region run exact + the chain VM bit-identical to the golden after every op and at the end + the
selector exact.  Composition: the field node cycles are the vehicle's measured phases (tools/s81/field_phases_1792.py
composes them with the routed-die wire); this bench is the exactness gate, not a timing record.

    python3 tools/s81/token_bench_l20.py prep --work W           # localhost: binding, plan, checkpoint slices, fixtures
    python3 tools/s81/token_bench_l20.py run  --work W --jobs 40 # compute host: build, field runs, select, chain
    python3 tools/s81/token_bench_l20.py check --work W          # chain + verdict only (after run)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
BIND_REC = ROOT / "results/uarch/dsrom_s81_field_phases_1792_20261007/binding"
GOLD_VM = Path("/home/ubuntu/w17work/die/ctx1048576_s20260930_L20_r0")
REF = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
LAYER = 20
QELEM = 10
SEL = dict(Q=4, W=16, IW=20, K=512, AW=8)
PY = sys.executable


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sh(cmd, env=None, log=None):
    print("+", " ".join(map(str, cmd)), flush=True)
    e = dict(os.environ, **(env or {}))
    with open(log, "a") if log else open(os.devnull, "w") as lf:
        r = subprocess.run(list(map(str, cmd)), cwd=ROOT, env=e, stdout=lf if log else None, stderr=subprocess.STDOUT
                           if log else None)
    if r.returncode:
        raise SystemExit(f"FAIL step rc={r.returncode}: {' '.join(map(str, cmd))}")


def field_env(work: Path) -> dict:
    return dict(OT_DSROM_FIELD_BINDING=str(work / "binding"), OT_DSROM_FIELD_REF=str(work / "fix" / "ref"))


# ---------------------------------------------------------------------------------------------------------------- prep
def cmd_prep(a):
    work = a.work.resolve()
    (work / "fix" / "ref").mkdir(parents=True, exist_ok=True)
    b = work / "binding"
    want = dict(ln.split()[::-1] for ln in (BIND_REC / "half_dedicated_ksplit.sha256").read_text().splitlines())
    want = {Path(k).name: v for k, v in want.items()}
    if not (b / "matrix_map.jsonl.gz").exists():
        sh([PY, "tools/dsrom_bf_geometry_alloc.py", "--out", b, "--pbf", 1792, "--pq", 1792, "--nbf-reg", 4,
            "--ksplit", "gate"], log=work / "alloc.log")
    for f in ("matrix_map.jsonl.gz", "stage_map.json", "inventory.json"):
        got = sha(b / f)
        if got != want[f]:
            raise SystemExit(f"FAIL binding {f} sha256 {got} != committed {want[f]}")
    # fixtures: the golden layer record (L20 only) and the rank-0 executor VM snapshots + weight ops
    for f in (f"ctx1048576_L{LAYER:02d}.json", f"ctx1048576_L{LAYER:02d}.npz"):
        shutil.copy2(REF / f, work / "fix" / "ref" / f)
    gv = work / "fix" / "die" / GOLD_VM.name
    if not gv.exists():
        shutil.copytree(GOLD_VM, gv)
    wj = GOLD_VM.parent / f"ctx1048576_s20260930_L{LAYER}" / "r0" / "weights.json"
    (work / "fix" / "die" / wj.parent.parent.name / "r0").mkdir(parents=True, exist_ok=True)
    shutil.copy2(wj, work / "fix" / "die" / wj.parent.parent.name / "r0" / "weights.json")
    env = field_env(work)
    f = work / "field"
    sh([PY, "tools/dsrom_1m_field.py", "plan", "--work", f, "--gold-vm", gv, "--layers", LAYER, "--qelem", QELEM],
       env=env, log=work / "plan.log")
    sh([PY, "tools/dsrom_1m_field.py", "extract", "--work", f, "--snapshot", a.snapshot], env=env, log=work / "extract.log")
    (work / "STATUS.md").write_text(f"S81 L{LAYER} token bench work dir (tools/s81/token_bench_l20.py): fixtures + "
                                    "binding + field plan / slices; keep until the bench verdict is recorded.\n")
    print("PREP done", work)
    return 0


# ----------------------------------------------------------------------------------------------------------------- run
def cmd_run(a):
    work = a.work.resolve()
    env = field_env(work)
    f = work / "field"
    if not (f / "build" / "tb").exists():
        sh([PY, "tools/dsrom_1m_field.py", "build", "--work", f, "--qelem", QELEM], env=env, log=work / "build.log")
    rc_field = subprocess.run([PY, "tools/dsrom_1m_field.py", "run", "--work", f, "--jobs", a.jobs],
                              cwd=ROOT, env=dict(os.environ, **env)).returncode
    sel = run_select(work)
    rc = finish(work, rc_field, sel)
    rcm = finish(work, rc_field, sel, mutant=True)       # the negative control must fail
    print("MUTANT", "DETECTED" if rcm else "MISSED", flush=True)
    return rc if rcm else 2


def run_select(work: Path) -> dict:
    """The S81 die selector (ot_hdc_v41x_sel at the slab's parameters) on the layer's golden 1M index scores."""
    import hdc_golden_v41 as G
    import rtl_hdc_v41x_sel_campaign as S
    G.set_arith("chunk8")
    t0 = time.time()
    s = np.load(work / "fix" / "ref" / f"ctx1048576_L{LAYER:02d}.npz")[f"L{LAYER}.index_scores"]
    n = len(s)
    idx = np.arange(n)
    bits = S.bf16_bits(s)
    if not np.array_equal(S.vals_of(bits), s, equal_nan=True):
        return dict(exact=False, error="golden index scores are not BF16 values")
    k = SEL["K"]
    gold = sorted(int(i) for i in np.lexsort((idx, -s))[:k])
    unit = sorted(int(i) for i in G.topk_lowest_index(S.vals_of(bits), k))
    cuts = [(n * q) // SEL["Q"] for q in range(SEL["Q"] + 1)]
    rng = np.random.default_rng(0)
    beats, exps = [], []
    for q in range(SEL["Q"]):
        lo, hi = cuts[q], cuts[q + 1]
        beats.append(S.to_beats(rng, bits[lo:hi], idx[lo:hi], SEL["W"], True))
        exps.append([(int(idx[i]), int(bits[i]), int(bits[i] == S.NINF)) for i in unit if lo <= i < hi])
    d = work / "select"
    d.mkdir(exist_ok=True)
    maxb = max(len(b) for b in beats) + 64
    cfg = S.run_config("L20_sel_1m", SEL["Q"], SEL["W"], SEL["IW"], SEL["K"], SEL["AW"], [(beats, k, exps, {"n": n})],
                       ["L20_topk_1m"], d, ((0, 0, 1),), maxb=maxb)
    r = cfg["runs"][0]
    ps = (r.get("per_segment") or [None])[0]
    out = dict(unit="ot_hdc_v41x_sel (S81 dsfd_bk_selector core, unchanged)", params=SEL, n_keys=n, k=k,
               rtl_pass=cfg["pass"], errors=r.get("errors"), unit_reference_equals_golden_lexsort=unit == gold,
               cycles=None if ps is None else ps["last"] - ps["first"] + 1 + ps["tail"],
               replays=None if ps is None else ps["replays"], wall_s=round(time.time() - t0, 1),
               rtl_sha256={str(p.relative_to(ROOT)): sha(p) for p in S.RTL})
    out["exact"] = bool(cfg["pass"] and out["unit_reference_equals_golden_lexsort"])
    (d / "select.json").write_text(json.dumps(out, indent=1) + "\n")
    print("SELECT", "PASS" if out["exact"] else "FAIL", out["cycles"], flush=True)
    return out


# --------------------------------------------------------------------------------------------------------------- chain
def read_sparse(path: Path) -> dict:
    vm, ad = {}, 0
    for ln in path.read_text().split():
        if ln.startswith("@"):
            ad = int(ln[1:], 16)
        else:
            vm[ad] = int(ln, 16)
            ad += 1
    return vm


def chain(work: Path, mutant: bool = False) -> dict:
    f = work / "field"
    plan = json.loads((f / "plan.json").read_text())
    gv = Path(plan["gold_vm"])
    if not gv.exists():                                  # plan written on the prep host: same relative fixture
        gv = work / "fix" / "die" / gv.name
    xs = np.load(f / "x.npz")
    wops = {o["pc"]: o for o in json.loads((gv / "weight_ops.json").read_text())["ops"]}
    # RTL row words per field op: {pc: {vm address: word}}, from every region's result
    rtl, xused, missing, bad_region = {}, {}, 0, []
    for ph in plan["phases"]:
        isa = {m["alias"]: m["isa"] for m in ph["mats"]}
        for reg in ph["regions"]:
            rf = f / "runs" / ph["phase"] / f"r{reg:03d}" / "result.json"
            if not rf.exists():
                missing += 1
                continue
            r = json.loads(rf.read_text())
            if not r["pass_"]:
                bad_region.append((ph["phase"], reg))
            for (al, row, _f32, _b16), w in zip(r["xcheck"], r.get("rtl") or [None] * len(r["xcheck"])):
                i = isa.get(al)
                if not i:
                    continue
                rtl.setdefault(i["pc"], {})[i["out_vm"] + i["row0"] + row] = w
                xused[i["pc"]] = ph["phase"]
    if mutant and rtl:                                  # negative control: one RTL row word, one bit flipped
        pc0 = min(rtl)
        ad0 = min(rtl[pc0])
        rtl[pc0][ad0] = (rtl[pc0][ad0] or 0) ^ 1
    pcs = sorted(int(p.name[5:8]) for p in gv.glob("vm_pc*.hex"))
    cur = read_sparse(gv / f"vm_pc{pcs[0]:03d}.hex")
    prev_gold = cur
    ops, first_bad = [], None
    for pc in pcs[1:]:
        gold = read_sparse(gv / f"vm_pc{pc:03d}.hex")
        rec = dict(pc=pc, unit=wops.get(pc, {}).get("unit"), tag=wops.get(pc, {}).get("tag"))
        if pc in rtl:
            op = wops[pc]
            xv = np.array([cur.get(op["x_vm"] + j, 0) for j in range(op["k"])], dtype=np.uint32)
            rec.update(stage="FIELD (RTL rows)", phase=xused[pc], x_equals_rtl_run_x=bool(np.array_equal(xv, xs[xused[pc]])),
                       rows=len(rtl[pc]), rows_unwritten=sum(w is None for w in rtl[pc].values()))
        else:
            rec.update(stage="golden-composed")
        # every other VM change of this op: the golden executor's delta
        for ad in set(gold) | set(prev_gold):
            g, p = gold.get(ad, 0), prev_gold.get(ad, 0)
            if g != p and not (pc in rtl and ad in rtl[pc]):
                cur[ad] = g
        if pc in rtl:
            for ad, w in rtl[pc].items():
                cur[ad] = 0 if w is None else w
        diff = [ad for ad in set(gold) | set(cur) if gold.get(ad, 0) != cur.get(ad, 0)]
        rec["vm_mismatch_words"] = len(diff)
        rec["ok"] = not diff and rec.get("x_equals_rtl_run_x", True) and not rec.get("rows_unwritten", 0)
        if not rec["ok"] and first_bad is None:
            first_bad = dict(pc=pc, addrs=sorted(diff)[:8])
        ops.append(rec)
        prev_gold = gold
    final = read_sparse(gv / "expect_vm.hex")
    fdiff = sum(1 for ad in final if final[ad] != cur.get(ad, 0))
    field_ops = [o for o in ops if o["stage"].startswith("FIELD")]
    return dict(field_phases=len(plan["phases"]), field_region_runs=sum(len(p["regions"]) for p in plan["phases"]),
                field_region_runs_missing=missing, field_region_runs_failed=len(bad_region),
                field_failed_first=bad_region[:4], ops=len(ops), field_ops_rtl=len(field_ops),
                field_rows_rtl=sum(o["rows"] for o in field_ops),
                golden_composed_ops=len(ops) - len(field_ops), chain_ok=all(o["ok"] for o in ops),
                first_bad=first_bad, final_expect_vm_words=len(final), final_mismatch_words=fdiff, per_op=ops)


def src_commit():
    if (ROOT / "SOURCE_COMMIT").exists():
        return (ROOT / "SOURCE_COMMIT").read_text().strip()
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or None


def finish(work: Path, rc_field: int, sel: dict | None, mutant: bool = False) -> int:
    c = chain(work, mutant)
    if sel is None:
        sp = work / "select" / "select.json"
        sel = json.loads(sp.read_text()) if sp.exists() else dict(exact=False, error="select not run")
    ok = (rc_field == 0 and c["field_region_runs_missing"] == 0 and c["field_region_runs_failed"] == 0
          and c["chain_ok"] and c["final_mismatch_words"] == 0 and sel.get("exact"))
    rec = dict(schema="opentallas.s81.token_bench_l20.v1", layer=LAYER, rank=0, token_position=1048575,
               mapping="1,792 HALF dedicated + router K split (half_dedicated_ksplit)",
               binding_sha256={p.name: sha(p) for p in sorted((work / "binding").glob("*.json*"))},
               field_build=json.loads((work / "field" / "build" / "build.json").read_text()) if
               (work / "field" / "build" / "build.json").exists() else None,
               select=sel, chain={k: v for k, v in c.items() if k != "per_op"},
               source_commit=src_commit(), mutant=mutant,
               verdict="PASS" if ok else "FAIL")
    out = work / ("token_bench_mutant.json" if mutant else "token_bench.json")
    out.write_text(json.dumps(rec, indent=1) + "\n")
    if not mutant:
        (work / "chain_ops.json").write_text(json.dumps(c["per_op"], indent=1) + "\n")
    print(f"{rec['verdict']} s81_token_l20{'_MUTANT' if mutant else ''} field_ops_rtl={c['field_ops_rtl']} rows={c['field_rows_rtl']} "
          f"golden_composed_ops={c['golden_composed_ops']} chain_ok={c['chain_ok']} final_mismatch={c['final_mismatch_words']} "
          f"select={'exact' if sel.get('exact') else 'FAIL'} cycles={sel.get('cycles')}", flush=True)
    return 0 if ok else 1


def cmd_check(a):
    return finish(a.work.resolve(), 0, None, a.mutant)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("prep", "run", "check"))
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=40)
    ap.add_argument("--mutant", action="store_true", help="check: flip one bit of one RTL row word (must FAIL)")
    ap.add_argument("--snapshot", type=Path, default=Path.home() / ".cache/huggingface/hub/models--deepseek-ai--"
                    "DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277")
    a = ap.parse_args()
    return dict(prep=cmd_prep, run=cmd_run, check=cmd_check)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
