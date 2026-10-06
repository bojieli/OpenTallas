#!/usr/bin/env python3
"""QY exactness gate for ot_v41_rom_elem_q_qy_w10 (2026-10-04): tools/dsrom_qz_exact.py on the QY copy
(rtl/test/tb_dsrom_qy_exact.sv): builds pos (QY = 1), xs0 (QY = 1, QP_XS = 0), qy0 (QY = 0: the qz circuit), qz0
(QY = 0, QZ = 0: the qp circuit) and the negative controls on QY = 1.

QZ exactness gate for the DS-V4.1 ROM q-pair element (ot_v41_rom_elem_q_qz_w10, 2026-10-04).

tools/dsrom_qpipe_exact.py run on the QZ copy (rtl/test/tb_dsrom_qy_exact.sv, bank-distinct ROM fixture): QZ adds no
cycle, so every build keeps its QPIPE shift L.  Builds: pos (QZ = 1, L = 2), xs0 (QZ = 1, QP_XS = 0, L = 1), qz0 (QZ = 0,
the qp circuit, L = 2), and negative controls dp / tree / half / shadow / lu (inherited, on QZ = 1) plus bk (one bank
select copy inverted) and z (registered gate enable without its drain term).

Original description (tools/dsrom_qpipe_exact.py):
QPIPE exactness gate for the DS-V4.1 ROM q-pair element (ot_v41_rom_elem_q_qp_w10, 2026-10-03).

Builds rtl/test/tb_dsrom_qpipe_exact.sv under Verilator and runs it against the PINNED ot_v41_rom_elem_q_w10:
  pos      - QPIPE=1, QP_XS=1, QP_CAP=0, QP_P1=1 (L = 2) with +define+QT_CHECK+QP_CHECK, several seeds;
  cap      - the same with QP_CAP=1 (L = 3);
  xs0      - QP_XS=0: go / configuration / reset one cycle early, beats unshifted (L = 1);
  qp0      - QPIPE=0: the copy's default must be the qt circuit (L = 0);
  neg_*    - negative controls, built WITHOUT the internal checks, each must be caught by the shifted output /
             state comparison: wrong precomputed pair offset (dp), segment-tree hold ignoring the held bit
             (tree), lost FP8 exponent half (half), output tables read live instead of QK cycles late (shadow),
             walker last-unit lookahead ignoring a sub-block advance (lu).
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TB = "rtl/test/tb_dsrom_qy_exact.sv"
RTL = ["rtl/v41rom/ot_v41_rom_elem_q_w10.sv", "rtl/v41rom/ot_v41_rom_elem_q_qp_w10.sv",
       "rtl/v41rom/ot_v41_rom_elem_w10.sv", "rtl/v41rom/ot_v41_rom_elem_qy_w10.sv", "rtl/v41rom/ot_v41_rom_elem_q_qy_w10.sv",
       "rtl/v41rom/ot_v41_kreg.sv", "rtl/v41rom/ot_v41_chain3.sv"]
RTL += [f"rtl/v41rom/{n}.sv" for n in ("ot_v41_bterm", "ot_v41_chain", "ot_v41_segtree", "ot_v41_bf16_lanes",
        "ot_v41_fadd", "ot_v41_bmul2", "ot_v41_bterm2_w10", "ot_v41_chain2", "ot_v41_segtree2", "ot_v41_bf16_lanes2",
        "ot_v41_bterm3_w10", "ot_v41_segtree3")]
RTL += [f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_delay", "ot_hdc_cg")]
RTL += ["rtl/common/ot_prefix.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv"]
PASS = re.compile(r"PASS QP=(\d+) XS=(\d+) CAP=(\d+) P1=(\d+) L=(\d+) compared=(\d+) exempt=(\d+) seed=(\d+) cycles=(\d+) "
                  r"gated_edges=(\d+) closed_cycles=(\d+) hits=(\d+) issues=(\d+) rows=(\d+) nonzero=(\d+) classes=(\d+) "
                  r"wraps=(\d+) qadv=(\d+) restarts=(\d+) rejected=(\d+) go_closed=(\d+) go_drain=(\d+) go_open=(\d+) "
                  r"resets=(\d+)")
KEYS = ("QPIPE", "QP_XS", "QP_CAP", "QP_P1", "shift_L", "compared_cycles", "exempt_cycles", "seed", "cycles",
        "gated_edges", "closed_cycles", "hits", "issues", "rows", "nonzero", "classes_mask", "wraps", "q_advances",
        "mtp_restarts", "rejected", "go_gate_closed", "go_mid_drain", "go_walking", "resets")
CHK = ["+define+QT_CHECK", "+define+QP_CHECK"]
BUILDS = {"pos": CHK, "xs0": CHK + ["-GXS=0"], "qy0": CHK + ["-GQY=0"], "qz0": CHK + ["-GQY=0", "-GQZ=0"],
          "neg_bk": ["+define+QZ_MUTANT_BK"], "neg_z": ["+define+QZ_MUTANT_Z"], "neg_cl": ["+define+QY_MUTANT_CL"],
          "neg_dp": ["+define+QP_MUTANT_DP"], "neg_tree": ["+define+QP_MUTANT_TREE"],
          "neg_half": ["+define+QP_MUTANT_HALF"], "neg_shadow": ["+define+QP_MUTANT_SHADOW"],
          "neg_lu": ["+define+QP_MUTANT_LU"]}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--verilator", default=str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
    a = ap.parse_args()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--", *RTL, TB, "tools/dsrom_qy_exact.py"],
                                    cwd=ROOT, text=True).strip()
    if dirty and not a.allow_dirty:
        raise SystemExit("exact gate requires committed sources:\n" + dirty)
    a.work.mkdir(parents=True, exist_ok=True)

    def build(name):
        cmd = [a.verilator, "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module",
               "tb_dsrom_qy_exact", "--Mdir", str(a.work / name), "-j", "8", "-CFLAGS", "-O1"]
        cmd += BUILDS[name] + [str(ROOT / p) for p in RTL] + [str(ROOT / TB)]
        with (a.work / f"{name}.build.log").open("w") as f:
            if subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode:
                raise RuntimeError(f"{name} build failed")
        return cmd

    def run(name, seed):
        p = subprocess.run([str(a.work / name / "Vtb_dsrom_qy_exact"), f"+seed={seed}"], cwd=a.work,
                           capture_output=True, text=True)
        log = a.work / f"{name}_seed{seed}.log"
        log.write_text(p.stdout + p.stderr)
        return name, seed, p.returncode, p.stdout + p.stderr, sha(log)

    record = dict(schema="opentallas.dsrom_qy.exact.v1", verdict="FAIL",
                  git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  sources_dirty=bool(dirty),
                  parameters=dict(NB=2, MTP=1, EARLY=1, FAST=1, PP=1, FRONT_PAR=0, QTIMING_FIX=1, HC=3, QPIPE=1,
                                  QP_XS="1 (pos, qz0) / 0 (xs0)", QP_CAP=0, QP_P1=1, QP_CSAM=10,
                                  QZ="1 / 0 (qz0)", QZ_NS=8, QZ_NE=4, QY="1 (pos, xs0, negatives) / 0 (qy0, qz0)",
                                  fault_report_delay_cycles=2),
                  reference="pinned rtl/v41rom/ot_v41_rom_elem_q_w10.sv + ot_v41_rom_elem_w10.sv (unchanged)",
                  comparison="every cycle: dut pv, busy and fault equal the ref's L cycles earlier, and every data field "
                             "(value, row, segment, segments, error, position) of each macro under its pv; the walker / "
                             "FIFO / issue / drain state equals the ref's QP_XS cycles earlier (after a reset: from the "
                             "next go); only the L + 1 cycles after a reset assertion are exempt.  QT_CHECK / QP_CHECK: "
                             "match copies, the clock-gate enable and the segment-tree local decisions against the "
                             "original expressions every cycle",
                  added_latency_cycles=dict(pos=2, xs0_with_early_spine_control=1, qz0=2, qz_over_qpipe=0),
                  source_sha256={p: sha(ROOT / p) for p in RTL + [TB, "tools/dsrom_qy_exact.py"]},
                  tool_version=subprocess.check_output([a.verilator, "--version"], text=True).strip(), runs=[])
    try:
        with cf.ThreadPoolExecutor(len(BUILDS)) as ex:
            record["build_commands"] = dict(zip(BUILDS, ex.map(build, BUILDS)))
        jobs = [("pos", s) for s in range(1, a.seeds + 1)] + [("qz0", 100 + s) for s in range(1, max(2, a.seeds // 2) + 1)]
        jobs += [("qy0", 400 + s) for s in range(1, max(2, a.seeds // 2) + 1)]
        jobs += [("xs0", 200 + s) for s in range(1, max(2, a.seeds // 2) + 1)]
        jobs += [("neg_dp", 1), ("neg_tree", 1), ("neg_half", 1), ("neg_shadow", 1), ("neg_lu", 3), ("neg_bk", 1),
                 ("neg_z", 1), ("neg_cl", 1)]
        with cf.ThreadPoolExecutor(a.jobs) as ex:
            results = list(ex.map(lambda j: run(*j), jobs))
        for name, seed, rc, log, lsha in results:
            r = dict(name=name, seed=seed, returncode=rc, log_sha256=lsha)
            if name.startswith("neg"):
                if rc == 0 or ("divergence" not in log and "mismatch" not in log):
                    raise RuntimeError(f"negative control {name} not caught")
                r["caught"] = True
                r["failure_excerpt"] = [l[:200] for l in log.splitlines() if "Fatal" in l][:1]
            else:
                m = PASS.search(log)
                if rc or not m:
                    raise RuntimeError(f"{name} seed {seed} failed: {log[-1500:]}")
                r["coverage"] = dict(zip(KEYS, map(int, m.groups())))
            record["runs"].append(r)
        record["total_compared_cycles"] = sum(r["coverage"]["compared_cycles"] for r in record["runs"] if "coverage" in r)
        record["verdict"] = "PASS"
    except Exception as e:  # noqa: BLE001
        record["error"] = str(e)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(record, indent=1) + "\n")
    print(record["verdict"], record.get("total_compared_cycles"), record.get("error", ""))


if __name__ == "__main__":
    main()
