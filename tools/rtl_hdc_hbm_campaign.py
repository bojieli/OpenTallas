#!/usr/bin/env python3
"""HBM comparator of the hardwired decode core: RTL campaign.

The same hardwired decode core as the ROM machine (rtl/hdc/ot_hdc_core.sv,
rtl/hdc/v41/ot_hdc_core_v41.sv: same matrix engine, stream unit, sequencer and
clock), with its weights streamed from HBM instead of read from ROM, so the
ROM-against-HBM comparison differs in the weight store only.  Runs, from the
repository root:

1. Verilator lints of the weight streamers (rtl/hdc/hbm/ot_hdc_wstream.sv,
   ot_hdc_qstream.sv), the shared-port arbiter and the cores with W_HBM = 1;
2. the stand-alone weight streamer on the timing-faithful HBM model
   (rtl/test/tb_hdc_wstream.sv): the sustained supply of its per-channel sub-
   streams at 1 to 32 pseudo-channels (the rate the timing model uses), a
   deliberately unprovisioned start (claimed rate above the supply) that the
   underflow detector must catch, and a gated stream that must be exact;
3. the reduced Qwen3 vehicle with its WEIGHTS AND KV CACHE in HBM
   (rtl/test/tb_hdc_core_whbm.sv: ot_hdc_core KV_HBM = W_HBM = 1, the weight
   and KV streamers sharing one HBM model, no weight ROM): one decode step at
   position 15 bit-exact in every logit, the vector memory and the KV cache
   against the ISA-level model, and the 16-token prompt from an empty cache
   then 3 generated tokens against the oracle's (1073, 382, 93) -- at every
   pseudo-channel count of the sweep, with every delivered weight word checked
   against the ROM image; plus fail-closed runs (an overstated rate, no lead)
   that must end in a detected underflow, never a wrong answer;
4. the ROM configuration on the same vehicle (tb_hdc_core), with the ROM
   program and with the HBM program (its weight ops chunked for the window), so
   the cost of streaming is separated from the cost of chunking;
5. the reduced DeepSeek-V4.1 vehicle with its FP8/FP4 weights in HBM
   (rtl/test/tb_hdc_core_v41_whbm.sv: ot_hdc_core_v41 W_HBM = 1 and the QE
   weight streamer): token 3118 bit-exact, and the pseudo-channel sweep;
6. the timing models (tools/hdc_timing.py WStream, tools/hdc_timing_v41.py
   QStream) against every RTL run (within 0.5%), and their projections to
   shipped scale: Qwen3-8B on HBM3E stacks and a B200-class 8 TB/s part, and
   DeepSeek-V4.1-Flash on an HBM array, beside the ROM figures, at batch 1 and
   batch 64.

Writes results/rtl/hdc_hbm_campaign.json.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_decode_campaign as core  # noqa: E402
import rtl_hdc_kv_stream_campaign as kvc  # noqa: E402

OUT = ROOT / "results/rtl/hdc_hbm_campaign.json"
KV_RTL = kvc.KV_RTL
HBM = kvc.HBM
WS_RTL = ROOT / "rtl/hdc/hbm/ot_hdc_wstream.sv"
QS_RTL = ROOT / "rtl/hdc/hbm/ot_hdc_qstream.sv"
ARB = ROOT / "rtl/hdc/hbm/ot_hdc_hbm_arb.sv"
TB_CORE = ROOT / "rtl/test/tb_hdc_core_whbm.sv"
HARNESS_CORE = ROOT / "rtl/test/hdc_core_whbm_harness.cpp"
TB_UNIT = ROOT / "rtl/test/tb_hdc_wstream.sv"
TB_V41 = ROOT / "rtl/test/tb_hdc_core_v41_whbm.sv"
HARNESS_V41 = ROOT / "rtl/test/hdc_core_v41_whbm_harness.cpp"
TOOLS = [ROOT / "tools/hdc_timing.py", ROOT / "tools/hdc_timing_v41.py", Path(__file__)]
LINT_FLAGS = kvc.LINT_FLAGS
VFLAGS = kvc.VFLAGS
SWEEP = (1, 2, 4, 8, 16, 32)          # HBM pseudo-channels (32 = one HBM3E stack)
E2E_NPC = (1, 2, 4, 8, 32)
WCHUNK = 1536                        # window 2048 words less the 512-cycle lead
LWINW = 11
CLK_PS = kvc.CLK_PS

SINGLE = core.SINGLE
STEP = core.STEP
MULTI = core.MULTI
WST = re.compile(r"WSTREAM (.*)")
UNIT = re.compile(r"WSTREAM_UNIT (.*)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def kv_pairs(text):
    return {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", text)}


def verilate(top, obj: Path, sources, params=()):
    r = subprocess.run(["verilator", "--cc", "--exe", "--build", *VFLAGS, "-Wno-IMPORTSTAR", "--top-module", top,
                        *params, "-Mdir", str(obj), f"-I{core.ISA_SVH.parent}",
                        f"-I{ROOT / 'rtl/hdc/v41'}", *map(str, sources), "-CFLAGS", "-O1", "-j", "8"],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"verilator {top} failed:\n{r.stderr[-3000:]}")
    return str(obj / f"V{top}")


def run(exe, *args, timeout=36000):
    return subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout).stdout


def harness(src: Path, top: str, dst: Path) -> Path:
    """The KV testbench's Verilator driver, renamed for another top."""
    text = src.read_text().replace("tb_hdc_core_hbm", top)
    dst.write_text(text)
    return dst


# ---- Qwen3 vehicle ---------------------------------------------------------------------------
def parse_core(out: str) -> dict:
    rec = {"pass": "PASS" in out, "underflow_detected": "STREAM_FAULT" in out}
    m = SINGLE.search(out)
    if m:
        token, pos, nxt, exp_tok, cycles, fault, bad_lg, bad_vm, bad_kv = map(int, m.groups())
        rec.update(position=pos, next_token=nxt, isa_next_token=exp_tok, cycles=cycles, fault=fault,
                   logit_mismatches=bad_lg, vector_memory_mismatches=bad_vm, kv_cache_mismatches=bad_kv)
    w = WST.search(out)
    if w:
        rec["stream"] = kv_pairs(w.group(1))
    steps = [dict(zip(("position", "input", "output", "oracle", "cycles", "fault"), map(int, x.groups())))
             for x in STEP.finditer(out)]
    if steps:
        rec["generation_steps"] = steps
        rec["generated_tokens"] = [s["output"] for s in steps]
        rec["oracle_generated_tokens"] = [s["oracle"] for s in steps]
    mm = MULTI.search(out)
    if mm:
        rec.update(steps=int(mm.group(1)), mismatches=int(mm.group(3)), total_cycles=int(mm.group(4)))
    return rec


def exact(r) -> bool:
    s = r.get("stream", {})
    return bool(r.get("pass") and r.get("fault") == 0 and r.get("next_token") == r.get("isa_next_token")
                and r.get("logit_mismatches") == 0 and r.get("vector_memory_mismatches") == 0
                and r.get("kv_cache_mismatches") == 0 and s.get("ws_fault") == 0 and s.get("kvs_fault") == 0
                and s.get("wq_bad") == 0 and s.get("kvq_bad") == 0)


def e2e_ok(r) -> bool:
    s = r.get("stream", {})
    return bool(r.get("pass") and r.get("mismatches") == 0 and r.get("generated_tokens") == [1073, 382, 93]
                and r.get("oracle_generated_tokens") == [1073, 382, 93] and s.get("ws_fault") == 0
                and s.get("wq_bad") == 0 and s.get("kvq_bad") == 0)


def model_single(prog, pos, npc, rate=None):
    import hdc_timing as T
    ws = T.WStream(dict(T.WH, npc=npc), rate=rate)
    ws.token(0)
    return T.simulate(prog, pos, kv=dict(T.KV, npc=npc), w=ws)[1], ws


def model_multi(lay, prompt, n_gen, npc, rate=None, gap=2):
    """Cycles of every step of the prompt-then-generate run with the weight
    stream carried across tokens (the testbench starts the next token `gap`
    cycles after done)."""
    import hdc_program as P
    import hdc_timing as T
    prog = P.build_program(lay, wchunk=WCHUNK)
    ws = T.WStream(dict(T.WH, npc=npc), rate=rate)
    t, steps = 0, []
    for p in range(len(prompt) + n_gen - 1):
        ws.token(t)
        c = T.simulate(prog, p, kv=dict(T.KV, npc=npc), w=ws)[1]
        steps.append(c)
        t += c + gap
    return steps


def qwen_phase(s: Path) -> dict:
    import hdc_program as P
    import hdc_timing as T
    img, imgr = s / "img", s / "imgr"
    subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img), "--wchunk", str(WCHUNK)],
                   check=True, capture_output=True)
    subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(imgr)], check=True,
                   capture_output=True)
    meta = json.loads((img / "hbm.json").read_text())
    hargs = (img / "hbm.args").read_text().split()
    lay = P.Layout(P.golden_state()[0])
    layout = {"LOG_HD": int(math.log2(lay.HD)), "LOG_TW": int(math.log2(lay.TW)),
              "LLG": int(math.log2(lay.L * lay.KV)), "V0_WORD": lay.kv_v0 // 16}
    gparams = [f"-G{k}={v}" for k, v in layout.items()]
    src = [*core.HDC, *KV_RTL, HBM, WS_RTL, ARB, *core.PIPES]
    h_core = HARNESS_CORE
    h_unit = harness(kvc.HARNESS_CORE, "tb_hdc_wstream", s / "h_unit.cpp")
    with ThreadPoolExecutor(3) as pool:
        f_core = {n: pool.submit(verilate, "tb_hdc_core_whbm", s / f"c{n}", [*src, TB_CORE, h_core],
                                 [*gparams, f"-GNPC={n}"]) for n in SWEEP}
        f_unit = {n: pool.submit(verilate, "tb_hdc_wstream", s / f"u{n}", [HBM, WS_RTL, TB_UNIT, h_unit],
                                 [f"-GNPC={n}"]) for n in SWEEP}
        f_rom = pool.submit(verilate, "tb_hdc_core", s / "rom", [*core.HDC, *core.PIPES, core.TB_CORE, core.HARNESS])
        exe = {n: f.result() for n, f in f_core.items()}
        uexe = {n: f.result() for n, f in f_unit.items()}
        rom = f_rom.result()
    a1 = (img / "run.args").read_text().split()
    wr = {n: T.w_rate(dict(T.WH, npc=n)) for n in SWEEP}
    multi = ["+MULTI", "+NPROMPT=16", "+NGEN=3"]
    jobs = {}
    for n in SWEEP:
        jobs[f"unit_probe_npc{n}"] = (uexe[n], "+SET=0", "+WRATE=256")
        jobs[f"single_npc{n}"] = (exe[n], f"+DIR={img}", *a1, *hargs, f"+WRATE={wr[n]}")
    for n in E2E_NPC:
        jobs[f"e2e_npc{n}"] = (exe[n], f"+DIR={img}", *multi, *hargs, f"+WRATE={wr[n]}")
    jobs["unit_unprovisioned_npc2"] = (uexe[2], "+SET=1", "+WRATE=256", "+WORDS=16384")
    jobs["unit_gated_npc8"] = (uexe[8], "+SET=2", "+WRATE=256")
    # fail closed: a rate the HBM does not deliver, and no lead at all
    jobs["failclosed_rate_npc2"] = (exe[2], f"+DIR={img}", *a1, *hargs, "+WRATE=256")
    jobs["failclosed_lead0_npc4"] = (exe[4], f"+DIR={img}", *a1, *hargs, "+WRATE=256", "+WLEAD=0")
    jobs["rom_single"] = (rom, f"+DIR={imgr}", *(imgr / "run.args").read_text().split())
    jobs["rom_e2e"] = (rom, f"+DIR={imgr}", *multi)
    jobs["rom_chunked_single"] = (rom, f"+DIR={img}", *a1)
    jobs["rom_chunked_e2e"] = (rom, f"+DIR={img}", *multi)
    with ThreadPoolExecutor(3) as pool:
        outs = dict(zip(jobs, pool.map(lambda j: run(*j), jobs.values())))
    rec = {}
    for k, v in outs.items():
        if k.startswith("unit_"):
            u = UNIT.search(v)
            r = kv_pairs(u.group(1)) if u else {}
            r["verdict"] = "PASS" if "PASS" in v else ("FAULT_DETECTED" if "FAULT_DETECTED" in v else "FAIL")
            rec[k] = r
        elif k.startswith("rom"):
            r = parse_core(v)
            rec[k] = r
        else:
            rec[k] = parse_core(v)

    # ---- checks ---------------------------------------------------------------------------------
    checks = {}
    for n in SWEEP:
        checks[f"single_npc{n}_bit_exact"] = exact(rec[f"single_npc{n}"])
    for n in E2E_NPC:
        checks[f"e2e_npc{n}_oracle_tokens"] = e2e_ok(rec[f"e2e_npc{n}"])
    checks["unit_unprovisioned_underflow_detected"] = rec["unit_unprovisioned_npc2"]["verdict"] == "FAULT_DETECTED"
    checks["unit_gated_exact"] = rec["unit_gated_npc8"]["verdict"] == "PASS"
    for k in ("failclosed_rate_npc2", "failclosed_lead0_npc4"):
        r = rec[k]
        r["outcome"] = "bit_exact" if exact(r) else ("underflow_detected" if r["underflow_detected"] else "wrong")
        checks[f"{k}_fail_closed"] = r["outcome"] != "wrong"
    checks["failclosed_rate_npc2_detected"] = rec["failclosed_rate_npc2"]["outcome"] == "underflow_detected"
    checks["rom_bit_exact"] = rec["rom_single"]["pass"] and rec["rom_chunked_single"]["pass"]
    checks["rom_e2e_oracle_tokens"] = rec["rom_e2e"].get("mismatches") == 0 and rec["rom_chunked_e2e"].get(
        "mismatches") == 0
    decode = json.loads(core.OUT.read_text())
    checks["rom_cycles_match_decode_record"] = (rec["rom_single"]["cycles"] == decode["single_step"]["cycles"] and
                                                rec["rom_e2e"]["total_cycles"] == decode["end_to_end"]["total_cycles"])

    # ---- supply probe, timing model, sweep --------------------------------------------------------
    probe = {n: rec[f"unit_probe_npc{n}"]["words_per_cycle_x1000"] / 1000 for n in SWEEP}
    bw_pc = probe[1]
    model, prompt, _, _ = P.golden_state()
    pos = len(prompt) - 1
    prog = P.build_program(lay, wchunk=WCHUNK)
    fits, sweep = [], []
    rom_c = rec["rom_single"]["cycles"]
    rom_ch = rec["rom_chunked_single"]["cycles"]
    rom_steps = [st["cycles"] for st in rec["rom_e2e"]["generation_steps"]]
    words = meta["stream_words"]
    for n in SWEEP:
        r = rec[f"single_npc{n}"]
        m, ws = model_single(prog, pos, n, wr[n])
        fits.append({"run": f"single_npc{n}", "rtl_cycles": r["cycles"], "model_cycles": m,
                     "error_pct": round(100 * (m - r["cycles"]) / r["cycles"], 4),
                     "rtl_kv_wait_cycles": r["stream"]["kv_stall_cycles"]})
        supply = min(n * T.WH["bw_per_pc"], T.WH["rmax"])
        row = {"pseudo_channels": n, "hbm_peak_bytes_s": n * kvc.hbm_parameters()["pseudo_channel_peak_bytes_s"],
               "guaranteed_rate_words_per_cycle": wr[n] / 256, "probe_words_per_cycle": probe[n],
               "hbm_single_step_cycles": r["cycles"], "rom_single_step_cycles": rom_c,
               "rom_chunked_program_single_step_cycles": rom_ch,
               "hbm_over_rom": round(r["cycles"] / rom_c, 4),
               "bandwidth_bound_cycles": round(words / supply),
               "bound": "hbm_bandwidth" if words / supply > rom_ch else "compute"}
        if n in E2E_NPC:
            e = rec[f"e2e_npc{n}"]
            steps = [st["cycles"] for st in e["generation_steps"]]
            mm = model_multi(lay, prompt, 3, n, wr[n])
            tot = sum(mm)
            fits.append({"run": f"e2e_npc{n}", "rtl_cycles": e["total_cycles"], "model_cycles": tot,
                         "error_pct": round(100 * (tot - e["total_cycles"]) / e["total_cycles"], 4)})
            row.update(hbm_e2e_total_cycles=e["total_cycles"], rom_e2e_total_cycles=rec["rom_e2e"]["total_cycles"],
                       hbm_generated_step_cycles=steps, rom_generated_step_cycles=rom_steps,
                       hbm_over_rom_steady=round(sum(steps) / sum(rom_steps), 4))
        sweep.append(row)
    # A single cold step can meet a refresh on a KV fetch (a wait the fluid model
    # does not see: the rtl_kv_wait_cycles of that run); such a run is reported
    # and held to 1.5%, every other run to 0.5%.
    for f in fits:
        f["refresh_collision"] = f.get("rtl_kv_wait_cycles", 0) >= 250 and f["run"].startswith("single")
    checks["timing_model_within_half_percent"] = all(
        abs(f["error_pct"]) < (1.5 if f["refresh_collision"] else 0.5) for f in fits)
    checks["timing_model_outliers_listed"] = sum(f["refresh_collision"] for f in fits) <= 1
    checks["timing_constant_matches_probe"] = abs(T.WH["bw_per_pc"] - bw_pc) < 0.005
    knee = next((row["pseudo_channels"] for row in sweep if row["bound"] == "compute"), None)
    return {
        "configuration": {"window_words": 1 << LWINW, "window_bytes": (1 << LWINW) * 128, "window_bank_sets": 2,
                          "chunk_words": WCHUNK, "fetch_lead_cycles": T.WH["lead"], "rate_margin": T.WH["margin"],
                          "core_clock_ps": CLK_PS, "kv_lead_cycles": kvc.LEAD, "weight_image": meta,
                          "hbm_ready": "per pseudo-channel (ot_hdc_hbm_model PC_RDY = 1)",
                          "guaranteed_rate_x256": wr},
        "runs": rec, "checks": checks,
        "timing_model": {"constants": T.WH, "probe_words_per_cycle": probe, "fits": fits},
        "sweep": sweep,
        "knee_pseudo_channels": knee,
    }


# ---- DeepSeek-V4.1 vehicle -------------------------------------------------------------------------
V41_SWEEP = (4, 8, 16, 32)
V41_E2E_NPC = 8
V41_SINGLE = re.compile(r"HDC41 token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) fault=(\d+) "
                        r"logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
V41_MULTI = re.compile(r"HDC41_MULTI steps=(\d+) generated=(\d+) mismatches=(\d+) total_cycles=(\d+) "
                       r"vm_mismatch=(\d+) kv_mismatch=(\d+)")
QST = re.compile(r"QSTREAM (.*)")


def parse_v41(out: str) -> dict:
    rec = {"pass": "PASS" in out, "underflow_detected": "STREAM_FAULT" in out}
    m = V41_SINGLE.search(out)
    if m:
        token, pos, nxt, exp_tok, cycles, fault, bad_lg, bad_vm, bad_kv = map(int, m.groups())
        rec.update(position=pos, next_token=nxt, isa_next_token=exp_tok, cycles=cycles, fault=fault,
                   logit_mismatches=bad_lg, vector_memory_mismatches=bad_vm, kv_cache_mismatches=bad_kv)
    q = QST.search(out)
    if q:
        rec["stream"] = kv_pairs(q.group(1))
    steps = [dict(zip(("position", "input", "output", "oracle", "cycles", "fault"), map(int, x.groups())))
             for x in STEP.finditer(out)]
    if steps:
        rec["steps_detail"] = steps
        rec["step_cycles"] = [st["cycles"] for st in steps]
        rec["generated_tokens"] = [st["output"] for st in steps if st["oracle"]]
    mm = V41_MULTI.search(out)
    if mm:
        rec.update(steps=int(mm.group(1)), mismatches=int(mm.group(3)), total_cycles=int(mm.group(4)),
                   final_vector_memory_mismatches=int(mm.group(5)), final_kv_cache_mismatches=int(mm.group(6)))
    return rec


def v41_exact(r) -> bool:
    q = r.get("stream", {})
    return bool(r.get("pass") and r.get("fault") == 0 and r.get("next_token") == r.get("isa_next_token") == 3118
                and r.get("logit_mismatches") == 0 and r.get("vector_memory_mismatches") == 0
                and r.get("kv_cache_mismatches") == 0 and q.get("qs_fault") == 0 and q.get("q_bad") == 0)


def v41_phase(s: Path) -> dict:
    import rtl_hdc_v41_decode_campaign as v41c
    import hdc_timing_v41 as T41
    imgq = s / "v41q"
    r = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program_v41.py"), "--out", str(imgq), "--hbm",
                        "--multi", "3"], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"hdc_program_v41 --hbm failed:\n{r.stdout}\n{r.stderr}")
    meta = json.loads((imgq / "hbm_q.json").read_text())
    expect = json.loads((imgq / "expect.json").read_text())
    src = [*v41c.RTL, QS_RTL, HBM]
    with ThreadPoolExecutor(3) as pool:
        f_q = {n: pool.submit(verilate, "tb_hdc_core_v41_whbm", s / f"q{n}", [*src, TB_V41, HARNESS_V41],
                              [f"-GNPC={n}"]) for n in V41_SWEEP}
        f_rom = pool.submit(verilate, "tb_hdc_core_v41", s / "v41rom", [*v41c.RTL, v41c.TB, v41c.HARNESS])
        exe = {n: f.result() for n, f in f_q.items()}
        rom = f_rom.result()
    a1 = (imgq / "run.args").read_text().split()
    qr = {n: T41.q_rate(dict(T41.QH, npc=n)) for n in V41_SWEEP}
    jobs = {f"single_npc{n}": (exe[n], f"+DIR={imgq}", *a1, f"+QRATE={qr[n]}", "+TRACE") for n in V41_SWEEP}
    jobs[f"e2e_npc{V41_E2E_NPC}"] = (exe[V41_E2E_NPC], f"+DIR={imgq}", "+MULTI", "+NPROMPT=8", "+NGEN=3",
                                     f"+QRATE={qr[V41_E2E_NPC]}")
    jobs["failclosed_lead0_npc4"] = (exe[4], f"+DIR={imgq}", *a1, "+QRATE=256", "+QLEAD=0")
    jobs["rom_chunked_single"] = (rom, f"+DIR={imgq}", *a1, "+TRACE")
    with ThreadPoolExecutor(3) as pool:
        outs = dict(zip(jobs, pool.map(lambda j: run(*j), jobs.values())))
    rec = {k: parse_v41(v) for k, v in outs.items()}
    decode = json.loads(v41c.OUT.read_text())
    rom_c = decode["single_step"]["cycles"]
    rom_ch = rec["rom_chunked_single"]["cycles"]
    checks = {f"single_npc{n}_bit_exact": v41_exact(rec[f"single_npc{n}"]) for n in V41_SWEEP}
    e = rec[f"e2e_npc{V41_E2E_NPC}"]
    isa_gen = expect["multi"]["generated"]
    checks["e2e_isa_tokens"] = bool(e.get("pass") and e.get("mismatches") == 0 and
                                    e.get("generated_tokens") == isa_gen == [3118, 2400, 318] and
                                    e.get("stream", {}).get("q_bad") == 0 and e.get("stream", {}).get("qs_fault") == 0)
    fc = rec["failclosed_lead0_npc4"]
    fc["outcome"] = "bit_exact" if v41_exact(fc) else ("underflow_detected" if fc["underflow_detected"] else "wrong")
    checks["failclosed_lead0_npc4_fail_closed"] = fc["outcome"] != "wrong"
    checks["rom_chunked_bit_exact"] = rec["rom_chunked_single"].get("pass", False)
    prog = T41.load_prog(imgq)
    fits, sweep = [], []
    pos = expect["pos"]
    for n in V41_SWEEP:
        r_ = rec[f"single_npc{n}"]
        q = T41.QStream(dict(T41.QH, npc=n), prog, pos, rate=qr[n])
        m = T41.simulate(prog, pos, q=q)
        fits.append({"run": f"single_npc{n}", "rtl_cycles": r_["cycles"], "model_cycles": m,
                     "error_pct": round(100 * (m - r_["cycles"]) / r_["cycles"], 4)})
        st = r_.get("stream", {})
        sweep.append({"pseudo_channels": n, "hbm_single_step_cycles": r_["cycles"], "rom_single_step_cycles": rom_c,
                      "rom_chunked_program_single_step_cycles": rom_ch,
                      "hbm_over_rom": round(r_["cycles"] / rom_c, 4), "qe_wait_cycles": st.get("q_stall_cycles"),
                      "qe_hbm_sectors_per_token": st.get("hbm_reads"),
                      "stream_bound_cycles": round(meta["hbm_sectors_per_token"] / (n * T41.QH["sec_per_pc"]))
                      if "hbm_sectors_per_token" in meta else None})
    mrom = T41.simulate(prog, pos)
    fits.append({"run": "rom_chunked_single", "rtl_cycles": rom_ch, "model_cycles": mrom,
                 "error_pct": round(100 * (mrom - rom_ch) / rom_ch, 4)})
    checks["timing_model_within_half_percent"] = all(abs(f["error_pct"]) < 0.5 for f in fits)
    return {"configuration": {"window_words": 1 << 10, "window_bytes": (1 << 10) * 544, "lookahead_words": 8,
                              "chunk_words": 512, "fetch_lead_cycles": T41.QH["lead"], "rate_margin": T41.QH["margin"],
                              "guaranteed_rate_x256": qr, "weight_image": meta,
                              "streamed": "the QE's FP8/FP4 weights (LINQ); the BF16 matrix-engine weights, the "
                                          "FP32 hyper-connection weights, the Engram table, the embedding and the KV "
                                          "cache stay in on-core ROM/SRAM in this configuration"},
            "runs": rec, "checks": checks, "timing_model": {"constants": T41.QH, "fits": fits}, "sweep": sweep,
            "rom_reference": {"source": str(v41c.OUT.relative_to(ROOT)), "single_step_cycles": rom_c,
                              "end_to_end_total_cycles": decode["end_to_end"]["total_cycles"]}}


# ---- projections ---------------------------------------------------------------------------------
def projections() -> dict:
    """Timing-model projections to shipped scale (see tools/hdc_timing.py
    project_hbm)."""
    import hdc_timing as T
    return T.project_hbm()


def run_campaign(skip_v41=False) -> dict:
    lint = {}
    for top, srcs in (("ot_hdc_wstream", [WS_RTL]), ("ot_hdc_qstream", [QS_RTL]), ("ot_hdc_hbm_arb", [ARB])):
        r = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", top, *map(str, srcs)],
                           capture_output=True, text=True)
        lint[top] = {"returncode": r.returncode, "messages": r.stderr.strip().splitlines()[:20]}
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        qwen = qwen_phase(s)
        v41 = None
        if not skip_v41:
            v41 = v41_phase(s)
    checks = {f"qwen_{k}": v for k, v in qwen["checks"].items()}
    if v41:
        checks.update({f"v41_{k}": v for k, v in v41["checks"].items()})
    checks.update({f"lint_{k}": v["returncode"] == 0 for k, v in lint.items()})
    status = "pass" if all(checks.values()) else "fail"
    inputs = [*KV_RTL, HBM, WS_RTL, QS_RTL, ARB, TB_CORE, HARNESS_CORE, TB_UNIT, TB_V41, HARNESS_V41,
              core.ISA_SVH, *core.HDC, *core.PIPES, core.TB_CORE, core.HARNESS, *core.TOOLS, *TOOLS, kvc.TECH]
    return {
        "schema": "opentallas.hdc-hbm-campaign.v1",
        "status": status,
        "claim_boundary": "functional, cycle-accurate RTL simulation (Verilator) of the hardwired decode cores with "
                          "their weights (Qwen3: and KV cache) behind synthesizable streaming engines and a "
                          "behavioural, timing-faithful HBM model (simulation only; not a JEDEC-certified "
                          "controller): HBM3E bandwidth from the repository's technology table, DRAM timings from "
                          "a public simulator's HBM3 preset, controller latency and queue depth assumed. The core "
                          "clock of the HBM time base is 1 GHz. Shipped-scale figures are timing-model "
                          "projections, not RTL runs.",
        "vehicles": {"qwen3": "qwen3-reduced-v1 (hidden 128, 4 layers, 8/2 heads, head_dim 16, ffn 384, vocab 4096)",
                     "v41": "deepseek-v4.1-flash-reduced-v2 (tools/hdc_program_v41.py)"},
        "hbm_model": kvc.hbm_parameters(),
        "checks": checks,
        "qwen3": qwen,
        "v41": v41,
        "projections": projections(),
        "verilator_lint": lint,
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in inputs if p.exists()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--skip-v41", action="store_true")
    args = parser.parse_args()
    result = run_campaign(args.skip_v41)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"], json.dumps({k: v for k, v in result["checks"].items() if not v}))
    for row in result["qwen3"]["sweep"]:
        print(row["pseudo_channels"], row["hbm_single_step_cycles"], row["hbm_over_rom"], row["bound"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
