#!/usr/bin/env python3
"""Memory-BIST campaign on the DS-V4.1 ROM S81 element bench (rtl/test/tb_v41_elem_mbist.sv).

Personalises the four ot_rom_4096x274_m8 macros of the q pair element (ref r_*, dut d_*: the same words), computes
each macro's expected CRC-32 signature (tools/mem_compiler/ecc.py, the value rom_gen.py personalise writes beside
the via map), builds the bench under Verilator with the fault-capable behavioural macro models, and runs:

  func_<seed>  functional exactness vs the pinned element before, during and after a clean BIST (must PASS);
  fault cases  injected ROM / KV-SRAM defects, BIST only, statuses checked against the expectation.

Run on a compute host (ot-epyc1tb via admit.sh): python3 tools/dft/elem_mbist_campaign.py --work W --output R
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))
import ecc  # noqa: E402
import rom_gen  # noqa: E402

TB = "rtl/test/tb_v41_elem_mbist.sv"
RTL = ["rtl/dft/v41/ot_v41_elem_mbist_top.sv", "rtl/dft/v41/ot_v41_rom_elem_qp_mb_w10.sv",
       "rtl/v41rom/ot_v41_rom_elem_q_qp_w10.sv", "rtl/v41rom/ot_v41_rom_elem_qp_w10.sv",
       "rtl/v41rom/ot_v41_rom_elem_w10.sv"]
RTL += [f"rtl/v41rom/{n}.sv" for n in ("ot_v41_bterm", "ot_v41_chain", "ot_v41_segtree", "ot_v41_bf16_lanes",
        "ot_v41_fadd", "ot_v41_bmul2", "ot_v41_bterm2_w10", "ot_v41_chain2", "ot_v41_segtree2", "ot_v41_bf16_lanes2",
        "ot_v41_bterm3_w10", "ot_v41_segtree3")]
RTL += [f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_delay", "ot_hdc_cg")]
RTL += ["rtl/common/ot_prefix.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv"]
RTL += [f"rtl/dft/{n}.sv" for n in ("ot_mbist_ctrl", "ot_mbist_bira", "ot_mbist_rom_collar", "ot_mbist_rom_collar_par", "ot_mbist_sram_collar")]
MODELS = [f"physical/asap7_memory_macros/{n}/{n}.v" for n in
          ("ot_rom_4096x274_m8", "ot_rom_8192x274_m8", "ot_sram_1r1w_256x256_m2_r2c2")]
ROM_SHEET = ROOT / "physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.json"
KIND = {"SA0": 1, "SA1": 2, "TF_UP": 3, "TF_DOWN": 4, "CFIN": 5, "CFID": 6, "CFST": 7,
        "AF_NONE": 8, "AF_ALIAS": 9, "AF_MULTI": 10, "ROW_SA": 11, "COL_SA": 12}
INST = {"r": ["r_0", "r_1", "rb_0", "rb_1"], "d": ["d_0", "d_1", "db_0", "db_1"]}
DONE = re.compile(r"BIST done pass=(\d) sram=([01]{4}) rom=([01]{8}) cycles=(\d+) sig=([0-9a-f]+)")
PASS = re.compile(r"^PASS .*$", re.M)
ST = {"00": "not_run", "01": "pass", "10": "repaired", "11": "fail"}


def word(a: int, m: int) -> int:
    """The q bench's address-hashed word (tb_dsrom_qpipe_exact fixture), salted per macro."""
    M = (1 << 32) - 1
    h = (a * 0x9E3779B1 + 0x7F4A7C15 + 0x1000193 * m) & M
    w = 0
    for i in range(9):
        w |= h << (32 * i)
        h = (h * 0x85EBCA6B + 0xC2B2AE35 + i) & M
    w &= (1 << 256) - 1
    w |= (h & 0x3FFFF) << 256
    def put(lo, v):
        nonlocal w
        w = (w & ~(0xFF << lo)) | ((v & 0xFF) << lo)
    put(128, 120 + (a & 7)); put(264, 124 + ((a >> 1) & 7)); put(256, 122 + ((a >> 2) & 7))
    return w


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def f(m, kind, r=0, c=0, ar=0, ac=0, v=0):
    return (m, KIND[kind], r, c, ar, ac, v)


def scenarios(rows: list[list[int]]) -> list[dict]:
    def bit(m, r, c):
        return (rows[m][r] >> c) & 1
    out = []
    # ROM defects, one per macro (index m = 2*mb + k)
    c1 = next(c for c in range(2192) if bit(0, 3, c) == 1)
    c0 = next(c for c in range(2192) if bit(1, 4, c) == 0)
    rom = [("rom_via_missing", 0, [f(0, "SA0", 3, c1)]),
           ("rom_via_extra", 1, [f(1, "SA1", 4, c0)]),
           ("rom_wordline_open", 2, [f(2, "ROW_SA", 7, v=0)]),
           ("rom_bitline_short", 3, [f(3, "COL_SA", 0, next(c for c in range(17, 2192)
                                                             if any(bit(3, r, c) == 0 for r in range(512))), v=1)]),
           ("rom_decoder_no_row", 0, [f(0, "AF_NONE", 100)]),
           ("rom_decoder_alias", 2, [f(2, "AF_ALIAS", 200, 0, 201)]),
           ("rom_decoder_multi", 3, [f(3, "AF_MULTI", 300, 0, 301)])]
    for name, m, fl in rom:
        exp_rom = ["pass"] * 4
        exp_rom[m] = "fail"
        out.append({"name": name, "faults": fl, "expect": {"pass": 0, "sram": ["pass", "pass"], "rom": exp_rom}})
    # KV SRAM (bank index b -> macro 4 + b); physical col = bit * 2 + s, 128 rows + 2 spare rows, 2 spare cols
    def col(b, s):
        return b * 2 + s
    v = col(77, 1)
    single = [("SA0", [("SA0", 5, col(3, 1))]), ("SA1", [("SA1", 127, col(255, 1))]),
              ("TF_UP", [("TF_UP", 17, col(11, 0))]), ("TF_DOWN", [("TF_DOWN", 18, col(12, 1))]),
              ("CFIN", [("CFIN", 10, v, 9, v, 1)]), ("CFID", [("CFID", 12, v, 3, v, 0b01)]),
              ("CFST", [("CFST", 14, v, 20, col(9, 1), 0b00)]),
              ("AF_NONE", [("AF_NONE", 7)]), ("AF_ALIAS", [("AF_ALIAS", 12, 0, 13)]),
              ("AF_MULTI", [("AF_MULTI", 30, 0, 31)]),
              ("ROW_SA0", [("ROW_SA", 40, 0, 0, 0, 0)]), ("COL_SA1", [("COL_SA", 0, col(200, 1), 0, 0, 1)])]
    for i, (name, fl) in enumerate(single):
        b = i % 2
        faults = [f(4 + b, k, *rest) for k, *rest in fl]
        sram = ["pass", "pass"]
        sram[b] = "repaired"
        out.append({"name": f"kv{b}_{name}", "faults": faults,
                    "expect": {"pass": 1, "sram": sram, "rom": ["pass"] * 4}})
    out.append({"name": "kv0_two_rows_two_cols", "faults": [f(4, "ROW_SA", 3, v=1), f(4, "ROW_SA", 90, v=0),
                                                            f(4, "COL_SA", 0, col(10, 0), v=1),
                                                            f(4, "COL_SA", 0, col(250, 1), v=0)],
                "expect": {"pass": 1, "sram": ["repaired", "pass"], "rom": ["pass"] * 4}})
    out.append({"name": "kv1_unrepairable_three_rows", "faults": [f(5, "ROW_SA", 3, v=1), f(5, "ROW_SA", 50, v=0),
                                                                  f(5, "ROW_SA", 100, v=1)],
                "expect": {"pass": 0, "sram": ["pass", "fail"], "rom": ["pass"] * 4}})
    out.append({"name": "mixed_rom_and_kv", "faults": [f(1, "SA0", 3, next(c for c in range(2192) if bit(1, 3, c))),
                                                      f(4, "SA1", 60, col(100, 0))],
                "expect": {"pass": 0, "sram": ["repaired", "pass"], "rom": ["pass", "fail", "pass", "pass"]}})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--bira-pop-pipe", action="store_true", help="Select default-off BIRA search pipeline")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--verilator", default=str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    spec = rom_gen.spec_from_sheet(ROM_SHEET)
    romdir = a.work / "rom"
    sigs, rows, recs = [], [], []
    for m in range(4):
        words = [word(x, m) for x in range(spec.words)]
        for p in ("r", "d"):
            rec = rom_gen.personalise_instance(spec, words, INST[p][m], romdir)
            if p == "d":
                recs.append(rec)
        s = ecc.signature_fast(words, spec.bits)
        assert f"{s:08x}" == recs[-1]["signature_crc32"]
        sigs.append(s)
        rows.append(rom_gen.via_map(spec, words))
    die_sig = rom_gen.die_signature(recs)

    if a.bira_pop_pipe:
        selected = a.work / "ot_mbist_ctrl.sv"
        text = (ROOT / "rtl/dft/ot_mbist_ctrl_bira_pipe.sv").read_text()
        selected.write_text(text.replace("module ot_mbist_ctrl_bira_pipe #(", "module ot_mbist_ctrl #(", 1)
                           .replace("parameter integer POP_PIPE = 0", "parameter integer POP_PIPE = 1", 1))
        RTL[RTL.index("rtl/dft/ot_mbist_ctrl.sv")] = str(selected)
        RTL[RTL.index("rtl/dft/ot_mbist_bira.sv")] = "rtl/dft/ot_mbist_bira_pipe.sv"

    build = a.work / "obj"
    cmd = [a.verilator, "--binary", "--timing", "-j", "16", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-PINMISSING",
           "-Wno-MULTIDRIVEN", "-Wno-CASEINCOMPLETE", "--top-module", "tb_v41_elem_mbist", "+define+OT_MEM_FAULTS",
           "-Mdir", str(build), "-o", "tb", TB, *RTL, *MODELS]
    tb_ = time.time()
    b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (a.work / "build.log").write_text(b.stdout + b.stderr)
    if b.returncode != 0:
        print(b.stderr[-3000:])
        raise SystemExit("build failed")
    build_s = time.time() - tb_
    exe = build / "tb"
    sigargs = [f"+ROMSIG{m}={sigs[m]:08x}" for m in range(4)] + [f"+OT_ROM_DIR={romdir}"]

    def run(name, extra):
        log = a.work / f"{name}.log"
        t = time.time()
        p = subprocess.run([str(exe), *sigargs, *extra], cwd=a.work, capture_output=True, text=True)
        log.write_text(p.stdout + p.stderr)
        return name, p.returncode, p.stdout + p.stderr, time.time() - t

    cases = scenarios(rows)
    jobs = [(f"func_seed{s}", [f"+seed={s}"]) for s in range(1, a.seeds + 1)]
    for c in cases:
        ff = a.work / f"{c['name']}.faults"
        ff.write_text("".join(" ".join(map(str, x)) + "\n" for x in c["faults"]))
        jobs.append((c["name"], [f"+FAULTS={ff}"]))
    results = {}
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for name, rc, out, secs in ex.map(lambda j: run(*j), jobs):
            results[name] = (rc, out, secs)

    func = []
    for s in range(1, a.seeds + 1):
        rc, out, secs = results[f"func_seed{s}"]
        m = DONE.search(out)
        pm = PASS.search(out)
        func.append({"seed": s, "rc": rc, "pass": rc == 0 and bool(pm), "line": pm.group(0) if pm else out.strip()[-600:],
                     "bist": m.groups() if m else None, "seconds": round(secs, 1)})
    fcases = []
    for c in cases:
        rc, out, secs = results[c["name"]]
        m = DONE.search(out)
        got = None
        ok = False
        if m:
            sram = [ST[m.group(2)[2 * i:2 * i + 2]] for i in (1, 0)]   # status[2m+1:2m], MSB first in print
            rom = [ST[m.group(3)[2 * i:2 * i + 2]] for i in (3, 2, 1, 0)]
            got = {"pass": int(m.group(1)), "sram": sram, "rom": rom, "cycles": int(m.group(4)),
                   "sig": m.group(5)}
            ok = got["pass"] == c["expect"]["pass"] and sram == c["expect"]["sram"] and rom == c["expect"]["rom"]
        fcases.append({"name": c["name"], "faults": c["faults"], "expect": c["expect"], "got": got, "ok": ok,
                       "rc": rc})
    clean = func[0]["bist"]
    rec = {
        "schema": "opentallas.dft.elem_mbist.v1",
        "date": time.strftime("%Y-%m-%d"),
        "vehicle": "ot_v41_elem_mbist_top: S81 q pair element (4 x ot_rom_4096x274_m8 behind ROM collars, generated "
                   "successor ot_v41_rom_elem_qp_mb_w10) + 2 KV staging banks (ot_sram_1r1w_256x256_m2_r2c2) behind "
                   "SRAM collars, one shared ot_mbist_ctrl",
        "reference": "pinned ot_v41_rom_elem_q_qp_w10 at the routed S81 parameters",
        "simulator": a.verilator, "build_seconds": round(build_s, 1),
        "rom": {"macros": INST["d"], "expected_signatures": [f"{s:08x}" for s in sigs], "die_signature": die_sig,
                "personalisation": recs},
        "functional": func,
        "functional_pass": all(x["pass"] for x in func),
        "clean_bist": {"pass": clean[0] if clean else None, "sram_status": clean[1] if clean else None,
                       "rom_status": clean[2] if clean else None,
                       "cycles": int(clean[3]) if clean else None,
                       "us_at_1p2GHz": round(int(clean[3]) / 1.2e3, 3) if clean else None,
                       "signatures": clean[4] if clean else None},
        "fault_cases": fcases,
        "fault_cases_ok": sum(x["ok"] for x in fcases),
        "fault_cases_total": len(fcases),
        "sources": {p: sha(ROOT / p) for p in [TB, *RTL, *MODELS, "tools/dft/elem_mbist_campaign.py",
                                               "tools/dft/gen_elem_mbist.py"]},
        "seconds": round(time.time() - t0, 1),
    }
    rec["verdict"] = "PASS" if rec["functional_pass"] and rec["fault_cases_ok"] == rec["fault_cases_total"] else "FAIL"
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("verdict", "functional_pass", "fault_cases_ok", "fault_cases_total",
                                          "clean_bist")}))
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
