#!/usr/bin/env python3
"""KV cache in HBM for the hardwired decode core: RTL campaign.

Runs, from the repository root:

1. a Verilator lint of the KV streaming engine (rtl/hdc/kv/ot_hdc_kv_stream.sv);
2. the stand-alone streamer test (rtl/test/tb_hdc_kv_stream.sv) against the
   timing-faithful HBM model (rtl/hdc/kv/ot_hdc_hbm_model.sv): every word the
   modelled matrix engine takes is checked against HBM, over both fetch modes,
   every GQA share, several rounds and ops 23x longer than the window; a
   deliberately unprovisioned op (demand above supply) must be caught by the
   underflow detector; and a bandwidth probe measures the sustained read rate of
   one pseudo-channel;
3. the decode core with KV_HBM = 1 (rtl/test/tb_hdc_core_hbm.sv) on the reduced
   Qwen3 vehicle, checked like tools/rtl_hdc_decode_campaign.py checks the SRAM
   core -- every logit, the vector memory and the whole KV cache (HBM plus the
   tail SRAM) bit for bit against the ISA-level model:
   * one decode step at position 15 (prefilled cache),
   * one step at position 59 (tools/hdc_program.py --context 60),
   * 16 prompt tokens from an empty cache, then 3 generated tokens compared with
     the torch oracle's,
   * 60 prompt tokens from an empty cache with the final step checked in full:
     every K and V row is written, flushed and re-read through HBM;
   plus a sweep of the fetch lead, and the same runs with half the HBM
   pseudo-channels;
4. the SRAM-KV core on the 60-token run, for the cost comparison;
5. the timing model (tools/hdc_timing.py, KV constants) against the HBM runs,
   and its projection of Qwen3-8B cycles per token at 8K, 200K and 1M context
   with the KV cache in HBM.

Writes results/rtl/hdc_kv_stream_campaign.json.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_decode_campaign as core  # noqa: E402

OUT = ROOT / "results/rtl/hdc_kv_stream_campaign.json"
KV_RTL = [ROOT / "rtl/hdc/kv/ot_hdc_kv_walk.sv", ROOT / "rtl/hdc/kv/ot_hdc_kv_stream.sv"]
HBM = ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv"
TB_CORE = ROOT / "rtl/test/tb_hdc_core_hbm.sv"
HARNESS_CORE = ROOT / "rtl/test/hdc_core_hbm_harness.cpp"
TB_UNIT = ROOT / "rtl/test/tb_hdc_kv_stream.sv"
HARNESS_UNIT = ROOT / "rtl/test/hdc_kv_stream_harness.cpp"
TECH = ROOT / "configs/hardware/technology.json"
TOOLS = [ROOT / "tools/hdc_timing.py", Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ")
VFLAGS = ["-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ"]
NPC = 4                  # the vehicle's provisioning: 4 pseudo-channels = 1/8 of an HBM3E stack
LEAD = 512               # fetch lead, cycles (>= the worst-case latency below)
CLK_PS = 1000            # core clock of the HBM model's time base (1 GHz)
POSITIONS = (8192, 200_000, 1_000_000)

SINGLE = core.SINGLE
UTIL = core.UTIL
KVS = re.compile(r"KVSTREAM kv_stall_cycles=(\d+) kv_ops=(\d+) stream_fault=(\d+) kvq_bad=(\d+) kvq_zero=(\d+)"
                 r"(?: hbm_reads=(\d+) hbm_writes=(\d+) acts=(\d+) row_hits=(\d+) row_conflicts=(\d+) "
                 r"refreshes=(\d+) rd_lat_avg_ps=(\d+) rd_lat_max_ps=(\d+) req_backpressure_cycles=(\d+))? "
                 r"total_cycles=(\d+)")
STEP = core.STEP
MULTI = core.MULTI
UNIT = re.compile(r"KVSTREAM_UNIT set=(\d+) ops=(\d+)/(\d+) checked=(\d+) mismatches=(\d+) zero_mismatches=(\d+) "
                  r"fault=(\d+) wait_cycles=(\d+) cycles=(\d+) hbm_rd_lat_max_ps=(\d+)")
PROBE = re.compile(r"PROBE npc=(\d+) hbm_words=(\d+) cycles=(\d+)")
HBM_PC = re.compile(r"HBM_PC pc=(\d+) reads=(\d+) writes=(\d+) acts=(\d+) row_hits=(\d+) row_conflicts=(\d+) "
                    r"refreshes=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hbm_parameters() -> dict:
    """The HBM model's parameters (its SV defaults), with the bandwidth tied to
    configs/hardware/technology.json."""
    text = HBM.read_text()
    par = {m.group(1): int(m.group(2)) for m in re.finditer(r"parameter integer (\w+_PS)\s*=\s*(\d+)", text)}
    tech = json.loads(TECH.read_text())
    stack = tech["hbm"]["hbm3e"]["stack_bandwidth_bytes_s"]["value"]
    pcs, pc_bits, burst_bytes = 32, 32, 32
    pin_bps = stack * 8 / (pcs * pc_bits)
    burst_ps = burst_bytes * 8 / pc_bits / pin_bps * 1e12
    assert abs(burst_ps - par["BURST_PS"]) < 1, (burst_ps, par["BURST_PS"])
    return {
        "timings_ps": par,
        "pseudo_channels_per_stack": pcs, "pseudo_channel_bits": pc_bits, "burst_bytes": burst_bytes,
        "banks_per_pseudo_channel": 32, "row_bytes": 1024,
        "stack_bandwidth_bytes_s": stack, "pin_rate_bps": pin_bps,
        "pseudo_channel_peak_bytes_s": stack / pcs,
        "sources": {
            "bandwidth": "configs/hardware/technology.json hbm.hbm3e.stack_bandwidth_bytes_s (B200 8 TB/s over 8 "
                         "HBM3E stacks) over 32 pseudo-channels of 32 bits: the burst time BURST_PS follows",
            "core_timings": "Ramulator 2 HBM3 6400 Mb/s preset (CMU-SAFARI/ramulator2 python/ramulator/dram/hbm3.py "
                            "at commit 72427a1bba37; nCL, nRCDRD, nRCDWR, nRP, nRAS, nWR, nRTP, nCWL, nRRDS/L, nFAW, "
                            "nWTRS/L are marked there as estimates), converted to ns at its tCK 625 ps; tCCD_L = "
                            "max(4 tCK, 2.5 ns) at tCK 512 ps; tRTW per JESD238 note 18 as Ramulator resolves it",
            "refresh": "JESD238 Table 93 as Ramulator 2 cites it: tRFC 350 ns (16 Gb dies, 8-high), tREFI 3.9 us; "
                       "all-bank refresh, staggered over pseudo-channels (conservative against per-bank refresh)",
            "organisation": "JESD238 Table 4 via Ramulator 2 HBM3_16Gb_8hi: 2 SIDs x 4 bank groups x 4 banks per "
                            "pseudo-channel, 1 KB rows, BL8 of 32 bits = 32 B",
            "controller": "ASSUMED: 10 ns request path and 10 ns response path (controller + PHY); a 16-deep "
                          "reordering window per pseudo-channel, earliest-ready first, same-sector order kept",
        },
        "grade": "bandwidth derived from the repository's technology table; DRAM timings are a public simulator's "
                 "HBM3 preset (partly estimates); controller latency assumed",
    }


def lead_analysis(par: dict) -> dict:
    t = par["timings_ps"]
    # a fetch issued just as its pseudo-channel starts an all-bank refresh behind an open row
    worst = t["REQ_PS"] + t["RP_PS"] + t["RFC_PS"] + t["RCDRD_PS"] + t["CL_PS"] + t["BURST_PS"] + t["RSP_PS"]
    cyc = math.ceil(worst / CLK_PS)
    win, bk, il = 256, 16, 8
    rows = []
    for jsh in range(4):
        thr = (LEAD >> jsh) + 1
        cap = win - (bk << (3 - jsh))
        rows.append({"jsh": jsh, "threshold_lines": thr, "window_cap_lines": cap, "covered": thr <= cap})
    return {"worst_single_fetch_latency_ps": worst, "worst_single_fetch_latency_cycles": cyc,
            "lead_cycles": LEAD, "lead_covers_worst_latency": LEAD >= cyc,
            "window_lines": win, "k_mode_block_words": bk,
            "thresholds": rows,
            "rule": "an op issues once min(its lines, lead >> jsh + 1) lines are complete; with the HBM supply at or "
                    "above the op's demand (G words per 2^jsh cycles) the buffered lines cover a refresh plus a "
                    "row-conflict fetch, so no read can find its word missing -- and one that would is detected "
                    "(fault)"}


def verilate(top, obj: Path, sources, params=()):
    subprocess.run(["verilator", "--cc", "--exe", "--build", *VFLAGS, "--top-module", top, *params,
                    "-Mdir", str(obj), f"-I{core.ISA_SVH.parent}", *map(str, sources), "-CFLAGS", "-O1", "-j", "8"],
                   check=True, capture_output=True)
    return str(obj / f"V{top}")


def run(exe, *args, timeout=7200):
    return subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout).stdout


def parse_core(out: str) -> dict:
    rec = {"pass": "PASS" in out}
    m = SINGLE.search(out)
    if m:
        token, pos, nxt, exp_tok, cycles, fault, bad_lg, bad_vm, bad_kv = map(int, m.groups())
        rec.update(position=pos, next_token=nxt, isa_next_token=exp_tok, cycles=cycles, fault=fault,
                   logit_mismatches=bad_lg, vector_memory_mismatches=bad_vm, kv_cache_mismatches=bad_kv)
    k = KVS.search(out)
    if k:
        g = k.groups()
        rec.update(kv_stall_cycles=int(g[0]), kv_ops=int(g[1]), stream_fault=int(g[2]), delivered_word_mismatches=int(g[3]),
                   zero_substituted_words=int(g[4]), total_cycles=int(g[14]))
        if g[5] is not None:
            rec["hbm"] = dict(zip(("reads", "writes", "activates", "row_hits", "row_conflicts", "refreshes",
                                   "read_latency_avg_ps", "read_latency_max_ps", "request_backpressure_cycles"),
                                  map(int, g[5:14])))
    steps = [dict(zip(("position", "input", "output", "oracle", "cycles", "fault"), map(int, x.groups())))
             for x in STEP.finditer(out)]
    if steps:
        rec["generation_steps"] = steps
        rec["generated_tokens"] = [s["output"] for s in steps]
        rec["oracle_generated_tokens"] = [s["oracle"] for s in steps]
    mm = MULTI.search(out)
    if mm:
        rec.update(steps=int(mm.group(1)), mismatches=int(mm.group(3)), total_cycles=int(mm.group(4)))
    rec["underflow_detected"] = "STREAM_FAULT" in out
    return rec


def parse_unit(out: str) -> dict:
    m = UNIT.search(out)
    g = list(map(int, m.groups()))
    rec = dict(zip(("set", "ops_done", "ops", "words_checked", "mismatches", "zero_mismatches", "fault",
                    "issue_wait_cycles", "cycles", "hbm_read_latency_max_ps"), g))
    rec["verdict"] = "PASS" if "PASS" in out else ("FAULT_DETECTED" if "FAULT_DETECTED" in out else "FAIL")
    rec["pseudo_channels"] = [dict(zip(("pc", "reads", "writes", "activates", "row_hits", "row_conflicts",
                                        "refreshes"), map(int, x.groups()))) for x in HBM_PC.finditer(out)]
    p = PROBE.search(out)
    if p:
        rec["probe"] = {"pseudo_channels": int(p.group(1)), "words": int(p.group(2)), "cycles": int(p.group(3)),
                        "words_per_cycle": round(int(p.group(2)) / int(p.group(3)), 4)}
    return rec


def _price(args):
    import hdc_timing as T
    model, groups, pos, kv = args
    return T.price(model, groups, pos, 1.0, kv=kv)


def projections(bw_per_pc: float) -> list:
    import hdc_timing as T
    kv = dict(T.KV, bw_per_pc=bw_per_pc)
    demand_wide = 1024 >> 2                                 # G/2^jsh words per cycle at 1,024 groups, GQA 4:1
    matched = 32 * math.ceil(demand_wide / bw_per_pc / 32)
    configs = [
        ("64 lanes (the built core), KV in SRAM", 4, None),
        ("64 lanes, KV in HBM: 4 pseudo-channels", 4, dict(kv, npc=4)),
        ("16,384 lanes, KV in SRAM", 1024, None),
        ("16,384 lanes, KV in HBM: one HBM3E stack (32 pseudo-channels)", 1024, dict(kv, npc=32)),
        (f"16,384 lanes, KV in HBM: {matched // 32} stacks (rate-matched, {matched} pseudo-channels)", 1024,
         dict(kv, npc=matched)),
    ]
    jobs = [("qwen3-8b", g, pos, k) for _, g, k in configs for pos in POSITIONS]
    with ProcessPoolExecutor(8) as pool:
        res = list(pool.map(_price, jobs))
    out, i = [], 0
    for name, g, k in configs:
        for pos in POSITIONS:
            r = res[i]
            i += 1
            row = {"configuration": name, "lanes": g * 16, "position": pos, "cycles_per_token": r["cycles_per_token"],
                   "kv_store": "hbm" if k else "sram"}
            if k:
                kh = r["kv_hbm"]
                row.update(hbm_pseudo_channels=k["npc"], kv_bytes_per_token=kh["kv_bytes_per_token"],
                           kv_wait_cycles=kh["kv_wait_cycles"], kv_ops=kh["kv_ops"],
                           kv_supply_limited_ops=kh["kv_supply_limited_ops"],
                           kv_window_lines_required=kh["kv_window_lines_required"],
                           no_stall_window_suffices=kh["kv_supply_limited_ops"] == 0)
            out.append(row)
    return out


def run_campaign() -> dict:
    import hdc_program as P
    import hdc_timing as T
    par = hbm_parameters()
    lead = lead_analysis(par)
    lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_hdc_kv_stream",
                           *map(str, KV_RTL)], capture_output=True, text=True)
    core_src = [*core.HDC, *KV_RTL, HBM, *core.PIPES]
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        # images
        img, imgc = s / "img", s / "imgc"
        for d, extra in ((img, []), (imgc, ["--context", "60"])):
            subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(d), *extra], check=True,
                           capture_output=True)
        lay = P.Layout(P.golden_state()[0])
        layout = {"LOG_HD": int(math.log2(lay.HD)), "LOG_TW": int(math.log2(lay.TW)),
                  "LLG": int(math.log2(lay.L * lay.KV)), "V0_WORD": lay.kv_v0 // 16}
        gparams = [f"-G{k}={v}" for k, v in layout.items()]
        with ThreadPoolExecutor(6) as pool:
            f_h4 = pool.submit(verilate, "tb_hdc_core_hbm", s / "h4", [*core_src, TB_CORE, HARNESS_CORE],
                               [*gparams, f"-GNPC={NPC}"])
            f_h2 = pool.submit(verilate, "tb_hdc_core_hbm", s / "h2", [*core_src, TB_CORE, HARNESS_CORE],
                               [*gparams, "-GNPC=2"])
            f_sr = pool.submit(verilate, "tb_hdc_core", s / "sram", [*core.HDC, *core.PIPES, core.TB_CORE, core.HARNESS])
            f_u = {n: pool.submit(verilate, "tb_hdc_kv_stream", s / f"u{n}",
                                  [*KV_RTL, HBM, TB_UNIT, HARNESS_UNIT], [f"-GNPC={n}"]) for n in (1, 2, 4)}
            h4, h2, sram = f_h4.result(), f_h2.result(), f_sr.result()
            unit = {n: f.result() for n, f in f_u.items()}
        a1 = (img / "run.args").read_text().split()
        a60 = (imgc / "run.args").read_text().split()
        jobs = {
            "single_step": (h4, f"+DIR={img}", *a1, f"+LEAD={LEAD}"),
            "long_context": (h4, f"+DIR={imgc}", *a60, f"+LEAD={LEAD}"),
            "end_to_end": (h4, f"+DIR={img}", "+MULTI", "+NPROMPT=16", "+NGEN=3", f"+LEAD={LEAD}"),
            "prompt60_from_empty": (h4, f"+DIR={imgc}", *a60, "+MULTI", "+NPROMPT=60", "+NGEN=1", "+CHECKLAST",
                                    f"+LEAD={LEAD}"),
            "npc2_single_step": (h2, f"+DIR={img}", *a1, f"+LEAD={LEAD}"),
            "npc2_long_context": (h2, f"+DIR={imgc}", *a60, f"+LEAD={LEAD}"),
            "npc2_prompt60_from_empty": (h2, f"+DIR={imgc}", *a60, "+MULTI", "+NPROMPT=60", "+NGEN=1", "+CHECKLAST",
                                         f"+LEAD={LEAD}"),
            "sram_prompt60_from_empty": (sram, f"+DIR={imgc}", "+MULTI", "+NPROMPT=60", "+NGEN=1"),
            "sram_long_context": (sram, f"+DIR={imgc}", *a60),
            "sram_single_step": (sram, f"+DIR={img}", *a1),
            "unit_provisioned_npc4": (unit[4], f"+LEAD={LEAD}"),
            "unit_provisioned_npc2": (unit[2], f"+LEAD={LEAD}"),
            "unit_unprovisioned_npc4": (unit[4], "+SET=1", "+LEAD=64"),
            "unit_probe_npc1": (unit[1], "+SET=2", "+LEAD=16"),
        }
        for L in (0, 32, 128):
            jobs[f"lead_{L}"] = (h4, f"+DIR={imgc}", *a60, f"+LEAD={L}")
        with ThreadPoolExecutor(len(jobs)) as pool:
            outs = dict(zip(jobs, pool.map(lambda j: run(*j), jobs.values())))
    rec = {k: (parse_unit(v) if k.startswith("unit_") else parse_core(v)) for k, v in outs.items()}

    # ---- verdicts -------------------------------------------------------------------------
    def exact(r):
        return (r.get("pass") and r.get("fault") == 0 and r.get("stream_fault") == 0 and r.get("next_token") ==
                r.get("isa_next_token") and r.get("logit_mismatches") == 0 and r.get("vector_memory_mismatches") == 0
                and r.get("kv_cache_mismatches") == 0 and r.get("delivered_word_mismatches") == 0)
    e2e = rec["end_to_end"]
    checks = {
        "lint_clean": lint.returncode == 0,
        "single_step_bit_exact": exact(rec["single_step"]),
        "long_context_bit_exact": exact(rec["long_context"]),
        "prompt60_from_empty_bit_exact": exact(rec["prompt60_from_empty"]),
        "end_to_end_oracle_tokens": e2e.get("pass") and e2e.get("mismatches") == 0 and
        e2e.get("generated_tokens") == e2e.get("oracle_generated_tokens") and e2e.get("stream_fault") == 0,
        "npc2_bit_exact": all(exact(rec[k]) for k in ("npc2_single_step", "npc2_long_context",
                                                      "npc2_prompt60_from_empty")),
        "unit_provisioned_pass": rec["unit_provisioned_npc4"]["verdict"] == "PASS" and
        rec["unit_provisioned_npc2"]["verdict"] == "PASS",
        "unit_unprovisioned_underflow_detected": rec["unit_unprovisioned_npc4"]["verdict"] == "FAULT_DETECTED",
        "probe_clean": rec["unit_probe_npc1"]["verdict"] == "PASS",
        "lead_covers_worst_latency": lead["lead_covers_worst_latency"],
        "sram_reference_bit_exact": rec["sram_single_step"]["pass"] and rec["sram_long_context"]["pass"],
    }
    # lead sweep: bit-exact, or a detected underflow -- never a silent wrong answer
    for L in (0, 32, 128):
        r = rec[f"lead_{L}"]
        r["outcome"] = "bit_exact" if exact(r) else ("underflow_detected" if r["underflow_detected"] else "wrong")
        checks[f"lead_{L}_fail_closed"] = r["outcome"] != "wrong"

    # ---- cost of streaming at the vehicle ----------------------------------------------------
    def cost(h, s_):
        return {"sram_cycles": s_, "hbm_cycles": h, "added_cycles": h - s_, "added_fraction": round((h - s_) / s_, 5)}
    sram60 = rec["sram_prompt60_from_empty"]["total_cycles"]
    costs = {
        "single_step_position_15": cost(rec["single_step"]["cycles"], rec["sram_single_step"]["cycles"]),
        "single_step_position_59": cost(rec["long_context"]["cycles"], rec["sram_long_context"]["cycles"]),
        "prompt60_from_empty_total": cost(rec["prompt60_from_empty"]["total_cycles"], sram60),
    }
    decode = json.loads(core.OUT.read_text())
    costs["end_to_end_16_plus_3_total"] = cost(e2e["total_cycles"], decode["end_to_end"]["total_cycles"])
    checks["sram_cycles_match_decode_record"] = (rec["sram_single_step"]["cycles"] == decode["single_step"]["cycles"]
                                                 and rec["sram_long_context"]["cycles"] ==
                                                 decode["long_context"]["cycles"])

    # ---- timing model -----------------------------------------------------------------------
    probe = rec["unit_probe_npc1"]["probe"]
    bw_pc = probe["words_per_cycle"]
    model_rows = []
    for name, ctx, r in (("single_step_position_15", None, rec["single_step"]),
                         ("single_step_position_59", 60, rec["long_context"])):
        model, prompt, _, _ = P.golden_state(ctx)
        prog = P.build_program(P.Layout(model))
        m = T.simulate(prog, len(prompt) - 1, kv=dict(T.KV, npc=NPC))[1]
        model_rows.append({"run": name, "rtl_cycles": r["cycles"], "model_cycles": m,
                           "error_pct": round(100 * (m - r["cycles"]) / r["cycles"], 4)})
    timing = {"constants": T.KV, "probe_words_per_cycle_per_pseudo_channel": bw_pc,
              "constant_matches_probe": abs(T.KV["bw_per_pc"] - bw_pc) < 0.01, "fits": model_rows}
    checks["timing_model_within_half_percent"] = all(abs(x["error_pct"]) < 0.5 for x in model_rows)
    checks["timing_constant_matches_probe"] = timing["constant_matches_probe"]
    proj = projections(T.KV["bw_per_pc"])

    status = "pass" if all(checks.values()) else "fail"
    return {
        "schema": "opentallas.hdc-kv-stream-campaign.v1",
        "status": status,
        "claim_boundary": "functional, cycle-accurate RTL simulation (Verilator) of the decode core with its KV cache "
                          "behind the synthesizable streaming engine and a behavioural, timing-faithful HBM model "
                          "(simulation only; not a JEDEC-certified controller). HBM3E-class timing: bandwidth from "
                          "the repository's technology table, DRAM timings from a public simulator's HBM3 preset, "
                          "controller latency assumed. The core clock of the HBM time base is 1 GHz. Qwen3-8B "
                          "figures are timing-model projections (tools/hdc_timing.py), not RTL runs, and positions "
                          "beyond 40,960 price a hypothetical context extension.",
        "vehicle": "qwen3-reduced-v1 (hidden 128, 4 layers, 8/2 heads, head_dim 16)",
        "configuration": {"hbm_pseudo_channels": NPC, "fetch_lead_cycles": LEAD, "window_lines": 256,
                          "window_bytes": 256 * 4 * 32, "k_mode_block_words": 16,
                          "tail_sram_bytes": 2 * (1 << (layout["LLG"] + layout["LOG_HD"])) * 32,
                          "layout": layout, "core_clock_ps": CLK_PS,
                          "demand_words_per_cycle_full_occupancy": 1.0,
                          "supply_words_per_cycle_peak": round(NPC * CLK_PS / par["timings_ps"]["BURST_PS"], 4)},
        "hbm_model": par,
        "lead": lead,
        "checks": checks,
        "vehicle_cost": costs,
        "runs": rec,
        "timing_model": timing,
        "qwen3_8b_projection": proj,
        "verilator_lint": {"returncode": lint.returncode, "flags": list(LINT_FLAGS),
                           "messages": lint.stderr.strip().splitlines()[:20]},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p)
                         for p in (*KV_RTL, HBM, TB_CORE, HARNESS_CORE, TB_UNIT, HARNESS_UNIT, TECH, core.ISA_SVH,
                                   *core.HDC, *core.PIPES, core.TB_CORE, core.HARNESS, *core.TOOLS, *TOOLS)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = run_campaign()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"], json.dumps(result["checks"]))
    for k, v in result["vehicle_cost"].items():
        print(k, v)
    for r in result["qwen3_8b_projection"]:
        print(r["configuration"], r["position"], r["cycles_per_token"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
