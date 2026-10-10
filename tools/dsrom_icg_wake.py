#!/usr/bin/env python3
"""DS ROM element clock-gate WAKE LATENCY gate (mtp-wake-1010, 2026-10-10).

Runs rtl/test/tb_dsrom_icg_wake.sv under Verilator: the qx exactness bench's stimulus (go into a closed gate, mid-drain,
back-to-back, resets, x noise) on a LOCKSTEP pair of the deployed DS ROM q-pair element ot_v41_rom_elem_qx_w10 -- CG = 1
(element ICG) against CG = 0 (free-running clock: a domain that never sleeps) -- compared every cycle with shift 0, and
the clk edges from a go sampled into a closed gate to the first gated edge measured.

Builds: pos (QZ registered enable, as the routed q pair), qze (+ QZE retimed enable, as the BF recut pair), tcg (+ TCG
per-column clock tiles), neg_godly (gated element sees go one cycle late = a 1-cycle exposed wake; must FAIL).

    python3 tools/dsrom_icg_wake.py --work /srv/.../icgwake --output results/rtl/dsrom_icg_wake_20261010/wake.json
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_qx_exact as QX  # noqa: E402  (same RTL list and PASS line)

TB = "rtl/test/tb_dsrom_icg_wake.sv"
# the qx element now instantiates the GRADUAL_RNE / RC BF lane module (rtl/v41rom/ot_v41_bf16_lanes2_rne_prepare.sv,
# same module name), so it replaces ot_v41_bf16_lanes2.sv with its multiplier companions (unused at BF16 = 0)
RTL = [p for p in QX.RTL if p != "rtl/v41rom/ot_v41_bf16_lanes2.sv"] + [
    "rtl/v41rom/ot_v41_bf16_lanes2_rne_prepare.sv", "rtl/v41rom/ot_v41_bmul2_rne_prepare.sv",
    "rtl/v41rom/ot_v41_bmul_subnormal_rne_prepare.sv", "rtl/v41rom/ot_v41_tile_clk.sv"]
CHK = ["+define+QT_CHECK", "+define+QP_CHECK"]
BUILDS = {"pos": CHK, "qze": CHK + ["+define+WK_QZE=1"], "tcg": CHK + ["+define+WK_QZE=1", "+define+WK_TCG=1"],
          "neg_godly": ["+define+WK_MUTANT_GODLY"]}
WAKE = re.compile(r"WAKE QZE=(\d+) TCG=(\d+) closed_go=(\d+) open_go=(\d+) edges_to_first_gated_edge min=(-?\d+) max=(-?\d+) "
                  r"mean_x1000=(\d+) hist1\.\.7\+ ((?:\d+ ?){7})")
LOCK = re.compile(r"WAKE lockstep compared=(\d+) exempt=(\d+) gated_edges=(\d+) free_edges=(\d+) closed_cycles=(\d+)")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--verilator", default=str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
    a = ap.parse_args()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--", *RTL, TB, "tools/dsrom_icg_wake.py"],
                                    cwd=ROOT, text=True).strip()
    if dirty:
        raise SystemExit("gate requires committed sources:\n" + dirty)
    a.work.mkdir(parents=True, exist_ok=True)

    def build(name):
        cmd = [a.verilator, "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module",
               "tb_dsrom_icg_wake", "--Mdir", str(a.work / name), "-j", "8", "-CFLAGS", "-O1"]
        cmd += BUILDS[name] + [str(ROOT / p) for p in RTL] + [str(ROOT / TB)]
        with (a.work / f"{name}.build.log").open("w") as f:
            if subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode:
                raise RuntimeError(f"{name} build failed")
        return cmd

    def run(name, seed):
        p = subprocess.run([str(a.work / name / "Vtb_dsrom_icg_wake"), f"+seed={seed}"], cwd=a.work,
                           capture_output=True, text=True)
        log = a.work / f"{name}_seed{seed}.log"
        log.write_text(p.stdout + p.stderr)
        return name, seed, p.returncode, p.stdout + p.stderr, sha(log)

    rec = dict(schema="opentallas.dsrom.icg_wake.v1", verdict="FAIL",
               git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               element="ot_v41_rom_elem_qx_w10 QX 10 QY 1 QZ 1 QTIMING_FIX 1 QPIPE 1 QP_XS 1 QP_P1 1 NB 2 MTP 1 EARLY 1 FAST 1 PP 1 BF16 0",
               comparison="gated (CG 1) vs free-running (CG 0) element on identical pins, every cycle, shift 0: pv, busy, "
                          "fault, each macro's data under pv, and walker / FIFO / issue / drain state",
               source_sha256={p: sha(ROOT / p) for p in RTL + [TB, "tools/dsrom_icg_wake.py"]},
               tool_version=subprocess.check_output([a.verilator, "--version"], text=True).strip(), runs=[])
    try:
        with cf.ThreadPoolExecutor(len(BUILDS)) as ex:
            rec["build_commands"] = dict(zip(BUILDS, ex.map(build, BUILDS)))
        jobs = [(b, s) for b in ("pos", "qze", "tcg") for s in range(1, a.seeds + 1)] + [("neg_godly", 1)]
        with cf.ThreadPoolExecutor(a.jobs) as ex:
            res = list(ex.map(lambda j: run(*j), jobs))
        for name, seed, rc, log, lsha in res:
            r = dict(name=name, seed=seed, returncode=rc, log_sha256=lsha)
            if name.startswith("neg"):
                if rc == 0 or "WAKE lockstep" not in log or "mismatch" not in log and "divergence" not in log:
                    raise RuntimeError(f"negative control {name} not caught: {log[-800:]}")
                r["caught"] = True
                r["failure_excerpt"] = [l[:220] for l in log.splitlines() if "Fatal" in l or "WAKE lockstep" in l][:2]
            else:
                m, w, k = QX.PASS.search(log), WAKE.search(log), LOCK.search(log)
                if rc or not (m and w and k):
                    raise RuntimeError(f"{name} seed {seed} failed: {log[-1500:]}")
                r["wake"] = dict(QZE=int(w[1]), TCG=int(w[2]), go_into_closed_gate=int(w[3]), go_into_open_gate=int(w[4]),
                                 edges_to_first_gated_edge_min=int(w[5]), edges_to_first_gated_edge_max=int(w[6]),
                                 edges_to_first_gated_edge_mean=int(w[7]) / 1000, hist_1_to_7plus=[int(x) for x in w[8].split()])
                r["lockstep"] = dict(compared_cycles=int(k[1]), exempt_cycles=int(k[2]), gated_edges=int(k[3]),
                                     free_edges=int(k[4]), gate_closed_cycles=int(k[5]), output_mismatches=0)
                r["qx_coverage"] = dict(zip(QX.KEYS, map(int, m.groups())))
            rec["runs"].append(r)
        pos = [r for r in rec["runs"] if "wake" in r]
        rec["summary"] = dict(
            go_into_closed_gate=sum(r["wake"]["go_into_closed_gate"] for r in pos),
            edges_to_first_gated_edge=sorted({r["wake"]["edges_to_first_gated_edge_min"] for r in pos} |
                                             {r["wake"]["edges_to_first_gated_edge_max"] for r in pos}),
            lockstep_compared_cycles=sum(r["lockstep"]["compared_cycles"] for r in pos),
            exposed_wake_cycles_per_element_op=0,
            reading="every go into a closed gate opens it at the edge after the one that samples go_pin, which is the "
                    "edge at which the element first consumes its registered go (b_go, free clock): the gated element's "
                    "outputs and state equal the never-gated element's in the same cycle, so the wake costs 0 cycles; "
                    "a 1-cycle-late go (neg_godly) is caught")
        rec["verdict"] = "PASS"
    except Exception as e:  # noqa: BLE001
        rec["error"] = str(e)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["verdict"], rec.get("summary"), rec.get("error", ""))


if __name__ == "__main__":
    main()
