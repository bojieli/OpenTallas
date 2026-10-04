#!/usr/bin/env python3
"""Configuration write/read-back test of every V4.1 ROM element copy (rtl/test/tb_v41_rom_elem_cfg_rw.sv).

Every entry cfg_a = 0 .. 31 is written (ascending, descending, the image writers' order 2NSEG+1+s before s, and 400
random writes) and every decoded configuration register is read back against the documented map.  Each element copy
that decodes the configuration is built on its own (Verilator 5.050, S81 parameters NSEG 8, NB 2, MTP, EARLY, FAST,
PP); the QPIPE copies also check the delayed output-table shadow.  Control: the pre-fix ot_v41_rom_elem_w10 (the
low-bit decode of entry 2NSEG+1+s, read from git at --prefix-rev) must FAIL.

    python3 tools/dsrom_elem_cfg_rw.py run --work DIR [--jobs 8] [--prefix-rev f23c56908]
    python3 tools/dsrom_elem_cfg_rw.py record --work DIR --out results/rtl/dsrom_correctness_20261004/elem_cfg_rw.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
TB = "rtl/test/tb_v41_rom_elem_cfg_rw.sv"
PRIM = [f"rtl/v41rom/{n}.sv" for n in ("ot_v41_bterm", "ot_v41_chain", "ot_v41_segtree", "ot_v41_bf16_lanes",
                                         "ot_v41_fadd", "ot_v41_bmul2", "ot_v41_bterm2_w10", "ot_v41_chain2",
                                         "ot_v41_segtree2", "ot_v41_bf16_lanes2", "ot_v41_bterm3_w10",
                                         "ot_v41_segtree3", "ot_v41_chain3", "ot_v41_kreg")]
PRIM += [f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_delay", "ot_hdc_cg")]
PRIM += ["rtl/common/ot_prefix.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv"]
RNE = [f"rtl/v41rom/{n}.sv" for n in ("ot_v41_bmul2_rne_prepare", "ot_v41_bmul_subnormal_rne_prepare")]
# the RNE copy's BF16 lanes (same module name as ot_v41_bf16_lanes2, with GRADUAL_RNE) replace the plain ones
RNE_SWAP = {"rtl/v41rom/ot_v41_bf16_lanes2.sv": "rtl/v41rom/ot_v41_bf16_lanes2_rne_prepare.sv"}
W10 = "rtl/v41rom/ot_v41_rom_elem_w10.sv"
# name -> (module, element sources, extra -G parameters, defines)
VARIANTS = {
    "w10":            ("ot_v41_rom_elem_w10", [W10], [], []),
    "w10_cg0":        ("ot_v41_rom_elem_w10", [W10], ["-GCG=0"], []),
    "nv_w10":         ("ot_v41_rom_elem_nv_w10", ["rtl/v41rom/ot_v41_rom_elem_nv_w10.sv"], [], []),
    "qt_w10":         ("ot_v41_rom_elem_qt_w10", [W10, "rtl/v41rom/ot_v41_rom_elem_qt_w10.sv"],
                       ["-GQTIMING_FIX=1"], []),
    "qp_w10_qpipe":   ("ot_v41_rom_elem_qp_w10", [W10, "rtl/v41rom/ot_v41_rom_elem_qp_w10.sv"],
                       ["-GQTIMING_FIX=1", "-GQPIPE=1"], ["QSH", "PIN"]),
    "qz_w10_qz":      ("ot_v41_rom_elem_qz_w10", [W10, "rtl/v41rom/ot_v41_rom_elem_qz_w10.sv"],
                       ["-GQTIMING_FIX=1", "-GQPIPE=1", "-GQZ=1"], ["QSH", "PIN"]),
    "wake_w10":       ("ot_v41_rom_elem_wake_w10", ["rtl/v41rom/ot_v41_rom_elem_wake_w10.sv"], [], []),
    "CONTROL_rowfix_fix0":("ot_v41_rom_elem_w10", ["rtl/v41rom/ot_v41_rom_elem_w10_rowfix_prepare.sv"],
                       ["-GFIX_SECOND_ROW_INDEX=0"], []),
    "rowfix_fix1":    ("ot_v41_rom_elem_w10", ["rtl/v41rom/ot_v41_rom_elem_w10_rowfix_prepare.sv"],
                       ["-GFIX_SECOND_ROW_INDEX=1"], []),
    "CONTROL_rne_wake_fix0":("ot_v41_rom_elem_w10", ["rtl/v41rom/ot_v41_rom_elem_w10_rne_wake_prepare.sv"] + RNE,
                       ["-GFIX_SECOND_ROW_INDEX=0"], []),
    "rne_wake_fix1":  ("ot_v41_rom_elem_w10", ["rtl/v41rom/ot_v41_rom_elem_w10_rne_wake_prepare.sv"] + RNE,
                       ["-GFIX_SECOND_ROW_INDEX=1"], []),
    "elem_pre_w10":   ("ot_v41_rom_elem", ["rtl/v41rom/ot_v41_rom_elem.sv"], [], ["NO_PBASE", "BASE_OLD"]),
    "xneed_qp":       ("ot_v41_rom_elem_qp_xneed_w10", [W10, "rtl/v41rom/xneed_lookahead/ot_v41_rom_elem_qp_xneed_w10.sv",
                        "rtl/v41rom/xneed_lookahead/ot_v41_need_lookahead.sv"],
                       ["-GQTIMING_FIX=1", "-GQPIPE=1"], ["QSH", "PIN"]),
}
PASS = re.compile(r"^PASS writes=(\d+) checks=(\d+) out_of_contract=(\d+)", re.M)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def one(work: Path, name: str, module: str, srcs: list[str], params: list[str], defs: list[str], root: Path):
    obj = work / name
    obj.mkdir(parents=True, exist_ok=True)
    d = [f"+define+ELEM={module}"] + [f"+define+{x}" for x in defs if x != "BASE_OLD"]
    if "BASE_OLD" in defs:
        d.append("+define+ELEM_BASE=.MTP(1),.EARLY(1)")
    cmd = [str(VERILATOR), "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-PINMISSING",
           "--top-module", "tb_v41_rom_elem_cfg_rw", "--Mdir", str(obj / "obj"), "-j", "2", "-CFLAGS", "-O0",
           *d]
    # element parameters go through ELEM_PARAMS (the bench instance), not -G (which targets the top)
    if params:
        cmd.append("+define+ELEM_PARAMS=," + ",".join(f".{p[2:].split('=')[0]}({p.split('=')[1]})" for p in params))
    prim = [RNE_SWAP.get(s, s) for s in PRIM] if any(s in RNE for s in srcs) else PRIM
    cmd += [str(root / s) for s in prim + srcs] + [str(ROOT / TB)]
    b = subprocess.run(cmd, cwd=obj, capture_output=True, text=True)
    (obj / "build.log").write_text(b.stdout + b.stderr)
    rec = dict(variant=name, module=module, sources=srcs, element_parameters=params, defines=defs,
               build_rc=b.returncode, source_root=str(root))
    if b.returncode:
        rec.update(result="BUILD_FAIL", log_tail=(b.stdout + b.stderr)[-1500:])
        return rec
    r = subprocess.run([str(obj / "obj" / "Vtb_v41_rom_elem_cfg_rw")], cwd=obj, capture_output=True, text=True)
    log = r.stdout + r.stderr
    (obj / "run.log").write_text(log)
    m = PASS.search(log)
    rec.update(run_rc=r.returncode, readbacks=log.count("READBACK"),
               mismatches=[l for l in log.splitlines() if l.startswith("MISMATCH")][:12])
    if m:
        rec.update(result="PASS", writes=int(m.group(1)), checks=int(m.group(2)), out_of_contract_writes=int(m.group(3)))
    else:
        f = re.search(r"^FAIL writes=(\d+) checks=(\d+) errors=(\d+)", log, re.M)
        rec.update(result="FAIL", errors=int(f.group(3)) if f else None, log_tail=log[-800:])
    return rec


def cmd_run(a):
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    jobs = [(n, *v, ROOT) for n, v in VARIANTS.items()]
    # control: the pre-fix decode, from git
    pre = work / "prefix_src"
    for p in [W10] + PRIM:
        q = pre / p
        q.parent.mkdir(parents=True, exist_ok=True)
        if a.prefix_dir:                              # a host without the repository: pre-exported sources
            q.write_bytes((a.prefix_dir / p).read_bytes())
        else:
            q.write_bytes(subprocess.check_output(["git", "show", f"{a.prefix_rev}:{p}"], cwd=ROOT))
    jobs.append(("CONTROL_prefix_w10", "ot_v41_rom_elem_w10", [W10], [], [], pre))
    with ThreadPoolExecutor(a.jobs) as ex:
        recs = list(ex.map(lambda j: one(work, *j), jobs))
    tv = subprocess.check_output([str(VERILATOR), "--version"], text=True).strip()
    (work / "runs.json").write_text(json.dumps(dict(prefix_rev=a.prefix_rev, tool_version=tv, runs=recs), indent=1) + "\n")
    for r in recs:
        print(r["variant"], r["result"], r.get("checks"), r.get("errors"))
    return 0


def cmd_record(a):
    d = json.loads((a.work / "runs.json").read_text())
    runs = d["runs"]
    ok = all(r["result"] == "PASS" for r in runs if not r["variant"].startswith("CONTROL")) and \
        all(r["result"] == "FAIL" for r in runs if r["variant"].startswith("CONTROL"))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tv = d.get("tool_version")
    srcs = sorted({s for v in VARIANTS.values() for s in v[1]} | set(PRIM) | {TB, "tools/dsrom_elem_cfg_rw.py"})
    rec = dict(schema="opentallas.dsrom.elem-cfg-rw.v1", verdict="PASS" if ok else "FAIL",
               bug="ot_v41_rom_elem_w10 (and copies) decoded entry 2NSEG+1+s as s_row[NSEG + a[SW-1:0] - 1]: for "
                   "s = NSEG-1 the low bits wrap, so the second macro's segment-7 row s_row[2NSEG-1] was never written "
                   "and the first macro's s_row[NSEG-1] was overwritten; entries a > 3NSEG aliased onto s_row too",
               fix="if (NB > 1 && a <= 3NSEG) s_row[a - (NSEG + 1)] <= d[15:0]  (entries a > 3NSEG write nothing)",
               test=TB, tool_version=tv,
               git_head=head, prefix_rev=d["prefix_rev"], runs=runs,
               source_sha256={s: sha(ROOT / s) for s in srcs})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["verdict"])
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run")
    r.add_argument("--work", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=8)
    r.add_argument("--prefix-rev", default="f23c56908")
    r.add_argument("--prefix-dir", type=Path, help="pre-fix sources exported from --prefix-rev (no git on the host)")
    c = sp.add_parser("record")
    c.add_argument("--work", type=Path, required=True)
    c.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    return dict(run=cmd_run, record=cmd_record)[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
