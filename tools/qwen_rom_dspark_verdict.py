#!/usr/bin/env python3
"""Qwen ROM 8K operating-mode verdict on the STREAM4 path: AR_MODE or DSPARK_PAYS.

Inputs (all records in the repository):
  * AR token on STREAM4: results/rtl/qwen_rom_kv_fullbw_20261004/compose_P8191_token.json (measured composition);
  * verify layers on STREAM4, measured exact at P8187 (np = 2, 3, 4; baseline and MERGE_SU programs): --verify NAME:NP:CYCLES:RESULT
  * draft terms: the DSpark ctx8k record (drafter layers 5 x D0 at S = 3, draft heads) + the measured ingest/Markov
    (fac4b889e, 75,000 at S = 3);
  * tau: third-party published (results/speculative/third_party_acceptance_20261004/acceptance.json), taken per
    draft length; lengths 1 and 2 by the same published derivation (per benchmark constant conditional acceptance
    r from the gamma-7 Table 1 values, tau_k = 1 + sum_{i<=k} r^i, equal weight; it reproduces the published
    3 and 4 values);
  * the single-pass area estimate: dspark_breakeven.json.
step(np) = 36 x verify(np) + verify head + draft(S = np - 1) + commit; per-user = tau(S) x clock / step.
DSpark pays iff some np gives tau(S) x AR token > step.

--relays (owner ADOPT 2026-10-07, die relay stations at the measured 430.56 um reach): the measured verify/draft
components ran on the token RTL's base wire stages, so every step is charged the SAME per-op stage deltas the AR
headline token is charged (relay_token_cost.json: delta_per_me_op on every ME op, delta_link_per_traversal on every
hub<->stack collective), plus the other adopted per-op / per-step AR levers given by --extra-per-me-op (slab
MUL_LAT 7: +1 a ME op) and --extra-per-step (KV_MAP Option M: +54 on the cold first layer).  ME ops and collectives
per component are counted from the RTL program images the components ran (RELAY_OPS); AR is the composed headline
token (--ar-cycles, tools/three_machine_compose.py qwen_rom.token_cycles).  ANALYTICAL composition of measured
cycles + priced stage deltas, the same method the AR headline uses for the relays."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import third_party_tau as T  # noqa: E402

HZ = 1.2e9

# ME ops / hub<->stack collectives a component issues, decoded from the program images the measured components ran
# (hdc_qwen_fullshape_isa_w12.decode_instruction unit field; die 0; ot-epyc1tb /srv/opentallas-scratch/claude/...):
#   qwen-dspark-system/img_p1/L0-d0 6 ME (AR layer) | img_p4/L0-d0 24 | img_p3/L0-d0 18 | fullbw-hbm/img_m4 24, img_m3 18
#   (MERGE_SU merges stream ops only) -> 6 ME a position a layer, 2 all-reduces a layer pass;
#   img_p1/head-d0 4 ME (chunked lm_head) | img_p4/head-d0 16 -> 4 ME + 1 argmax gather a position;
#   drafter/images/D0-d0 18 ME at S = 3 -> 6 ME a slot, 2 all-reduces a drafter layer;
#   ingest (tools/qwen_dspark_ingest_markov_rtl.py ING / CTXj / MKV programs, 14 / 10 / 3 words): ING 3 ME (FC x 3)
#   + 1 all-reduce; CTXj 1 ME (QKV) a context row a drafter layer (3 rows x 5 layers); MKV 1 ME a slot; the priced
#   argmax + gather a slot carries 2 link latencies.
RELAY_OPS = dict(me_per_position_layer=6, coll_per_layer=2, head_me_per_position=4, head_coll_per_position=1,
                 drafter_me_per_slot_layer=6, drafter_coll_per_layer=2, drafter_layers=5,
                 ingest_me=3 + 3 * 5, ingest_coll=1, markov_me_per_slot=1, markov_link_per_slot=2,
                 draft_head_me_per_slot=4, draft_head_coll_per_slot=1, ar_me_per_token_in_relay_record=217,
                 note="the AR relay record counts the head as 1 ME op and its argmax gather as 0 (217 = 36 x 6 + 1, "
                      "72 links); the RTL head issues 4 ME + 1 gather: +3 x delta_me + delta_link not charged to AR")


def tau_by_draft():
    acc = json.loads((ROOT / "results/speculative/third_party_acceptance_20261004/acceptance.json").read_text())
    q = acc["models"]["qwen3_8b"]["by_draft_tokens"]
    pb = q["3"]["per_benchmark"]

    def r_of(t3):
        lo, hi = 0.0, 1.0
        for _ in range(200):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if 1 + m + m * m + m ** 3 < t3 else (lo, m)
        return lo

    rs = [r_of(v) for v in pb.values()]
    out = {k: sum(1 + sum(r ** i for i in range(1, k + 1)) for r in rs) / len(rs) for k in (1, 2, 3, 4)}
    assert abs(out[3] - T.tau_qwen3_8b()) < 1e-3 and abs(out[4] - q["4"]["tau"]) < 1e-3
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="append", default=[], help="NAME:NP:CYCLES:RESULT_JSON (measured, exact)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--relays", type=Path, help="relay_token_cost.json: charge its per-op stage deltas to every step")
    ap.add_argument("--ar-cycles", type=int, help="AR headline token cycles (composed, with the same deltas)")
    ap.add_argument("--extra-per-me-op", type=int, default=0, help="other adopted per-ME-op AR deltas (slab MUL_LAT 7: 1)")
    ap.add_argument("--extra-per-step", type=int, default=0, help="other adopted per-token AR deltas (KV_MAP M: 54)")
    a = ap.parse_args()
    rel = json.loads(a.relays.read_text()) if a.relays else None
    if rel and not a.ar_cycles:
        raise SystemExit("--relays needs --ar-cycles (the composed AR headline token)")
    R = ROOT / "results/rtl"
    rec = json.loads((R / "qwen_dspark_system_20261004/ctx8k/step_composed_ctx8k.json").read_text())
    tok = json.loads((R / "qwen_rom_kv_fullbw_20261004/compose_P8191_token.json").read_text())
    be = json.loads((R / "qwen_rom_kv_fullbw_20261004/dspark_breakeven.json").read_text())
    ar = tok["stream4"]["token_cycles"]
    ar_wire = tok["wire_bound"]["bound_cycles"]
    if rel:
        ar = a.ar_cycles
    dme = (rel["delta_per_me_op"] + a.extra_per_me_op) if rel else 0
    dlk = rel["delta_link_per_traversal"] if rel else 0
    O = RELAY_OPS

    def relay_add(np_, S, bound):
        """priced stage cycles a step gains: (ME ops, links, cycles); drafter layers follow draft()'s S bound"""
        s_lay = 3 if (S == 3 or bound == "upper") else S
        me = (36 * O["me_per_position_layer"] * np_ + O["head_me_per_position"] * np_
              + O["drafter_layers"] * O["drafter_me_per_slot_layer"] * s_lay + O["draft_head_me_per_slot"] * S
              + O["ingest_me"] + O["markov_me_per_slot"] * S)
        lk = (36 * O["coll_per_layer"] + O["head_coll_per_position"] * np_ + O["drafter_layers"] * O["drafter_coll_per_layer"]
              + O["draft_head_coll_per_slot"] * S + O["ingest_coll"] + O["markov_link_per_slot"] * S)
        return me, lk, (me * dme + lk * dlk + a.extra_per_step) if rel else 0
    taus = tau_by_draft()
    dt = rec["composed"]["draft_terms"]
    head = rec["components_cycles"]["verify_head_p4_step1"]
    commit = rec["composed"]["commit_cycles"]
    layers_s3, heads_s3 = dt["drafter_layers_rtl"], dt["drafter_lm_head_S_slots_from_measured_heads"]
    ingest, markov_s3 = 70032, 4968

    def draft(S, bound):
        # S-dependent terms: draft heads and Markov scale with the slots (measured per slot); the drafter layers were
        # measured at S = 3 only: 'upper' keeps the S = 3 value, 'lower' scales it by S / 3 (both unvalidated for S < 3)
        lay = layers_s3 if (S == 3 or bound == "upper") else layers_s3 * S / 3
        return lay + heads_s3 * S / 3 + ingest + markov_s3 * S / 3

    rows = {}
    for v in a.verify:
        name, np_, cyc, res = v.split(":")
        np_, cyc = int(np_), int(cyc)
        r = json.loads(Path(res).read_text())
        S = np_ - 1
        tau = taus[S]
        row = {"np": np_, "draft_tokens": S, "tau": round(tau, 4), "verify_layer": cyc, "exact": r["status"] == "pass",
               "result": str(Path(res).relative_to(ROOT)) if Path(res).is_relative_to(ROOT) else res}
        for bound in ("upper", "lower"):
            d = draft(S, bound)
            me, lk, radd = relay_add(np_, S, bound)
            step = 36 * cyc + head + d + commit + radd
            if rel:
                row[f"relay_{bound}"] = dict(me_ops=me, link_traversals=lk, cycles=radd, measured_step=round(step - radd))
            row[f"draft_{bound}"] = round(d)
            row[f"step_{bound}"] = round(step)
            row[f"tok_s_{bound}"] = round(tau * HZ / step, 1)
            row[f"speedup_vs_ar_{bound}"] = round(tau * ar / step, 3)
        # break-even verify layer (measured, before its own relay share) with the relay cycles of the step kept
        ru, rl = relay_add(np_, S, "upper")[2], relay_add(np_, S, "lower")[2]
        row["break_even_verify_layer_draft_upper"] = round((tau * ar - draft(S, "upper") - commit - head - ru) / 36, 1)
        row["break_even_verify_layer_draft_lower"] = round((tau * ar - draft(S, "lower") - commit - head - rl) / 36, 1)
        row["break_even_verify_layer_free_draft"] = round((tau * ar - commit - head - ru) / 36, 1)
        rows[name] = row
    best = max(rows.values(), key=lambda x: x["speedup_vs_ar_lower"])
    verdict = "DSPARK_PAYS" if any(x["exact"] and x["speedup_vs_ar_upper"] > 1.0 for x in rows.values()) else "AR_MODE"
    out = {
        "schema": "opentallas.qwen-rom-dspark-verdict.v1",
        "verdict": verdict,
        "context": "Qwen3-8B ROM TP4, 8K (P8187..8191), 4-stack STREAM4 KV path, 1.2 GHz",
        "method": __doc__.split("\n\n", 1)[1].strip(),
        "ar": ({"token_cycles": ar, "tok_s": round(HZ / ar, 1), "record": "results/arch/three_machine_compose/compose.json "
                "qwen_rom.token_cycles (measured terminal token + adopted levers incl. the r21 relays)",
                "pre_relay_stream4_record": {"token_cycles": tok["stream4"]["token_cycles"],
                                             "record": "results/rtl/qwen_rom_kv_fullbw_20261004/compose_P8191_token.json"}}
               if rel else
               {"token_cycles": ar, "tok_s": round(HZ / ar, 1), "wire_bound_cycles": ar_wire,
                "wire_bound_tok_s": round(HZ / ar_wire, 1), "record": "results/rtl/qwen_rom_kv_fullbw_20261004/compose_P8191_token.json"}),
        "tau_by_draft_tokens": {str(k): round(v, 4) for k, v in taus.items()},
        "tau_source": T.tau_src("qwen3_8b"),
        "draft_terms_s3": {"drafter_layers_5xD0_realmem": layers_s3, "draft_heads": heads_s3, "ingest_measured": ingest,
                           "markov_measured_plus_priced_argmax": markov_s3, "source": "step_composed_ctx8k.json + ingest_markov_rtl/README.md (fac4b889e)"},
        "verify_head": head, "commit": commit,
        "variants": rows,
        "best": best,
        "single_pass_area": be.get("single_pass_4pos_area_estimate"),
        "levers": json.loads((R / "qwen_rom_kv_fullbw_20261004/dspark_levers.json").read_text()),
        "unvalidated": ["drafter layers at S < 3 (bounded: S = 3 value upper, x S/3 lower)",
                        "drafter layers measured on REAL_MEM, not STREAM4",
                        "draft argmax + gather priced (3 x 736 at S = 3)",
                        "verify head for np < 4 taken at the np = 4 value (upper)"],
    }
    if rel:
        out["context"] += ", die r21 relay stations at 430.56 um charged on every ME op and collective"
        out["relays"] = {"record": str(a.relays.resolve().relative_to(ROOT)), "decision": rel.get("decision"),
                         "delta_per_me_op": rel["delta_per_me_op"], "delta_link_per_traversal": rel["delta_link_per_traversal"],
                         "extra_per_me_op": a.extra_per_me_op, "extra_per_me_op_what": "slab MUL_LAT 7 (+1 a ME op, adopted r11c)",
                         "extra_per_step": a.extra_per_step, "extra_per_step_what": "KV_MAP Option M cold first layer (+54, adopted)",
                         "ops": RELAY_OPS, "pre_relay_verdict": "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verdict.json",
                         "status": "ANALYTICAL: measured RTL component cycles + priced stage deltas (same method as the AR headline's relays)"}
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("verdict", "ar", "tau_by_draft_tokens")}, indent=1))
    for n, x in rows.items():
        print(n, {k: x[k] for k in ("np", "tau", "verify_layer", "exact", "speedup_vs_ar_upper", "speedup_vs_ar_lower",
                                     "break_even_verify_layer_draft_lower")})


if __name__ == "__main__":
    main()
