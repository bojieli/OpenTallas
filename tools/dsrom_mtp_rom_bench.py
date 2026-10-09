#!/usr/bin/env python3
"""DS-ROM MTP control-plane benches (stream mtp-rom, 2026-10-08).

    python3 tools/dsrom_mtp_rom_bench.py run --out DIR [--only NAME,...] [--jobs N]
    python3 tools/dsrom_mtp_rom_bench.py one NAME --out DIR          # one case (closure-loop bench stage)

Cases (rtl/dsrom_sys/mtp/tb/*.sv, Icarus Verilog -g2012):
  s0_*    tb_mtp_rom_s0: the closed SOURCE WFC + dsfd_wfc_lnk + dsfd_wfc_tok + dsfd_wfc_vmx + dsfd_mtp_seq on the
          minimum vehicle (stage pipeline / head / drafter / VM / S0 core as delays with content checks).
          MODE 0 replays the reduced V4.1 golden's own greedy speculative decode (results/rtl/dshbm_dspark_rtl_20261003/
          traces/*.cfg.json: tools/hdc_golden_v41.generate_spec, drafter dspark / forced), MODE 1 a hash model with
          several users and random draft accuracy.
  stg_*   tb_mtp_rom_stg: the closed STAGE WFC (r11 stg parameters) + dsfd_wfc_lnk + dsfd_wfc_vmx: HIDDEN in -> VM
          writes across 3:4 -> core start / done -> outbound payload from the staging buffer; random link / VM stalls.
  tok_*   tb_mtp_rom_tok: the token store against a reference model (random draft blocks, epochs, prompt reads).
  fan_*   tb_mtp_rom_fan: the draft fan-out node, random routed messages down, whole-message merge up.
Negative controls (expect FAIL) build the same bench with one mutant define.
Writes DIR/<case>/{build,run}.log and DIR/summary.json (case, expect, verdict, PASS line).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M = "rtl/dsrom_sys/mtp"
TRACES = "results/rtl/dshbm_dspark_rtl_20261003/traces"
FIXTURES = ROOT / "rtl/test/mtp_rom_fixtures"
COMMON = [f"{M}/ot_dsrom_mtp_skid.sv", f"{M}/ot_dsrom_mtp_link_pair.sv", f"{M}/ot_dsrom_mtp_seq.sv", f"{M}/ot_dsrom_wfc_tok.sv", f"{M}/ot_dsrom_wfc_lnk.sv",
          f"{M}/ot_dsrom_wfc_vmx.sv", f"{M}/ot_dsrom_drf_fan.sv", f"{M}/dsfd_mtp_tops.sv", "rtl/common/ot_ratio_cdc_fifo.sv",
          "rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv",
          "physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"]


def trace_hex(cfg: Path, out: Path):
    d = json.loads(cfg.read_text())
    w = [d["plen"], d["ngen"], len(d["steps"])] + list(d["prompt"]) + list(d["tokens"])
    for s in d["steps"]:
        dr = list(s["drafts"]) + [0] * (5 - len(s["drafts"]))
        tg = list(s["targets"]) + [0] * (6 - len(s["targets"]))
        w += [s["anchor"], s["accepted"], len(s["drafts"])] + dr + tg
    out.write_text("".join(f"{x:08x}\n" for x in w))
    return dict(trace=str(cfg.relative_to(ROOT)), plen=d["plen"], ngen=d["ngen"], passes=len(d["steps"]),
                drafter=d["drafter"], accepted=[s["accepted"] for s in d["steps"]])


def trace_cfg(name: str) -> Path:
    """Keep golden bytes available when remote archives omit bulk results."""
    filename = f"{name}.cfg.json"
    original = ROOT / TRACES / filename
    cfg = original if original.is_file() else FIXTURES / filename
    binding = json.loads((FIXTURES / "manifest.json").read_text())["files"][filename]
    if hashlib.sha256(cfg.read_bytes()).hexdigest() != binding["sha256"]:
        raise ValueError(f"golden trace differs from pinned fixture: {cfg}")
    return cfg


def cases():
    c = {}
    s0 = dict(tb="tb_mtp_rom_s0")
    for tr in ("tr_dspark", "tr_forced", "tr_forced_w16"):
        c[f"s0_{tr}"] = dict(s0, trace=tr, params=dict(MODE=0, NUSR=2))
    c["s0_hash_u3"] = dict(s0, params=dict(MODE=1, NUSR=3, NGEN_H=48, RHO=70, SEED=3))
    c["s0_hash_u4_ar1"] = dict(s0, params=dict(MODE=1, NUSR=4, SEQ_MAXU=3, NGEN_H=30, RHO=85, SEED=11))
    c["s0_hash_u1_fast"] = dict(s0, params=dict(MODE=1, NUSR=1, NGEN_H=60, RHO=95, SEED=5, T_DRAFT=120, T_HEAD=8))
    neg = dict(s0, trace="tr_forced", params=dict(MODE=0, NUSR=1), expect="fail")
    for mut in ("OT_MTPSEQ_MUT_OFF1", "OT_MTPSEQ_MUT_NOEPOCH", "OT_MTPSEQ_MUT_NOHOLD", "OT_MTPSEQ_MUT_PREV",
                "OT_WFCLNK_MUT_DRAFT2WFC", "OT_WFCVMX_MUT_DONEEARLY"):
        c[f"s0_neg_{mut.split('MUT_')[1].lower()}"] = dict(neg, defines=[mut])
    stg = dict(tb="tb_mtp_rom_stg")
    c["stg_r1"] = dict(stg, params=dict(SEED=1, NJOB=60))
    c["stg_vmnat"] = dict(stg, params=dict(SEED=4, NJOB=40, VMNAT=1))
    c["stg_lag1"] = dict(stg, params=dict(SEED=6, NJOB=40, LAG=1))
    c["stg_r2_slowvm"] = dict(stg, params=dict(SEED=2, NJOB=60, VMSLOW=1))
    c["stg_neg_startearly"] = dict(stg, params=dict(SEED=2, NJOB=40, VMSLOW=1), defines=["OT_WFCVMX_MUT_STARTEARLY"],
                                   expect="fail")
    c["stg_neg_nocred"] = dict(stg, params=dict(SEED=2, NJOB=40, VMSLOW=1), defines=["OT_WFCLNK_MUT_NOCRED"], expect="fail")
    c["tok_r1"] = dict(tb="tb_mtp_rom_tok", params=dict(SEED=1))
    c["tok_neg_noepoch"] = dict(tb="tb_mtp_rom_tok", params=dict(SEED=1), defines=["OT_WFCTOK_MUT_NOEPOCH"], expect="fail")
    c["fan_r1"] = dict(tb="tb_mtp_rom_fan", params=dict(SEED=1))
    c["fan_neg_interleave"] = dict(tb="tb_mtp_rom_fan", params=dict(SEED=1), defines=["OT_DRFFAN_MUT_INTERLEAVE"],
                                   expect="fail")
    c["fan_neg_dest"] = dict(tb="tb_mtp_rom_fan", params=dict(SEED=1), defines=["OT_DRFFAN_MUT_DEST"], expect="fail")
    for k in c:
        c[k].setdefault("expect", "pass")
    return c


def run_case(name, spec, out: Path):
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    rec = dict(case=name, expect=spec["expect"], params=spec.get("params", {}), defines=spec.get("defines", []))
    if "trace" in spec:
        rec["trace"] = trace_hex(trace_cfg(spec["trace"]), d / "trace.hex")
    srcs = [str(ROOT / s) for s in COMMON] + [str(ROOT / M / "tb" / f"{spec['tb']}.sv")]
    cmd = ["iverilog", "-g2012", "-s", spec["tb"], "-o", str(d / "sim.vvp")]
    cmd += [f"-D{x}" for x in spec.get("defines", [])]
    cmd += [f"-P{spec['tb']}.{k}={v}" for k, v in spec.get("params", {}).items()]
    b = subprocess.run(cmd + srcs, capture_output=True, text=True)
    (d / "build.log").write_text(b.stdout + b.stderr)
    if b.returncode:
        rec.update(verdict="BUILD_ERROR")
        return rec
    r = subprocess.run(["vvp", "-n", str(d / "sim.vvp")], capture_output=True, text=True, cwd=d)
    (d / "run.log").write_text(r.stdout + r.stderr)
    tag = {"tb_mtp_rom_s0": "MTP_S0", "tb_mtp_rom_stg": "MTP_STG", "tb_mtp_rom_tok": "MTP_TOK",
           "tb_mtp_rom_fan": "MTP_FAN"}[spec["tb"]]
    m = re.search(rf"^{tag} (PASS|FAIL).*$", r.stdout, re.M)
    got = m.group(1).lower() if m else "nolog"
    rec.update(result=m.group(0) if m else r.stdout[-400:], got=got,
               verdict="OK" if got == spec["expect"] else "UNEXPECTED")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--only")
    p.add_argument("--jobs", type=int, default=8)
    p = sub.add_parser("one")
    p.add_argument("name")
    p.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    cs = cases()
    if a.cmd == "one":
        rec = run_case(a.name, cs[a.name], a.out)
        print(json.dumps(rec))
        print(f"MTP_BENCH {a.name} {rec.get('got', rec['verdict']).upper()}")
        return 0 if rec.get("got") == "pass" else 1
    names = a.only.split(",") if a.only else list(cs)
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        recs = list(ex.map(lambda n: run_case(n, cs[n], a.out), names))
    a.out.mkdir(parents=True, exist_ok=True)
    ok = all(r["verdict"] == "OK" for r in recs)
    (a.out / "summary.json").write_text(json.dumps(dict(all_ok=ok, cases=recs), indent=1) + "\n")
    for r in recs:
        print(f"{r['verdict']:10s} {r['case']:24s} expect={r['expect']:4s} {r.get('result', '')[:200]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
