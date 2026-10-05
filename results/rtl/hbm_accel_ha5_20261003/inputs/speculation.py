#!/usr/bin/env python3
"""DeepSeek-V4.1 HBM comparator: price the checkpoint's speculative method (DSpark) against AR, with the real draft
cost and the measured MoE expert union of the verify pass (opt-in; no default row or pinned file changes).

    python3 tools/v41_hbm_speculation_methods.py union --router ROUTER.pt --out results/.../router_union.json
    python3 tools/v41_hbm_speculation_methods.py price --out results/.../v41_hbm_speculation_methods.json

WHAT THE "MTP" OF V4.1 IS.  DeepSeek-V4.1-Flash ships no V3-style chained MTP.  Its num_nextn_predict_layers = 3
modules (mtp.0-2) are ONE DSpark block drafter (config dspark_block_size 5, vendor inference/model.py DSparkBlock):
the three stages run in series over a block of 5 slots [verified token, noise x4] and draft 5 tokens in one call
(semi-autoregressive: the 3 stages are parallel over the 5 slots; only the rank-256 Markov head is sequential, one
argmax per slot).  Every repo "MTP" row (V41_TAU 3.649, gamma 5, 6 verified positions) is therefore DSpark already.

UNION.  Verifying P positions in one TP-96 pass streams the union of the routed experts (6 of 384 a position a
layer): measured here on the model's own greedy continuations (router-only capture, tools/v41_dspark_onpolicy/
v41router.py), against the uniform-routing formula the audit used and W19's one-window synthetic-state union.

PRICES.  Every term is the W19 composer (claude/w19-hbm-token 71b3ffc5, vendored byte-for-byte as an input of the
record, reproducing AR 442.14 us and the P = 6 verify pass 715.82 us) on W19's own measured element records:
  verify(P)  the composer's MTP mode with the measured per-layer union at P;
  draft      a program built from W19's layer-0 ops (a sliding-window, no-indexer, no-Engram layer, as a DSpark
             stage is) x 3 stages at P = 5 slots, 128 experts top-3 with the drafter's measured union, stage 0
             prefixed with main_proj (5,120 x 15,360 FP8) + main_norm; the LM head over the 5 slots; then 5 serial
             Markov steps (rank-256 head over 129,280 rows, local argmax, 96-way argmax merge, embed-row fetch).
Step = verify(gamma + 1) + draft (strictly serial: the draft needs the verify's bonus token and the layer-37..39
attention inputs of the last accepted position).  Rate = tau(gamma) / step.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC_DIR = ROOT / "results/speculative/v41_hbm_speculation_methods_20261003"
COMPOSER = REC_DIR / "inputs/w19_hbm_token_compose_71b3ffc5.py"
R = "results/rtl/"
W19_INPUTS = dict(program=R + "w19_hbm_tp96_program_oreduce.json",
                  sm=[R + "w19_sm_real_ops.json", R + "w19_sm_real_ops_oreduce.json"],
                  fetch=R + "w19_expert_fetch.json", coll=R + "w15_hbm_nvls.json",
                  select=R + "w15_topk_merge_hbm96_p1024f256.json",
                  mtp_isa=R + "w19_hbm_tp96_isa_mtp_oreduce.json")
W19_REF = dict(ar_us=442.14, mtp_pass_us=715.82, drafter_us=49.9)     # uarch_model.HBM_W19
CTXS = (1048576, 200000)
N_LAYERS, N_EXP, TOPK = 40, 384, 6
D_EXP, D_TOPK, BLOCK = 128, 3, 5
V41_TAU = 3.649
DRAFT_FRACTION_ASSUMED = 3 / 40
ROM_PILOT = dict(ar_us=358.8, step_g5_us=795.2, src="results/speculative/v41_mtp_acceptance_pilot_20261003/"
                 "mtp_acceptance.json sensitivity.designs.v41_rom_product (T_ar 358.8 us, step 795.2 us at gamma 5 "
                 "with the ASSUMED 3/40 draft)")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def uniform_union(p, E=N_EXP, k=TOPK):
    return E * (1 - (1 - k / E) ** p)


# ------------------------------------------------------------------------------------------------- union
def cmd_union(a):
    import torch
    gen = torch.load(a.router, weights_only=False)
    P_MAX = 8
    acc = {p: [[0.0, 0] for _ in range(N_LAYERS)] for p in range(1, P_MAX + 1)}
    mult = {p: [0.0, 0] for p in range(1, P_MAX + 1)}
    sub = {}
    prompt_acc = {p: [0.0, 0] for p in (6,)}
    d_acc = [[0.0, 0] for _ in range(3)]
    d_slots = [0.0, 0]
    agree = [0, 0]
    per_trace = []
    for tr in gen:
        idx = tr["router_idx"].long()                      # [40, n, 6]
        L, n = tr["L"], idx.size(1)
        oh = torch.zeros(N_LAYERS, n, N_EXP, dtype=torch.int32)
        oh.scatter_(2, idx, 1)
        cs = torch.cat([torch.zeros(N_LAYERS, 1, N_EXP, dtype=torch.int32), oh.cumsum(1)], 1)
        wl = tr["item"]["workload"]
        for p in range(1, P_MAX + 1):
            q0, q1 = L, n - p + 1                          # windows of p consecutive generated positions
            if q1 <= q0:
                continue
            cnt = cs[:, q0 + p:q1 + p] - cs[:, q0:q1]     # [40, windows, 384]
            u = (cnt > 0).sum(-1).double()                 # distinct experts per window
            for l in range(N_LAYERS):
                acc[p][l][0] += u[l].sum().item(); acc[p][l][1] += u.size(1)
            mx = cnt.max(-1).values.double()
            mult[p][0] += mx.sum().item(); mult[p][1] += mx.numel()
            s = sub.setdefault(wl, {}).setdefault(p, [0.0, 0])
            s[0] += u.sum().item(); s[1] += u.numel()
        q1 = min(L, n) - 6 + 1                             # prompt-region windows (teacher-forced prompt tokens)
        if q1 > 0:
            cnt = cs[:, 6:q1 + 6] - cs[:, 0:q1]
            u = (cnt > 0).sum(-1).double()
            prompt_acc[6][0] += u.sum().item(); prompt_acc[6][1] += u.numel()
        for p, di in tr.get("drafter_idx", {}).items():   # [3 stages, 5 slots, 3]
            di = di.long()
            for s in range(di.size(0)):
                d_acc[s][0] += len(set(di[s].flatten().tolist())); d_acc[s][1] += 1
                d_slots[0] += di.size(1); d_slots[1] += 1
        if "drafts_agree_with_pilot" in tr:
            agree[0] += tr["drafts_agree_with_pilot"][0]; agree[1] += tr["drafts_agree_with_pilot"][1]
        per_trace.append(dict(prompt_id=tr["item"]["prompt_id"], workload=wl, L=L, n=n, generated=n - L))
    out = dict(
        schema="opentallas.v41-router-union.v1",
        source=dict(router_pt=str(a.router), router_pt_sha256=sha(a.router)),
        definition="U(p) = mean over windows of p consecutive GENERATED positions (the model's own greedy "
                   "continuation, teacher-forced) of the number of distinct routed experts (top-6 of 384) in a "
                   "layer; mean over windows within each layer, pooled over traces",
        traces=len(gen), generated_positions=sum(t["generated"] for t in per_trace),
        union_by_p={str(p): dict(mean_over_layers=round(sum(v / max(c, 1) for v, c in acc[p]) / N_LAYERS, 3),
                                 per_layer=[round(v / max(c, 1), 3) for v, c in acc[p]],
                                 windows_per_layer=acc[p][0][1],
                                 uniform_routing=round(uniform_union(p), 3))
                    for p in acc},
        max_multiplicity_by_p={str(p): round(v / max(c, 1), 3) for p, (v, c) in mult.items()},
        union_by_workload={w: {str(p): round(v / max(c, 1), 3) for p, (v, c) in d.items()} for w, d in sub.items()},
        prompt_region_union_p6=round(prompt_acc[6][0] / max(prompt_acc[6][1], 1), 3),
        drafter=dict(definition="distinct experts (top-3 of 128) over the 5 block slots of one DSpark call, per stage",
                     union_per_stage=[round(v / max(c, 1), 3) for v, c in d_acc],
                     calls=d_acc[0][1], uniform_routing=round(uniform_union(BLOCK, D_EXP, D_TOPK), 3)),
        drafts_teacher_forced_vs_pilot_decode_path=dict(agree=agree[0], rows=agree[1]),
        per_trace=per_trace)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("per_trace", "union_by_workload")}, indent=1)[:4000])


def cmd_tau(a):
    """Exact greedy speculative replay at gamma 1..5 from DSpark drafts (truncating the same 5-token block is exact
    for a block drafter: the drafts do not depend on gamma)."""
    trs = json.loads(Path(a.drafts).read_text())
    multi = ("agentic_swe", "agentic_tau", "agentic_mind2web")
    def acc_rows(tr):
        toks, L = tr["tokens"], tr["L"]
        last = len(toks) - 1
        out = {}
        for p, d in tr["drafts"].items():
            p = int(p)
            if p + 1 + 5 > last:
                continue
            k = 0
            while k < 5 and d[k] == toks[p + 2 + k]:
                k += 1
            out[p] = k
        return out
    res = {}
    for name, sel in (("agentic_all5_pilot_n30", lambda w: True),
                      ("agentic_multiturn_pilot", lambda w: w.startswith(multi))):
        row = {}
        for g in range(1, 6):
            com = cyc = 0
            for tr in trs:
                if not sel(tr["item"]["workload"]):
                    continue
                acc = acc_rows(tr)
                p = tr["L"]
                while p in acc:
                    a5 = min(acc[p], g)
                    com += a5 + 1; cyc += 1; p += a5 + 1
            row[str(g)] = dict(tau=round(com / cyc, 4), cycles=cyc)
        res[name] = row
    out = dict(schema="opentallas.v41-dspark-tau-by-gamma.v1", drafts=str(a.drafts), drafts_sha256=sha(a.drafts),
               definition="tau(gamma) = committed tokens per verify cycle (bonus included), exact greedy replay "
                          "(analyze.walk) with acceptance truncated at gamma", sets=res)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


# ------------------------------------------------------------------------------------------------- pricing
def load_composer():
    spec = importlib.util.spec_from_file_location("w19c", COMPOSER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class W19:
    def __init__(self):
        self.C = C = load_composer()
        rd = lambda p: json.loads((ROOT / p).read_text())                      # noqa: E731
        self.prog = rd(W19_INPUTS["program"])
        self.sm = C.SMTable([rd(p) for p in W19_INPUTS["sm"]], "ar")
        self.coll = C.w15_prod(rd(W19_INPUTS["coll"]), "hbm_p48_ss")
        sr = rd(W19_INPUTS["select"])
        self.coll["select_cycles"] = next(c["cycles"] for c in sr["cases"] if c["case"] == "l20_index_topk" and c["exact"])
        fr = rd(W19_INPUTS["fetch"])
        self.fetch_us = fr["audit_comparison"]["exposed_ns"]["ar_L0_refresh_postponed"] / 1e3
        case = next(c for c in fr["cases"] if c["case"] == "mtp_union35_refresh_postponed")
        self.stream_per_expert = (case["ns_from_first_router_value"]["done"] - case["ns_from_first_router_value"]["req"]) / 1e3 / 35
        self.routed_sm_us = 12 * self.sm.op("fp4", 5120, 1)[0] / C.F_FAST * 1e6
        C.FUSION["on"] = True                                                   # W19 fused (the selected AR)
        mr = next(iter(rd(W19_INPUTS["mtp_isa"])["runs"].values()))["result"]
        self.w19_union = {l["layer"]: l["n_union"] for l in mr["layers"]}

    def m(self):
        C = self.C
        return dict(n_keys=0, node_parts=C.NODE_PARTS, fusion=True, off_path=sorted(C.OFF_PATH))

    def prog_ctx(self, ctx):
        p = copy.deepcopy(self.prog)
        for lay in p["layers"]:
            for op in lay["ops"]:
                if op["kind"] == "local" and "n" in op and op.get("fn") in ("index_scores", "cand_local", "cand_mask"):
                    op["n"] = math.ceil(op["n"] * ctx / 1048576)
        return p

    def run(self, prog, P=1, union=None):
        mtp = None
        if P > 1 or union is not None:
            mtp = dict(P=P, union=union, stream_us_per_expert=self.stream_per_expert, routed_sm_us=self.routed_sm_us)
        return self.C.compose(prog, self.sm, self.coll, self.fetch_us, self.m(), mtp)

    # the DSpark drafter program, built from W19's layer-0 ops
    def draft_programs(self):
        L0 = next(l for l in self.prog["layers"] if l["layer"] == 0)
        head = next(l for l in self.prog["layers"] if l["layer"] == "head")
        split = lambda n: [[n * r // 96, n * (r + 1) // 96] for r in range(96)]      # noqa: E731
        stages = []
        for s in range(3):
            ops = []
            if s == 0:
                ops += [dict(kind="mv", unit="SM", layer=0, fn="linear_q", n=5120, k=15360, fmt="fp8",
                             rows=split(5120), tag="dspark main_proj (concat of layers 37-39 attention inputs)"),
                        dict(kind="all_gather", unit="COLL", layer=0, bufs=["main_x"], elems=5120, bytes=10240,
                             dest="all", tag="main_x gather"),
                        dict(kind="local", unit="DU", layer=0, fn="hc_pre_norm", ranks="all", tag="main_norm")]
            for op in copy.deepcopy(L0["ops"]):
                if op["kind"] == "mv" and op["tag"] == "router gate":
                    op["n"], op["rows"] = D_EXP, split(D_EXP)
                if op["kind"] == "all_gather" and op["tag"] == "expert_intermediate_gather":
                    op["elems"], op["bytes"] = (D_TOPK + 1) * 2304, (D_TOPK + 1) * 2304 * 2
                ops.append(op)
            stages.append(dict(layer=f"dspark{s}", ops=ops))
        hops = [op for op in copy.deepcopy(head["ops"]) if op["kind"] != "topk_merge" and op.get("fn") != "argmax_local"]
        markov = [dict(kind="expert_fetch", unit="HBM", layer="markov", experts=1, tag="markov embed row of the "
                       "previous slot's token (replicated table, one data-dependent first access)"),
                  dict(kind="mv", unit="SM", layer="markov", fn="mv", n=129280, k=256, fmt="bf16", rows=split(129280),
                       tag="markov head (rank 256) logit bias"),
                  next(op for op in head["ops"] if op.get("fn") == "argmax_local"),
                  next(op for op in head["ops"] if op["kind"] == "topk_merge")]
        return dict(layers=stages), dict(layers=[dict(layer="dhead", ops=hops)]), dict(layers=[dict(layer="markov", ops=markov)])

    def draft(self, u_stage):
        st, hd, mk = self.draft_programs()
        a = self.run(st, BLOCK, {f"dspark{s}": u_stage[s] for s in range(3)})
        b = self.run(hd, BLOCK, {})
        c = self.run(mk, 1, None)
        parts = {k: a["parts_us"][k] + b["parts_us"][k] + BLOCK * c["parts_us"][k] for k in a["parts_us"]}
        return dict(total_us=round(a["total_us"] + b["total_us"] + BLOCK * c["total_us"], 2),
                    stages_us=a["total_us"], head_us=b["total_us"], markov_step_us=c["total_us"],
                    markov_steps=BLOCK, parts_us={k: round(v, 2) for k, v in parts.items()},
                    flags=sorted(set(a["flags"]) | set(b["flags"]) | set(c["flags"])))


def cmd_price(a):
    w = W19()
    uj = json.loads((REC_DIR / "router_union.json").read_text())
    tj = json.loads((REC_DIR / "tau_by_gamma.json").read_text())
    onp = json.loads((ROOT / "results/speculative/v41_flash_dspark_onpolicy_greedy.json").read_text())
    surv = onp["results"]["overall"]["walk"]["survival_by_position"]
    p1m = w.prog_ctx(1048576)
    # reproduction gate: the composer + inputs give W19's committed numbers
    ar_chk = w.run(p1m)["total_us"]
    v_chk = w.run(p1m, 6, w.w19_union)["total_us"]
    repro = dict(ar_us=ar_chk, verify_p6_w19_union_us=v_chk, expected=W19_REF,
                 ok=abs(ar_chk - W19_REF["ar_us"]) < 0.01 and abs(v_chk - W19_REF["mtp_pass_us"]) < 0.01)
    assert repro["ok"], repro
    meas = {int(p): {l: v["per_layer"][l] for l in range(N_LAYERS)} for p, v in uj["union_by_p"].items()}
    unif = {p: {l: uniform_union(p) for l in range(N_LAYERS)} for p in range(1, 9)}
    u_draft_meas = uj["drafter"]["union_per_stage"]
    u_draft_unif = [uniform_union(BLOCK, D_EXP, D_TOPK)] * 3
    dr_meas = w.draft(u_draft_meas)
    dr_unif = w.draft(u_draft_unif)
    tau_sets = {"current_headline_mixed_n36 (gamma<5 derived by truncation of the walk survival)":
                {str(g): round(1 + sum(surv[:g]), 4) for g in range(1, 6)}}
    for k, v in tj["sets"].items():
        tau_sets[k + " (exact replay)"] = {g: x["tau"] for g, x in v.items()}
    ctx_rows = {}
    for ctx in CTXS:
        pc = w.prog_ctx(ctx)
        ar = w.run(pc)
        ver = {}
        for P in range(2, 7):
            vm = w.run(pc, P, meas[P])
            vu = w.run(pc, P, unif[P])
            ver[P] = dict(measured_union_us=vm["total_us"], uniform_union_us=vu["total_us"],
                          parts_measured_us=vm["parts_us"], mean_union_measured=round(sum(meas[P].values()) / N_LAYERS, 3),
                          mean_union_uniform=round(uniform_union(P), 3))
        ver[6]["w19_isa_union_us"] = w.run(pc, 6, w.w19_union)["total_us"]
        rates = {}
        for ts, tg in tau_sets.items():
            rr = []
            for g in range(1, 6):
                P = g + 1
                step = ver[P]["measured_union_us"] + dr_meas["total_us"]
                tau = tg[str(g)]
                rr.append(dict(gamma=g, verify_positions=P, tau=tau, step_us=round(step, 2),
                               tokens_s=round(tau * 1e6 / step, 1), speedup_vs_ar=round(tau * ar["total_us"] / step, 3)))
            best = max(rr, key=lambda r: r["tokens_s"])
            rates[ts] = dict(by_gamma=rr, best_gamma=best["gamma"], best_tokens_s=best["tokens_s"])
        g5 = ver[6]
        ctx_rows[str(ctx)] = dict(
            ar_us=ar["total_us"], ar_tokens_s=round(1e6 / ar["total_us"], 1), verify_by_P=ver, rates=rates,
            headline_comparison_tau_3649_gamma5=dict(
                current_W19_row=dict(step_us=round(W19_REF["mtp_pass_us"] + W19_REF["drafter_us"], 2),
                                     tokens_s=round(V41_TAU * 1e6 / (W19_REF["mtp_pass_us"] + W19_REF["drafter_us"]), 1),
                                     note="uarch_model.HBM_W19 (1M only): W19 ISA one-window union + audit drafter 49.9 us"),
                assumed_3_40_draft=dict(step_us=round(g5["measured_union_us"] + DRAFT_FRACTION_ASSUMED * ar["total_us"], 2),
                                        tokens_s=round(V41_TAU * 1e6 / (g5["measured_union_us"] + DRAFT_FRACTION_ASSUMED * ar["total_us"]), 1)),
                dspark_priced=dict(step_us=round(g5["measured_union_us"] + dr_meas["total_us"], 2),
                                   tokens_s=round(V41_TAU * 1e6 / (g5["measured_union_us"] + dr_meas["total_us"]), 1)),
                dspark_priced_uniform_union=dict(step_us=round(g5["uniform_union_us"] + dr_unif["total_us"], 2),
                                                 tokens_s=round(V41_TAU * 1e6 / (g5["uniform_union_us"] + dr_unif["total_us"]), 1))))
    # ROM note: re-price only the draft term of the pilot's ROM step with the HBM-structural draft ratio
    ratio = dr_meas["total_us"] / ctx_rows["1048576"]["ar_us"]
    rom_verify = ROM_PILOT["step_g5_us"] - DRAFT_FRACTION_ASSUMED * ROM_PILOT["ar_us"]
    rom = dict(note="NOTE ONLY (owner decision: ROM = DSpark/MTP m=1 time-multiplexed). The ROM step is the pilot "
                    "sensitivity's (verify 6 positions + ASSUMED 3/40 draft); here only the draft term is replaced by "
                    "the HBM composition's draft/AR ratio, a structural proxy, not a ROM pricing.",
               source=ROM_PILOT["src"], verify_g5_us=round(rom_verify, 1),
               draft_assumed_us=round(DRAFT_FRACTION_ASSUMED * ROM_PILOT["ar_us"], 1),
               draft_hbm_ratio=round(ratio, 4), draft_proxy_us=round(ratio * ROM_PILOT["ar_us"], 1),
               tokens_s_tau3649_assumed=round(V41_TAU * 1e6 / ROM_PILOT["step_g5_us"], 1),
               tokens_s_tau3649_proxy=round(V41_TAU * 1e6 / (rom_verify + ratio * ROM_PILOT["ar_us"]), 1),
               verify_is_union_insensitive="ROM experts are stationary in their macros: a verify pass re-reads each "
                    "position's experts (cheap) and the union saves no bytes; what matters is positions colliding on "
                    "one expert's element (max multiplicity, below)",
               max_multiplicity_by_p=uj["max_multiplicity_by_p"])
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = dict(
        schema="opentallas.v41-hbm-speculation-methods.v1", source_commit=head,
        generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        status="opt-in model rows; NOT adopted; defaults and pinned files unchanged",
        method_identity=dict(
            finding="the repo's V4.1 'MTP' IS DSpark: the checkpoint's num_nextn_predict_layers = 3 modules mtp.0-2 "
                    "are the three serial stages of one DSpark block drafter (dspark_block_size 5, noise token "
                    "128799, target layers 37/38/39, MoE 128 experts top-3, Markov head rank 256); V41_TAU 3.649 was "
                    "measured with the vendor forward_spec; the 328b5fff golden/ISA evidence is DSpark (drafter: "
                    "dspark). No V3-style chained MTP exists in V4.1, so DSpark is the only real-GPU-stack method.",
            what_the_rows_got_wrong=["draft cost ASSUMED 3/40 of AR (uarch_model.V41_DRAFT_FRACTION) or the audit's "
                                     "49.9 us; a DSpark call is 3 full stages at 5 slots + LM head x 5 + 5 serial "
                                     "Markov argmax steps (priced here)",
                                     "verify union from the uniform formula (34.6 at P 6) or one synthetic window "
                                     "(W19 ISA, 27.6); measured here on real greedy continuations"],
            structure=dict(draft_block=BLOCK, verify_width_max=BLOCK + 1, stages=3, stage_kind="full V4.1 block, "
                           "sliding window 128 + the 5 block slots, no compressor/indexer/Engram",
                           semi_autoregressive="stages parallel over the 5 slots; the Markov head chains the 5 "
                           "argmaxes sequentially (each slot's bias depends on the previous slot's token)",
                           drafter_inputs="verified (bonus) token + attention input of layers 37-39 (mean over hc) "
                           "at the last accepted position: the draft cannot start before the verify head")),
        drafter_parameters=json.loads((REC_DIR / "drafter_params.json").read_text()),
        reproduction_gate=repro,
        union=dict(source="router_union.json", measured_mean_by_P={str(P): round(sum(meas[P].values()) / N_LAYERS, 3) for P in range(1, 9)},
                   uniform_by_P={str(P): round(uniform_union(P), 3) for P in range(1, 9)},
                   w19_isa_p6_mean=round(sum(w.w19_union.values()) / N_LAYERS, 3),
                   drafter_measured_per_stage=u_draft_meas, drafter_uniform=round(u_draft_unif[0], 3)),
        draft=dict(measured_union=dr_meas, uniform_union=dr_unif,
                   ratio_to_ar_1m=round(dr_meas["total_us"] / ctx_rows["1048576"]["ar_us"], 4),
                   assumed_ratio=DRAFT_FRACTION_ASSUMED, w19_audit_drafter_us=W19_REF["drafter_us"]),
        tau_sets=tau_sets, contexts=ctx_rows, rom_note=rom,
        inputs={p: sha(ROOT / p) for p in [W19_INPUTS["program"], *W19_INPUTS["sm"], W19_INPUTS["fetch"],
                                            W19_INPUTS["coll"], W19_INPUTS["select"], W19_INPUTS["mtp_isa"],
                                            "results/speculative/v41_flash_dspark_onpolicy_greedy.json"]}
        | {str(COMPOSER.relative_to(ROOT)): sha(COMPOSER),
           "router_union.json": sha(REC_DIR / "router_union.json"), "tau_by_gamma.json": sha(REC_DIR / "tau_by_gamma.json"),
           "drafter_params.json": sha(REC_DIR / "drafter_params.json")},
        source_sha256={"tools/v41_hbm_speculation_methods.py": sha(Path(__file__))})
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    for ctx, c in ctx_rows.items():
        print(ctx, "AR", c["ar_tokens_s"], json.dumps(c["headline_comparison_tau_3649_gamma5"]))
        for ts, r in c["rates"].items():
            print("  ", ts[:40], [(x["gamma"], x["tokens_s"]) for x in r["by_gamma"]])
    print("draft", dr_meas["total_us"], "uniform", dr_unif["total_us"], "ROM", rom["tokens_s_tau3649_assumed"], "->",
          rom["tokens_s_tau3649_proxy"])


def cmd_params(a):
    """DSpark parameter and byte inventory from the checkpoint's safetensors headers (no weights read)."""
    import glob
    import re
    import struct
    rows = {}
    for f in sorted(glob.glob(str(Path(a.snapshot) / "model-*.safetensors"))):
        with open(f, "rb") as fh:
            n = struct.unpack("<Q", fh.read(8))[0]
            h = json.loads(fh.read(n))
        for k, v in h.items():
            if k.startswith("mtp."):
                o = v["data_offsets"]
                rows[k] = (v["dtype"], v["shape"], o[1] - o[0])
    grp = {}
    for k, (dt, sh, b) in rows.items():
        g = re.sub(r"^mtp\.\d\.", "", k)
        g = "routed_experts" if ".experts." in g else ("markov_head" if "markov" in g else
                                                      ("main_proj" if "main_proj" in g else
                                                       ("attention" if g.startswith("attn") else
                                                        ("shared_expert" if "shared" in g else "other"))))
        grp[g] = grp.get(g, 0) + b
    per_expert = sum(b for k, (_, _, b) in rows.items() if k.startswith("mtp.0.ffn.experts.0."))
    out = dict(snapshot=str(a.snapshot), tensors=len(rows), bytes_total=sum(b for _, _, b in rows.values()),
               bytes_by_group=grp, bytes_per_routed_expert=per_expert,
               bytes_read_per_call_excl_routed=sum(v for k, v in grp.items() if k != "routed_experts"),
               note="head and embed are tied to the backbone's (no separate tensors)")
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    u = sp.add_parser("union"); u.add_argument("--router", required=True); u.add_argument("--out", required=True)
    t = sp.add_parser("tau"); t.add_argument("--drafts", required=True); t.add_argument("--out", required=True)
    q = sp.add_parser("params"); q.add_argument("--snapshot", required=True); q.add_argument("--out", required=True)
    p = sp.add_parser("price"); p.add_argument("--out", default=str(REC_DIR / "v41_hbm_speculation_methods.json"))
    a = ap.parse_args()
    dict(union=cmd_union, tau=cmd_tau, params=cmd_params, price=cmd_price)[a.cmd](a)


if __name__ == "__main__":
    main()
