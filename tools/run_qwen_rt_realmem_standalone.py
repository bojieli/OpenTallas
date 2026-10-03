#!/usr/bin/env python3
"""Standalone Verilator benches of the REAL_MEM memory services, each against expected data.

  kv     rtl/test/qwen_rom_runtime/realmem/tb_qwen_rt_kv_service.{sv,cpp}: the KV fill/write service
         + HBM timing model with write-done; every slice byte (1,536 tiles x 128 x 64) and the
         token's written-back K/V codes exact at P = 0, 255, 256, 2,047, 4,095, 8,191; two negative
         cases must fault.  Run at fill lookahead LKA = 8, 64 and the adopted 512.
  rom    rtl/test/qwen_rom_runtime/realmem/tb_qwen_rt_rom_services.{sv,cpp}: a scale-ROM port bank of
         ASAP7 ot_rom_4096x266_m8 macro models read through the macros' via masks, and the INT8
         embedding ROM.
  hbm    rtl/test/qwen_rom_runtime/realmem/tb_hbm_refresh_stream.{sv,cpp}: the HBM model's sustained
         read rate for an in-order stream before and after the first all-bank refreshes.
Writes one JSON record (source-pinned).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RM = ROOT / "rtl/test/qwen_rom_runtime/realmem"
MAC = ROOT / "physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v"
KV = [ROOT / "rtl/hdc/kv/ot_qwen_rt_kv_fill_service.sv", ROOT / "rtl/hdc/kv/ot_qwen_hbm_model_ack.sv",
      RM / "tb_qwen_rt_kv_service.sv", RM / "tb_qwen_rt_kv_service.cpp"]
ROM = [MAC, ROOT / "rtl/hdc/ot_qwen_rt_rom_bank.sv", ROOT / "rtl/hdc/ot_qwen_rt_embed_rom.sv",
       RM / "tb_qwen_rt_rom_services.sv", RM / "tb_qwen_rt_rom_services.cpp"]
HBM = [ROOT / "rtl/hdc/kv/ot_qwen_hbm_model_ack.sv", RM / "tb_hbm_refresh_stream.sv", RM / "tb_hbm_refresh_stream.cpp"]
FLAGS = ["--cc", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--result", type=Path, required=True)
    ap.add_argument("--verilator", default=os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    srcs = sorted(set(KV + ROM + HBM + [Path(__file__)]))
    pins = {str(p.relative_to(ROOT)): sha(p) for p in srcs}
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([a.verilator, "-V"], text=True)).group(1)
    rec = {"schema": "opentallas.qwen-rom-realmem-standalone.v1", "source_sha256": pins, "benches": {}}

    def sh(cmd, log):
        p = subprocess.run(list(map(str, cmd)), cwd=work, capture_output=True, text=True)
        (work / log).write_text(p.stdout + p.stderr)
        return p

    # KV service at three lookahead depths
    for lka in (8, 64, 512):
        o = work / f"kv_lka{lka}"
        t0 = time.monotonic()
        p = sh([a.verilator, *FLAGS, "--exe", "--build", f"-GLKA={lka}", "--top-module", "tb_qwen_rt_kv_service", "-Mdir", o,
                *KV, "-CFLAGS", "-O1", "-j", a.jobs], f"kv_lka{lka}_build.log")
        if p.returncode:
            raise SystemExit(f"kv build failed: {p.stdout[-2000:]}{p.stderr[-2000:]}")
        r = sh([o / "Vtb_qwen_rt_kv_service"], f"kv_lka{lka}.log")
        js = json.loads(r.stdout.strip().splitlines()[-1])
        js["stats"] = [ln for ln in r.stdout.splitlines() if ln.startswith("STATS")]
        js["seconds"] = round(time.monotonic() - t0, 1)
        rec["benches"][f"kv_service_lka{lka}"] = js
    # ROM services: preload helpers are generated from the verilated root header
    o = work / "rom"
    (work / "pub.vlt").write_text('`verilator_config\npublic_flat_rw -module "ot_rom_4096x266_m8" -var "arr"\n')
    p = sh([a.verilator, *FLAGS, "--top-module", "tb_qwen_rt_rom_services", "-Mdir", o, work / "pub.vlt", *ROM[:4]], "rom_verilate.log")
    if p.returncode:
        raise SystemExit("rom verilate failed")
    h = (o / "Vtb_qwen_rt_rom_services___024root.h").read_text()
    bank = {int(m.group(1)): m.group(0) for m in re.finditer(r'\w*u_bank__DOT__g_m__BRA__(\d+)__KET____DOT__u_rom__DOT__arr\b', h)}
    if len(bank) != 13:
        raise SystemExit(f"scale bank macros: {len(bank)}")
    (o / "rom_access_bench.hpp").write_text(
        "static uint32_t* bank_arr(int m) { switch (m) {\n" +
        "".join(f"case {k}: return reinterpret_cast<uint32_t*>(&R->{n}[0][0]);\n" for k, n in sorted(bank.items())) +
        "} return nullptr; }\n")
    sh(["make", "-C", o, "-f", "Vtb_qwen_rt_rom_services.mk", f"-j{a.jobs}", "Vtb_qwen_rt_rom_services__ALL.a"], "rom_make.log")
    p = sh(["g++", "-O1", "-std=c++17", f"-I{o}", f"-I{vroot}/include", f"-I{vroot}/include/vltstd", ROM[4],
            o / "Vtb_qwen_rt_rom_services__ALL.a", f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
            "-pthread", "-o", work / "rombench"], "rom_link.log")
    if p.returncode:
        raise SystemExit("rom link failed")
    r = sh([work / "rombench"], "rom.log")
    rec["benches"]["rom_services"] = {"status": "pass" if "ROM_SERVICES_STANDALONE PASS" in r.stdout else "fail",
                                      "lines": r.stdout.strip().splitlines()}
    # HBM model sustained rate with and without refresh
    hb = {}
    for idle in (10, 5000):
        o = work / f"hbm_idle{idle}"
        sh([a.verilator, *FLAGS, "--exe", "--build", f"-GIDLE={idle}", "--top-module", "tb_hbm_refresh_stream", "-Mdir", o, *HBM, "-j", a.jobs],
           f"hbm{idle}_build.log")
        r = sh([o / "Vtb_hbm_refresh_stream"], f"hbm{idle}.log")
        m = re.search(r"phase1_cycles=(\d+) phase2_cycles=(\d+)", r.stdout)
        c1, c2 = int(m.group(1)), int(m.group(2))
        hb[f"idle{idle}"] = {"sectors": 16384, "phase1_cycles": c1, "phase2_cycles": c2,
                             "phase1_sectors_per_cycle": round(16384 / c1, 2), "phase2_sectors_per_cycle": round(16384 / c2, 2)}
    rec["benches"]["hbm_in_order_stream"] = hb
    ok = (all(rec["benches"][f"kv_service_lka{k}"]["status"] == "pass" for k in (8, 64, 512))
          and rec["benches"]["rom_services"]["status"] == "pass")
    rec["status"] = "pass" if ok else "fail"
    rec["source_stable"] = pins == {str(p.relative_to(ROOT)): sha(p) for p in srcs}
    a.result.parent.mkdir(parents=True, exist_ok=True)
    a.result.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": rec["status"], "hbm": hb}, indent=1))


if __name__ == "__main__":
    main()
