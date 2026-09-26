#!/usr/bin/env python3
"""Token-level RTL simulation of a multi-package ROM array of V4.1 decode cores.

rtl/test/tb_hdc_v41_array.sv builds each package from one ot_hdc_core_v41 and
one ot_rom_pkg_ctrl_x (the package controller with token forwarding and SIDE
messages; memories behavioural), in the layer-range pipeline that
tools/hdc_program_v41_array.py plans: body package k holds a contiguous range
of the 40 layers (package 0 also the embedding), lm_head shares the last body
package or is split by vocabulary over its own packages.  Every user starts from
an EMPTY state, runs an 8-token prompt and generates 3 tokens; users alternate
between two prompts (the oracle's and a different one), so per-user state
slices are exercised with different contexts in flight at once.

Checked, bit for bit, against hdc_golden_v41 (through the ISA pipeline model,
which is itself checked against the golden before any RTL runs):
* every step's reduced token at package 0 (prompt positions too), and the
  generated tokens;
* every step's logits of every lm_head package (all 4,040 rows);
* at the end, every package's KV slice and persistent vector-memory segment of
  every user against the ISA pipeline model's final state for that prompt.

Reports cycles per token-step (aggregate over users), speed-up over one core
(results/rtl/hdc_v41_decode_campaign.json end-to-end), per-package busy /
starved / waiting-for-SIDE / waiting-for-send cycles, link credit stalls, and
the one-user step latency.  Writes results/rtl/hdc_v41_array_campaign.json.
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

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402
import hdc_program_v41 as P  # noqa: E402
import hdc_program_v41_array as A  # noqa: E402
import hdc_timing_v41 as T  # noqa: E402
import rtl_hdc_v41_decode_campaign as core  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_array_campaign.json"
TB = ROOT / "rtl/test/tb_hdc_v41_array.sv"
HARNESS = ROOT / "rtl/test/hdc_v41_array_harness.cpp"
LINK = ROOT / "rtl/rom/ot_rom_pkg_link.sv"
ROUTER = ROOT / "rtl/rom/ot_rom_fabric_router.sv"
CTRL = ROOT / "rtl/rom/ot_rom_pkg_ctrl_x.sv"
MG_SIDE, MG_HEAD, DESTS = 32, 48, 64

# name: (body packages, lm_head parts, lm_head multicast, shared state, fabric, users, extra user counts, stall %,
#        prompt tokens, generated tokens).  A V4.1 token step costs ~1.05 M core cycles, so the wider arrays
#        run a prefix of each prompt (every package still sees every user at several positions).
CONFIGS = {
    "b2_p2p": (2, 0, False, "relay", "p2p", 2, (), 0, 8, 3),
    "b4_p2p": (4, 0, False, "relay", "p2p", 4, (), 0, 4, 2),
    "b8_switch_mcast_h2": (8, 2, True, "mcast", "switch", 8, (), 0, 3, 2),
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
    txt = ["// GENERATED by tools/rtl_hdc_v41_array_campaign.py -- one array configuration.\n",
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
    exe = obj / "Vtb_hdc_v41_array"
    stamp = hashlib.sha256((svh + f"{users} {stall}" + "".join(
        hashlib.sha256(p.read_bytes()).hexdigest() for p in rtl_sources())).encode()).hexdigest()
    if REUSE and exe.exists() and (obj / "stamp").exists() and (obj / "stamp").read_text() == stamp:
        return exe
    (obj / "v41_array_cfg.svh").write_text(svh)
    with BUILD_SLOTS:
        sh([*GATE, "verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
            "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "-Wno-MULTIDRIVEN", "--top-module", "tb_hdc_v41_array",
            f"-GUSERS={users}", f"-GSTALL={stall}", "-Mdir", str(obj), f"-I{obj}", f"-I{core.SVH.parent}",
            f"+define+HDC_SW={I.SU_LANES}",
            *map(str, core.RTL), str(LINK), str(ROUTER), str(CTRL), str(TB), str(HARNESS),
            "-CFLAGS", "-O1", "-j", "4"])
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
    body, hp, hmc, shared, fabric, users, fewer, stall, plen, ngen = spec
    lay, model, base = ctx["lay"], ctx["model"], ctx["base"]
    with ctx["isa_lock"]:
        t0 = time.time()
        gold = A.golden_runs(model, ngen, scratch / "gold.json", plen)
        plan = A.Plan(lay, A.split(model, body), hp, hmc, shared)
        progs = A.stage_programs(plan)
        recs, states = A.run_pipeline(plan, progs, base, gold)
        img = scratch / f"cfg_{name}"
        steps = A.write_config(img, plan, progs, gold, states)
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
    for active in (users, *fewer):
        t0 = time.time()
        log_path = scratch / f"out_{name}_u{active}.txt"
        if REUSE and log_path.exists() and RES.search(log_path.read_text()) and \
                (scratch / f"obj_{name}" / "stamp").read_text() == (scratch / f"stamp_{name}_u{active}").read_text():
            runs.append(parse(log_path.read_text(), active, steps, ngen))
            log(f"{name} u{active}: reused")
            continue
        with open(log_path, "w") as fh:          # streamed, so a long run can be watched
            rc = subprocess.run(["stdbuf", "-oL", str(exe), f"+DIR={img}", f"+ROMS={ctx['roms']}",
                                 f"+NUSERS={active}", f"+NPROMPT={plen}", f"+NGEN={ngen}", "+HB=1000000"],
                                stdout=fh, stderr=subprocess.STDOUT).returncode
        out = log_path.read_text()
        (scratch / f"stamp_{name}_u{active}").write_text((scratch / f"obj_{name}" / "stamp").read_text())
        if rc:
            raise RuntimeError(f"{name}: simulator exited {rc}\n{out[-3000:]}")
        r = parse(out, active, steps, ngen)
        log(f"{name} u{active}: {'PASS' if r['pass'] else 'FAIL'} {r['total_cycles']} cycles "
            f"({time.time() - t0:.0f} s)")
        runs.append(r)
    roles = [plan.role(k) for k in range(plan.n)]
    return {
        "name": name, "body_packages": body, "lm_head_packages": hp or 0, "lm_head_multicast": hmc,
        "shared_state": shared, "fabric": fabric, "stall_percent": stall,
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
    return [TB, HARNESS, LINK, ROUTER, CTRL, core.SVH, *core.RTL]


def sources():
    return [*rtl_sources(), *core.TOOLS, ROOT / "tools/hdc_program_v41_array.py", Path(__file__)]


def run(names, scratch: Path) -> dict:
    single = json.loads(core.OUT.read_text())
    e2e = single["end_to_end"]
    single_at = {st["position"]: st["cycles"] for st in e2e["per_step"]}
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
    base = P.Machine(lay, np.zeros(I.KV_WORDS * I.W_LANES, dtype=np.float32),
                     np.zeros(I.VM_ELEMS, dtype=np.float32))
    ctx = dict(lay=lay, model=model, base=base, roms=roms, isa_lock=threading.Lock())
    with ThreadPoolExecutor(len(names)) as pool:
        results = list(pool.map(lambda nm: run_config(nm, CONFIGS[nm], ctx, scratch, log), names))
    for c in results:
        for r in c["runs"]:
            # the single core's measured cycles at the same positions (its end-to-end run, empty state)
            ref = sum(single_at[p] for p in range(c["steps_per_user"])) / c["steps_per_user"]
            r["single_core_cycles_per_token_step"] = round(ref, 1)
            r["aggregate_speedup_vs_single_core"] = round(ref / r["cycles_per_token_step"], 3)
            busy = [p["busy"] for p in r["per_package"]]
            r["bottleneck_package"] = int(np.argmax(busy))
            r["bottleneck_busy_cycles_per_token_step"] = round(max(busy) / r["token_steps"], 1)
    return {
        "schema": "opentallas.hdc-v41-array-campaign.v1",
        "status": "pass" if all(c["pass"] for c in results) else "fail",
        "claim_boundary": "functional, cycle-accurate RTL simulation (Verilator) of a layer-range pipeline of "
                          "V4.1 decode cores; package control (ot_rom_pkg_ctrl_x) and the switch "
                          "(ot_rom_fabric_router) are RTL, the memories behavioural, the package link's PHY a "
                          "delay-line stand-in (60 cycles point-to-point, 30 per switch half-link); per-user "
                          "persistent state by base offsets in the behavioural memories; the Engram history "
                          "restore is testbench logic. Clock rate is not claimed.",
        "vehicle": "deepseek-v4.1-flash-reduced-v2 (40 layers, vocab 4040)",
        "single_core": {"cycles_per_position_end_to_end": single_at,
                        "single_step_cycles_pos7": single["single_step"]["cycles"]},
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
    args = parser.parse_args()
    global REUSE
    REUSE = args.reuse
    names = args.only or list(CONFIGS)
    with tempfile.TemporaryDirectory() as tmp:
        scratch = args.scratch or Path(tmp)
        scratch.mkdir(parents=True, exist_ok=True)
        result = run(names, scratch)
    args.output.write_text(json.dumps(result, indent=1) + "\n")
    for c in result["configurations"]:
        for r in c["runs"]:
            print("PASS" if r["pass"] else "FAIL", c["name"], r["users"], "users:", r["total_cycles"], "cycles,",
                  r["cycles_per_token_step"], "cycles/step, x", r["aggregate_speedup_vs_single_core"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
