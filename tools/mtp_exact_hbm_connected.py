#!/usr/bin/env python3
"""HBM accelerator MTP, CONNECTED closed control plane vs the golden speculative decode (mtp-exact, 2026-10-08).

The DSpark loop bench rtl/test/tb_dshbm_dspark.sv (tools/dshbm_dspark_rtl_campaign.py bench: every command, every
spec-state gather / write address stream against the golden's rows, router top-k ids, expert unions streamed through
W19's expert fetch and the HBM model, every argmax, emitted tokens, per-step accepts, and the FINAL state at the last
committed position against the AUTOREGRESSIVE run) on rtl/experimental/mtp_exact_20261008/ot_dshbm_mtp_closed_top.sv:
the closed 1.2 GHz variants together -- ctl_f2, accept_a0, argmax_f1, union_f3, spec_state token-edge
TOKEN_EDGE_FIX = 1, scratch_c2 (verify-token staging) -- with the as-built router top-k.  The bench is a patched copy
in the run directory (top module name only); every pinned source is unchanged.

Golden traces come from tools/dshbm_dspark_trace.py (GPU host).  Negative mutants (each must FAIL): --mut 1/2/3
(control mutations of ot_dshbm_dspark_ctl), --wr W / --sr r (rings without the speculative headroom), --accx (an
ot_hdc_accept that accepts one draft past the first mismatch: tools/mtp_exact_mutants.py), --tef0 (spec_state
successor with TOKEN_EDGE_FIX = 0: exact in this protocol, which never resets mid-run -- reported, not a mutant).

    python3 tools/mtp_exact_hbm_connected.py --trace DIR [--mut N] [--wr W] [--sr R] [--accx] --out PART.json
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dshbm_dspark_rtl_campaign as C  # noqa: E402
import mtp_exact_mutants as MUT  # noqa: E402

SS = "results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005/source_set/"
TOP = "rtl/experimental/mtp_exact_20261008/ot_dshbm_mtp_closed_top.sv"
CLOSED = ["rtl/gpu/dshbm/ot_dshbm_accept_port.sv", SS + "rtl/gpu/dshbm/ot_dshbm_argmax.sv",
          SS + "rtl/gpu/dshbm/ot_dshbm_expert_union.sv",
          "rtl/experimental/ctl_spec_seed8_20261005/ot_dshbm_spec_state_f_token_edge.sv",
          "rtl/gpu/dshbm/ot_dshbm_dspark_ctl.sv", SS + "rtl/gpu/ot_gpu_scratch_service.sv",
          "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v", TOP]
TB = "rtl/test/tb_dshbm_dspark.sv"


def sha(p) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def bench_copy(d: Path, tef: int) -> Path:
    s = (ROOT / TB).read_text()
    a = "    ot_dshbm_dspark_top #("
    assert s.count(a) == 1
    s = s.replace(a, f"    ot_dshbm_mtp_closed_top #(.TOKEN_EDGE_FIX({tef}), ")
    out = d / "tb_dshbm_dspark_closed.sv"
    out.write_text(s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--trace", required=True)
    ap.add_argument("--mut", type=int, default=0)
    ap.add_argument("--wr", type=int, default=0)
    ap.add_argument("--sr", type=int, default=0)
    ap.add_argument("--leaf", type=int, default=0)
    ap.add_argument("--accx", action="store_true")
    ap.add_argument("--tef0", action="store_true")
    ap.add_argument("--workdir", default="/tmp/claude-1000/mtp-exact-hbm")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    tdir = Path(a.trace)
    cfg = json.loads((tdir / "cfg.json").read_text())
    params = C.bench_params(cfg, a)
    Path(a.workdir).mkdir(parents=True, exist_ok=True)
    bdir = Path(tempfile.mkdtemp(prefix="bench_", dir=a.workdir))
    srcs = [ROOT / p for p in CLOSED + [s for s in C.REUSED]]
    if a.accx:
        srcs = MUT.swap(srcs, MUT.ACCEPT, MUT.accept_extra(bdir))
    tb = bench_copy(bdir, 0 if a.tef0 else 1)
    top = "tb_dshbm_dspark"
    exe = bdir / "sim.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(exe), "-s", top] + [f"-P{top}.{k}={v}" for k, v in params.items()] + \
        [str(s) for s in srcs] + [str(tb)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (bdir / "build.log").write_text(r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit(f"iverilog failed: {bdir / 'build.log'}\n{r.stderr[-2000:]}")
    t0 = time.time()
    p = subprocess.run(["vvp", "-n", str(exe)], cwd=tdir, capture_output=True, text=True)
    wall = time.time() - t0
    (bdir / "sim.log").write_text(p.stdout + p.stderr)
    line = next((ln for ln in p.stdout.splitlines() if ln.startswith("DSHBM ")), "DSHBM FAIL no-summary")
    st = line.split()[1]
    kv = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", line)}
    msgs = [ln for ln in p.stdout.splitlines() if "MISMATCH" in ln or "FINAL" in ln or "TIMEOUT" in ln][:12]
    expect_fail = bool(a.mut or a.wr or a.sr or a.accx)
    rec = dict(schema="opentallas.rtl.mtp_exact_hbm_connected.v1", dut="ot_dshbm_mtp_closed_top",
               closed_blocks=dict(ctl="ctl_f2 (FAST=1)", accept="accept_a0 (ot_hdc_accept NSLOT 8)",
                                  argmax="argmax_f1 (FAST=1)", union="union_f3 (FAST=1)",
                                  spec_state=f"token_edge TOKEN_EDGE_FIX={0 if a.tef0 else 1}",
                                  scratch="scratch_c2 (CAP2=1, verify-token staging)",
                                  router="as-built ot_gpu_router_topk (successor not physically closed)"),
               trace=dict(dir=str(tdir), drafter=cfg["drafter"], gamma=cfg["gamma"], ngen=cfg["ngen"],
                          window=params["W"], n_final=cfg["n_final"], records=cfg["records"],
                          accepted_per_step=[s["accepted"] for s in cfg["steps"]], golden=cfg["golden"],
                          script_sha256=hashlib.sha256((tdir / "script.hex").read_bytes()).hexdigest()),
               params=params, mutation=dict(mut=a.mut, wr=a.wr, sr=a.sr, accept_extra=a.accx) if expect_fail else None,
               sim_status=st, summary=kv, messages=msgs, wall_s=round(wall, 1), simulator="icarus " +
               subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0],
               source_sha256={p: sha(p) for p in CLOSED + C.REUSED + [TB, "tools/mtp_exact_hbm_connected.py",
                                                                      "tools/mtp_exact_mutants.py",
                                                                      "tools/dshbm_dspark_rtl_campaign.py"]})
    rec["detected" if expect_fail else "exact"] = (st != "PASS") if expect_fail else (st == "PASS")
    rec["status"] = "pass" if (rec.get("detected") or rec.get("exact")) else "fail"
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(a.out.name, rec["status"], st, {k: kv.get(k) for k in ("cyc_total", "steps", "emitted", "gathers")})
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
