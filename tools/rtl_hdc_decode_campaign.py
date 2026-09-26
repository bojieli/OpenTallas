#!/usr/bin/env python3
"""Token-level RTL simulation of the hardwired decode core (HDC).

Runs, from the repository root:

1. the special-function pipelines (exp, reciprocal, rsqrt) under Icarus on
   18,010 golden vectors with random bubbles, bit for bit;
   the core's multipliers under Verilator: the stage-rebalanced FP32 multiplier
   cycle-equivalent to the qualified pipe, and the exact BF16 multiplier equal
   to it wherever it does not refuse, on 20 million edge-biased operand pairs;
2. a Verilator lint of the core;
3. the core under Verilator on the reduced Qwen3 vehicle:
   * one decode step at position 15 on the golden-prefilled KV cache, checked
     bit for bit against the ISA-level model (every logit, the whole vector
     memory, the whole KV cache) and against the oracle's next token;
   * an end-to-end run from an EMPTY KV cache: the core consumes all 16 prompt
     tokens (writing its own KV rows) and then generates 3 tokens, compared
     with the torch oracle's generated ids.

Images come from tools/hdc_program.py; arithmetic is tools/hdc_golden.py.
Writes results/rtl/hdc_decode_campaign.json.

``--memory-macros`` runs the same core runs with the memories built from the
ASAP7 compiled macros (rtl/hdc/ot_hdc_memsys.sv, +define+OT_HDC_MEMSYS): the
ROM images are personalised into per-instance via maps with SECDED by
tools/mem_compiler/rom_gen.py, and the record goes to
results/rtl/hdc_decode_campaign_memory_macros.json.  It must reproduce the
default record's tokens, cycle counts and bit-exact checks.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402

OUT = ROOT / "results/rtl/hdc_decode_campaign.json"
OUT_MEMSYS = ROOT / "results/rtl/hdc_decode_campaign_memory_macros.json"
MACROS = ROOT / "physical/asap7_memory_macros"
MEMSYS_MACROS = ("ot_rom_4096x266_m8", "ot_rom_4096x72_m8", "ot_rom_8192x266_m8", "ot_sram_1r1w_1024x256_m2_r2c2")
MEMSYS_RTL = [ROOT / "rtl/hdc/ot_hdc_memsys.sv", *(ROOT / f"rtl/dft/{n}.sv" for n in (
                  "ot_rom_secded_dec", "ot_mbist_ctrl", "ot_mbist_bira", "ot_mbist_sram_collar", "ot_mbist_rom_collar")),
              *(MACROS / m / f"{m}.v" for m in MEMSYS_MACROS)]
WROM_ROWS = 6
VERILATOR5 = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
PIPES = [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/proto/ot_fp32_mul_rne_pipe.sv"]
ISA_SVH = ROOT / "rtl/hdc/ot_hdc_isa.svh"
HDC = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_sfu",
                                          "ot_hdc_reduce", "ot_hdc_matvec", "ot_hdc_stream", "ot_hdc_core")]
TB_SFU = ROOT / "rtl/test/tb_hdc_sfu.sv"
TB_MUL = ROOT / "rtl/test/tb_hdc_mul_equiv.sv"
HARNESS_MUL = ROOT / "rtl/test/hdc_mul_equiv_harness.cpp"
MUL_VECTORS = 20_000_000
TB_CORE = ROOT / "rtl/test/tb_hdc_core.sv"
HARNESS = ROOT / "rtl/test/hdc_core_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_isa.py", ROOT / "tools/hdc_program.py", Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ")
SINGLE = re.compile(r"HDC token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) fault=(\d+) "
                    r"logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
UTIL = re.compile(r"UTIL me_issue_cycles=(\d+) su_issue_cycles=(\d+) both_idle_cycles=(\d+)")
STEP = re.compile(r"STEP pos=(\d+) in=(\d+) out=(\d+) gold=(\d+) cycles=(\d+) fault=(\d+)")
MULTI = re.compile(r"HDC_MULTI steps=(\d+) generated=(\d+) mismatches=(\d+) total_cycles=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sfu_vectors(path: Path) -> int:
    rng = np.random.default_rng(1)
    F = np.float32
    ex = np.concatenate([rng.uniform(-100, 100, 3000), rng.uniform(-20, 5, 3000),
                         [0, -0.0, 88, -87, 88.5, -90, 1e-30, -1e-30, 0.3465735, -0.3465735]]).astype(F)
    rc = np.concatenate([np.exp(rng.uniform(-80, 80, 3000)), -np.exp(rng.uniform(-80, 80, 1000)),
                         rng.uniform(1, 40, 2000)]).astype(F)
    rs = np.concatenate([np.exp(rng.uniform(-80, 80, 3000)), rng.uniform(1e-6, 2, 3000)]).astype(F)
    lines = []
    for f, xs, fn in ((0, ex, G.exp), (1, rc, G.reciprocal), (2, rs, G.rsqrt)):
        for x, y in zip(xs, np.asarray(fn(xs), dtype=F)):
            lines.append(f"{f:x} {int(G.bits(x)):08x} {int(G.bits(y)):08x}\n")
    rng.shuffle(lines)
    path.write_text("".join(lines))
    return len(lines)


def personalise(img: Path, groups: int) -> dict:
    """Split one image directory's ROM contents into the wrapper's via maps (SECDED)."""
    sys.path.insert(0, str(ROOT / "tools/mem_compiler"))
    import rom_gen  # noqa: E402
    out = img / "rom"
    plan = (("prog", "prog.hex", 1024, "ot_rom_4096x266_m8", 256, 1),
            ("crom", "crom.hex", 64, "ot_rom_4096x72_m8", 64, 1),
            ("wrom", "wrom.hex", groups * 256, "ot_rom_8192x266_m8", 256, WROM_ROWS))
    recs = {}
    for prefix, name, width, macro, tile, rows in plan:
        spec = rom_gen.spec_from_sheet(MACROS / macro / f"{macro}.json")
        image = rom_gen.read_hex(img / name)
        tiles = rom_gen.tile_image(image, width, spec, tile, "secded")
        ncol = width // tile
        for r in range(rows):
            for c in range(ncol):
                tiles.setdefault((r, c), [])
        recs[prefix] = [rom_gen.personalise_instance(spec, ws, f"{prefix}_r{r}_c{c}", out)
                        for (r, c), ws in sorted(tiles.items())]
    order = ([f"prog_r0_c{c}" for c in range(4)] + ["crom_r0_c0"]
             + [f"wrom_r{r}_c{c}" for r in range(WROM_ROWS) for c in range(groups)])
    sigs = {i["instance"]: i["signature_crc32"] for v in recs.values() for i in v}
    (out / "signatures.hex").write_text("".join(f"{sigs[n]}\n" for n in order))
    return {"dir": out, "instances": sum(len(v) for v in recs.values()),
            "signatures": {i["instance"]: i["signature_crc32"] for v in recs.values() for i in v},
            "viamap_sha256": {i["instance"]: i["viamap_sha256"] for v in recs.values() for i in v}}


def run(memsys: bool = False) -> dict:
    extra_rtl = [str(p) for p in MEMSYS_RTL] if memsys else []
    extra_def = ["+define+OT_HDC_MEMSYS", "+define+OT_MEM_FAULTS"] if memsys else []
    # The memory-macro build needs Verilator 5: 4.038 mis-evaluates the SECDED
    # decoders' flags inside this design (spurious "corrected" on clean codewords
    # with the data itself unchanged); 5.050 counts zero.  The default build keeps
    # the verilator on PATH so its record is unchanged.
    vl = str(VERILATOR5) if memsys and VERILATOR5.is_file() else "verilator"
    pers: dict = {}
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        # 1. special functions
        n_vec = sfu_vectors(s / "sfu.txt")
        subprocess.run(["iverilog", "-g2012", "-o", str(s / "sfu.vvp"), str(TB_SFU),
                        *map(str, HDC[0:4]), *map(str, PIPES)], check=True)
        sfu = subprocess.run(["vvp", "-n", str(s / "sfu.vvp"), f"+VEC={s / 'sfu.txt'}"],
                             check=True, capture_output=True, text=True).stdout
        m = re.search(r"SFU vectors=(\d+) checked=(\d+) errors=(\d+)", sfu)
        sfu_rec = {"vectors": n_vec, "checked": int(m.group(2)), "errors": int(m.group(3)),
                   "pass": "PASS" in sfu and int(m.group(3)) == 0 and int(m.group(2)) == n_vec}
        # 1b. multipliers
        subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH",
                        "-Wno-UNUSED", "--top-module", "tb_hdc_mul_equiv", "-Mdir", str(s / "objm"),
                        str(HDC[1]), str(HDC[2]), *map(str, PIPES), str(TB_MUL), str(HARNESS_MUL),
                        "-CFLAGS", "-O1"], check=True, capture_output=True)
        mul = subprocess.run([str(s / "objm" / "Vtb_hdc_mul_equiv"), f"+N={MUL_VECTORS}"], check=True,
                             capture_output=True, text=True).stdout
        m1 = re.search(r"MULEQ checked=(\d+) mismatches=(\d+)", mul)
        m2 = re.search(r"BMULEQ checked=(\d+) faulted=(\d+) mismatches=(\d+)", mul)
        mul_rec = {"vectors": MUL_VECTORS, "fp32_rebalanced_checked": int(m1.group(1)),
                   "fp32_rebalanced_mismatches": int(m1.group(2)), "bf16_exact_checked": int(m2.group(1)),
                   "bf16_refused": int(m2.group(2)), "bf16_mismatches": int(m2.group(3)),
                   "pass": "PASS" in mul}
        # 2. lint
        lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_hdc_core",
                               f"-I{ISA_SVH.parent}", *map(str, HDC), *map(str, PIPES)], capture_output=True, text=True)
        # 3. core
        img = s / "img"
        subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img)], check=True,
                       capture_output=True)

        def rom_args(d: Path, groups: int) -> list:
            if not memsys:
                return []
            p = personalise(d, groups)
            pers[d.name] = {"instances": p["instances"], "signatures": p["signatures"],
                            "viamap_sha256": p["viamap_sha256"]}
            return [f"+OT_ROM_DIR={p['dir']}"]

        img_rom = rom_args(img, I.GROUPS)
        obj = s / "obj"
        subprocess.run([vl, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH",
                        "-Wno-UNUSED", "-Wno-BLKSEQ", "--top-module", "tb_hdc_core", "-Mdir", str(obj),
                        f"-I{ISA_SVH.parent}", *extra_def,
                        *map(str, HDC), *map(str, PIPES), *extra_rtl, str(TB_CORE), str(HARNESS), "-CFLAGS", "-O1"],
                       check=True, capture_output=True)
        exe = str(obj / "Vtb_hdc_core")
        args = (img / "run.args").read_text().split()
        one = subprocess.run([exe, f"+DIR={img}", *img_rom, *args], check=True, capture_output=True,
                             text=True).stdout
        multi = subprocess.run([exe, f"+DIR={img}", *img_rom, "+MULTI", "+NPROMPT=16", "+NGEN=3"], check=True,
                               capture_output=True, text=True).stdout
        bist_runs = {}
        if memsys:
            # memory self-test before the token: clean, then with a stuck KV cell and a missing weight-ROM via
            row0 = int((img / "rom" / "wrom_r0_c0.viamap.hex").read_text().split()[0], 16)
            via_col = (row0 & -row0).bit_length() - 1          # first programmed cell of row 0
            faults = {"clean": [], "kv_sa1_and_wrom_missing_via": [
                "+FAULT_KV_KIND=2", "+FAULT_KV_ROW=3", "+FAULT_KV_COL=10",
                "+FAULT_WROM_KIND=1", "+FAULT_WROM_ROW=0", f"+FAULT_WROM_COL={via_col}"]}
            for label, extra in faults.items():
                out = subprocess.run([exe, f"+DIR={img}", *img_rom, "+BIST", *extra, *args], check=True,
                                     capture_output=True, text=True).stdout
                mb = re.search(r"BIST pass=(\d+) sram_status=([01]+) rom_status=([01]+) bist_cycles=(\d+)", out)
                ms = SINGLE.search(out)
                me = re.search(r"ROM_ECC corrected=(\d+) uncorrectable=(\d+)", out)
                bist_runs[label] = {
                    "faults": extra, "bist_pass": int(mb.group(1)), "sram_status": mb.group(2),
                    "rom_status": mb.group(3), "bist_cycles": int(mb.group(4)),
                    "next_token": int(ms.group(3)), "cycles": int(ms.group(5)),
                    "logit_mismatches": int(ms.group(7)), "vector_memory_mismatches": int(ms.group(8)),
                    "kv_cache_mismatches": int(ms.group(9)),
                    "rom_ecc_corrected": int(me.group(1)), "rom_ecc_uncorrectable": int(me.group(2)),
                    "token_pass": "PASS" in out}
        expect = json.loads((img / "expect.json").read_text())
        prog_len = expect["prog_words"]
        # long context: attention over every group
        imgc = s / "imgc"
        subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(imgc), "--context", "60"],
                       check=True, capture_output=True)
        imgc_rom = rom_args(imgc, I.GROUPS)
        onec = subprocess.run([exe, f"+DIR={imgc}", *imgc_rom, *(imgc / "run.args").read_text().split()],
                              check=True, capture_output=True, text=True).stdout
        # scaling point: 8 lane groups
        img8, obj8 = s / "img8", s / "obj8"
        env8 = dict(os.environ, HDC_GROUPS="8")
        subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img8)], check=True,
                       capture_output=True, env=env8)
        img8_rom = rom_args(img8, 8)
        subprocess.run([vl, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH",
                        "-Wno-UNUSED", "-Wno-BLKSEQ", "--top-module", "tb_hdc_core", "-GG=8", "-Mdir", str(obj8),
                        f"-I{ISA_SVH.parent}", *extra_def,
                        *map(str, HDC), *map(str, PIPES), *extra_rtl, str(TB_CORE), str(HARNESS), "-CFLAGS", "-O1"],
                       check=True, capture_output=True)
        one8 = subprocess.run([str(obj8 / "Vtb_hdc_core"), f"+DIR={img8}", *img8_rom,
                               *(img8 / "run.args").read_text().split()],
                              check=True, capture_output=True, text=True).stdout
    m = SINGLE.search(one)
    token, pos, nxt, exp_tok, cycles, fault, bad_lg, bad_vm, bad_kv = map(int, m.groups())
    u = list(map(int, UTIL.search(one).groups()))
    single = {"token": token, "position": pos, "next_token": nxt, "oracle_next_token": exp_tok,
              "cycles": cycles, "fault": fault, "logit_mismatches": bad_lg,
              "vector_memory_mismatches": bad_vm, "kv_cache_mismatches": bad_kv,
              "me_issue_cycles": u[0], "su_issue_cycles": u[1], "both_units_idle_cycles": u[2],
              "pass": "PASS" in one and nxt == exp_tok and fault == 0 and bad_lg + bad_vm + bad_kv == 0}
    steps = [dict(zip(("position", "input", "output", "oracle", "cycles", "fault"), map(int, x.groups())))
             for x in STEP.finditer(multi)]
    mm = list(map(int, MULTI.search(multi).groups()))
    multi_rec = {"prompt_tokens": 16, "generated_tokens": [st["output"] for st in steps],
                 "oracle_generated_tokens": [st["oracle"] for st in steps], "steps": mm[0],
                 "mismatches": mm[2], "total_cycles": mm[3], "generation_steps": steps,
                 "pass": "PASS" in multi and mm[2] == 0}
    mc = SINGLE.search(onec)
    longc = {"position": int(mc.group(2)), "next_token": int(mc.group(3)), "isa_next_token": int(mc.group(4)),
             "cycles": int(mc.group(5)), "logit_mismatches": int(mc.group(7)),
             "vector_memory_mismatches": int(mc.group(8)), "kv_cache_mismatches": int(mc.group(9)),
             "pass": "PASS" in onec and mc.group(3) == mc.group(4) and int(mc.group(6)) == 0}
    m8 = SINGLE.search(one8)
    u8 = list(map(int, UTIL.search(one8).groups()))
    scale8 = {"groups": 8, "next_token": int(m8.group(3)), "cycles": int(m8.group(5)),
              "logit_mismatches": int(m8.group(7)), "vector_memory_mismatches": int(m8.group(8)),
              "kv_cache_mismatches": int(m8.group(9)), "me_issue_cycles": u8[0], "su_issue_cycles": u8[1],
              "both_units_idle_cycles": u8[2],
              "pass": "PASS" in one8 and int(m8.group(3)) == int(m8.group(4)) and int(m8.group(6)) == 0}
    ecc_seen = [tuple(map(int, m.groups())) for m in
                re.finditer(r"ROM_ECC corrected=(\d+) uncorrectable=(\d+)", one + onec + one8)]
    macs = 4 * (128 * 192 + 128 * 128 + 128 * 768 + 384 * 128) + 128 * 4096
    bist_ok = True
    if memsys:
        c, f = bist_runs["clean"], bist_runs["kv_sa1_and_wrom_missing_via"]
        bist_ok = (c["bist_pass"] == 1 and c["token_pass"] and f["token_pass"] and f["bist_pass"] == 0
                   and f["sram_status"][-2:] == "10" and f["rom_ecc_corrected"] > 0
                   and f["rom_status"][-2 * 6:-2 * 5] == "11" and f["cycles"] == c["cycles"])
    status = "pass" if bist_ok and sfu_rec["pass"] and mul_rec["pass"] and single["pass"] and scale8["pass"] and longc["pass"] and multi_rec["pass"] and lint.returncode == 0 \
        else "fail"
    record = {
        "schema": "opentallas.hdc-decode-campaign.v1",
        "status": status,
        "claim_boundary": "functional token-level RTL simulation (Verilator, cycle-accurate at the core "
                          "boundary) with behavioural synchronous-read memories; clock rate is not "
                          "claimed here -- see the ASAP7 physical records.",
        "vehicle": "qwen3-reduced-v1 (hidden 128, 4 layers, 8/2 heads, head_dim 16, ffn 384, vocab 4096)",
        "parameters": {"lanes_per_group": I.W_LANES, "groups": I.GROUPS, "interleave": I.INTERLEAVE,
                       "kv_positions": I.T_MAX,
                       "program_instructions": prog_len},
        "weight_macs_per_token": macs,
        "sfu": sfu_rec,
        "multipliers": mul_rec,
        "single_step": single,
        "end_to_end": multi_rec,
        "scaling_8_groups": scale8,
        "long_context": longc,
        "verilator_lint": {"returncode": lint.returncode, "flags": list(LINT_FLAGS),
                           "messages": lint.stderr.strip().splitlines()[:20]},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p)
                         for p in (ISA_SVH, *HDC, *PIPES, TB_SFU, TB_MUL, HARNESS_MUL, TB_CORE, HARNESS, *TOOLS,
                                   *(MEMSYS_RTL if memsys else []))},
    }
    if memsys:
        record["memory_macros"] = {
            "wrapper": "rtl/hdc/ot_hdc_memsys.sv (+define+OT_HDC_MEMSYS)",
            "macros": list(MEMSYS_MACROS),
            "macro_views_sha256": {m: sha(MACROS / m / f"{m}.v") for m in MEMSYS_MACROS},
            "verilator": subprocess.run([vl, "--version"], capture_output=True, text=True).stdout.strip(),
            "rom_ecc": "SECDED (266,256) on program and weight ROM tiles, (72,64) on the constant ROM",
            "rom_ecc_events_per_run": [{"corrected": c, "uncorrectable": u} for c, u in ecc_seen],
            "personalisation": pers,
            "vector_memory": "standard-cell register file inside the wrapper (7 reads / 4 writes per cycle measured)",
            "bist": bist_runs,
            "bist_status_encoding": "2 bits per macro, macro 0 in the LSBs: 01 pass, 10 repaired, 11 fail; "
                                    "SRAM order q*2+t (KV replica q, column tile t); ROM order prog c0..c3, crom, "
                                    "wrom r0c0.. (row-major)",
        }
        record["claim_boundary"] = (record["claim_boundary"] + "; memories are the behavioural models of the "
                                    "ASAP7 compiled macros (physical array, via-map ROM content, SECDED read path)")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--memory-macros", action="store_true",
                        help="build the memories from the ASAP7 compiled macros (rtl/hdc/ot_hdc_memsys.sv)")
    args = parser.parse_args()
    if args.output is None:
        args.output = OUT_MEMSYS if args.memory_macros else OUT
    result = run(args.memory_macros)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    s = result["single_step"]
    print(result["status"], "next token", s["next_token"], "cycles", s["cycles"],
          "generated", result["end_to_end"]["generated_tokens"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
