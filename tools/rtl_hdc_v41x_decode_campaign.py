#!/usr/bin/env python3
"""Token-level RTL simulation of the RE-SPECIFIED DeepSeek-V4.1 decode core (ot_hdc_core_v41x).

The as-built campaign (tools/rtl_hdc_v41_decode_campaign.py) on ot_hdc_core_v41x: the as-built sequencer and
ISA with each unit replaced by an adapter onto its re-specified engine (rtl/hdc/v41x/ot_hdc_v41x_*_adapt.sv),
the engines' memories in their own layouts (tools/hdc_images_v41x.py).  --units picks the re-specified units
(the rest stay as built) and the ISA model runs with HDC_V41_ARITH = the R-ARITH classes those units bring.

Runs, from the repository root:

1. a Verilator lint of ot_hdc_core_v41x;
2. the core under Verilator on the reduced DeepSeek-V4.1-Flash
   (build/models/deepseek-v4.1-flash-reduced-v2):
   * one decode step at position 7 (the oracle prompt's last token) from the
     golden-prefilled state, checked bit for bit against the ISA-level model
     (tools/hdc_program_v41.py) -- every logit, the whole vector memory, the
     whole KV cache -- and its token against the golden's and the oracle's
     (3118); the issue trace gives a per-operator cycle breakdown;
   * an end-to-end run from an EMPTY state: the core consumes the 8 prompt
     tokens (writing its own KV rows, compressed rows, index keys, compressor
     slots and Engram history) and generates --ngen tokens, compared with the
     ISA model's (which equal hdc_golden_v41's, step for step bit-exact), and
     its final vector memory and KV cache with the ISA model's;
   * (--context N) one step at position N-1 of the prompt cycled to N tokens,
     where the index top-k SELECTS (N > 17 for ratio-1 layers, > 33 for
     ratio-2), checked against the ISA model;
   * (--sweep-lanes W,...) the single step again with the stream unit built
     W lanes wide (tools/hdc_isa_v41.SU_LANES, HDC_SW), each checked the same way.

Arithmetic is tools/hdc_golden_v41.py; images from tools/hdc_program_v41.py and tools/hdc_images_v41x.py.
Writes results/rtl/hdc_v41x_decode_campaign.json.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41x_decode_campaign.json"
# the re-specified units (bring-up switches of ot_hdc_core_v41x) and the R-ARITH classes each one brings
X_UNITS = ("he", "me", "att", "idx", "sel", "eg", "su")
# idx: the FUSED indexer (tools/hdc_program_v41.py Builder idx_fused, HDC_V41_IDX_FUSED=1): one ME op per
# indexer computes the index scores on the indexer engine (dots, ReLU x weight, the head sum under R-ARITH
# class "idx"), the per-head score op and the stream unit's head-sum op are dropped from the program, and the
# keys stream from the HBM model through ot_hdc_v41x_idx_kstream
X_CLASSES = {"he": ("he",), "me": ("me",), "att": ("att",), "idx": ("idx",), "sel": (), "eg": (),
             "su": ("su", "idx")}
# su: the vector unit sums under R-ARITH everywhere, including the indexer-tagged stream sums (the index head
# sum), which the ISA model files under "idx"; "idx" also switches the ISA's index dots on the matrix engine,
# which the as-built engine still matches: FP4 x FP4 products of one 32-block share its scales, so every
# partial sum is exact and the order cannot change the result
UNITS = X_UNITS           # set by main(): the units built re-specified
IDX_POOL = False          # X_IDX=2: replicated four-stack pooled correctness path
PARAMS = {"hhw": 8, "mg": 8, "sun": 16, "sum": 8}      # engine geometry of the build
RTL = ([ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/proto/ot_fp32_mul_rne_pipe.sv"] +
       [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_sfu",
                                           "ot_hdc_reduce", "ot_hdc_accept")] +
       [ROOT / f"rtl/hdc/v41/{n}.sv" for n in ("ot_hdc_engram_tables_pkg", "ot_hdc_engram_hash", "ot_hdc_select",
                                               "ot_hdc_blockdot", "ot_hdc_chunk8_stack", "ot_hdc_actquant",
                                               "ot_hdc_fp4qdq", "ot_hdc_fdiv",
                                               "ot_hdc_fsqrt", "ot_hdc_softplus", "ot_hdc_sinkhorn_seq",
                                               "ot_hdc_sk_arith", "ot_hdc_sk_recip_rom", "ot_hdc_sinkhorn",
                                               "ot_hdc_sinkhorn_mc", "ot_hdc_v41_matvec",
                                               "ot_hdc_v41_stream", "ot_hdc_v41_qe", "ot_hdc_v41_xu",
                                               "ot_hdc_v41_hcproj")] +
       [ROOT / "rtl/hdc/ot_hdc_fastfp.sv", ROOT / "rtl/hdc/ot_hdc_fastfp_lat.sv"] +
       [ROOT / f"rtl/hdc/v41x/{n}.sv" for n in ("ot_hdc_v41x_hcp", "ot_hdc_v41x_he_adapt",
                                                 "ot_hdc_v41x_wgt_bdot", "ot_hdc_v41x_wgt_red", "ot_hdc_v41x_wgt_mac",
                                                 "ot_hdc_v41x_wgt_tile", "ot_hdc_v41x_me_adapt",
                                                 "ot_hdc_v41x_attn_tile", "ot_hdc_v41x_attn_staging",
                                                 "ot_hdc_v41x_attn", "ot_hdc_v41x_att_adapt",
                                                 "ot_hdc_v41x_sel_lib", "ot_hdc_v41x_sel_slice", "ot_hdc_v41x_sel",
                                                 "ot_hdc_v41x_egather", "ot_hdc_v41x_xu_adapt",
                                                 "ot_hdc_v41x_idx_arith", "ot_hdc_v41x_idx", "ot_hdc_v41x_idx_kstream",
                                                 "ot_hdc_v41x_idx_hbm", "ot_hdc_v41x_idx_adapt",
                                                  "ot_hdc_v41x_sfu", "ot_hdc_v41x_vec_lane", "ot_hdc_v41x_vec_side",
                                                  "ot_hdc_v41x_vec_red", "ot_hdc_v41x_vec", "ot_hdc_v41x_su_adapt",
                                                  "ot_hdc_v41x_dyn_unit", "ot_hdc_core_v41x")] +
       [ROOT / "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/"
               "ot_sram_1r1w_256x256_m2_r2c2.v"])
FASTFP = ROOT / "rtl/hdc/ot_hdc_fastfp.sv"
DPI_SV = ROOT / "rtl/test/sim_hdc_v41x_fastfp_dpi.sv"
DPI_WRAP = ROOT / "rtl/test/sim_hdc_v41x_fastfp_wrap.sv"
DPI_CPP = ROOT / "rtl/test/sim_hdc_v41x_fastfp_dpi.cpp"


def rtl_sources(build=False):
    """Select bit-level RTL or bit-equivalent simulation stand-ins for the large full-core gate."""
    if PARAMS.get("fp", "rtl") != "dpi":
        return list(RTL)
    return [p for p in RTL if p != FASTFP] + [DPI_SV, DPI_WRAP] + ([DPI_CPP] if build else [])


SVH = ROOT / "rtl/hdc/v41/ot_hdc_isa_v41.svh"
VLT = ROOT / "rtl/test/tb_hdc_v41x_idx.vlt"       # no_inline on the indexer's replicated arithmetic
TB = ROOT / "rtl/test/tb_hdc_core_v41x.sv"
HARNESS = ROOT / "rtl/test/hdc_core_v41x_harness.cpp"
TOOLS = [ROOT / f"tools/{n}.py" for n in ("hdc_golden", "hdc_golden_v41", "hdc_isa_v41", "hdc_program_v41",
                                          "hdc_timing_v41", "hdc_timing_v41x", "hdc_images_v41x")] + \
        [Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ", "-Wno-PINCONNECTEMPTY",
              "-Wno-IMPORTSTAR",
              # ot_hdc_v41x_csa is declared by both the weight block (wgt_bdot) and the indexer block
              # (idx_arith): the bodies are identical, only the default W differs and every instance sets W
              "-Wno-MODDUP",
              # the index-key stream (block RTL) resets some flops synchronously
              "-Wno-SYNCASYNCNET", "-Wno-VARHIDDEN", "-Wno-UNOPTFLAT")
SINGLE = re.compile(r"HDC41 token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) fault=(\d+) "
                    r"logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
UTIL = re.compile(r"UTIL me_busy=(\d+) su_busy=(\d+) qe_busy=(\d+) xu_busy=(\d+) he_busy=(\d+) all_idle=(\d+)")
IDXHBMWR = re.compile(r"IDXHBMWR records=(\d+) writes=(\d+) highwater=(\d+) read_stalls=(\d+) "
                      r"writer_stalls=(\d+) refreshes=(\d+) refpb=(\d+)")
ISSUE = re.compile(r"ISSUE cyc=(\d+) pc=(\d+) unit=(\d+)")
STEP = re.compile(r"STEP pos=(\d+) in=(\d+) out=(\d+) gold=(\d+) cycles=(\d+) fault=(\d+)")
XCNT = re.compile(r"XCNT unit=(\w+) ops=(\d+) elems=(\d+)")
# classes whose counters the bench prints (a re-specified unit not listed here has no activation proof yet)
COUNTED = ("he", "me", "att", "idx", "sel", "eg", "su")
# the indexer's extra counters (bench XCNT lines): keys the HBM key stream delivered (elems: HBM beats), keys
# the engine scored (elems: head terms fused), index keys written to the HBM image (the key writer)
IDX_COUNTERS = ("idx_hbm", "idx_fused", "idx_kwr")
# coverage the runs do NOT prove, per unit (recorded, never counted as proven)
NOT_EXERCISED = {
    "he": ["MTP lane multiplier (mx_m > 1): the MTP program is not run on this core"],
    "idx": ["the HBM model's write path: runtime index keys reach it through a backdoor (write timing not "
            "modelled)", "more than one HBM stack (ot_hdc_v41x_idx_kmerge) and the 128-dim shipped key "
            "(the reduced key is 32-dim, NB = 1)", "the candidate mask (k_keep): every block is kept at the "
            "reduced shapes", "MTP lane multiplier"],
    "me": ["MTP lane multiplier (mx_m > 1) and the MTP layout's images"],
    "sel": ["static-count SELECTs (router top-6 over FP32 biased scores, a draft's top-1 over FP32 logits) stay "
            "on the as-built FP32 select: the re-specified select takes BF16 keys only -- not exercised on the new "
            "unit (SPEC GAP, owner a2e48e15: an FP32-key mode of the streaming select)",
            "the overflow fallback (rep_req re-stream): the reduced vehicle's <= 128 scores never overflow the "
            "line memories (reps counted, expected 0)",
            "k > 16 and the candidate top-2,048 (ot_hdc_v41x_sel_cand): the reduced vehicle's index top-k is 16",
            "the MTP program (sel_first of a draft top-1 is FP32, as-built path)"],
    "eg": ["BEATS > 1 (the shipped 256-code rows): the reduced vehicle's rows are 32 codes, one beat",
           "24 separate column-bank ROMs and the links between them: the core's single Engram ROM port stands "
           "in, one slice read a cycle",
           "more than one token slot in flight (the core runs one EGATHER at a time)"],
}


def expected_xu(prog, pos):
    """What the re-specified XU paths must have processed in ONE step at `pos`: the index-score SELECTs'
    scores (sum of n = xu_n + DYN over the dynamic-count SELECTs the step runs: X_SEL's ops) and the
    EGATHER ops' rows (24 each)."""
    dyn = I.dyn_values(0, pos)
    sel_ops = sel_n = eg_ops = 0
    for f in prog:
        if f["unit"] != I.UNIT_XU:
            continue
        if (f["pred"] == I.PRED_ODD and not pos & 1) or (f["pred"] == I.PRED_NZ and pos == 0):
            continue
        if f["xu_op"] == I.XU_SEL and f["xu_d_n"] != 0:
            n = f["xu_n"] + dyn[f["xu_d_n"]]
            if n:
                sel_ops += 1
                sel_n += n
        elif f["xu_op"] == I.XU_EGATHER:
            eg_ops += 1
    return {"sel": {"ops": sel_ops, "elements": sel_n}, "eg": {"ops": eg_ops, "elements": 24 * eg_ops}}


def xu_check(rec, img):
    """A single step's sel / eg counters must equal what its program asks of them."""
    import hdc_timing_v41 as T
    exp = expected_xu(T.load_prog(img), rec["position"])
    cnt = rec["activation"]["counters"]
    bad = {u: {"counted": cnt.get(u), "expected": exp[u]} for u in ("sel", "eg")
           if u in UNITS and cnt.get(u) != exp[u]}
    rec["activation"]["expected_from_program"] = {u: exp[u] for u in ("sel", "eg") if u in UNITS}
    rec["activation"]["count_mismatches"] = bad
    rec["activation"]["pass"] = rec["activation"]["pass"] and not bad
    rec["pass"] = rec["pass"] and not bad
    return rec
def indexer_record(prog, tags, issues):
    """The fused indexer in the record: the program's indexer ops, the dropped stream-unit head sum (an SU op
    tagged indexer that reduces -- none may be issued) and the key source."""
    issued = collections.Counter(tags[pc] for _, pc, _ in issues)
    su_hs = [n for n, f in enumerate(prog) if f["unit"] == I.UNIT_SU and "indexer" in tags[n] and f["red"]]
    fused = [n for n, f in enumerate(prog) if f["unit"] == I.UNIT_ME and f.get("me_fuse")]
    su_idx = [n for n, f in enumerate(prog) if f["unit"] == I.UNIT_SU and "indexer" in tags[n]]
    return {
        "fused_ops_in_program": len(fused),
        "su_indexer_headsum_ops_in_program": len(su_hs),
        "su_indexer_headsum_ops_issued": sum(1 for _, pc, u in issues if u == I.UNIT_SU and pc in set(su_hs)),
        "su_indexer_other_ops_in_program": len(su_idx) - len(su_hs),
        "dropped": "the per-head index-score ME op (S region) and the stream unit's ReLU x weight head-sum op "
                   "(S, WTS -> IS): the fused ME op (me_fuse, me_wts) writes IS on the indexer engine",
        "key_source": ("HBM: four replicated 68-B FP4 key images, dynamic quarter/group selector, kmerge and one "
                       "pooled tile; full K32/K128 writer records traverse three timed sector writes per stack"
                       if IDX_POOL else
                       "HBM: ot_hdc_v41x_idx_kstream (one stack, 32 pseudo-channels, 68-B FP4 keys) from the "
                       "bench's ot_hdc_v41x_idx_hbm (REFPB = 3 refresh-aware per-bank refresh, MRU tie-break, "
                       "64-beat queues); runtime keys written by ot_hdc_v41x_idx_kwr through the model's backdoor"),
    }


def counters(run):
    """{unit: {ops, elements}} from a bench log; the proof that each re-specified unit fired."""
    return {m.group(1): {"ops": int(m.group(2)), "elements": int(m.group(3))} for m in XCNT.finditer(run)}


def activation(cnt):
    """Every selected unit must have run ops and processed elements; one that stayed at 0 FAILS the run."""
    missing = [u for u in UNITS if u in COUNTED and (cnt.get(u, {}).get("ops", 0) == 0 or
                                                     cnt.get(u, {}).get("elements", 0) == 0)]
    if "idx" in UNITS:
        missing += [c for c in IDX_COUNTERS if cnt.get(c, {}).get("ops", 0) == 0]
    uncounted = [u for u in UNITS if u not in COUNTED]
    return {"counters": cnt, "zero_counter_units": missing, "units_without_counters": uncounted,
            "pass": not missing and not uncounted}


MULTI = re.compile(r"HDC41_MULTI steps=(\d+) generated=(\d+) mismatches=(\d+) total_cycles=(\d+) "
                   r"vm_mismatch=(\d+) kv_mismatch=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def category(tag):
    """Operator class of a program tag ("L12.softmax" -> "softmax")."""
    return tag.split(".", 1)[1] if "." in tag else tag


def breakdown(trace, tags, cycles):
    """Sequencer-attributed cycles: the interval up to an instruction's issue is
    charged to that instruction's operator (what the core waited for to issue
    it); the tail after the last issue to 'drain'."""
    issues = [(int(m.group(1)), int(m.group(2)), int(m.group(3))) for m in ISSUE.finditer(trace)]
    by = collections.Counter()
    ops = collections.Counter()
    prev = 0
    for cyc, pc, _unit in issues:
        c = category(tags[pc])
        by[c] += cyc - prev
        ops[c] += 1
        prev = cyc
    by["drain"] += cycles - prev
    return issues, {k: {"cycles": v, "issued_ops": ops.get(k, 0), "share": round(v / cycles, 4)}
                    for k, v in sorted(by.items(), key=lambda kv: -kv[1])}


def defines(lanes=None):
    return [f"+define+HDC_SW={lanes or I.SU_LANES}", f"+define+HDC_HHW={PARAMS['hhw']}",
            f"+define+HDC_MG={PARAMS['mg']}",
            f"+define+HDC_SUN={PARAMS['sun']}", f"+define+HDC_SUM={PARAMS['sum']}"] + \
        [f"+define+HDC_X_{u.upper()}={2 if u == 'idx' and IDX_POOL else int(u in UNITS)}" for u in X_UNITS]


def arith():
    """HDC_V41_ARITH of the ISA model: the R-ARITH classes of the re-specified units."""
    cls = sorted({c for u in UNITS for c in X_CLASSES[u]})
    return "legacy" if not cls else ("chunk8" if set(cls) == set(V.ARITH_CLASSES) else ",".join(cls))


def build(scratch: Path, lanes=None) -> Path:
    obj = scratch / f"obj{lanes or ''}"
    r = subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                        "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "--top-module", "tb_hdc_core_v41x", "-Mdir", str(obj),
                        f"-I{SVH.parent}", *defines(lanes), str(VLT), *map(str, rtl_sources(True)), str(TB),
                        str(HARNESS), "-CFLAGS", "-O1", "-j", "8"],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"verilator failed:\n{r.stdout[-4000:]}\n{r.stderr[-4000:]}")
    return obj / "Vtb_hdc_core_v41x"


def images(out: Path, *extra, lanes=None):
    env = dict(os.environ, HDC_SW=str(lanes or I.SU_LANES), HDC_V41_ARITH=arith(),
               HDC_V41_IDX_FUSED=str(int("idx" in UNITS)))
    r = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program_v41.py"), "--out", str(out), *extra],
                       capture_output=True, text=True, env=env)
    if r.returncode:
        raise SystemExit(f"hdc_program_v41 failed:\n{r.stdout}\n{r.stderr}")
    r2 = subprocess.run([sys.executable, str(ROOT / "tools/hdc_images_v41x.py"), "--out", str(out),
                         "--hhw", str(PARAMS["hhw"]), "--mg", str(PARAMS["mg"])], capture_output=True, text=True, env=env)
    if r2.returncode:
        raise SystemExit(f"hdc_images_v41x failed:\n{r2.stdout}\n{r2.stderr}")
    return r.stdout


def single(exe, img, trace=True):
    args = (img / "run.args").read_text().split()
    run = subprocess.run([str(exe), f"+DIR={img}", *args, *(["+TRACE"] if trace else [])], check=True,
                         capture_output=True, text=True).stdout
    m = SINGLE.search(run)
    if m is None:
        raise RuntimeError("core token did not produce a result:\n" + run[-4000:])
    token, pos, nxt, exp_tok, cycles, fault, bad_lg, bad_vm, bad_kv = map(int, m.groups())
    u = list(map(int, UTIL.search(run).groups()))
    rec = {"token": token, "position": pos, "next_token": nxt, "isa_next_token": exp_tok, "cycles": cycles,
           "fault": fault, "logit_mismatches": bad_lg, "vector_memory_mismatches": bad_vm,
           "kv_cache_mismatches": bad_kv,
           "unit_busy_cycles": dict(zip(("me", "su", "qe", "xu", "he"), u[:5])), "all_units_idle_cycles": u[5],
           "pass": "PASS" in run and nxt == exp_tok and fault == 0 and bad_lg + bad_vm + bad_kv == 0}
    rec["activation"] = activation(counters(run))
    rec["pass"] = rec["pass"] and rec["activation"]["pass"]
    m = re.search(r"XCNT unit=sel .* reps=(\d+)", run)
    if m:
        rec["activation"]["sel_replays"] = int(m.group(1))
    if IDX_POOL:
        wm = IDXHBMWR.search(run)
        if wm is None:
            raise RuntimeError("pooled token did not report timed HBM writes:\n" + run[-4000:])
        vals = list(map(int, wm.groups()))
        wr = dict(zip(("records", "sector_writes", "fifo_highwater", "read_stall_cycles",
                       "writer_stall_cycles", "refresh_events", "refpb_mode"), vals))
        rec["index_key_hbm_writer"] = wr
        rec["pass"] = rec["pass"] and wr["records"] == rec["activation"]["counters"]["idx_kwr"]["ops"] and \
                      wr["sector_writes"] == 12 * wr["records"] and wr["fifo_highwater"] <= 4 and \
                      wr["refpb_mode"] == 3 and wr["refresh_events"] > 0
    return xu_check(rec, img), run


def banking(prog, pos, lanes):
    """How the stream unit's vectors would fare in a vector memory of `lanes`
    word-interleaved banks (bank = element address mod lanes) instead of the
    behavioural many-ported one: a vector's lanes read a stream at stride
    si (VEC_I) or so (VEC_O); stride 0 is one broadcast read, an odd stride hits
    distinct banks, an even one collides.  Counted per vector (issue cycle) over
    the vector-memory streams (A..D reads, element writes) of the token."""
    dyn = I.dyn_values(0, pos)
    vec = clean = 0
    worst = collections.Counter()
    for f in prog:
        if f["unit"] != I.UNIT_SU or f["su_vec"] == I.VEC_SCALAR:
            continue
        if (f["pred"] == I.PRED_ODD and not pos & 1) or (f["pred"] == I.PRED_NZ and pos == 0):
            continue
        no, ni = f["su_nout"] + dyn[f["su_d_nout"]], f["su_nin"] + dyn[f["su_d_nin"]]
        if not no or not ni:
            continue
        n = no * -(-ni // lanes) if f["su_vec"] == I.VEC_I else -(-no // lanes) * ni
        axis = "si" if f["su_vec"] == I.VEC_I else "so"
        strides = [f[f"{x}_{axis}"] >> (1 if x in "bd" and f["b_half"] and axis == "si" else 0)
                   for x in "abcd" if f[f"{x}_src"] == I.SRC_VM and not (x == "c" and f["c_pair"])]
        if f["dst"] == I.DST_VM:
            strides.append(f[f"o_{axis}"])
        ok = all(st == 0 or st % 2 for st in strides)
        vec += n
        clean += n if ok else 0
        if not ok:
            worst[f"{axis}:{sorted(set(st for st in strides if st and not st % 2))}"] += n
    return {"bank_model": f"{lanes} banks, element address mod {lanes}", "vector_cycles": vec,
            "conflict_free_vector_cycles": clean, "conflict_free_share": round(clean / vec, 4) if vec else 1.0,
            "colliding_strides": dict(worst.most_common(8))}


def lane_sweep(s: Path, widths) -> list:
    """The single step at other stream-unit widths: same arithmetic, other lane counts."""
    import hdc_timing_v41 as T
    out = []
    for w in widths:
        img = s / f"img_sw{w}"
        images(img, lanes=w)
        rec, _ = single(build(s, w), img, trace=False)
        saved, I.SU_LANES = I.SU_LANES, w
        try:
            rec["timing_model_cycles"] = T.simulate(T.load_prog(img), rec["position"])
        finally:
            I.SU_LANES = saved
        out.append(dict(su_lanes=w, **rec))
    return out


def run(ngen: int, context: int, sweep=(), single_only=False, single_output=None) -> dict:
    with tempfile.TemporaryDirectory(dir=os.environ.get("OT_SCRATCH")) as scratch:   # a pool worker's /tmp is a 16 GB tmpfs
        s = Path(scratch)
        lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_hdc_core_v41x",
                               f"-GSW={I.SU_LANES}", f"-GHHW={PARAMS['hhw']}", f"-GMG={PARAMS['mg']}",
                               f"-GSUN={PARAMS['sun']}", f"-GSUM={PARAMS['sum']}",
                               *[f"-GX_{u.upper()}={2 if u == 'idx' and IDX_POOL else int(u in UNITS)}"
                                 for u in X_UNITS],
                               "-Wno-TIMESCALEMOD", f"-I{SVH.parent}", *map(str, rtl_sources())],
                              capture_output=True, text=True)
        img = s / "img"
        isa_out = images(img, "--multi", str(ngen))
        exe = build(s)
        expect = json.loads((img / "expect.json").read_text())
        tags = [ln.split(" ", 1)[1] for ln in (img / "prog_tags.txt").read_text().splitlines()]
        one, trace = single(exe, img)
        issues, bd = breakdown(trace, tags, one["cycles"])
        import hdc_timing_v41 as T
        prog = T.load_prog(img)
        tm, tiss = T.simulate(prog, one["position"], trace=True)
        model_at = {n: g for g, n, _ in tiss}
        err = [model_at[pc] - c for c, pc, _ in issues]
        one["timing_model"] = {"cycles": tm, "relative_error": round((tm - one["cycles"]) / one["cycles"], 6),
                               "max_abs_issue_error_cycles": max(map(abs, err))}
        one["vector_memory_banking"] = banking(prog, one["position"], I.SU_LANES)
        one["golden_next_token"] = expect["golden"]
        one["oracle_next_token"] = expect["oracle"]
        one["pass"] = one["pass"] and one["next_token"] == expect["golden"]
        single_record = {
            "schema": "opentallas.hdc-v41x-decode-single.v1",
            "mode": "single_step",
            "respecified_units": list(UNITS),
            "as_built_units": [u for u in X_UNITS if u not in UNITS],
            "hdc_v41_arith": arith(),
            "engine_parameters": dict(PARAMS),
            "fp_simulation": PARAMS.get("fp", "rtl"),
            "claim_boundary": (
                "Single-token functional Verilator gate with DPI bit-equivalent FP simulation stand-ins; "
                "physical FP RTL is not elaborated. Four replicated HBM key images use 272 encoded bytes/key "
                "and twelve timed sector writes/key; the selector rereads super-block prefixes and one pooled "
                "tile back-pressures kmerge, so full-rate bandwidth is not claimed."
                if IDX_POOL and PARAMS.get("fp") == "dpi" else
                "Single-token functional Verilator gate; physical timing is not established."),
            "not_exercised": {u: NOT_EXERCISED.get(u, []) for u in UNITS},
            **({"indexer": indexer_record(prog, tags, issues)} if "idx" in UNITS else {}),
            "status": "pass" if one["pass"] and lint.returncode == 0 else "fail",
            "single_step": one,
            "per_operator_cycles": bd,
            "verilator_lint": {"returncode": lint.returncode, "flags": list(LINT_FLAGS),
                               "messages": lint.stderr.strip().splitlines()[:20]},
            "input_sha256": {str(p.relative_to(ROOT)): sha(p)
                             for p in (SVH, VLT, *rtl_sources(True), TB, HARNESS, *TOOLS)},
        }
        if single_output is not None:
            single_output.parent.mkdir(parents=True, exist_ok=True)
            pending = single_output.with_name(single_output.name + ".tmp")
            pending.write_text(json.dumps(single_record, indent=2) + "\n")
            pending.replace(single_output)
        if single_only:
            return single_record
        multi = subprocess.run([str(exe), f"+DIR={img}", "+MULTI", "+NPROMPT=8", f"+NGEN={ngen}"], check=True,
                               capture_output=True, text=True).stdout
        steps = [dict(zip(("position", "input", "output", "isa_output", "cycles", "fault"), map(int, x.groups())))
                 for x in STEP.finditer(multi)]
        mm = list(map(int, MULTI.search(multi).groups()))
        gen = [st["output"] for st in steps[7:]]
        multi_rec = {"prompt_tokens": 8, "generated_tokens": gen,
                     "isa_generated_tokens": expect["multi"]["generated"],
                     "golden_generated_tokens": expect["multi"]["golden"],
                     "isa_logits_bit_exact_with_golden_every_step": expect["multi"]["all_logits_exact"],
                     "steps": mm[0], "mismatches": mm[2], "total_cycles": mm[3],
                     "final_vector_memory_mismatches": mm[4], "final_kv_cache_mismatches": mm[5],
                     "per_step": steps,
                     "activation": activation(counters(multi)),
                     "pass": "PASS" in multi and mm[2] + mm[4] + mm[5] == 0 and gen == expect["multi"]["golden"]}
        multi_rec["pass"] = multi_rec["pass"] and multi_rec["activation"]["pass"]
        longc = None
        if context:
            imgc = s / "imgc"
            images(imgc, "--context", str(context))
            rec, _ = single(exe, imgc, trace=False)
            longc = rec
        sweep_rec = lane_sweep(s, sweep) if sweep else None
    counts = collections.Counter(u for _, _, u in issues)
    status = "pass" if one["pass"] and multi_rec["pass"] and lint.returncode == 0 and \
        (longc is None or longc["pass"]) and all(r["pass"] for r in sweep_rec or ()) else "fail"
    return {
        "schema": "opentallas.hdc-v41x-decode-campaign.v1",
        "respecified_units": list(UNITS),
        "as_built_units": [u for u in X_UNITS if u not in UNITS],
        "hdc_v41_arith": arith(),
        "engine_parameters": dict(PARAMS),
        "not_exercised": {u: NOT_EXERCISED.get(u, []) for u in UNITS},
        **({"indexer": indexer_record(prog, tags, issues)} if "idx" in UNITS else {}),
        "status": status,
        "claim_boundary": "functional token-level RTL simulation (Verilator, cycle-accurate at the core boundary) "
                          "with behavioural synchronous-read memories (many-ported vector memory: four operand reads, "
                          "an element write and a reducer write per stream lane); the Sinkhorn "
                          "is the routed one-normalisation-per-step unit (ot_hdc_sinkhorn) run as a 7-core-cycle "
                          "multicycle path (its 151.9 MHz route at a 1 GHz core); clock rate is not claimed here. "
                          + ("FP arithmetic uses bit-equivalent DPI simulation stand-ins; physical FP RTL is not "
                             "elaborated in this full-core gate. " if PARAMS.get("fp") == "dpi" else "")
                          + ("X_IDX=2 uses four replicated HBM images (272 encoded bytes per logical key), "
                             "twelve timed sector writes per key, and a prefix-rereading correctness-rate selector; "
                             "full-rate read bandwidth and tile replication are not claimed."
                             if IDX_POOL else ""),
        "fp_simulation": PARAMS.get("fp", "rtl"),
        "vehicle": "deepseek-v4.1-flash-reduced-v2 (dim 160, 40 layers, 64 heads of 32, hc 4, 12 experts top-6 "
                   "inter 64, window 128, index top-16, Engram layers 1 and 14, vocab 4040)",
        "parameters": {"su_lanes": I.SU_LANES, "me_lanes_per_group": I.W_LANES, "me_groups": I.GROUPS,
                       "interleave": I.INTERLEAVE,
                       "qe_blockdot_lanes": I.BL, "he_lanes": I.HE_LANES, "attention_rows_per_layer": I.T_MAX,
                       "program_instructions": expect["prog_words"],
                       "issued_per_unit": {n: counts.get(u, 0) for n, u in (("me", 1), ("su", 2), ("qe", 3),
                                                                            ("xu", 4), ("he", 5))},
                       "me_rom_words": expect["wrom_words"], "qe_rom_words": expect["qrom_words"],
                       "constant_rom_words": expect["crom_words"], "engram_rom_rows": expect["erom_words"]},
        "isa_model": isa_out.strip().splitlines(),
        "single_step": one,
        "per_operator_cycles": bd,
        "end_to_end": multi_rec,
        "long_context": longc,
        **({"su_lane_sweep": sweep_rec} if sweep_rec else {}),
        "verilator_lint": {"returncode": lint.returncode, "flags": list(LINT_FLAGS),
                           "messages": lint.stderr.strip().splitlines()[:20]},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (SVH, VLT, *rtl_sources(True), TB, HARNESS, *TOOLS)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--ngen", type=int, default=3)
    parser.add_argument("--context", type=int, default=40)
    parser.add_argument("--sweep-lanes", default="", help="also run the single step at these stream-unit widths, "
                                                          "e.g. 4,16")
    parser.add_argument("--units", default="he",
                        help="the re-specified units to build (the rest as built), e.g. he,qe; '' for none")
    parser.add_argument("--idx-pool", action="store_true", help="use X_IDX=2, four replicated HBM stacks and pooled tile")
    parser.add_argument("--hhw", type=int, default=8, help="HCP lanes per group")
    parser.add_argument("--mg", type=int, default=8, help="ME weight tile chunk units (8*mg lanes)")
    parser.add_argument("--sun", type=int, default=16, help="vector-unit light lanes")
    parser.add_argument("--sum", type=int, default=8, help="vector-unit SFU lanes")
    parser.add_argument("--fp", choices=("rtl", "dpi"), default="rtl",
                        help="bit-level RTL or bit-equivalent host-float stand-ins for the large full-core simulator")
    parser.add_argument("--single-only", action="store_true", help="stop after the bit-exact single decode step")
    parser.add_argument("--single-output", type=Path, help="incremental single-step JSON path; defaults to "
                        "<output stem>.single.json")
    args = parser.parse_args()
    global UNITS, IDX_POOL
    UNITS = tuple(u for u in args.units.split(",") if u)
    assert set(UNITS) <= set(X_UNITS), UNITS
    IDX_POOL = args.idx_pool
    assert not IDX_POOL or "idx" in UNITS
    if IDX_POOL:
        RTL.extend(ROOT / f"rtl/hdc/v41x/{n}.sv" for n in (
            "ot_hdc_v41x_idx_pcol", "ot_hdc_v41x_idx_hsum", "ot_hdc_v41x_idx_pool_finish",
            "ot_hdc_v41x_idx_pool_batch", "ot_hdc_v41x_idx_pool_replica",
            "ot_hdc_v41x_idx_pool_adapt", "ot_hdc_v41x_idx_pool_kwr",
            "ot_hdc_v41x_idx_pool_hbm_bridge"))
        NOT_EXERCISED["idx"] = [
            "the index-key HBM controllers are timing models, not physical HBM RTL",
            "the shipped K128 program (the decode vehicle uses K32)",
            "the candidate mask (k_keep): every block is kept in the reduced vehicle",
            "the full-rate replicated tile layout; the functional selector rereads super-block prefixes",
            "MTP lane multiplier"]
    PARAMS["hhw"] = args.hhw
    PARAMS["mg"] = args.mg
    PARAMS["sun"], PARAMS["sum"] = args.sun, args.sum
    PARAMS["fp"] = args.fp
    single_output = args.single_output or args.output.with_name(args.output.stem + ".single.json")
    result = run(args.ngen, args.context, [int(x) for x in args.sweep_lanes.split(",") if x],
                 single_only=args.single_only, single_output=single_output)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    s = result["single_step"]
    print(result["status"], "next token", s["next_token"], "cycles", s["cycles"],
          "generated", result.get("end_to_end", {}).get("generated_tokens", []))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
