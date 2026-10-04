#!/usr/bin/env python3
"""Compose the DS ROM DSpark MTP step (S81, wavefront verify) from the measured minimum-component slices.

Measured (tools/dsrom_dspark_step_slices_rtl.py, one speculative step on the as-built V4.1 core, gamma 5, every
section bit-exact): the draft = embed + three DSpark blocks over the 5 draft positions + the draft head, a SERIAL
sampling chain (row i needs row i-1's token: lm_head matvec, Markov matvec on the previous draft token, vocab bias
add, vocab argmax select); verify = prologue + 40 layers x 6 positions + 6 heads; DSpark seeding; ACCEPT (commit).

The reduced vehicle (dim 160, vocab 4,040) is not shape-faithful, so each draft section is transferred to the
full shape through the section whose full-shape time the S81 model already prices, using the measured
cycle ratio on the same vehicle:
  block5 (one DSpark block, 5 positions)   = measured block5 / measured non-scan verify layer (6 positions)
                                             x the S81 m = 1 verify pass time per layer (heads removed);
  chain step (one draft position)          = head_occ (S81 lm_head per position; the RTL head II equals its
                                             latency, so positions do not overlap) x
                                             (1 + Markov MACs / lm_head MACs)            [fused: bias add and
                                             argmax ride the head's output stream, as the verify head's me_amax does]
                                             or x measured chain step / measured head step [as built: separate
                                             vocab-length SU add + XU select, the reduced core's relative cost].
  seed + commit                            = measured share of the verify pass x the S81 verify pass.
The draft runs after the previous verify (it needs the accepted state), so step = wavefront verify + draft +
seed + commit.  The draft does not depend on context (it runs on the head dies).

    python3 tools/dsrom_dspark_mtp_step_compose.py [--out results/rtl/dsrom_dspark_step_slices_20261004/composition.json]
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/dsrom_dspark_step_slices_20261004"
WAVE = ROOT / "results/rtl/dsrom_wavefront_verify_20261004/record.json"
DIM, VOCAB, MARKOV_IN = 160, 4040, 32          # reduced vehicle; the Markov block reads a 32-wide token embedding
FULL_DIM, FULL_VOCAB = 4096, 129280             # DeepSeek-V4.1-Flash hidden size and vocabulary
OLD_DRAFT_OVER_AR = 0.1173                     # the assumption this record replaces
NONSCAN = "L4"                                 # a non-scan, non-Engram verify layer (every such layer is identical)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=REC / "composition.json")
    a = ap.parse_args()
    res = {v: json.loads((REC / v / "result.json").read_text()) for v in ("dspark", "forced")}
    plain = json.loads((REC / "plain/plain-on2.json").read_text())
    wave = json.loads(WAVE.read_text())["composition"]
    r = res["dspark"]
    cyc = {s["name"]: s["cycles"] - r["null_slice_cycles"] for s in r["slices"] if s["name"] != "null"}
    # both drafters run the same instructions (the forced drafter only replaces the tokens): identical cycles
    same = all(s["cycles"] == t["cycles"] for s, t in zip(r["slices"], res["forced"]["slices"]))
    g = r["composed"]["groups"]
    head6 = cyc["head"]
    block5 = cyc["draft_L40"]
    chain5 = cyc["draft_1"]
    meas = dict(
        step_cycles=r["composed"]["step_cycles"], draft_cycles=g["draft"]["cycles"],
        verify_cycles=r["composed"]["verify_cycles"], dspark_seed_cycles=g["dspark_seed"]["cycles"],
        commit_cycles=g["commit"]["cycles"], draft_embed_cycles=cyc["draft"], draft_block5_cycles=block5,
        draft_blocks=[cyc[n] for n in ("draft_L40", "draft_L41", "draft_L42")], draft_head_chain5_cycles=chain5,
        verify_head6_cycles=head6, verify_nonscan_layer6_cycles=cyc[NONSCAN],
        ar_cycles_per_token=plain["runs"][0]["rtl"]["cycles_per_token"], ar_prompt=plain["runs"][0]["image"],
        identical_cycles_dspark_vs_forced=same, all_slices_pass=r["all_slices_pass"] and res["forced"]["all_slices_pass"],
        isa_step={v: res[v]["isa_step"] for v in res})
    meas["draft_over_ar_reduced"] = round(meas["draft_cycles"] / meas["ar_cycles_per_token"], 4)
    meas["verify_over_ar_reduced"] = round(meas["verify_cycles"] / meas["ar_cycles_per_token"], 4)
    meas["draft_over_verify_reduced"] = round(meas["draft_cycles"] / meas["verify_cycles"], 4)
    ratios = dict(block5_over_verify_layer6=block5 / cyc[NONSCAN],
                  chain_step_over_head_step=(chain5 / 5) / (head6 / 6),
                  markov_over_head_macs_full=MARKOV_IN / FULL_DIM,
                  markov_over_head_macs_reduced=MARKOV_IN / DIM,
                  seed_commit_over_verify=(meas["dspark_seed_cycles"] + meas["commit_cycles"]) / meas["verify_cycles"])
    head_occ = 12.37                           # us per lm_head position, S81 (dsrom_wavefront_rtl_campaign STAGE_US)
    rows = {}

    def vpass(c):                              # S81 m = 1 verify pass (6 positions)
        return c["pass_m1"]["step_us"] - OLD_DRAFT_OVER_AR * c["ar_us"]
    # the DSpark blocks run on the head dies with no index scan: price their layer from the 200K pass (the
    # least scan-loaded S81 figure; still includes the scan layers, so an upper bound) at every context
    layer6 = (vpass(wave["ctx"]["200000"]) - 6 * head_occ) / 40
    block5_us = ratios["block5_over_verify_layer6"] * layer6
    for ctx, c in wave["ctx"].items():
        ar = c["ar_us"]
        verify_pass = vpass(c)
        sc = ratios["seed_commit_over_verify"] * verify_pass
        out = dict(ar_us=ar, verify_pass_m1_us=round(verify_pass, 2), verify_layer6_us=round(layer6, 3),
                   draft_block5_us=round(block5_us, 3), seed_commit_us=round(sc, 3),
                   old=dict(draft_us=round(OLD_DRAFT_OVER_AR * ar, 2),
                            mtp_tok_s=c["wavefront_occupancy"]["mtp_tok_s"]))
        for variant, step_f in (("fused_head", 1 + ratios["markov_over_head_macs_full"]),
                                ("as_built_chain", ratios["chain_step_over_head_step"])):
            chain_us = 5 * head_occ * step_f
            draft = 3 * block5_us + chain_us
            v = dict(draft_chain5_us=round(chain_us, 2), draft_us=round(draft, 2), draft_over_ar=round(draft / ar, 4))
            for rule in ("occupancy", "window"):
                ver = c[f"wavefront_{rule}"]["verify_us"]
                step = ver + draft + sc
                v[f"wavefront_{rule}"] = dict(verify_us=ver, step_us=round(step, 2),
                                              mtp_tok_s=round(wave["tau"] * 1e6 / step, 1),
                                              vs_old=round((wave["tau"] * 1e6 / step)
                                                           / c[f"wavefront_{rule}"]["mtp_tok_s"] - 1, 4))
            out[variant] = v
        rows[ctx] = out
    srcs = [Path(__file__), WAVE, REC / "plain/plain-on2.json", *(REC / v / "result.json" for v in res)]
    rec = dict(schema="opentallas.dsrom-dspark-mtp-step-composition.v1",
               measured_reduced=meas, transfer_ratios={k: round(v, 5) for k, v in ratios.items()},
               full_shape=dict(tau=wave["tau"], head_occ_us=head_occ, ctx=rows,
                               note="draft is context-independent (head dies); verify from the adopted wavefront "
                                    "record; tau inherited from it"),
               replaces=dict(draft_over_ar=OLD_DRAFT_OVER_AR, source="tools/dsrom_wavefront_rtl_campaign.py "
                                                                     "DRAFT_OVER_AR (main 025d24e3b)"),
               basis=__doc__.split("\n\n")[1].strip(),
               source_commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                            text=True).stdout.strip(),
               input_sha256={str(p.relative_to(ROOT)): sha(p) for p in srcs})
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(measured={k: meas[k] for k in ("step_cycles", "draft_cycles", "verify_cycles",
                                                          "dspark_seed_cycles", "commit_cycles", "ar_cycles_per_token",
                                                          "draft_over_ar_reduced")},
                          ratios=rec["transfer_ratios"], s81=rows), indent=1))


if __name__ == "__main__":
    main()
