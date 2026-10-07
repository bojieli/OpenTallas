#!/usr/bin/env python3
"""QX exactness gate for ot_v41_rom_elem_q_qx_w10 (2026-10-04): the QY gate below on the QX copy
(rtl/test/tb_dsrom_qx_exact.sv): pos / xs0 / negatives with QX = 10 (QX = 9 + zero-cycle fixes; outputs compared as per-key sequences), qx9 (QX = 9), qx8 (QX = 8), qx7 (QX = 7), qx6 (QX = 6), qx5 (QX = 5), qx4 (QX = 4), qx3 (QX = 3), qx2 (QX = 2), qx1 (QX = 1), qx0 (QX = 0: the qy circuit), qy0 (QX = QY = 0:
the qz circuit), qz0 (QX = QY = QZ = 0: the qp circuit), plus neg_qxlu (the one-hot lookahead ignoring a sub-block
advance) and neg_qxca (the registered case-A decision ignoring it).

QY exactness gate for ot_v41_rom_elem_q_qy_w10 (2026-10-04): tools/dsrom_qz_exact.py on the QY copy
(rtl/test/tb_dsrom_qy_exact.sv): builds pos (QY = 1), xs0 (QY = 1, QP_XS = 0), qy0 (QY = 0: the qz circuit), qz0
(QY = 0, QZ = 0: the qp circuit) and the negative controls on QY = 1.

QZ exactness gate for the DS-V4.1 ROM q-pair element (ot_v41_rom_elem_q_qz_w10, 2026-10-04).

tools/dsrom_qpipe_exact.py run on the QZ copy (rtl/test/tb_dsrom_qx_exact.sv, bank-distinct ROM fixture): QZ adds no
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
TB = "rtl/test/tb_dsrom_qx_exact.sv"
RTL = ["rtl/v41rom/ot_v41_rom_elem_q_w10.sv", "rtl/v41rom/ot_v41_rom_elem_q_qp_w10.sv",
       "rtl/v41rom/ot_v41_rom_elem_w10.sv", "rtl/v41rom/ot_v41_rom_elem_qx_w10.sv", "rtl/v41rom/ot_v41_rom_elem_q_qx_w10.sv",
       "rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv", "rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv", "rtl/v41rom/ot_v41_elem_pq_tags.sv",
       "rtl/v41rom/ot_v41_kreg.sv", "rtl/v41rom/ot_v41_chain3.sv"]
RTL += [f"rtl/v41rom/{n}.sv" for n in ("ot_v41_bterm", "ot_v41_chain", "ot_v41_segtree", "ot_v41_bf16_lanes",
        "ot_v41_fadd", "ot_v41_bmul2", "ot_v41_bterm2_w10", "ot_v41_chain2", "ot_v41_segtree2", "ot_v41_bf16_lanes2",
        "ot_v41_bterm3_w10", "ot_v41_bterm4_w10", "ot_v41_bterm5_w10", "ot_v41_segtree3", "ot_v41_segtree4", "ot_v41_segtree5", "ot_v41_segtree6", "ot_v41_chain4", "ot_v41_fadd2")]
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
BUILDS = {"pos": CHK, "pos_pq0": CHK + ["+define+QX_DUT_PQ0"], "pos_qw": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QW=1"], "pos_qm": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QM=1"], "pos_qm2": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QM=2"], "pos_qm3": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QM=3"], "pos_qm4": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QM=4"], "pos_qm5": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QM=5"],
          "neg_qm2z": ["+define+QX_DUT_PQ0", "+define+QX_QM=2", "+define+ST6_MUTANT_Z"], "neg_qm2q": ["+define+QX_DUT_PQ0", "+define+QX_QM=2", "+define+ST6_MUTANT_Q"],
          "pos_qm6": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QM=6"], "neg_qm6ns": ["+define+QX_DUT_PQ0", "+define+QX_QM=6", "+define+BT5_MUTANT_NS"], "neg_qm6sh": ["+define+QX_DUT_PQ0", "+define+QX_QM=6", "+define+BT5_MUTANT_SH"], "neg_qm6f4": ["+define+QX_DUT_PQ0", "+define+QX_QM=6", "+define+QM6_MUTANT_F4"], "neg_qm6sf": ["+define+QX_DUT_PQ0", "+define+QX_QM=6", "+define+QM6_MUTANT_SF"],
          "pos_qm7": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QM=7"], "neg_qm7rz": ["+define+QX_DUT_PQ0", "+define+QX_QM=7", "+define+QM7_MUTANT_RZ"], "neg_qm7ns": ["+define+QX_DUT_PQ0", "+define+QX_QM=7", "+define+BT5_MUTANT_NS"],
          "pos_qs5": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=1"], "neg_qs5ns": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=1", "+define+BT5_MUTANT_NS"], "neg_qs5sh": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=1", "+define+BT5_MUTANT_SH"],
          "pos_qs2": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=2"], "neg_qs2ns": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=2", "+define+BT5_MUTANT_NS"], "neg_qs2sh": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=2", "+define+BT5_MUTANT_SH"],
          "pos_qs3": CHK + ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=3"], "neg_qs3ns": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=3", "+define+BT5_MUTANT_NS"], "neg_qs3sh": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=3", "+define+BT5_MUTANT_SH"], "neg_qs3yf": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=3", "+define+ST7_MUTANT_YF"], "neg_qs3nr": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=3", "+define+WRT_MUTANT_NR"], "neg_qs3sb": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+QX_QS=3", "+define+WRT_MUTANT_SB"],
          "neg_qm5ns": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+BT5_MUTANT_NS"], "neg_qm5sh": ["+define+QX_DUT_PQ0", "+define+QX_QM=5", "+define+BT5_MUTANT_SH"],
          "neg_qmns": ["+define+QX_DUT_PQ0", "+define+QX_QM=1", "+define+BT5_MUTANT_NS"], "neg_qmsh": ["+define+QX_DUT_PQ0", "+define+QX_QM=1", "+define+BT5_MUTANT_SH"], "xs0": CHK + ["-GXS=0"], "qx1": CHK + ["-GQX=1"], "qx0": CHK + ["-GQX=0"], "qy0": CHK + ["-GQX=0", "-GQY=0"],
          "qz0": CHK + ["-GQX=0", "-GQY=0", "-GQZ=0"], "neg_qxlu": ["+define+QX_MUTANT_LU", "-GQX=8"],
          "neg_qxca": ["+define+QX_MUTANT_CA", "-GQX=8"], "neg_qxnca": ["+define+QX_MUTANT_NCA", "-GQX=8"],
          "qx2": CHK + ["-GQX=2"], "qx3": CHK + ["-GQX=3"], "qx4": CHK + ["-GQX=4"], "qx5": CHK + ["-GQX=5"], "qx6": CHK + ["-GQX=6"], "qx7": CHK + ["-GQX=7"], "qx8": CHK + ["-GQX=8"], "neg_fw": ["+define+ST_MUTANT_FW"], "qx9": CHK + ["-GQX=9"], "neg_ns": ["+define+BT_MUTANT_NS"], "neg_pd": ["+define+CH_MUTANT_PD"], "neg_dp10": ["+define+QP_MUTANT_DP"], "neg_tree9": ["+define+QP_MUTANT_TREE"], "neg_xc": ["+define+ST_MUTANT_XC", "-GQX=8"], "neg_qxsf": ["+define+QX_MUTANT_SF", "-GQX=8"], "neg_qxhz": ["+define+QX_MUTANT_HZ", "-GQX=8"], "neg_p2s": ["+define+BT_MUTANT_P2S", "-GQX=8"],
          "neg_bk": ["+define+QZ_MUTANT_BK", "-GQX=8"], "neg_z": ["+define+QZ_MUTANT_Z", "-GQX=8"], "neg_cl": ["+define+QY_MUTANT_CL", "-GQX=8"],
          "neg_dp": ["+define+QP_MUTANT_DP", "-GQX=8"], "neg_tree": ["+define+QP_MUTANT_TREE", "-GQX=8"],
          "neg_half": ["+define+QP_MUTANT_HALF", "-GQX=8"], "neg_shadow": ["+define+QP_MUTANT_SHADOW", "-GQX=8"],
          "neg_lu": ["+define+QP_MUTANT_LU", "-GQX=8"]}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--quick", action="store_true",
                    help="one seed per configuration (owner ruling 2026-10-05, simple verification): every build runs once, "
                         "including every negative control; the comparison itself is unchanged")
    ap.add_argument("--tag", default="", help="also write the record with this suffix, so a quick run never hides the full one")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--only", default="", help="regex: run only the builds whose name matches (e.g. pos_qm|neg_qm.*)")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--verilator", default=str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
    a = ap.parse_args()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--", *RTL, TB, "tools/dsrom_qx_exact.py"],
                                    cwd=ROOT, text=True).strip()
    if dirty and not a.allow_dirty:
        raise SystemExit("exact gate requires committed sources:\n" + dirty)
    a.work.mkdir(parents=True, exist_ok=True)

    def build(name):
        cmd = [a.verilator, "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module",
               "tb_dsrom_qx_exact", "--Mdir", str(a.work / name), "-j", "8", "-CFLAGS", "-O1"]
        cmd += BUILDS[name] + [str(ROOT / p) for p in RTL] + [str(ROOT / TB)]
        with (a.work / f"{name}.build.log").open("w") as f:
            if subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode:
                raise RuntimeError(f"{name} build failed")
        return cmd

    def run(name, seed, extra=()):
        tag = name + "".join("_" + x.lstrip("+") for x in extra)
        p = subprocess.run([str(a.work / name / "Vtb_dsrom_qx_exact"), f"+seed={seed}", *extra], cwd=a.work,
                           capture_output=True, text=True)
        log = a.work / f"{tag}_seed{seed}.log"
        log.write_text(p.stdout + p.stderr)
        return tag, seed, p.returncode, p.stdout + p.stderr, sha(log)

    record = dict(schema="opentallas.dsrom_qx.exact.v1", verdict="FAIL",
                  git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  sources_dirty=bool(dirty),
                  parameters=dict(NB=2, MTP=1, EARLY=1, FAST=1, PP=1, FRONT_PAR=0, QTIMING_FIX=1, HC=3, QPIPE=1,
                                  QP_XS="1 (pos, qz0) / 0 (xs0)", QP_CAP=0, QP_P1=1, QP_CSAM=10,
                                  QZ="1 / 0 (qz0)", QZ_NS=8, QZ_NE=4, QY="1 (pos, xs0, qx0, negatives) / 0 (qy0, qz0)",
                                  QX="10 (pos, xs0, negatives; SEQ output compare) / 9 (qx9) / 8 (qx8) / 7 (qx7) / 6 (qx6) / 5 (qx5) / 4 (qx4) / 3 (qx3) / 2 (qx2) / 1 (qx1) / 0 (qx0, qy0, qz0)",
                                  fault_report_delay_cycles=2),
                  reference="pinned rtl/v41rom/ot_v41_rom_elem_q_w10.sv + ot_v41_rom_elem_w10.sv (unchanged)",
                  comparison="every cycle: dut pv, busy and fault equal the ref's L cycles earlier, and every data field "
                             "(value, row, segment, segments, error, position) of each macro under its pv; the walker / "
                             "FIFO / issue / drain state equals the ref's QP_XS cycles earlier (after a reset: from the "
                             "next go); only the L + 1 cycles after a reset assertion are exempt.  QT_CHECK / QP_CHECK: "
                             "match copies, the clock-gate enable and the segment-tree local decisions against the "
                             "original expressions every cycle",
                  added_latency_cycles=dict(pos=2, xs0_with_early_spine_control=1, qz0=2, qz_over_qpipe=0, qx_over_qy=0),
                  source_sha256={p: sha(ROOT / p) for p in RTL + [TB, "tools/dsrom_qx_exact.py"]},
                  tool_version=subprocess.check_output([a.verilator, "--version"], text=True).strip(), runs=[])
    try:
        with cf.ThreadPoolExecutor(len(BUILDS)) as ex:
            names = [b for b in BUILDS if not a.only or re.fullmatch(a.only, b)]
            record["build_commands"] = dict(zip(names, ex.map(build, names)))
        n = 1 if a.quick else a.seeds
        m = 1 if a.quick else max(2, a.seeds // 2)
        record["measurement_mode"] = ("quick: one seed per configuration" if a.quick else
                                      "pos x %d seeds, every other configuration x %d" % (n, m))
        jobs = [("pos", s) for s in range(1, n + 1)] + [("pos_pq0", s) for s in range(1, n + 1)] + [("pos_qw", s) for s in range(1, n + 1)] + [("pos_qw", 1, ("+nan_sparse",))] + [("pos_qm", s) for s in range(1, n + 1)] + [("pos_qm", 1, ("+nan_sparse",))] + [("qz0", 100 + s) for s in range(1, m + 1)]
        jobs += [("qx9", 1400 + s) for s in range(1, m + 1)]
        jobs += [("qx8", 1300 + s) for s in range(1, m + 1)]
        jobs += [("qx7", 1200 + s) for s in range(1, m + 1)]
        jobs += [("qx6", 1100 + s) for s in range(1, m + 1)]
        jobs += [("qx5", 1000 + s) for s in range(1, m + 1)]
        jobs += [("qx4", 900 + s) for s in range(1, m + 1)]
        jobs += [("qx3", 800 + s) for s in range(1, m + 1)]
        jobs += [("qx2", 700 + s) for s in range(1, m + 1)]
        jobs += [("qx1", 600 + s) for s in range(1, m + 1)]
        jobs += [("qx0", 500 + s) for s in range(1, m + 1)]
        jobs += [("qy0", 400 + s) for s in range(1, m + 1)]
        jobs += [("xs0", 200 + s) for s in range(1, m + 1)]
        jobs += [("neg_dp", 1), ("neg_tree", 1), ("neg_half", 1), ("neg_shadow", 1), ("neg_lu", 3), ("neg_bk", 1),
                 ("neg_z", 1), ("neg_cl", 1), ("neg_qxlu", 3), ("neg_qxca", 3), ("neg_qxnca", 3), ("neg_p2s", 1), ("neg_qxhz", 1), ("neg_qxsf", 1), ("neg_xc", 1), ("neg_fw", 1), ("neg_tree9", 1), ("neg_pd", 1), ("neg_dp10", 1)]
        # +nan_sparse (bench header): the QX = 10 lane-NaN partials (bterm4 NS) and their negative control on sparse NaNs
        jobs += [("pos", 1, ("+nan_sparse",)), ("neg_ns", 1, ("+nan_sparse",))]
        jobs += [("neg_qmns", 1, ("+nan_sparse",)), ("neg_qmsh", 1)]
        jobs += [("pos_qm2", s) for s in range(1, n + 1)] + [("pos_qm2", 7), ("neg_qm2z", 1), ("neg_qm2q", 1)]
        jobs += [("pos_qm3", s) for s in range(1, n + 1)] + [("pos_qm3", 7)]
        jobs += [("pos_qm4", s) for s in range(1, n + 1)] + [("pos_qm4", 1, ("+nan_sparse",))]
        jobs += [("pos_qm5", s) for s in range(1, n + 1)] + [("pos_qm5", 1, ("+nan_sparse",))] + [("neg_qm5ns", 1, ("+nan_sparse",)), ("neg_qm5sh", 1)]
        jobs += [("pos_qm6", s) for s in range(1, n + 1)] + [("pos_qm6", 1, ("+nan_sparse",)), ("neg_qm6ns", 1, ("+nan_sparse",)), ("neg_qm6sh", 1), ("neg_qm6f4", 1), ("neg_qm6sf", 1)]      # QM lane (ot_v41_bterm5_w10) controls
        jobs += [("pos_qm7", s) for s in range(1, n + 1)] + [("pos_qm7", 1, ("+nan_sparse",)), ("neg_qm7rz", 1), ("neg_qm7ns", 1, ("+nan_sparse",))]
        jobs += [("pos_qs5", s) for s in range(1, n + 1)] + [("pos_qs5", 1, ("+nan_sparse",)), ("neg_qs5ns", 1, ("+nan_sparse",)), ("neg_qs5sh", 1)]
        jobs += [("pos_qs2", s) for s in range(1, n + 1)] + [("pos_qs2", 1, ("+nan_sparse",)), ("neg_qs2ns", 1, ("+nan_sparse",)), ("neg_qs2sh", 1)]
        jobs += [("pos_qs3", s) for s in range(1, n + 1)] + [("pos_qs3", 1, ("+nan_sparse",)), ("neg_qs3ns", 1, ("+nan_sparse",)), ("neg_qs3sh", 1), ("neg_qs3yf", 1), ("neg_qs3nr", 1), ("neg_qs3sb", 1)]
        if a.only:
            jobs = [j for j in jobs if re.fullmatch(a.only, j[0])]
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
                sq = re.search(r"SEQ matched=(\d+) dropped_at_reset=(\d+) extra_delay_cycles min=(-?\d+) max=(-?\d+) mean_x1000=(-?\d+)", log)
                if sq:
                    hist = re.search(r"SEQ extra_delay_hist((?: \d+)+)", log)
                    r["sequence"] = dict(matched=int(sq[1]), dropped_at_reset=int(sq[2]), extra_delay_min=int(sq[3]),
                                         extra_delay_max=int(sq[4]), extra_delay_mean=int(sq[5]) / 1000,
                                         extra_delay_hist_0_to_15plus=[int(x) for x in hist[1].split()] if hist else None)
            record["runs"].append(r)
        record["total_compared_cycles"] = sum(r["coverage"]["compared_cycles"] for r in record["runs"] if "coverage" in r)
        record["verdict"] = "PASS"
    except Exception as e:  # noqa: BLE001
        record["error"] = str(e)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    if a.tag:
        a.output.with_name(a.output.stem + "_" + a.tag + a.output.suffix).write_text(json.dumps(record, indent=1) + "\n")
    a.output.write_text(json.dumps(record, indent=1) + "\n")
    print(record["verdict"], record.get("total_compared_cycles"), record.get("error", ""))


if __name__ == "__main__":
    main()
