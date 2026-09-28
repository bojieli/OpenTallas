#!/usr/bin/env python3
"""RTL package-array token gates for the V4.1x HCP core and controller.

Each package combines an ot_hdc_core_v41x (X_HE=1, other X units=0) and an
ot_rom_pkg_ctrl_x in a contiguous layer-range pipeline. The point-to-point
gate runs three prompt tokens and one generated token for one user. The
switched gate has three body packages, two split head packages, two users,
SIDE messages, head multicast, result collection, injected link stalls, and
30/109/228-cycle half-link delay taps (about 210 ns for two 109-cycle halves
at an assumed 0.92 ns cycle, before the router).
Both start from empty persistent state.
The ISA pipeline is checked against hdc_golden_v41 before RTL simulation.
RTL then checks reduced tokens, generated tokens, all 4,040 lm_head logits,
and final KV/vector-memory state bit for bit against that ISA pipeline.

The record includes cycles per token-step, per-package utilization and waits,
and link credit stalls. Memories are behavioral and the package link uses a
delay-line PHY stand-in. Writes results/rtl/hdc_v41x_array_campaign.json.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# The first package gate adopts the new HCP arithmetic order only. Keep the
# ISA/golden contract aligned with X_HE=1 in the array bench.
ALL_UNIT = "--all-unit" in sys.argv
LINK_ONLY = None
os.environ["HDC_V41_ARITH"] = "chunk8" if ALL_UNIT else "he"
if ALL_UNIT:
    os.environ["HDC_V41_IDX_FUSED"] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402
import hdc_program_v41 as P  # noqa: E402
import hdc_program_v41_array as A  # noqa: E402
import hdc_timing_v41 as T  # noqa: E402
import rtl_hdc_v41x_decode_campaign as core  # noqa: E402
import hdc_images_v41x as ximg  # noqa: E402
if ALL_UNIT:
    core.UNITS = tuple(core.X_UNITS)
    core.PARAMS["fp"] = "dpi"

OUT = ROOT / "results/rtl/hdc_v41x_array_campaign.json"
TB = ROOT / "rtl/test/tb_hdc_v41x_array.sv"
HARNESS = ROOT / "rtl/test/hdc_v41x_array_harness.cpp"
LINK = ROOT / "rtl/rom/ot_rom_pkg_link.sv"
ROUTER = ROOT / "rtl/rom/ot_rom_fabric_router.sv"
CTRL = ROOT / "rtl/rom/ot_rom_pkg_ctrl_x.sv"
# Verilator 4 resolves hierarchical testbench memory references even inside
# inactive generate branches. Include these definitions in either build mode;
# the unused instances are removed during elaboration.
BENCH_AUX_RTL = sorted((ROOT / "rtl/hdc/v41x").glob("ot_hdc_v41x_idx_pool_*.sv")) + [
    ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_pcol.sv",
    ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_hsum.sv",
    ROOT / "rtl/hdc/hbm/ot_hdc_qstream.sv",
    ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv",
]
MG_SIDE, MG_HEAD, DESTS = 32, 48, 64

# name: (body packages, lm_head parts, lm_head multicast, shared state, fabric,
#        users, extra user counts, stall %, prompt tokens, generated tokens,
#        channel-delay sweep in cycles per link/half-link).
CONFIGS = {
    "b2_p2p": (2, 0, False, "relay", "p2p", 1, (), 0, 3, 1, (60,)),
    "b2_p2p_u2": (2, 0, False, "relay", "p2p", 2, (), 0, 3, 1, (60,)),
    "b3_h2_switch_stall": (3, 2, True, "mcast", "switch", 2, (), 10, 2, 1, (30, 109, 228)),
}
RES = re.compile(r"HDC41_ARRAY nodes=(\d+) users=(\d+) generated=(\d+) mismatches=(\d+) logit_mismatch=(\d+) "
                 r"lm_head_checks=(\d+) state_mismatch=(\d+) total_cycles=(\d+)")
NODE = re.compile(r"NODE node=(\d+) busy=(\d+) side_wait=(\d+) tx_wait=(\d+) starved=(\d+) jobs=(\d+) "
                  r"state_mismatch=(\d+)")
TOK = re.compile(r"TOK user=(\d+) pos=(\d+) token=(\d+) cycle=(\d+)")
STALLS = re.compile(r"LINK_STALLS (\d+)")
DONE = re.compile(r"USERS_DONE (\d+)")
BUILD_SLOTS = threading.Semaphore(2)       # Verilator builds of this bench take ~6.5 GB each
# a machine-wide gate for heavy builds, if the host provides one (waits for a slot and free memory)
GATE = [g] if (g := os.environ.get("OT_BUILD_GATE", "/tmp/claude-1000/orfs_gate.sh")) and Path(g).exists() else []
REUSE = False                              # --reuse: keep existing builds and finished run logs


def sh(cmd, **kw) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r.stdout


def fn(name, values):
    cases = "".join(f"            {k}: {name} = {int(v)};\n" for k, v in enumerate(values))
    return (f"    function automatic integer {name}(input integer n);\n        case (n)\n{cases}"
            f"            default: {name} = 0;\n        endcase\n    endfunction\n")


def config_svh(plan, lay, fabric):
    n = plan.n
    roles = [plan.role(k) for k in range(n)]
    V_ = lay.vm.map

    def hid(r):
        d = r["hid_dest"]
        return MG_HEAD if d == "HEADS" else d

    route = 0
    if fabric == "switch":
        for d in range(n):
            route |= 1 << (d * n + d)
        for q, s in plan.side.items():
            for d in s["dests"]:
                route |= 1 << ((MG_SIDE + q) * n + d)
        for d in range(plan.nb, n):
            route |= 1 << (MG_HEAD * n + d)
    else:
        assert not plan.side and not plan.head_mcast, "multicast needs the switched fabric"
    side = [plan.side.get(k) for k in range(n)]
    sdest = [(s["dests"][0] if len(s["dests"]) == 1 else MG_SIDE + k) if s else 0 for k, s in enumerate(side)]
    vocab = plan.vocab
    prows = [(vocab if r["head"] is True else vocab // plan.hp) if r["head"] is not None else 0 for r in roles]
    txt = ["// GENERATED by tools/rtl_hdc_v41x_array_campaign.py -- one array configuration.\n",
           f"    localparam integer NODES = {n}, FABRIC = {int(fabric == 'switch')}, PB = {plan.pb};\n",
           f"    localparam integer TMAP = {lay.cb['tmap']}, VOCAB = {vocab}, NPR = 2;\n",
           f"    localparam integer RPARTS = {plan.result_parts()};\n",
           f"    localparam [{DESTS * n - 1}:0] ROUTE = {DESTS * n}'h{route:x};\n",
           fn("C_PRIME", [plan.ehash(k) for k in range(n)]),
           fn("C_HEAD", [r["head"] is not None for r in roles]),
           fn("C_PROWS", prows),
           fn("C_ROW0", [r["row0"] for r in roles]),
           fn("C_HID", [hid(r) for r in roles]),
           fn("C_TXW", [r["txw"] for r in roles]),
           fn("C_RXW", [r["rxw"] for r in roles]),
           fn("C_TXB", [r["txb"] for r in roles]),
           fn("C_RXB", [r["rxb"] for r in roles]),
           fn("C_RES", [r["send_result"] for r in roles]),
           fn("C_COMB", [r["combine"] for r in roles]),
           fn("C_SOUT", [s is not None for s in side]),
           fn("C_SDEST", sdest),
           fn("C_SW", [s["words"] if s else 0 for s in side]),
           fn("C_STXB", [s["txb"] if s else 0 for s in side]),
           fn("C_SRXB", [s["rxb"] if s else 0 for s in side]),
           fn("C_SIN", [r["side_in"] for r in roles])]
    assert V_["H"] == 0
    return "".join(txt)


def build(obj: Path, svh: str, users: int, stall: int) -> Path:
    obj.mkdir(parents=True, exist_ok=True)
    exe = obj / "Vtb_hdc_v41x_array"
    stamp = hashlib.sha256((svh + f"{users} {stall} all_unit={ALL_UNIT}" + "".join(
        hashlib.sha256(p.read_bytes()).hexdigest() for p in rtl_sources())).encode()).hexdigest()
    if REUSE and exe.exists() and (obj / "stamp").exists() and (obj / "stamp").read_text() == stamp:
        return exe
    (obj / "v41_array_cfg.svh").write_text(svh)
    with BUILD_SLOTS:
        sh([*GATE, "verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
            "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "-Wno-MULTIDRIVEN", "-Wno-TIMESCALEMOD",
            "-Wno-MODDUP", "-Wno-VARHIDDEN", "-Wno-UNOPTFLAT", "-Wno-PINMISSING",
            "--top-module", "tb_hdc_v41x_array",
            f"-GUSERS={users}", f"-GSTALL={stall}", "-Mdir", str(obj), f"-I{obj}", f"-I{core.SVH.parent}",
            *([str(core.VLT)] if ALL_UNIT else []),
            f"+define+HDC_SW={I.SU_LANES}",
            *([f"+define+HDC_X_{x}={2 if x == 'IDX' else 1}" for x in
               ("HE", "ME", "ATT", "IDX", "SEL", "EG", "SU")] + ["+define+HDC_W_HBM=1"]
              if ALL_UNIT else []),
            *map(str, core.rtl_sources(True) if ALL_UNIT else core.RTL),
            *map(str, BENCH_AUX_RTL),
            str(LINK), str(ROUTER), str(CTRL), str(TB), str(HARNESS),
            "-CFLAGS", "-O1", "-MAKEFLAGS", "OPT_FAST=-O0 OPT_GLOBAL=-O0", "-j", "16"])
    (obj / "stamp").write_text(stamp)
    return exe


def parse(out: str, users: int, steps_per_user: int, ngen: int) -> dict:
    m = RES.search(out)
    if not m:
        raise RuntimeError(f"no result\n{out[-3000:]}")
    nodes, u, gen, bad, lbad, lchk, sbad, cycles = map(int, m.groups())
    per = [dict(zip(("package", "busy", "side_wait", "send_wait", "starved", "jobs", "state_mismatches"),
                    map(int, x))) for x in NODE.findall(out)]
    per.sort(key=lambda d: d["package"])
    toks = [dict(zip(("user", "position", "token", "cycle"), map(int, t))) for t in TOK.findall(out)]
    steps = u * steps_per_user
    done = int(DONE.search(out).group(1))
    return {"packages": nodes, "users": u, "generated_tokens": gen, "token_mismatches": bad,
            "logit_mismatches": lbad, "lm_head_steps_checked": lchk, "state_mismatches": sbad,
            "total_cycles": cycles, "token_steps": steps, "cycles_per_token_step": round(cycles / steps, 1),
            "users_completed": done, "link_credit_stalls": int(STALLS.search(out).group(1)),
            "per_package": per, "tokens": toks,
            "pass": "PASS" in out and bad == 0 and lbad == 0 and sbad == 0 and done == u
            and gen == u * ngen and lchk > 0}


def timing(plan, progs, steps):
    """Cycle model of every package's program at every position (the RTL is the
    measurement; this attributes it)."""
    per = []
    for k, prog in enumerate(progs):
        per.append([T.simulate(prog, p) for p in range(steps)])
    return per


def run_config(name, spec, ctx, scratch: Path, log) -> dict:
    body, hp, hmc, shared, fabric, users, fewer, stall, plen, ngen, link_delays = spec
    if LINK_ONLY is not None:
        if LINK_ONLY not in link_delays:
            raise ValueError(f"{name}: link delay {LINK_ONLY} is not in configured sweep {link_delays}")
        link_delays = (LINK_ONLY,)
    lay, model, base = ctx["lay"], ctx["model"], ctx["base"]
    with ctx["isa_lock"]:
        t0 = time.time()
        gold = A.golden_runs(model, ngen, scratch / "gold.json", plen)
        plan = A.Plan(lay, A.split(model, body), hp, hmc, shared)
        progs = ([A.StageBuilder(plan.lay, qchunk=P.QCHUNK).stage(plan, k)
                  for k in range(plan.n)] if ALL_UNIT else A.stage_programs(plan))
        recs, states = A.run_pipeline(plan, progs, base, gold)
        img = scratch / f"cfg_{name}"
        steps = A.write_config(img, plan, progs, gold, states)
        if ALL_UNIT:
            sectors, first = P.qe_hbm_image(lay)
            for k, prog in enumerate(progs):
                ents = P.qe_fetch_list(lay, prog, first)
                (img / f"qlist_stage{k:02d}.hex").write_text(
                    P.hexwords(P.encode_list(ents), P.LIST_BITS))
                if not ents and k < plan.nb:
                    raise RuntimeError(f"body stage {k}: empty QE HBM fetch list")
        log(f"{name}: ISA pipeline {recs} ({time.time() - t0:.0f} s)")
    isa_ok = all(r["logits_bit_exact_every_step"] and r["argmax_and_value_every_step"] for r in recs)
    if not isa_ok:
        raise RuntimeError(f"{name}: ISA pipeline is not bit-exact with the golden: {recs}")
    svh = config_svh(plan, lay, fabric)
    t0 = time.time()
    exe = build(scratch / f"obj_{name}", svh, users, stall)
    log(f"{name}: built ({time.time() - t0:.0f} s)")
    tm = timing(plan, progs, steps)
    runs = []

    def link_record(r, link_ch):
        r["link_channel_cycles"] = link_ch
        r["two_half_link_cycles_before_router"] = 2 * (2 + link_ch + 2 + 1) if fabric == "switch" else None
        r["two_half_link_ns_at_assumed_0p92ns_before_router"] = (
            round(r["two_half_link_cycles_before_router"] * 0.92, 2) if fabric == "switch" else None)
        return r

    for link_ch in link_delays:
        for active in (users, *fewer):
            t0 = time.time()
            log_path = scratch / f"out_{name}_u{active}_ch{link_ch}.txt"
            run_stamp = scratch / f"stamp_{name}_u{active}_ch{link_ch}"
            if REUSE and log_path.exists() and run_stamp.exists() and RES.search(log_path.read_text()) and \
                    (scratch / f"obj_{name}" / "stamp").read_text() == run_stamp.read_text():
                runs.append(link_record(parse(log_path.read_text(), active, steps, ngen), link_ch))
                log(f"{name} u{active} ch{link_ch}: reused")
                continue
            with open(log_path, "w") as fh:          # streamed, so a long run can be watched
                rc = subprocess.run(["stdbuf", "-oL", str(exe), f"+DIR={img}", f"+ROMS={ctx['roms']}",
                                     f"+NUSERS={active}", f"+NPROMPT={plen}", f"+NGEN={ngen}",
                                     f"+LINK_CH={link_ch}", "+HB=1000000"],
                                    stdout=fh, stderr=subprocess.STDOUT).returncode
            out = log_path.read_text()
            run_stamp.write_text((scratch / f"obj_{name}" / "stamp").read_text())
            if rc:
                raise RuntimeError(f"{name}: simulator exited {rc}\n{out[-3000:]}")
            r = link_record(parse(out, active, steps, ngen), link_ch)
            log(f"{name} u{active} ch{link_ch}: {'PASS' if r['pass'] else 'FAIL'} {r['total_cycles']} cycles "
                f"({time.time() - t0:.0f} s)")
            runs.append(r)
    roles = [plan.role(k) for k in range(plan.n)]
    return {
        "name": name, "body_packages": body, "lm_head_packages": hp or 0, "lm_head_multicast": hmc,
        "shared_state": shared, "fabric": fabric, "stall_percent": stall,
        "link_flit_bytes": 64, "link_credits_flits": 32, "link_delay_sweep_cycles_per_half": list(link_delays),
        "prompt_tokens": plen, "generated_tokens_per_user": ngen, "steps_per_user": steps,
        "prompts": [g["prompt"] for g in gold], "golden_generated": [g["generated"] for g in gold],
        "layers_per_package": [plan.body[k] if k < plan.nb else [] for k in range(plan.n)],
        "hop_words": [r["txw"] for r in roles],
        "relayed_items": {k: [f"{a}{b}" for (a, b), _, _ in plan.out[k]] for k in range(plan.n)
                          if plan.out[k] and shared == "relay"},
        "side_messages": {k: {"words": s["words"], "consumer_packages": s["dests"],
                              "items": [f"{a}{b}" for (a, b), _, _ in plan.out[k]]}
                          for k, s in plan.side.items()},
        "engram_hashing_packages": [k for k in range(plan.n) if plan.ehash(k)],
        "program_instructions": [len(p) for p in progs],
        "isa_pipeline": recs,
        "timing_model_cycles_per_position": tm,
        "runs": runs,
        "pass": isa_ok and all(r["pass"] for r in runs),
    }


def rtl_sources():
    pool = [*BENCH_AUX_RTL, *([core.VLT] if ALL_UNIT else [])]
    return [TB, HARNESS, LINK, ROUTER, CTRL, core.SVH,
            *(core.rtl_sources(True) if ALL_UNIT else core.RTL), *pool]


def sources():
    return [*rtl_sources(), *core.TOOLS, ROOT / "tools/hdc_program_v41_array.py", Path(__file__)]


def run(names, scratch: Path) -> dict:
    lines = []
    lk = threading.Lock()

    def log(s):
        with lk:
            lines.append(s)
            print(s, flush=True)

    model = V.Model()
    lay = P.Layout(model)
    A.place_head_parts(lay)
    roms = scratch / "roms"
    if not (roms / "qrom.hex").exists():
        A.write_roms(roms, lay)
        ximg.write_banked(roms / "hbank.hex", ximg.hbank_image(lay, 8), 32, 8)
    if ALL_UNIT:
        ximg.write(roms, lay, hhw=8, mg=8)
        if not (roms / "hbm_q.hex").exists():
            sectors, _ = P.qe_hbm_image(lay)
            (roms / "hbm_q.hex").write_text(P.hexwords(sectors, P.QSEC))
    base = P.Machine(lay, np.zeros(I.KV_WORDS * I.W_LANES, dtype=np.float32),
                     np.zeros(I.VM_ELEMS, dtype=np.float32))
    ctx = dict(lay=lay, model=model, base=base, roms=roms, isa_lock=threading.Lock())
    with ThreadPoolExecutor(len(names)) as pool:
        results = list(pool.map(lambda nm: run_config(nm, CONFIGS[nm], ctx, scratch, log), names))
    for c in results:
        for r in c["runs"]:
            busy = [p["busy"] for p in r["per_package"]]
            r["bottleneck_package"] = int(np.argmax(busy))
            r["bottleneck_busy_cycles_per_token_step"] = round(max(busy) / r["token_steps"], 1)
    return {
        "schema": ("opentallas.hdc-v41x-array-allunit-hbm-gate.v1" if ALL_UNIT else
                   "opentallas.hdc-v41x-array-hcp-gate.v1"),
        "status": "pass" if all(c["pass"] for c in results) else "fail",
        "simulation_build_note": os.environ.get("OT_ARRAY_BUILD_NOTE", "Verilator --build, 16 jobs, OPT_FAST=-O0 OPT_GLOBAL=-O0"),
        "claim_boundary": ("All-unit X_HE=1 X_ME=1 X_ATT=1 X_IDX=2 X_SEL=1 X_EG=1 "
                           "X_SU=1 W_HBM=1; per-package QE qstream and timed HBM model, "
                           "bounded pooled index-key writer/read bridge and four timed HBM stack models; "
                           "reduced array gate with per-user pooled index-key HBM sectors. "
                           "Behavioral memories, link PHY stand-in, "
                           "and bit-equivalent simulation-only FP DPI units; "
                           "no full-model or production-rate claim." if ALL_UNIT else
                           "functional, cycle-accurate RTL simulation (Verilator) of a layer-range pipeline of "
                          "V4.1x cores with X_HE=1 and other X units=0; package control is ot_rom_pkg_ctrl_x; "
                          "the selected fabric is RTL point-to-point links or ot_rom_fabric_router; memories "
                          "are behavioral and the link PHY is a delay-line stand-in (60 cycles point-to-point, "
                          "30, 109 or 228 cycles per switched half-link; the 109-cycle setting represents about "
                          "209.76 ns over two half-links at an assumed 0.92 ns cycle before router latency; "
                          "credit return is immediate in the link RTL); per-user persistent state uses base offsets in behavioral "
                          "memories; Engram history restore is testbench logic. Clock rate is not claimed."),
        "vehicle": "deepseek-v4.1-flash-reduced-v2 (40 layers, vocab 4040)",
                "configurations": results,
        "log": lines,
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--only", nargs="*", choices=sorted(CONFIGS), help="run these configurations only")
    parser.add_argument("--scratch", type=Path, help="build and run here and keep it")
    parser.add_argument("--reuse", action="store_true",
                        help="with --scratch: keep builds and run logs made from the same sources")
    parser.add_argument("--all-unit", action="store_true", help="all adopted V4.1x X units and timed weight/index HBM")
    parser.add_argument("--link-delay", type=int, help="run one configured link delay (cycles per link/half-link)")
    args = parser.parse_args()
    if args.all_unit and args.only not in (["b2_p2p"], ["b2_p2p_u2"], ["b3_h2_switch_stall"]):
        parser.error("--all-unit requires one explicit b2 or b3 configuration")
    if args.link_delay is not None and (not args.only or len(args.only) != 1):
        parser.error("--link-delay requires exactly one --only configuration")
    global REUSE, LINK_ONLY
    REUSE = args.reuse
    LINK_ONLY = args.link_delay
    names = args.only or [n for n in CONFIGS if n != "b2_p2p_u2"]
    with tempfile.TemporaryDirectory() as tmp:
        scratch = args.scratch or Path(tmp)
        scratch.mkdir(parents=True, exist_ok=True)
        result = run(names, scratch)
    args.output.write_text(json.dumps(result, indent=1) + "\n")
    for c in result["configurations"]:
        for r in c["runs"]:
            print("PASS" if r["pass"] else "FAIL", c["name"], r["users"], "users:", r["total_cycles"], "cycles,",
                  r["cycles_per_token_step"], "cycles/step")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
