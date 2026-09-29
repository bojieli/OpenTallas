#!/usr/bin/env python3
"""W11: ring key layout in the adopted V4.1 die at FULL ring capacity, two users interleaved.

ot_chip_v41x_die with IDX_RING = 1, IDX_RING_RSB = 64, IDX_RING_RTAIL = 32 (C = 65,568
key slots a region a stack, UBLK = 1,090 blocks a region) and IDX_RING_MU = 1 (the
index-key user base keyed from the step's 10-bit user id: user u's region r at block
u x IKH_SLICE / 128 + r x 1,090).  Bench rtl/test/tb_chip_v41x_die_ring_mu.sv runs four
reduced DeepSeek-V4.1 decode steps back to back with no reset:

  step 0  user 1  position 7   (token 3582; the adopted smoke's step)
  step 1  user 2  position 63  (--context 64: ratio-1 regions reach 64 keys, a migration)
  step 2  user 1  position 8   (the token step 0 produced; images of the prompt extended by it)
  step 3  user 2  position 64  (the token step 1 produced)

Each step is checked bit for bit (every logit, the whole vector memory, the whole KV
cache against the ISA model of that step; token against golden).  The index-key rings
are placed from the images only at a user's first step; before steps 2 and 3 the bench
compares the user's ring in HBM -- written by the die in the user's earlier step, after
the other user's step ran -- with the ring placement of the step's golden key image.
The vector memory and the host-mode KV slice are loaded from each step's images by the
bench (a context switch host mode does not implement).  Writes
results/rtl/w11_die_idx_ring_mu_gate.json (new; never overwritten).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_chip_v41x_die_smoke as ds  # noqa: E402
import w11_die_idx_ring_gate as rg  # noqa: E402

core = ds.core
OUT = ROOT / "results/rtl/w11_die_idx_ring_mu_gate.json"
TB = ROOT / "rtl/test/tb_chip_v41x_die_ring_mu.sv"
HARNESS = ROOT / "rtl/test/chip_v41x_die_ring_mu_harness.cpp"
IMG_TOOL = ROOT / "tools/w11_die_ring_mu_images.py"
PARAMS = {"RSB": 64, "RTAIL": 32, "KEY_USERS": 3, "IKH_SLICE": 4 * 1090 * 128, "K_MEM": 1 << 21}
USERS = (1, 2)
ROMS = ("prog.hex", "wrom.hex", "hrom.hex", "hbank.hex", "mbank.hex", "erom.hex", "crom.hex", "qlist.hex",
        "cfg.hex", "qrom.hex", "hbm_q.hex")
STEP = re.compile(r"HDC41 step=(\d+) user=(\d+) token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) "
                  r"fault=(\d+) logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+) key_carry_mismatch=(\d+)")
CARRY = re.compile(r"STEP(\d+) user=(\d+) key_carry checked=(\d+) mismatches=(\d+)")
VERDICT = re.compile(r"STEP(\d+) (PASS|FAIL)")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_args(img: Path) -> dict:
    return {k.lstrip("+"): int(v) for k, v in (x.split("=") for x in (img / "run.args").read_text().split())}


def build(obj: Path) -> Path:
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [ds.VERILATOR, "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-IMPORTSTAR", "-Wno-MODDUP", "-Wno-TIMESCALEMOD", "-Wno-VARHIDDEN", "-Wno-UNOPTFLAT",
           "--top-module", "tb_chip_v41x_die_ring_mu", *[f"-G{k}={v}" for k, v in PARAMS.items()],
           "-Mdir", str(obj), f"-I{core.SVH.parent}",
           str(core.VLT), *map(str, rg.src_list(True)), str(TB), str(HARNESS), "-CFLAGS", "-O1", "-j", "8"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        raise SystemExit(f"verilator build failed:\n{r.stdout[-3000:]}\n{r.stderr[-4000:]}")
    return obj / "Vtb_chip_v41x_die_ring_mu"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, default=Path("/tmp/claude-1000/w11s/rd/mu_gate"))
    ap.add_argument("--reuse-images", action="store_true")
    a = ap.parse_args()
    ds.setup("dpi")
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    srcs = sorted(set(rg.src_list(True)), key=str)
    pins = {ds.rel(p): sha(p) for p in srcs + [core.SVH, core.VLT, TB, HARNESS, Path(__file__), IMG_TOOL,
                                               ROOT / "tools/w11_die_idx_ring_gate.py",
                                               ROOT / "tools/rtl_chip_v41x_die_smoke.py",
                                               ROOT / "tools/rtl_hdc_v41x_decode_campaign.py",
                                               ROOT / "tools/hdc_program_v41.py", ROOT / "tools/hdc_images_v41x.py"]}
    img = {k: a.scratch / f"img_{k}" for k in ("a1", "b1", "a2", "b2")}
    with cf.ThreadPoolExecutor(4) as ex:
        exe = ex.submit(build, a.scratch / "obj")
        if not a.reuse_images:
            list(ex.map(lambda kv: core.images(img[kv[0]], *kv[1]),
                        (("a1", ("--hbm",)), ("b1", ("--hbm", "--context", "64")))))
            ext = {"a2": ([], run_args(img["a1"])["EXPECT"]), "b2": (["--context", "64"], run_args(img["b1"])["EXPECT"])}

            def second(k):
                extra, tok = ext[k]
                r = subprocess.run([sys.executable, str(IMG_TOOL), "--out", str(img[k]), *extra, "--append", str(tok)],
                                   capture_output=True, text=True, cwd=ROOT)
                if r.returncode:
                    raise SystemExit(f"{k} images failed:\n{r.stdout[-2000:]}\n{r.stderr[-3000:]}")
            list(ex.map(second, ("a2", "b2")))
        exe = exe.result()
    built = exe.stat().st_mtime
    used = rg.used_sources(a.scratch / "obj")
    stale = [ds.rel(p) for p in used if p.stat().st_mtime > built]
    assert not stale, f"sources newer than the executable: {stale}"
    pins.update({ds.rel(p): sha(p) for p in used})
    # one model: every step's images carry the same ROM / weight images (the bench loads them once)
    rom_sha = {k: {n: sha(img[k] / n) for n in ROMS} for k in img}
    roms_identical = all(rom_sha[k] == rom_sha["a1"] for k in img)
    order = [("a1", USERS[0]), ("b1", USERS[1]), ("a2", USERS[0]), ("b2", USERS[1])]
    plus = ["+NSTEPS=4", "+QRATE=32"]
    for i, (k, u) in enumerate(order):
        ra = run_args(img[k])
        plus += [f"+DIR{i}={img[k]}", f"+USER{i}={u}", f"+TOKEN{i}={ra['TOKEN']}", f"+POS{i}={ra['POS']}",
                 f"+EXPECT{i}={ra['EXPECT']}", f"+NPRIME{i}={ra['NPRIME']}", f"+PFIRST{i}={ra['PFIRST']}"]
    # the second steps continue the first: their input token is the first step's output
    chained = (run_args(img["a2"])["TOKEN"] == run_args(img["a1"])["EXPECT"] and
               run_args(img["b2"])["TOKEN"] == run_args(img["b1"])["EXPECT"] and
               run_args(img["a2"])["POS"] == run_args(img["a1"])["POS"] + 1 and
               run_args(img["b2"])["POS"] == run_args(img["b1"])["POS"] + 1)
    t0 = time.perf_counter()
    sim = subprocess.run([str(exe), *plus], capture_output=True, text=True, timeout=12 * 3600, cwd=ROOT)
    wall = time.perf_counter() - t0
    log = sim.stdout + sim.stderr
    assert {ds.rel(p): sha(p) for p in srcs} == {k: v for k, v in pins.items() if k in {ds.rel(p) for p in srcs}}, \
        "sources changed during the run"
    names = ("step", "user", "input_token", "position", "next_token", "isa_next_token", "cycles", "fault",
             "logit_mismatches", "vm_mismatches", "kv_mismatches", "key_carry_mismatches")
    steps = [dict(zip(names, map(int, m.groups()))) for m in STEP.finditer(log)]
    carry = {int(m.group(1)): {"user": int(m.group(2)), "keys_checked_cumulative": int(m.group(3)),
                               "mismatches_cumulative": int(m.group(4))} for m in CARRY.finditer(log)}
    verdict = {int(m.group(1)): m.group(2) for m in VERDICT.finditer(log)}
    for s in steps:
        s["image"] = order[s["step"]][0]
        s["verdict"] = verdict.get(s["step"])
        if s["step"] in carry:
            s["key_carry"] = carry[s["step"]]
    ok = (sim.returncode == 0 and len(steps) == 4 and all(s["verdict"] == "PASS" for s in steps) and
          log.rstrip().splitlines()[-2:].count("PASS") >= 1 and set(carry) == {2, 3} and
          all(c["keys_checked_cumulative"] > 0 for c in carry.values()) and roms_identical and chained and
          all(s["next_token"] == s["isa_next_token"] for s in steps))
    rec = {
        "schema": "opentallas.w11-die-idx-ring-mu-gate.v1",
        "status": "pass" if ok else "fail",
        "git_head": head,
        "simulator": ds.tool_version(ds.VERILATOR),
        "configuration": {"die": "ot_chip_v41x_die", "IDX_RING": 1, "IDX_RING_RSB": PARAMS["RSB"],
                          "IDX_RING_RTAIL": PARAMS["RTAIL"], "IDX_RING_MU": 1, "KEY_USERS": PARAMS["KEY_USERS"],
                          "IKH_SLICE": PARAMS["IKH_SLICE"], "K_MEM": PARAMS["K_MEM"], "X_IDX": 2,
                          "units": list(core.X_UNITS), "W_HBM": 1, "KV_HBM": 1, "fp": "dpi",
                          "ring_slots_per_region_per_stack": PARAMS["RSB"] * 1024 + PARAMS["RTAIL"],
                          "blocks_per_region": PARAMS["RSB"] * 17 + 1 + (PARAMS["RTAIL"] + 63) // 64,
                          "key_region_base_block": "user x IKH_SLICE / 128 + r x 1,090 (r < 4: the reduced "
                                                   "vehicle's four indexed VM key regions); at full shape (one "
                                                   "indexed layer a die) user x 1,090"},
        "users": list(USERS),
        "steps": steps,
        "images_chained": chained,
        "rom_images_identical_across_steps": roms_identical,
        "image_sha256": {k: {n: sha(img[k] / n) for n in sorted(os.listdir(img[k]))
                             if n.endswith((".hex", ".json", ".args"))} for k in img},
        "simulation_exit": sim.returncode,
        "simulation_wall_seconds": round(wall, 1),
        "simulation_log_sha256": hashlib.sha256(log.encode()).hexdigest(),
        "simulation_tail": log[-2500:],
        "claim_boundary": (
            "Reduced V4.1 decode steps through the die top with the ring key layout at full ring capacity "
            "(65,568-slot, 1,090-block regions) and the key user base keyed from the step's user id: two users' "
            "rings resident in HBM together; each user's steps write and scan only its own rings (a user's second "
            "step finds its ring as its first step left it and exact), bit-exact against the ISA model. The bench "
            "loads each step's vector memory and host-mode KV slice (host mode has one of each; the per-user KV "
            "slices of controller mode are not exercised). Reduced positions stay below 128 "
            "(hdc_isa_v41.POS_MAX), so ring slots past 1,024 and the ring wrap are shown by the writer/reader "
            "gate results/rtl/w11_idx_ring_naming.json, not by a die token."),
        "sources_sha256": pins,
    }
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; records are never overwritten")
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    for s in steps:
        print(s)
    print(rec["status"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
