#!/usr/bin/env python3
"""S81 ROM FIELD on RTL at the 1M token: every layer (type) and every TP rank, with the token's REAL x.

r4 put L20 rank 0 on RTL (tools/s81/token_bench_l20.py: 26 field ops chained through the ISA executor's VM).  This
extends the field to the other ranks and layer types.  There is no TP-4 ISA-executor VM for the other layers, so the
x of every field phase is taken from the golden layer replay itself (the same replay tools/dsrom_1m_su.py uses, whose
layer output is asserted bit-identical to the recorded w17 shard): every linear_q / linear_bf16 / mv call is logged
with its weight tensor, x and output, and the attention's wo_a group matvecs are recomputed from its o.

    golden  --layers 0,1,2,... --gold G     (checkpoint host) capture x / out of every field tensor -> G/fld_LNN.npz
    plan    --layer L --rank R --gold G --work W   the S81 1,792 binding's phases of (L, R), x = the rank's slice
    extract / build / run                   tools/dsrom_1m_field.py steps on W (unchanged vehicle, --qelem 10)
    check   --work W [--mutant]             PASS = every region run exact vs the field golden AND every row of the
                                            field golden == the model's own output row of this token (row-split
                                            tensors), K-split partials (wo_b) checked in `combine`
    combine --layer L --works W0,W1,W2,W3   wo_b: the four ranks' FP32 partials, summed in the die's order, == golden

The RTL vehicle is tools/dsrom_1m_field.py's (pinned spine + VM + one full-shape region, q element QX 10 on the
FP8/FP4 pairs), every region of the die, placed by the 1,792 binding.  Negative controls: `check --mutant` (one RTL
row word flipped must FAIL) and an RTL mutant build (--define CH_MUTANT_PD, ot_v41_chain4 forward swap) on one layer.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
F = np.float32
O_RANK = 1024                      # wo_a rows per group (wa = weight.reshape(groups, o_rank, -1))


def bits(x):
    return np.asarray(x, dtype=F).reshape(-1).view(np.uint32).copy()


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ----------------------------------------------------------------------------------------------------------- golden
def cmd_golden(a):
    import dsrom_1m_su as SU
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    out = a.gold
    out.mkdir(parents=True, exist_ok=True)
    layers = [int(x) for x in a.layers.split(",")]
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=True)
    G, CTX, SEED = SU.GOLD, SU.CTX, SU.SEED
    for L in layers:
        t0 = time.time()
        z = np.load(G / f"ctx{CTX}_L{L:02d}.npz")
        js = json.loads((G / f"ctx{CTX}_L{L:02d}.json").read_text())
        st, _ = LC.synthetic_state(m, CTX, seed=SEED, layers=[L])
        src = m.kv_of.get(L)
        if src is not None and src < L:
            zs = np.load(G / f"ctx{CTX}_L{src:02d}.npz")
            if f"ckv{src}" in zs.files:
                st["ckv"][src].append(zs[f"ckv{src}"])
                st["ik"][src].append(zs[f"ik{src}"])
        hist = json.loads((G / f"golden_ctx{CTX}_0-39.json").read_text())["history"]
        st["tokens"] = list(hist)
        cx = {"pos": CTX - 1, "hist": hist, "h": z["h_in"].copy(), "pre": z["pre_in"].copy()}
        if L > 0:
            carry = json.loads((G / f"ctx{CTX}_L{L - 1:02d}.json").read_text())["ctx_out"]
            if "sel" in carry:
                cx["sel"] = carry["sel"]
            if "cand_file" in carry:
                cx["cand"] = np.load(G / carry["cand_file"])["cand"]
        assert LC.digest(cx["h"], cx["pre"]) == js["input_sha256"]
        # the replay logs linear_q / linear_bf16 / mv (mv is what linear_bf16 calls: its FP32 out is the field's)
        cap, log, tr = SU._replay(m, L, st, cx, V)
        checks = dict(h_out=SU.same(cx["h"], z["h_out"]), pre_out=SU.same(cx["pre"], z["pre_out"]))
        names = {id(v): k for k, v in m.w.items() if k.startswith(f"layers.{L}.")}
        rec, seen = {}, {}
        for e in log:
            if e["fn"] not in ("linear_q", "linear_bf16", "mv"):
                continue
            n = names.get(id(e["args"][0]))
            if n is None:
                continue
            x = e["args"][1]
            assert not isinstance(x, V.Folded), (L, n)
            key = f"{n}|{e['fn']}"
            xb, ob = bits(x), bits(e["out"])
            if key in seen:                          # a tensor used twice must see the same x (else ambiguous)
                assert np.array_equal(rec[key + "|x"], xb), (L, key)
                continue
            seen[key] = 1
            rec[key + "|x"], rec[key + "|out"] = xb, ob
        # wo_a: the attention replica calls matvec_c per group (not logged): recompute from its o
        at = cap["attend"]
        wa = m.lw(L, "attn.wo_a.weight").reshape(m.groups, m.o_rank, -1)
        assert m.o_rank == O_RANK
        og = np.asarray(at["o"], F).reshape(m.groups, -1)
        zz = []
        for g in range(m.groups):
            r = V.matvec_c(wa[g], og[g], V.WO_A_SPLIT)
            rec[f"layers.{L}.attn.wo_a.weight#g{g}|matvec_c|x"] = bits(og[g])
            rec[f"layers.{L}.attn.wo_a.weight#g{g}|matvec_c|out"] = bits(r)
            zz.append(r)
        checks["wo_a_recomputed_z"] = SU.same(V.to_bf16(np.stack(zz).reshape(-1)), at["z"])
        np.savez(out / f"fld_L{L:02d}.npz", **rec)
        meta = dict(layer=L, kind=js["kind"], experts=js["experts"], checks=checks,
                    tensors=sorted({k.rsplit("|", 2)[0] for k in rec}), wall_s=round(time.time() - t0, 1))
        (out / f"fld_L{L:02d}.json").write_text(json.dumps(meta, indent=1) + "\n")
        print(f"L{L:02d} {js['kind']} {len(meta['tensors'])} tensors checks {checks} {meta['wall_s']} s", flush=True)
        assert all(checks.values()), (L, checks)
        for k in [k for k in m.w if k.startswith(f"layers.{L}.")]:
            del m.w[k]
        del st, log, cap
    return 0


# ------------------------------------------------------------------------------------------------------------- plan
def _xkey(cap, tensor, alias, rows0):
    """The captured key of the x a mat consumes (and its golden out), for tensor `tensor` (with '.weight')."""
    if ".attn.wo_a." in tensor:
        return f"{tensor}#g{rows0 // O_RANK}|matvec_c", rows0 // O_RANK * O_RANK
    for fn in ("mv", "linear_q", "linear_bf16"):         # mv first: the FP32 out of a BF16 linear
        if f"{tensor}|{fn}|x" in cap.files:
            return f"{tensor}|{fn}", 0
    raise KeyError(f"{tensor} ({alias}) not captured")


def cmd_plan(a):
    import dsrom_1m_field as FLD
    FLD.RANK = a.rank
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    L = a.layer
    cap = np.load(a.gold / f"fld_L{L:02d}.npz")
    gmeta = json.loads((a.gold / f"fld_L{L:02d}.json").read_text())
    sm = json.loads((FLD.S81 / "stage_map.json").read_text())
    rb, bfs = sm["region_bounds"], set(sm["BF_site_IDs"])
    FLD.BY_STAGE = "region_bounds_by_stage" in sm
    sbf = FLD.stage_bounds(sm)
    experts = gmeta["experts"]
    ents = []
    with gzip.open(FLD.S81 / "matrix_map.jsonl.gz", "rt") as f:
        for ln in f:
            r = json.loads(ln)
            if r["layer"] == L and (r["expert"] is None or r["expert"] in experts):
                ents.append(r)
    phases, xs, gold = [], {}, {}
    for grp_s, (node, _xsrc, mats) in FLD.layer_groups(L, ents, sbf, None).items():
        grp = grp_s.split("@")[0]
        K = mats[0]["K"]
        bf = mats[0]["fmt"] == "bf16"
        out = "fp32" if (bf or grp == "wo_b") else "bf16"
        xv = None
        for mm in mats:
            key, gbase = _xkey(cap, mm["tensor"] + ".weight", mm["alias"], mm["rows"][0])
            (c0, c1) = mm["cols"]
            v = cap[key + "|x"][c0:c1]
            assert xv is None or np.array_equal(v, xv), (L, grp, "mats of one phase must share x")
            xv = v
            mm["gold"] = dict(key=key, row_base=gbase, ksplit=(c1 - c0) != len(cap[key + "|x"]))
        assert len(xv) == K, (L, grp, len(xv), K)
        stage = {m_["stage"] for m_ in mats}
        assert len(stage) == 1
        stage = stage.pop()
        groups = FLD.phase_groups(mats)
        for g in groups:
            name = f"L{L}.{grp_s}" + ("" if len(groups) == 1 else "." + "+".join(x["alias"] for x in g))
            srb, sbs = sbf(stage)
            phases.append(dict(layer=L, node=node, phase=name, group=grp, stage=stage, out=out,
                               x_source=f"golden replay {g[0]['gold']['key']} cols {g[0]['cols']}",
                               **(dict(region_bounds=srb, bf_sites=sorted(sbs)) if FLD.BY_STAGE else {}),
                               K=K, fmts=sorted({m_["fmt"] for m_ in g}), mats=g,
                               regions=sorted({int(r) for m_ in g for r in m_["regions"]})))
            xs[name] = xv
    np.savez(work / "x.npz", **xs)
    plan = dict(schema="opentallas.s81.field_all.plan.v1", layers=[L], rank=a.rank, experts={str(L): experts},
                region_bounds=rb, bf_sites=sorted(bfs), phases=phases, gold=str(a.gold),
                gold_sha256=sha(a.gold / f"fld_L{L:02d}.npz"), gold_checks=gmeta["checks"],
                x_sha256={k: hashlib.sha256(v.tobytes()).hexdigest() for k, v in xs.items()})
    (work / "plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    print(f"L{L} r{a.rank}: {len(phases)} phases, {sum(len(p['regions']) for p in phases)} region runs")
    return 0


# ------------------------------------------------------------------------------------------------------------ check
def cmd_check(a):
    work = a.work.resolve()
    plan = json.loads((work / "plan.json").read_text())
    cap = np.load(Path(plan["gold"]) / f"fld_L{plan['layers'][0]:02d}.npz")
    runs = missing = failed = 0
    rows = rows_bound = ksplit_rows = 0
    model_mismatch, first_bad = 0, []
    flipped = False
    partial = {}
    for ph in plan["phases"]:
        al = {m["alias"]: m for m in ph["mats"]}
        for reg in ph["regions"]:
            rf = work / "runs" / ph["phase"] / f"r{reg:03d}" / "result.json"
            if not rf.exists():
                missing += 1
                continue
            r = json.loads(rf.read_text())
            runs += 1
            ok = r["pass_"]
            if a.mutant and not flipped and r.get("rtl"):
                # negative control: the RTL's own row word, one bit flipped, against the field golden
                fp32 = ph["out"] == "fp32"
                al0, _, f32, b16 = r["xcheck"][0]
                exp = f32 if fp32 else (b16 << 16)
                ok = ok and ((r["rtl"][0] or 0) ^ 1) == exp
                flipped = True
            failed += not ok
            if not ok and len(first_bad) < 4:
                first_bad.append(dict(phase=ph["phase"], region=reg, first_mismatch=r.get("first_mismatch")))
            for (alias, row, f32, b16) in r["xcheck"]:
                m = al[alias]
                rows += 1
                gk = m["gold"]
                grow = m["rows"][0] + row - gk["row_base"]
                if gk["ksplit"]:
                    ksplit_rows += 1
                    partial.setdefault(alias, {})[grow] = f32
                    continue
                g = int(cap[gk["key"] + "|out"][grow])
                mine = f32 if ph["out"] == "fp32" else (b16 << 16)
                if gk["key"].endswith("|linear_q") and ph["out"] == "fp32":
                    mine = None                     # an FP32-out FP8 phase that is not K split: never expected
                if mine is None or g != mine:
                    model_mismatch += 1
                    if len(first_bad) < 8:
                        first_bad.append(dict(phase=ph["phase"], alias=alias, row=grow, field=mine, model=g))
                else:
                    rows_bound += 1
    if partial:
        np.savez(work / "ksplit_partials.npz", **{k: np.array([v[i] for i in sorted(v)], np.uint32)
                                                  for k, v in partial.items()},
                 **{k + "|rows": np.array(sorted(v), np.int64) for k, v in partial.items()})
    ok = missing == 0 and failed == 0 and model_mismatch == 0 and runs > 0
    rec = dict(schema="opentallas.s81.field_all.check.v1", layer=plan["layers"][0], rank=plan["rank"],
               phases=len(plan["phases"]), region_runs=runs, region_runs_missing=missing, region_runs_failed=failed,
               rows_checked=rows, rows_equal_model_output=rows_bound, ksplit_partial_rows=ksplit_rows,
               rows_not_equal_model=model_mismatch, first_bad=first_bad, gold_checks=plan["gold_checks"],
               mutant=bool(a.mutant), verdict="PASS" if ok else "FAIL")
    (work / ("check_mutant.json" if a.mutant else "check.json")).write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{rec['verdict']} field L{rec['layer']} r{rec['rank']}{' MUTANT' if a.mutant else ''}: phases {rec['phases']} "
          f"runs {runs} (missing {missing}, failed {failed}) rows {rows} == model {rows_bound} ksplit {ksplit_rows} "
          f"model_mismatch {model_mismatch}", flush=True)
    return 0 if ok else 1


# ---------------------------------------------------------------------------------------------------------- combine
def cmd_combine(a):
    """K-split tensors (wo_b): the four ranks' FP32 partial rows reduced in the die's collective order == the model's
    output.  Orders tried: sequential r0+r1+r2+r3 and the pairwise tree (r0+r1)+(r2+r3); the matching one is named."""
    import hdc_golden_v41 as V
    works = [Path(w) for w in a.works.split(",")]
    plans = [json.loads((w / "plan.json").read_text()) for w in works]
    L = plans[0]["layers"][0]
    assert sorted(p["rank"] for p in plans) == [0, 1, 2, 3]
    cap = np.load(Path(plans[0]["gold"]) / f"fld_L{L:02d}.npz")
    parts = {p["rank"]: np.load(w / "ksplit_partials.npz") for p, w in zip(plans, works)}
    res = {}
    for k in parts[0].files:
        if k.endswith("|rows"):
            continue
        rows = parts[0][k + "|rows"]
        assert all(np.array_equal(parts[r][k + "|rows"], rows) for r in range(4))
        pv = [V.from_bits(parts[r][k].astype(np.uint32)).astype(F) if hasattr(V, "from_bits") else
              parts[r][k].astype(np.uint32).view(F) for r in range(4)]
        tens = next(m for ph in plans[0]["phases"] for m in ph["mats"] if m["alias"] == k)
        g = cap[tens["gold"]["key"] + "|out"][rows]
        orders = dict(seq=V.add(V.add(V.add(pv[0], pv[1]), pv[2]), pv[3]),
                      tree=V.add(V.add(pv[0], pv[1]), V.add(pv[2], pv[3])))
        res[k] = {o: int(np.sum(bits(V.to_bf16(v)) != g)) for o, v in orders.items()}
        res[k]["rows"] = int(len(rows))
    ok = all(min(v["seq"], v["tree"]) == 0 for v in res.values())
    rec = dict(schema="opentallas.s81.field_all.combine.v1", layer=L, tensors=res, verdict="PASS" if ok else "FAIL")
    out = Path(a.out or works[0].parent / f"combine_L{L:02d}.json")
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["verdict"], f"combine L{L}", res, flush=True)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("golden", "plan", "check", "combine"))
    ap.add_argument("--gold", type=Path)
    ap.add_argument("--layers", default="0,1,2,3,14,20,21,24")
    ap.add_argument("--layer", type=int)
    ap.add_argument("--rank", type=int, default=0)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--works", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--mutant", action="store_true")
    a = ap.parse_args()
    import hdc_golden_v41 as V
    V.set_arith("chunk8")
    return dict(golden=cmd_golden, plan=cmd_plan, check=cmd_check, combine=cmd_combine)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
