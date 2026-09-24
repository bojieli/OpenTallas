#!/usr/bin/env python3
"""Token-level RTL simulation of a layer-per-package ROM array of decode cores.

rtl/test/tb_hdc_array.sv builds each package from one ot_hdc_core and one
ot_rom_pkg_ctrl (the synthesizable package controller; memories stay
behavioural): package n holds layer n (the first also the embedding), the
hidden state moves between packages as a HIDDEN message (one header and 8
data flits) and lm_head packages send a RESULT message {user, position, token,
logit} back to package 0, which reduces the parts of a step and feeds the token
back.  Every user starts from an EMPTY KV cache, runs the oracle's 16-token
prompt and generates 3 tokens; package 0 compares each generated id with the
torch oracle's.  Configurations (built and run in parallel):

point-to-point ot_rom_pkg_link fabric (package n -> n+1, last -> 0):
* 4 packages, 4 users: lm_head shares the last layer's package;
* 5 packages, 5 users: lm_head on a package of its own;
* 6 packages, 6 users: lm_head split by vocabulary over two packages, the
  last combining the two halves' argmax (strictly greater wins, so ties keep
  the lower row, as numpy's argmax does);
* 10 packages, 10 users: as 6, with every layer split into an attention
  package and an MLP package;
* 12 packages, 12 users: half-layer packages and lm_head split over four
  packages, the running argmax carried forward.

switched fabric (one NODES-port ot_rom_fabric_router, each package on an
uplink and a downlink of half the point-to-point channel delay), the 6- and
12-package arrays twice each, with every user and with one user (per-token
latency):
* chain: the lm_head parts chained as above;
* multicast: the last body package multicasts its hidden state to ALL lm_head
  parts at once through the router; each part applies the final norm and its
  rows in parallel and package 0 reduces their RESULTs.

stress: twice as many users as packages (messages queue at every package) with
every controller link port held off at random 30% of cycles -- 4 packages
point-to-point, and 6 packages switched with the multicast lm_head.

Aggregate throughput is token-steps per cycle across all users; the single-core
reference is results/rtl/hdc_decode_campaign.json.  Writes
results/rtl/hdc_array_campaign.json.
"""
import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_decode_campaign as core  # noqa: E402

OUT = ROOT / "results/rtl/hdc_array_campaign.json"
TB = ROOT / "rtl/test/tb_hdc_array.sv"
HARNESS = ROOT / "rtl/test/hdc_array_harness.cpp"
LINK = ROOT / "rtl/rom/ot_rom_pkg_link.sv"
ROUTER = ROOT / "rtl/rom/ot_rom_fabric_router.sv"
CTRL = ROOT / "rtl/rom/ot_rom_pkg_ctrl.sv"
# (packages, users, lm_head parts, half-layer packages, fabric, multicast, stall percent, extra runs with
#  fewer users)
CONFIGS = [(4, 4, 0, False, "p2p", False, 0, ()), (5, 5, 1, False, "p2p", False, 0, ()),
           (6, 6, 2, False, "p2p", False, 0, ()), (10, 10, 2, True, "p2p", False, 0, ()),
           (12, 12, 4, True, "p2p", False, 0, ()),
           (6, 6, 2, False, "switch", False, 0, (1,)), (6, 6, 2, False, "switch", True, 0, (1,)),
           (12, 12, 4, True, "switch", False, 0, (1,)), (12, 12, 4, True, "switch", True, 0, (1,)),
           # stress: twice as many users as packages, every controller port held off 30% of cycles
           (4, 8, 0, False, "p2p", False, 30, ()), (6, 12, 2, False, "switch", True, 30, ())]
STEPS_PER_USER = 16 + 3 - 1
RES = re.compile(r"HDC_ARRAY nodes=(\d+) users=(\d+) generated=(\d+) mismatches=(\d+) total_cycles=(\d+)")
BUSY = re.compile(r"NODE_BUSY node=(\d+) cycles=(\d+)")
GEN = re.compile(r"GEN user=(\d+) pos=(\d+) token=(\d+) cycle=(\d+)")
STALLS = re.compile(r"LINK_STALLS (\d+)")
DONE = re.compile(r"USERS_DONE (\d+)")


def sh(cmd, **kw) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r.stdout


def multicast_programs(img: Path, nodes: int, parts: int, half: bool) -> None:
    """Rewrite the lm_head part programs of a vocabulary-split array for
    multicast: every part receives the last body package's hidden state X
    (not the normalised state of a chained part 0), so each is built like part
    0 -- the sum of squares of X, the final norm, then its own rows."""
    import hdc_golden as G
    import hdc_isa as I
    import hdc_program as P
    lay = P.Layout(G.Model(P.GR))
    nb = 2 * lay.L if half else lay.L
    assert nodes == nb + parts and parts >= 2
    for k in range(parts):
        lk = copy.copy(lay)
        lk.mat = dict(lay.mat)
        lk.mat[("lm_head", parts, 0)] = lay.mat[("lm_head", parts, k)]
        prog = P.build_program(lk, [], embed=False, head=(0, parts))
        (img / f"prog_stage{nb + k:02d}.hex").write_text(P.hexwords((I.encode(**f) for f in prog), I.INSTR_BITS))


def run_config(scratch: Path, nodes: int, users: int, head_parts: int, half: bool, fabric: str,
               mcast: bool, stall: int, fewer: tuple) -> list:
    tag = f"{nodes}_{users}_{fabric}{'_mc' if mcast else ''}{f'_s{stall}' if stall else ''}"
    img, obj = scratch / f"img{tag}", scratch / f"obj{tag}"
    sh([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img), "--stages", str(nodes),
        "--head-parts", str(head_parts), *(["--half-layers"] if half else [])])
    if mcast:
        multicast_programs(img, nodes, head_parts, half)
    headsplit = head_parts if head_parts >= 2 else 0
    sh(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
        "-Wno-BLKSEQ", "--top-module", "tb_hdc_array", f"-GNODES={nodes}", f"-GUSERS={users}",
        f"-GHEADSPLIT={headsplit}", f"-GFABRIC={int(fabric == 'switch')}", f"-GMCAST={int(mcast)}",
        f"-GSTALL={stall}", "-Mdir", str(obj), f"-I{core.ISA_SVH.parent}", *map(str, core.HDC),
        *map(str, core.PIPES), str(LINK), str(ROUTER), str(CTRL), str(TB), str(HARNESS),
        "-CFLAGS", "-O1", "-j", "8"])
    results = []
    for active in (users, *fewer):
        out = sh([str(obj / "Vtb_hdc_array"), f"+DIR={img}", "+NGEN=3", f"+NUSERS={active}"])
        (scratch / f"out{tag}_u{active}.txt").write_text(out)
        m = RES.search(out)
        if not m:
            raise RuntimeError(f"{tag}: no result\n{out[-3000:]}")
        n, u, gen, bad, cycles = map(int, m.groups())
        busy = {int(a): int(b) for a, b in BUSY.findall(out)}
        gens = [dict(zip(("user", "position", "token", "cycle"), map(int, g))) for g in GEN.findall(out)]
        steps = u * STEPS_PER_USER
        results.append({
            "packages": n, "users": u, "lm_head_packages": max(head_parts, 1), "half_layer_packages": half,
            "fabric": fabric, "lm_head_multicast": mcast, "stall_percent": stall,
            "generated_tokens": gen, "mismatches": bad, "total_cycles": cycles,
            "token_steps": steps, "cycles_per_token_step": round(cycles / steps, 1),
            "cycles_per_user_step": round(cycles / STEPS_PER_USER, 1),
            "package_busy_cycles": [busy[i] for i in sorted(busy)],
            "package_busy_cycles_per_step": [round(busy[i] / steps, 1) for i in sorted(busy)],
            "users_completed": int(DONE.search(out).group(1)),
            "link_credit_stalls": int(STALLS.search(out).group(1)), "generated": gens,
            "pass": "PASS" in out and bad == 0 and gen == u * 3 and int(DONE.search(out).group(1)) == u})
    return results


def sources() -> list:
    return [TB, HARNESS, LINK, ROUTER, CTRL, core.ISA_SVH, *core.HDC, *core.PIPES, *core.TOOLS]


def run(configs=CONFIGS, keep=None) -> dict:
    single = json.loads(core.OUT.read_text())["single_step"]["cycles"]
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(len(configs)) as pool:
        scratch = keep or Path(tmp)
        results = [r for rs in pool.map(lambda c: run_config(scratch, *c), configs) for r in rs]
    for r in results:
        r["aggregate_speedup_vs_single_core"] = round(single / r["cycles_per_token_step"], 3)

    def find(n, users, fabric, mc):
        return next((r for r in results if r["packages"] == n and r["users"] == users and r["fabric"] == fabric
                     and r["lm_head_multicast"] == mc and not r["stall_percent"]), None)
    effects = []
    for r in results:
        if r["lm_head_multicast"] and not r["stall_percent"]:
            chain = find(r["packages"], r["users"], "switch", False)
            p2p = find(r["packages"], r["users"], "p2p", False)
            if chain:
                e = {"packages": r["packages"], "users": r["users"], "lm_head_packages": r["lm_head_packages"],
                     "switch_chain_cycles": chain["total_cycles"], "switch_multicast_cycles": r["total_cycles"],
                     "multicast_over_chain_cycle_ratio": round(r["total_cycles"] / chain["total_cycles"], 4)}
                if p2p:
                    e["p2p_chain_cycles"] = p2p["total_cycles"]
                    e["switch_chain_over_p2p_chain_cycle_ratio"] = round(chain["total_cycles"] / p2p["total_cycles"], 4)
                effects.append(e)
    return {
        "schema": "opentallas.hdc-array-campaign.v2",
        "status": "pass" if all(r["pass"] for r in results) else "fail",
        "claim_boundary": "functional, cycle-accurate RTL simulation of a layer-per-package array of decode "
                          "cores; package control (ot_rom_pkg_ctrl) and the switch (ot_rom_fabric_router) are "
                          "synthesizable RTL, the memories are behavioural and the package link's PHY is a "
                          "delay-line stand-in (ot_rom_pkg_link: 60 cycles point-to-point, 30 per switch "
                          "half-link). All users share the oracle's one prompt.",
        "single_core_cycles_per_token": single,
        "configurations": results,
        "multicast_effect": effects,
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--only", type=int, nargs="*", help="debug: run these CONFIGS indices only")
    parser.add_argument("--keep", type=Path, help="debug: build and run in this directory and keep it")
    args = parser.parse_args()
    configs = [CONFIGS[i] for i in args.only] if args.only else CONFIGS
    result = run(configs, args.keep)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for r in result["configurations"]:
        print(result["status"] if r["pass"] else "FAIL", r["packages"], "packages", r["users"], "users", r["fabric"],
              "multicast" if r["lm_head_multicast"] else "", f"stall {r['stall_percent']}" if r["stall_percent"] else "",
              ":", r["total_cycles"], "cycles,",
              r["cycles_per_token_step"], "cycles/step, x", r["aggregate_speedup_vs_single_core"],
              "busy/step", r["package_busy_cycles_per_step"])
    for e in result["multicast_effect"]:
        print("multicast effect", e)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
