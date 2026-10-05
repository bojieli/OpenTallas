#!/usr/bin/env python3
"""QTIMING_FIX exactness gate for the DS-V4.1 ROM q-pair element (ot_v41_rom_elem_q_qt_w10).

Builds rtl/test/tb_dsrom_qtiming_exact.sv under Verilator four ways and runs it:
  positive  - pinned ot_v41_rom_elem_q_w10 vs QTIMING_FIX=1 with +define+QT_CHECK, several seeds;
  fix0      - pinned original vs the copy at QTIMING_FIX=0 (the copy's default is the original circuit);
  neg_cg    - clock-gate enable mutant (drain > 2): must be caught;
  neg_hit   - one duplicated match copy's pair address + 1: must be caught.
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TB = "rtl/test/tb_dsrom_qtiming_exact.sv"
RTL = ["rtl/v41rom/ot_v41_rom_elem_q_w10.sv", "rtl/v41rom/ot_v41_rom_elem_q_qt_w10.sv",
       "rtl/v41rom/ot_v41_rom_elem_w10.sv", "rtl/v41rom/ot_v41_rom_elem_qt_w10.sv"]
RTL += [f"rtl/v41rom/{n}.sv" for n in ("ot_v41_bterm", "ot_v41_chain", "ot_v41_segtree", "ot_v41_bf16_lanes",
        "ot_v41_fadd", "ot_v41_bmul2", "ot_v41_bterm2_w10", "ot_v41_chain2", "ot_v41_segtree2", "ot_v41_bf16_lanes2")]
RTL += [f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_delay", "ot_hdc_cg")]
RTL += ["rtl/common/ot_prefix.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv"]
PASS = re.compile(r"PASS seed=(\d+) cycles=(\d+) gated_edges=(\d+) closed_cycles=(\d+) hits=(\d+) issues=(\d+) "
                  r"rows=(\d+) nonzero=(\d+) classes=(\d+) wraps=(\d+) qadv=(\d+) restarts=(\d+) rejected=(\d+) "
                  r"go_closed=(\d+) go_drain=(\d+) go_open=(\d+) resets=(\d+)")
KEYS = ("seed", "cycles", "gated_edges", "closed_cycles", "hits", "issues", "rows", "nonzero", "classes_mask", "wraps",
        "q_advances", "mtp_restarts", "rejected", "go_gate_closed", "go_mid_drain", "go_walking", "resets")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--verilator", default=str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
    ap.add_argument("--build-workers", type=int, default=4)
    ap.add_argument("--build-jobs", type=int, default=8)
    a = ap.parse_args()
    if not 1 <= a.build_jobs <= 16 or a.build_workers < 1:
        raise SystemExit("build jobs must be 1..16 and build workers positive")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise SystemExit("exact gate requires a clean worktree")
    a.work.mkdir(parents=True, exist_ok=True)
    tb_fix0 = a.work / "tb_fix0.sv"
    tb_fix0.write_text((ROOT / TB).read_text().replace(".QTIMING_FIX(1)", ".QTIMING_FIX(0)"))
    builds = {"positive": ("+define+QT_CHECK", ROOT / TB), "fix0": (None, tb_fix0),
              "neg_cg": ("+define+QT_MUTANT_CG", ROOT / TB), "neg_hit": ("+define+QT_MUTANT_HIT", ROOT / TB)}

    def build(name):
        define, tb = builds[name]
        cmd = [a.verilator, "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module",
               "tb_dsrom_qtiming_exact", "--Mdir", str(a.work / name), "-j", str(a.build_jobs), "-CFLAGS", "-O1"]
        cmd += ([define] if define else []) + [str(ROOT / p) for p in RTL] + [str(tb)]
        with (a.work / f"{name}.build.log").open("w") as f:
            if subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode:
                raise RuntimeError(f"{name} build failed")
        return cmd

    def run(name, seed):
        p = subprocess.run([str(a.work / name / "Vtb_dsrom_qtiming_exact"), f"+seed={seed}"], cwd=a.work,
                           capture_output=True, text=True)
        log = a.work / f"{name}_seed{seed}.log"
        log.write_text(p.stdout + p.stderr)
        return name, seed, p.returncode, p.stdout + p.stderr, sha(log)

    record = dict(schema="opentallas.dsrom_qtiming.exact.v1", verdict="FAIL",
                  git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  parameters=dict(NB=2, MTP=1, EARLY=1, FAST=1, PP=1, FRONT_PAR=0, QTIMING_FIX=1, HC=3),
                  reference="pinned rtl/v41rom/ot_v41_rom_elem_q_w10.sv + ot_v41_rom_elem_w10.sv (unchanged)",
                  comparison="every output bit every cycle (valid or not), the gated clock at both clock phases, "
                             "walker/FIFO/issue/drain/enable state every cycle, captured beat under fw_v, FIFO data; "
                             "QT_CHECK: each match copy and the ICG enable vs the original expressions every cycle",
                  added_latency_cycles=0,
                  source_sha256={p: sha(ROOT / p) for p in RTL + [TB, "tools/dsrom_qtiming_exact.py"]},
                  tool_version=subprocess.check_output([a.verilator, "--version"], text=True).strip(), runs=[])
    try:
        with cf.ThreadPoolExecutor(a.build_workers) as ex:
            record["build_commands"] = dict(zip(builds, ex.map(build, builds)))
        jobs = [("positive", s) for s in range(1, a.seeds + 1)] + [("fix0", 101), ("neg_cg", 1), ("neg_hit", 1)]
        with cf.ThreadPoolExecutor(a.jobs) as ex:
            results = list(ex.map(lambda j: run(*j), jobs))
        for name, seed, rc, log, lsha in results:
            r = dict(name=name, seed=seed, returncode=rc, log_sha256=lsha)
            if name.startswith("neg"):
                if rc == 0 or "divergence" not in log and "mismatch" not in log and "QT_CHECK" not in log:
                    raise RuntimeError(f"negative control {name} not caught")
                r["caught"] = True
                r["failure_excerpt"] = [l for l in log.splitlines() if "Fatal" in l][:1]
            else:
                m = PASS.search(log)
                if rc or not m:
                    raise RuntimeError(f"{name} seed {seed} failed: {log[-1500:]}")
                r["coverage"] = dict(zip(KEYS, map(int, m.groups())))
            record["runs"].append(r)
        record["total_compared_cycles"] = sum(r["coverage"]["cycles"] for r in record["runs"] if "coverage" in r)
        record["verdict"] = "PASS"
    except Exception as e:  # noqa: BLE001
        record["error"] = str(e)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(record, indent=1) + "\n")
    print(record["verdict"], record.get("total_compared_cycles"), record.get("error", ""))


if __name__ == "__main__":
    main()
