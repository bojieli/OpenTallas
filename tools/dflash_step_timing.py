#!/usr/bin/env python3
"""DFlash on the Qwen3-8B designs: measured acceptance per block and a serial draft/verify/commit step.

    python3 tools/dflash_step_timing.py [--out results/speculative/dflash_step_timing.json]

Replaces two approximations of the atlas's speculative figures (atlas 8.6, Table 8-16; the model is
tools/arch_budget_qwen3.py at 74359092, ``tokens_per_step()`` and ``rom_block_sweep()`` and
``dflash_budget()``):

1. ACCEPTANCE.  ``tokens_per_step(B)`` cut a block-16 acceptance histogram (6 prompts, fp32 torch) at B.
   DFlash drafts a block jointly, so a run at block B is a different drafter input.  Here tokens per
   step come from results/speculative/dflash_block_acceptance.json: the reference ``dflash_generate``
   RUN at each block B on the 264 prompt turns of results/speculative/acceptance_tau.json (greedy,
   BF16).  The truncation of the same prompts' block-16 run is carried beside it for comparison.

2. TIMING.  ``rom_block_sweep`` priced the step as max(verify compute + drafter MACs / lanes, KV
   stream): the drafter's MACs as throughput, its latency "overlapped".  It cannot overlap: the draft of
   step s+1 needs the token and the target hidden states that step s's verify accepts, and the verify
   needs the draft.  The step here is three serial phases on the same core:

   DRAFT   fc over the context positions the last step committed (5 x 4096 -> 4096), the drafter's 5
           Qwen3 layers over the B block slots (their own dependency chain -- the target layer's stage
           chain, tools/arch_budget_qwen3.py LAYER_STAGES_SPEC, its latency paid once per layer --
           plus K/V projections of the new context positions), the final norm, the shared lm_head over
           the B-1 draft slots and its argmax.  Against it the drafter's own KV (5 layers of context)
           streams from the KV stacks: the phase is max(drafter chain, drafter KV stream).
   VERIFY  the target over B slots: rom_token(slots=B, m) of the atlas model, max(chain, target KV).
   COMMIT  the accept unit's prefix-AND over B-1 compares, the bonus token, the next step's DYN banks
           (CTL ACCEPT/TOKX/DYN/END at the spec's 1-cycle issue gap); rollback is a commit pointer.

   HBM comparator (the same two-reticle core, 196,608 MAC lanes, weights and KV on its 8 HBM3E stacks): each phase
   is max(bytes / bandwidth, MACs / lanes, its chain latency), as the atlas's batch model prices a
   step.  The draft phase re-reads the shared lm_head (the drafter has none of its own), which the atlas
   model left out, and the verify's MACs are capped by the lanes, which it reported but did not apply.

The hardware basis (clock, the per-layer stage chain with the UCIe exchanges, KV stream cycles, lanes, lane
multiplier) is the Qwen3-8B ROM package of tools/arch_budget_qwen3.py (``timing_basis()``: two reticles, every
layer split across both dies, 8-bit weights, 12,288 groups, 8 HBM3E stacks, m = 5), computed afresh.  The
serial-step arithmetic itself was validated against the earlier atlas lineage's own sweep: that lineage's
basis stays pinned as results/speculative/dflash_timing_basis.json (74359092, a single reticle; not a design),
and the legacy checks reproduce its sweep from it before the package is priced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASIS = ROOT / "results/speculative/dflash_timing_basis.json"
ACCEPT = ROOT / "results/speculative/dflash_block_acceptance.json"
OUT = ROOT / "results/speculative/dflash_step_timing.json"

DRAFTER = "z-lab/Qwen3-8B-DFlash-b16"
DRAFTER_PARAMS = 1_048_626_432     # safetensors header (BF16): 5 layers + fc + norms; embedding and lm_head shared
DRAFTER_LAYERS = 5
DFLASH_FC = (4096, 5 * 4096)       # fc: 5 target layers' hidden states (1, 9, 17, 25, 33) -> 4096
BLOCKS = (1, 2, 3, 4, 5, 6, 8, 12, 16)
CTL_COMMIT_OPS = 4                 # ACCEPT, TOKX, DYN, END at the spec's issue gap
# The atlas's tokens_per_step() histogram (6 prompts, fp32 torch, block 16), for the legacy check only.
LEGACY_ACCEPT_HIST = {1: 169, 2: 118, 3: 79, 4: 51, 5: 29, 6: 13, 7: 12, 8: 9, 9: 14, 10: 9, 11: 5, 12: 3, 13: 3,
                      14: 9, 15: 4, 16: 34}
LEGACY_TAU_CENTRAL = 4.1


# -- basis --------------------------------------------------------------------------------------------
def make_basis(budget_path: Path, source: str) -> dict:
    """The fields of the atlas lineage's budget JSON this model uses, verbatim."""
    raw = budget_path.read_bytes()
    b = json.loads(raw)
    return {
        "what": "hardware basis of tools/dflash_step_timing.py, copied verbatim from the atlas lineage's budget",
        "source": source, "source_sha256": hashlib.sha256(raw).hexdigest(),
        "clock_hz": b["clock_hz"], "shape": b["shape"], "rom_design": b["rom_design"],
        "hbm_design": b["hbm_design"], "design_point": b["design_point"],
        "lane_multiplier_m": b["area"]["lane_multiplier_m"],
        "dependency_chain": {k: v for k, v in b["dependency_chain"].items() if k.endswith("/spec")},
        "rom_token": b["rom_token"],
        "workload": {k: {"weight_macs": v["weight_macs"], "attention_macs": v["attention_macs"],
                         "bytes": v["bytes"]} for k, v in b["workload"].items()},
        "hbm_comparator": b["hbm_comparator"],
        "legacy_dflash": b["dflash"],
    }


# -- engine arithmetic (tools/arch_budget_qwen3.py split_rounds / mv_cycles, same tiling rule) -------------
W_LANES, INTERLEAVE = 16, 8        # tools/hdc_isa.py W_LANES, INTERLEAVE


def mv_cycles(n, k, groups):
    tiles = -(-n // (W_LANES * INTERLEAVE))
    best = None
    s = 1
    while s <= groups:
        if k % s == 0:
            c = -(-tiles // (groups // s)) * (k // s) * INTERLEAVE
            if best is None or c < best:
                best = c
        s *= 2
    return best


class Machine:
    def __init__(self, basis: dict, ctx: int, kv_fmt: str):
        self.b = basis
        self.q = basis["shape"]
        self.ctx = ctx
        self.clock = basis["clock_hz"]
        self.groups = basis["rom_design"]["groups"]
        self.lanes = basis["rom_design"]["lanes"]
        ch = basis["dependency_chain"][f"{ctx}/spec"]
        self.comp = ch["components"]
        rows = ch["stages"]
        L = self.q["L"]
        self.layer = dict(
            weights=sum(r["throughput"] for r in rows if r["kind"] == "mv"),
            attention=sum(r["throughput"] for r in rows if r["kind"] == "attn"),
            elementwise=sum(r["throughput"] for r in rows if r["kind"] not in ("mv", "attn")),
            latency=sum(r["exposed_latency"] for r in rows),
            control=self.comp["control"] / L)
        assert abs(self.layer["latency"] * L - self.comp["latency"]) < 1e-6
        assert abs(self.layer["attention"] * L - self.comp["attention"]) < 1e-6
        assert abs(self.layer["elementwise"] * L - self.comp["elementwise"]) < 1e-6
        self.head_mv = self.comp["weights"] - L * self.layer["weights"]
        self.me_res = next(r["exposed_latency"] for r in rows if r["kind"] == "mv")
        self.argmax = next(r["exposed_latency"] for r in rows if r["kind"] == "mvred")
        self.norm = next(r["exposed_latency"] for r in rows if r["stage"] == "residual+sumsq") + \
            next(r["exposed_latency"] for r in rows if r["stage"] == "ffn_norm.rsqrt")
        self.su_width = ch["su_width"]
        self.wl = basis["workload"][str(ctx)]
        kvb = self.wl["bytes"]["kv_read"] * {"bf16": 2, "fp8": 1, "int4": 0.5}[kv_fmt] / 2
        self.kv_bytes = kvb
        self.kv_cycles = basis["rom_token"][f"{ctx}/{kv_fmt}"]["kv_stream_cycles"]
        H, KV, HD, NH, FF, V = (self.q[k] for k in ("H", "KV", "HD", "NH", "FF", "V"))
        self.layer_macs = (NH + 2 * KV) * HD * H + H * NH * HD + 2 * FF * H + H * FF
        self.head_macs = V * H
        self.kvproj_mv = mv_cycles(2 * KV * HD, H, self.groups)
        self.fc_mv = mv_cycles(DFLASH_FC[0], DFLASH_FC[1], self.groups)
        # TP-2 (the two-reticle package): the chain is one die's slice; the fc and K/V projections are the die's
        # slices (the fc at the golden's K-split), and every pass adds its serial UCIe exchanges
        self.tp = basis.get("tp")
        if self.tp:
            self.kvproj_mv = self.tp["kvproj_mv"]
            self.fc_mv = self.tp["fc_mv"]

    def exchanges(self, slots, phase="target"):
        """Serial UCIe exchange cycles of one pass under TP-2 (tools/arch_budget_qwen3.tp_exchanges); 0 on one die."""
        t = self.tp
        if not t:
            return 0
        H = self.q["H"]
        per = t["hop_cycles"] + slots * H * t["partial_bytes"] / t["link_bytes_per_cycle"] + t["reduce_add_cycles"]
        n, rows = (2 * self.q["L"] + 1, slots) if phase == "target" else (2 * DRAFTER_LAYERS + 2, 1)
        return math.ceil(n * per + t["hop_cycles"] + rows * t["emb_row_bytes"] / t["link_bytes_per_cycle"])

    # ROM package -------------------------------------------------------------------------------------
    def verify(self, B, m):
        """rom_token(slots=B, m) of the budget model, target KV only, with the pass's UCIe exchanges under TP-2."""
        c = self.comp
        comp = c["latency"] + c["control"] + math.ceil(B / m) * c["weights"] + math.ceil(B / m) * c["attention"] \
            + B * c["elementwise"] + self.exchanges(B)
        return dict(compute=comp, kv=self.kv_cycles, cycles=max(comp, self.kv_cycles))

    def draft(self, B, m, ctx_positions=None):
        """The drafter's forward over B slots on the same engine and lane copies."""
        p = B if ctx_positions is None else ctx_positions   # new context positions projected (<= B)
        ly = self.layer
        fc = math.ceil(p / m) * self.fc_mv + self.me_res + self.norm + math.ceil(p * self.q["H"] / self.su_width)
        per_layer = ly["latency"] + ly["control"] + math.ceil(B / m) * (ly["weights"] + ly["attention"]) \
            + B * ly["elementwise"] + math.ceil(p / m) * self.kvproj_mv
        final_norm = self.norm + math.ceil(B * self.q["H"] / self.su_width)
        head = math.ceil((B - 1) / m) * self.head_mv + self.me_res + self.argmax
        comp = fc + DRAFTER_LAYERS * per_layer + final_norm + head + self.exchanges(B, "draft")
        kv = self.kv_cycles * DRAFTER_LAYERS / self.q["L"]
        return dict(compute=comp, kv=kv, cycles=max(comp, kv),
                    parts=dict(fc=fc, layers=DRAFTER_LAYERS * per_layer, final_norm=final_norm, lm_head=head,
                               chain_latency_only=DRAFTER_LAYERS * (ly["latency"] + ly["control"]) +
                               2 * self.me_res + 2 * self.norm + self.argmax))

    @staticmethod
    def commit(B):
        return CTL_COMMIT_OPS + 2 * max(1, math.ceil(math.log2(B)))

    def plain(self):
        return self.verify(1, 1)["cycles"]

    def draft_mac_split(self, B, ctx):
        """The drafter's MACs a step, (weight, attention): its 5 layers over B slots, the shared lm_head over the
        B-1 draft slots, fc and K/V projections over B context positions (weights); scores and P.V of its 5
        layers over ctx + B positions (attention).  B = 1 drafts nothing."""
        if B == 1:
            return 0, 0
        q = self.q
        w = B * DRAFTER_LAYERS * self.layer_macs + (B - 1) * self.head_macs + \
            B * (DFLASH_FC[0] * DFLASH_FC[1] + DRAFTER_LAYERS * 2 * q["KV"] * q["HD"] * q["H"])
        return w, B * DRAFTER_LAYERS * 2 * q["NH"] * q["HD"] * (ctx + B)

    def draft_macs(self, B, ctx):
        """The atlas's rom_block_sweep drafter MAC count (fc and K/V projections over B positions)."""
        return sum(self.draft_mac_split(B, ctx))

    def step_macs(self, B, ctx):
        """MACs of one step, by phase and kind: the drafter's (draft_mac_split) and the target's verify over B slots
        (weights incl. lm_head, and attention over the ctx positions), the totals the power model charges."""
        dw, da = self.draft_mac_split(B, ctx)
        vw, va = B * self.wl["weight_macs"], B * self.wl["attention_macs"]
        return dict(draft_weight_macs=dw, draft_attention_macs=da, verify_weight_macs=vw, verify_attention_macs=va,
                    macs_per_step=dw + da + vw + va)

    def legacy_step(self, B, m):
        """atlas rom_block_sweep: max(verify compute + drafter MACs / (lanes x min(m, B)), KV x (1 + 5/36))."""
        if B == 1:
            return self.plain()
        v = self.verify(B, m)["compute"]
        kv = self.kv_cycles * (1 + DRAFTER_LAYERS / self.q["L"])
        return max(v + self.draft_macs(B, self.ctx) / (self.lanes * min(m, B)), kv)

    def serial_step(self, B, m):
        if B == 1:
            p = self.plain()
            return dict(cycles=p, draft=0, verify=p, commit=0)
        d, v, c = self.draft(B, m), self.verify(B, m), self.commit(B)
        return dict(cycles=d["cycles"] + v["cycles"] + c, draft=d["cycles"], verify=v["cycles"], commit=c,
                    draft_compute=d["compute"], draft_kv=d["kv"], verify_compute=v["compute"], verify_kv=v["kv"],
                    draft_parts=d["parts"])

    # HBM comparator ----------------------------------------------------------------------------------
    def hbm_step(self, B, bpp, fix=True):
        """One step on the HBM comparator.  fix=False is the atlas's dflash_budget pricing (one byte-bound
        read of target + drafter weights + both KVs, no lm_head re-read, no MAC cap), for the check."""
        hb = self.b["hbm_design"]
        lanes = hb.get("lanes", self.lanes)
        bw = hb["stacks"] * hb["stack_bytes_s"] * hb["efficiency"]
        wmacs = self.wl["weight_macs"]
        kvd = self.kv_bytes * DRAFTER_LAYERS / self.q["L"]
        if B == 1:
            t = max((wmacs * bpp + self.kv_bytes) / bw, (wmacs + self.wl["attention_macs"]) / (lanes * self.clock),
                    (self.comp["latency"] + self.comp["control"] + self.exchanges(1)) / self.clock)
            return dict(seconds=t, draft_s=0.0, verify_s=t, commit_s=0.0)
        if not fix:
            t = ((wmacs + DRAFTER_PARAMS) * bpp + self.kv_bytes + kvd) / bw
            return dict(seconds=t)
        d = self.draft(B, 1)
        draft_bytes = (DRAFTER_PARAMS + self.head_macs) * bpp + kvd
        draft_macs = self.draft_macs(B, self.ctx)
        t_d = max(draft_bytes / bw, draft_macs / (lanes * self.clock), d["parts"]["chain_latency_only"] / self.clock)
        ver_bytes = wmacs * bpp + self.kv_bytes
        ver_macs = B * (wmacs + self.wl["attention_macs"])
        t_v = max(ver_bytes / bw, ver_macs / (lanes * self.clock),
                  (self.comp["latency"] + self.comp["control"] + self.exchanges(1)) / self.clock)
        t_c = self.commit(B) / self.clock
        bind = {"draft": "bytes" if t_d == draft_bytes / bw else "macs" if t_d == draft_macs / (lanes * self.clock)
                else "latency",
                "verify": "bytes" if t_v == ver_bytes / bw else "macs" if t_v == ver_macs / (lanes * self.clock)
                else "latency"}
        return dict(seconds=t_d + t_v + t_c, draft_s=t_d, verify_s=t_v, commit_s=t_c, binding=bind)


def legacy_tokens_per_step(B):
    n = sum(LEGACY_ACCEPT_HIST.values())
    return sum(min(k, B) * v for k, v in LEGACY_ACCEPT_HIST.items()) / n


# -- acceptance ---------------------------------------------------------------------------------------
def acceptance(acc: dict) -> dict:
    """tokens per step per block: the direct run, and the truncation of the block-16 run, pooled over the
    primary workloads (cycle-weighted = total committed / total cycles; and the mean of workloads)."""
    out = {1: dict(direct=1.0, truncated=1.0, direct_mean_of_workloads=1.0, truncated_mean_of_workloads=1.0,
                   direct_range=[1.0, 1.0], measured=True, complete=True)}
    for B, e in acc["blocks"].items():
        p = e["pooled"]["primary"]
        out[int(B)] = dict(direct=p["tau_direct_cycle_weighted"], truncated=p["tau_truncated_cycle_weighted"],
                           direct_mean_of_workloads=p["tau_direct_mean_of_workloads"],
                           truncated_mean_of_workloads=p["tau_truncated_mean_of_workloads"],
                           direct_range=p["tau_direct_workload_range"], measured=True,
                           complete=all(w["complete"] for w in e["workloads"].values()))
    return out


def design_basis() -> dict:
    """The package's timing basis (tools/arch_budget_qwen3.timing_basis)."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import arch_budget_qwen3 as QB
    return QB.timing_basis()


def evaluate(basis: dict, acc: dict, legacy: dict | None = None) -> dict:
    tau = acceptance(acc)
    m_max = basis["lane_multiplier_m"]
    legacy = legacy if legacy is not None else json.loads(BASIS.read_text())
    braw = json.dumps(basis, sort_keys=True, default=float).encode()
    res = dict(schema="opentallas.dflash-step-timing.v1", tool="tools/dflash_step_timing.py",
               drafter=DRAFTER, basis=dict(source=basis["source"], sha256=hashlib.sha256(braw).hexdigest(),
                                           groups=basis["rom_design"]["groups"], lanes=basis["rom_design"]["lanes"],
                                           dies=basis["rom_design"].get("dies"),
                                           lane_multiplier_m=m_max, hbm_stacks=basis["hbm_design"]["stacks"],
                                           legacy_check_basis=str(BASIS.relative_to(ROOT)),
                                           legacy_check_source=legacy["source"]),
               acceptance=dict(path=str(ACCEPT.relative_to(ROOT)),
                               central="primary workloads, cycle-weighted (the convention of the atlas's pooled 4.1)",
                               band="mean of the primary workloads' tau (each workload weighted equally)",
                               per_block={str(k): v for k, v in sorted(tau.items())}),
               clock_hz=basis["clock_hz"], rom={}, hbm={}, checks={})
    for ctx in (8192, 2048):
        mc = Machine(basis, ctx, "fp8")
        plain = mc.plain()
        for m in sorted({1, m_max}):
            rows = []
            for B in BLOCKS:
                if B not in tau:
                    continue
                t = tau[B]
                s = mc.serial_step(B, m)
                row = dict(block=B, tokens_per_step=t["direct"], tokens_per_step_truncated=t["truncated"],
                           tokens_per_step_band=t["direct_mean_of_workloads"],
                           step_cycles=round(s["cycles"]), draft_cycles=round(s["draft"]),
                           verify_cycles=round(s["verify"]), commit_cycles=s["commit"],
                           tokens_s=round(t["direct"] * mc.clock / s["cycles"], 1),
                           tokens_s_band=round(t["direct_mean_of_workloads"] * mc.clock / s["cycles"], 1),
                           speedup=round(t["direct"] * plain / s["cycles"], 3),
                           tokens_s_serial_timing_truncated_tau=round(t["truncated"] * mc.clock / s["cycles"], 1),
                           **mc.step_macs(B, ctx))
                if B > 1:
                    row["draft_detail"] = {k: round(v) for k, v in s["draft_parts"].items()} | dict(
                        compute=round(s["draft_compute"]), kv_stream=round(s["draft_kv"]))
                    row["verify_detail"] = dict(compute=round(s["verify_compute"]), kv_stream=round(s["verify_kv"]))
                rows.append(row)
            best = max(rows, key=lambda r: r["tokens_s"])
            res["rom"][f"{ctx}/fp8/m{m}"] = dict(context=ctx, kv_format="fp8", lane_multiplier=m,
                                                 plain_cycles=plain, plain_tokens_s=round(mc.clock / plain, 1),
                                                 sweep=rows, best=best)
        # legacy check: the earlier atlas lineage's own sweep from its pinned basis (the step arithmetic's check)
        lmc = Machine(legacy, ctx, "fp8")
        for m in sorted({1, legacy["lane_multiplier_m"]}):
            key = f"{ctx}/fp8/m{m}"
            want = legacy["legacy_dflash"]["rom"][key]["sweep"]
            got = [dict(block=B, step_cycles=round(lmc.legacy_step(B, m)),
                        tokens_s=round(legacy_tokens_per_step(B) * lmc.clock / lmc.legacy_step(B, m), 1))
                   for B in (1, 2, 3, 4, 5, 6, 8, 12, 16)]
            ok = all(g["step_cycles"] == w["step_cycles"] and abs(g["tokens_s"] - w["tokens_s"]) < 0.11
                     for g, w in zip(got, want))
            res["checks"][f"legacy_rom_sweep_reproduced/{key}"] = ok
        if ctx == 8192:
            for fmt, bpp in (("bf16", 2), ("fp8", 1), ("rom_format_3.5b", 3.5 / 8)):
                legacy_b16 = legacy["legacy_dflash"]["hbm"][fmt]
                res["checks"][f"legacy_hbm_block16_reproduced/{fmt}"] = abs(
                    LEGACY_TAU_CENTRAL / lmc.hbm_step(16, bpp, fix=False)["seconds"] -
                    legacy_b16["tokens_s_at_tau_central"]) < 0.11
            for fmt, bpp in basis["hbm_weight_bytes_per_mac"].items():
                p = mc.hbm_step(1, bpp)
                rows = []
                for B in BLOCKS:
                    if B not in tau or B == 1:
                        continue
                    s = mc.hbm_step(B, bpp)
                    t = tau[B]
                    rows.append(dict(block=B, tokens_per_step=t["direct"],
                                     tokens_per_step_band=t["direct_mean_of_workloads"],
                                     step_us=round(s["seconds"] * 1e6, 2), draft_us=round(s["draft_s"] * 1e6, 2),
                                     verify_us=round(s["verify_s"] * 1e6, 2), commit_us=round(s["commit_s"] * 1e6, 4),
                                     binding=s["binding"],
                                     tokens_s=round(t["direct"] / s["seconds"], 1),
                                     tokens_s_band=round(t["direct_mean_of_workloads"] / s["seconds"], 1),
                                     speedup=round(t["direct"] * p["seconds"] / s["seconds"], 3),
                                     **mc.step_macs(B, ctx)))
                best = max(rows, key=lambda r: r["tokens_s"])
                b16 = next(r for r in rows if r["block"] == 16)
                res["hbm"][fmt] = dict(context=ctx, weight_bytes_per_mac=bpp, plain_tokens_s=round(1 / p["seconds"], 1),
                                       sweep=rows, best=best, block16=b16)
    res["checks"]["all"] = all(v for k, v in res["checks"].items())
    res["notes"] = [
        "Tokens per step are measured at BF16 on a GPU (results/speculative/dflash_block_acceptance.json), not in the "
        "deployment arithmetic (INT8 per-channel ROM weights, FP8 KV).",
        "Blocks below 16 run the block-16 drafter out of its training distribution; the direct runs measure that.",
        "The draft phase projects B new context positions (an upper bound: the last step committed tau of them).",
        "DRAFT and VERIFY are serial; each overlaps its own KV stream with its compute, as the atlas's rom_token does. "
        "Only one KV layer is buffered (the ring of the atlas's area ledger), so neither phase's stream runs ahead "
        "into the other.",
        "The HBM comparator's draft re-reads the shared lm_head (151,936 x 4096) at the weight format, and each "
        "phase is capped by the package's MAC lanes.",
        "Both dies split every layer (tensor-parallel 2): the chain carries the 73 UCIe exchanges a token (the "
        "control component), once a step for all of its slots; the drafter's layers are split the same way.",
    ]
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--acceptance", type=Path, default=ACCEPT)
    args = ap.parse_args()
    basis = design_basis()
    acc = json.loads(args.acceptance.read_text())
    res = evaluate(basis, acc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, indent=1) + "\n")
    print(f"checks: {res['checks']}")
    for k, v in res["rom"].items():
        print(f"ROM {k}: plain {v['plain_tokens_s']} tok/s")
        for r in v["sweep"]:
            print(f"  B={r['block']:>2} tau {r['tokens_per_step']:.3f} (trunc {r['tokens_per_step_truncated']:.3f}) "
                  f"step {r['step_cycles']:>8} = draft {r['draft_cycles']:>7} + verify {r['verify_cycles']:>7} + "
                  f"{r['commit_cycles']:>2}  -> {r['tokens_s']:>8} tok/s (band {r['tokens_s_band']})")
    for f, v in res["hbm"].items():
        print(f"HBM {f}: plain {v['plain_tokens_s']}")
        for r in v["sweep"]:
            print(f"  B={r['block']:>2} tau {r['tokens_per_step']:.3f} step {r['step_us']} us (draft {r['draft_us']}, "
                  f"verify {r['verify_us']}) {r['binding']} -> {r['tokens_s']} tok/s (band {r['tokens_s_band']})")


if __name__ == "__main__":
    main()
