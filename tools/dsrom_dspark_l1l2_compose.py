#!/usr/bin/env python3
"""Compose the DS ROM DSpark MTP step with the two approved draft levers, L1 and L2 (S81, wavefront verify).

Successor of tools/dsrom_dspark_mtp_step_compose.py (whose bytes are pinned by its composition.json): it reads that
record's measured slices and transfer ratios and prices the draft under each lever.  Nothing here is measured; the
measured lever cycles enter through --l1-chain-ratio / --l2-sweep-ratio / --l2-chain-ratio.

The DSpark draft is 3 blocks over the 5 draft positions plus a SERIAL sampling chain: position i needs the token of
i - 1 for its Markov term, so as built every chain step runs a full lm_head matvec, the Markov matvec, a vocab-length
bias add and a vocab argmax select.  But the lm_head matvec of position i depends only on the block output h_i, not
on the previous token; only the Markov add and the argmax are serial.
  as built   chain step = head_occ x R_chain                        (R_chain = measured chain step / head step, 1.637)
  L1 fused   bias add and argmax ride the head's output stream, as the verify head's me_amax does:
             chain step = head_occ x (1 + R_markov)                 (R_markov = Markov / lm_head MACs, 32 / 4096)
  L2 batched the 5 lm_head matvecs leave the chain and run as one batched sweep over the block outputs, k vectors per
             ROM read (ot_v41_rom_elem_nv_w10, NV = k).  The serial chain keeps the Markov add + argmax only:
             draft head = sweeps(k) + 5 x chain_L2
             sweeps(k) = ceil(5 / k) x T_sweep(k)
               ROM-read-bound: T_sweep(k) = head_occ             (the MACs replicated per vector keep pace with the read)
               MAC-bound:      T_sweep(k) = (vectors in it) x head_occ, so sweeps(k) = 5 x head_occ (no gain)
               measured:       T_sweep(k) = head_occ x --l2-sweep-ratio k=R  (batched k-vector sweep / single head step)
             chain_L2 = head_occ x (R_chain - 1)   with the as-built separate SU add + XU select (L2 alone)
             chain_L2 = head_occ x R_markov        with L1's fused bias + argmax (L1 + L2)
  draft = 3 x block5 + draft head;  step = wavefront verify + draft + seed/commit;  MTP tok/s = tau x 1e6 / step.
A vector count k >= 6 can also batch the 6 verify heads (sensitivity only, occupancy rule): the head leaves the
wavefront II, which becomes the next-slowest stage, and its single batched sweep stays inside the AR term.

    python3 tools/dsrom_dspark_l1l2_compose.py [--out results/rtl/dsrom_dspark_l1l2_20261004/expected.json]
        [--l1-chain-ratio R] [--l2-chain-ratio R] [--l2-sweep-ratio k=R ...] [--chain-fixed-us U]
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "results/rtl/dsrom_dspark_step_slices_20261004/composition.json"
WAVE = ROOT / "results/rtl/dsrom_wavefront_verify_20261004/record.json"
OUT = ROOT / "results/rtl/dsrom_dspark_l1l2_20261004/expected.json"
DRAFT_POS = 5
VECTORS = (1, 2, 3, 5, 6)
# next-slowest stage occupancy once the head leaves the II (S73, 4f0c050b8 dsrom_wavefront_verify model.json q1)
SECOND_OCC_US = {"1048576": 11.62, "200000": 4.51}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load():
    comp = json.loads(COMP.read_text())
    wave = json.loads(WAVE.read_text())["composition"]
    return comp, wave


def draft_us(comp, variant, k=None, bound=None, meas=None, fixed=0.0):
    """Draft time (us) at full shape; variant in as_built, l1, l2, l1l2."""
    fs, tr = comp["full_shape"], comp["transfer_ratios"]
    h = fs["head_occ_us"]
    block5 = next(iter(fs["ctx"].values()))["draft_block5_us"]
    r_chain, r_mk = tr["chain_step_over_head_step"], tr["markov_over_head_macs_full"]
    meas = meas or {}
    blocks = 3 * block5
    if variant == "as_built":
        return blocks + DRAFT_POS * (h * r_chain + fixed), dict(chain_step_us=h * r_chain + fixed, sweep_us=0.0)
    if variant == "l1":
        r = meas.get("l1_chain_ratio", 1 + r_mk)
        return blocks + DRAFT_POS * (h * r + fixed), dict(chain_step_us=h * r + fixed, sweep_us=0.0)
    if variant == "l2":
        rc = meas.get("l2_chain_ratio_as_built_select", r_chain - 1)
    else:
        rc = meas.get("l2_chain_ratio", r_mk)
    n = math.ceil(DRAFT_POS / k)
    if bound == "measured":
        sweeps = n * h * meas["l2_sweep_ratio"][k]
    elif bound == "rom_read":
        sweeps = n * h
    else:                                      # a partly filled sweep pays only its own vectors' MAC time
        sweeps = DRAFT_POS * h
    chain = h * rc + fixed
    return blocks + sweeps + DRAFT_POS * chain, dict(chain_step_us=chain, sweeps=n, sweep_us=sweeps)


def step_rows(comp, wave, d_us, verify_head_batched=False):
    fs = comp["full_shape"]
    tau = fs["tau"]
    out = {}
    for ctx, c in fs["ctx"].items():
        r = {}
        for rule in ("occupancy", "window"):
            ver = c["fused_head"][f"wavefront_{rule}"]["verify_us"]
            if verify_head_batched:
                if rule != "occupancy":
                    r[rule] = None
                    continue
                ii = SECOND_OCC_US[ctx] * (1 + wave["measured_interval_overhead"]) + wave["hop_us"]
                ver = c["ar_us"] + 5 * ii
            step = ver + d_us + c["seed_commit_us"]
            r[rule] = dict(verify_us=round(ver, 2), step_us=round(step, 2), mtp_tok_s=round(tau * 1e6 / step, 1))
        out[ctx] = r
    return out


def compose(meas=None, fixed=0.0):
    comp, wave = load()
    fs = comp["full_shape"]
    ref = {}
    for v in ("as_built", "l1"):
        d, parts = draft_us(comp, v, meas=meas, fixed=fixed)
        ref[v] = dict(draft_us=round(d, 2), **{k: round(x, 3) for k, x in parts.items()},
                      ctx=step_rows(comp, wave, d))
    base = {ctx: ref["as_built"]["ctx"][ctx]["occupancy"]["mtp_tok_s"] for ctx in fs["ctx"]}
    bounds = ["rom_read", "mac"] + (["measured"] if meas and meas.get("l2_sweep_ratio") else [])
    l2 = {}
    for variant in ("l2", "l1l2"):
        for bound in bounds:
            for k in VECTORS:
                if bound == "measured" and k not in meas["l2_sweep_ratio"]:
                    continue
                d, parts = draft_us(comp, variant, k, bound, meas, fixed)
                row = dict(variant=variant, bound=bound, vectors=k, draft_us=round(d, 2),
                           draft_over_ar={ctx: round(d / c["ar_us"], 4) for ctx, c in fs["ctx"].items()},
                           **{x: round(y, 3) for x, y in parts.items()}, ctx=step_rows(comp, wave, d))
                for ctx, b in base.items():
                    row["ctx"][ctx]["gain_vs_as_built_occupancy"] = round(
                        row["ctx"][ctx]["occupancy"]["mtp_tok_s"] / b - 1, 4)
                if k >= 6:
                    row["verify_head_batched_sensitivity"] = step_rows(comp, wave, d, True)
                l2[f"{variant}/{bound}/k{k}"] = row
    return comp, wave, dict(tau=fs["tau"], head_occ_us=fs["head_occ_us"],
                            block5_us=next(iter(fs["ctx"].values()))["draft_block5_us"],
                            transfer_ratios=comp["transfer_ratios"], chain_fixed_us=fixed,
                            reference=ref, levers=l2)


def table(res):
    lines = ["| variant | bound | k | draft us | chain step us | 1M occ | 1M win | 200K occ | 200K win |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for v, r in res["reference"].items():
        c = r["ctx"]
        lines.append(f"| {v} | - | 1 | {r['draft_us']} | {r['chain_step_us']} | {c['1048576']['occupancy']['mtp_tok_s']} | "
                     f"{c['1048576']['window']['mtp_tok_s']} | {c['200000']['occupancy']['mtp_tok_s']} | "
                     f"{c['200000']['window']['mtp_tok_s']} |")
    for r in res["levers"].values():
        c = r["ctx"]
        lines.append(f"| {r['variant']} | {r['bound']} | {r['vectors']} | {r['draft_us']} | {r['chain_step_us']} | "
                     f"{c['1048576']['occupancy']['mtp_tok_s']} | {c['1048576']['window']['mtp_tok_s']} | "
                     f"{c['200000']['occupancy']['mtp_tok_s']} | {c['200000']['window']['mtp_tok_s']} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--l1-chain-ratio", type=float, help="MEASURED fused chain step / head step (same vehicle)")
    ap.add_argument("--l2-chain-ratio", type=float, help="MEASURED fused Markov + argmax chain step / head step")
    ap.add_argument("--l2-chain-ratio-as-built-select", type=float,
                    help="MEASURED Markov + SU add + XU select chain step / head step")
    ap.add_argument("--l2-sweep-ratio", action="append", default=[],
                    help="k=R: MEASURED batched k-vector head sweep / single head step (same vehicle)")
    ap.add_argument("--chain-fixed-us", type=float, default=0.0,
                    help="fixed serial latency per chain step (cross-die argmax and token broadcast), sensitivity")
    ap.add_argument("--measured-source", default="", help="where the measured ratios come from (record path / SHA)")
    ap.add_argument("--print-table", action="store_true")
    a = ap.parse_args()
    meas = {}
    if a.l1_chain_ratio is not None:
        meas["l1_chain_ratio"] = a.l1_chain_ratio
    if a.l2_chain_ratio is not None:
        meas["l2_chain_ratio"] = a.l2_chain_ratio
    if a.l2_chain_ratio_as_built_select is not None:
        meas["l2_chain_ratio_as_built_select"] = a.l2_chain_ratio_as_built_select
    if a.l2_sweep_ratio:
        meas["l2_sweep_ratio"] = {int(k): float(v) for k, v in (s.split("=") for s in a.l2_sweep_ratio)}
    comp, wave, res = compose(meas, a.chain_fixed_us)
    srcs = [Path(__file__), COMP, WAVE]
    rec = dict(schema="opentallas.dsrom-dspark-l1l2-composition.v1",
               status="measured" if meas else "expected (model; no lever measured yet)",
               measured_inputs=dict(meas, source=a.measured_source) if meas else None,
               result=res, basis=__doc__.split("\n\n")[1].strip() + "\n" + __doc__.split("\n\n")[2].strip(),
               source_commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                            text=True).stdout.strip(),
               input_sha256={str(p.relative_to(ROOT)): sha(p) for p in srcs})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(table(res) if a.print_table else json.dumps(res["reference"], indent=1))


if __name__ == "__main__":
    main()
