#!/usr/bin/env python3
"""Die decode of the reduced V4.1 token on the OPERATOR-FUSION build (W11; tools/w11_su_fuse.py).

    python3 tools/w11_su_fuse_die.py --sukr K [--subcast B --suret R] [tools/rtl_hdc_v41x_decode_campaign.py args]

tools/rtl_hdc_v41x_decode_campaign.py (pinned) unchanged, run in-process with:
* the fusion build of the core and the vector unit (ot_hdc_core_v41x_kr.sv, ot_hdc_v41x_su_adapt_kr.sv,
  ot_hdc_v41x_vec_kr.sv, ot_hdc_v41x_vec_lane_kr.sv: the same modules, with lane registers) in place of the
  originals, built with SUKR = K, SUBCAST = B, SURET = R (macros OT_SUKR / OT_SUBCAST / OT_SURET);
* the program and images from tools/hdc_program_v41_fuse.py: with K > 0 the program is fused for the build's
  vector unit (HDC_V41_SU_FUSE = sun,sum,K) and the ISA model keeps the lane registers; K = 0 builds the unfused
  program on the same RTL (the control);
* the record says so (`operator_fusion`), with the swapped sources pinned in input_sha256.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_decode_campaign as D   # noqa: E402

SWAP = {"ot_hdc_v41x_vec": "ot_hdc_v41x_vec_kr", "ot_hdc_v41x_vec_lane": "ot_hdc_v41x_vec_lane_kr",
        "ot_hdc_v41x_su_adapt": "ot_hdc_v41x_su_adapt_kr", "ot_hdc_core_v41x": "ot_hdc_core_v41x_kr"}
FUSE = dict(sukr=0, subcast=0, suret=0)
EXTRA = ("rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv")


def _swap():
    for k, p in enumerate(D.RTL):
        if p.stem in SWAP:
            D.RTL[k] = p.with_name(SWAP[p.stem] + ".sv")
    assert sum(p.stem in SWAP.values() for p in D.RTL) == len(SWAP), [p.stem for p in D.RTL]
    # the vector unit's serial-domain primitives (keep-prefix adders, latency-parameterised FP), which the
    # campaign's list lacks (its committed runs build the SU as built: --units he,me)
    for n in EXTRA:
        if ROOT / n not in D.RTL:
            D.RTL.append(ROOT / n)


_defines = D.defines


def defines(lanes=None):
    # -Wno-TIMESCALEMOD (as the campaign's own lint passes): the SU's elaboration-time trap instances name
    # modules that do not exist in branches never built, which this Verilator reports as timescale-less modules
    return _defines(lanes) + [f"+define+OT_SUKR={FUSE['sukr']}", f"+define+OT_SUBCAST={FUSE['subcast']}",
                              f"+define+OT_SURET={FUSE['suret']}", "-Wno-TIMESCALEMOD"]


def images(out, *extra, lanes=None):
    env = dict(os.environ, HDC_SW=str(lanes or D.I.SU_LANES), HDC_V41_ARITH=D.arith(),
               HDC_V41_IDX_FUSED=str(int("idx" in D.UNITS)))
    if FUSE["sukr"]:
        env["HDC_V41_SU_FUSE"] = f"{D.PARAMS['sun']},{D.PARAMS['sum']},{FUSE['sukr']}"
    r = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program_v41_fuse.py"), "--out", str(out), *extra],
                       capture_output=True, text=True, env=env)
    if r.returncode:
        raise SystemExit(f"hdc_program_v41_fuse failed:\n{r.stdout}\n{r.stderr}")
    r2 = subprocess.run([sys.executable, str(ROOT / "tools/hdc_images_v41x.py"), "--out", str(out),
                         "--hhw", str(D.PARAMS["hhw"]), "--mg", str(D.PARAMS["mg"])], capture_output=True, text=True,
                        env=env)
    if r2.returncode:
        raise SystemExit(f"hdc_images_v41x failed:\n{r2.stdout}\n{r2.stderr}")
    return r.stdout


_breakdown = D.breakdown
_issues = {}


def breakdown(trace, tags, cycles):
    """The campaign's breakdown, keeping the issue trace (cycle, pc, unit) and the tags for the side record."""
    issues, bd = _breakdown(trace, tags, cycles)
    _issues.setdefault("runs", []).append(dict(cycles=cycles, issues=issues, tags=list(tags)))
    return issues, bd


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--sukr", type=int, default=0)
    ap.add_argument("--subcast", type=int, default=0)
    ap.add_argument("--suret", type=int, default=0)
    a, rest = ap.parse_known_args()
    FUSE.update(sukr=a.sukr, subcast=a.subcast, suret=a.suret)
    # the pinned Verilator (as the vector-unit campaigns use): the PATH one (4.038) resolves the bench's
    # hierarchical references inside generate branches that are not built (the index pool's) and fails
    pinned = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin"
    if pinned.exists():
        os.environ["PATH"] = f"{pinned}:{os.environ.get('PATH', '')}"
    FUSE["verilator"] = subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout.strip()
    _swap()
    D.defines, D.images, D.breakdown = defines, images, breakdown
    D.TOOLS += [ROOT / "tools/hdc_program_v41_fuse.py", ROOT / "tools/hdc_isa_v41_fuse.py", ROOT / "tools/w11_su_fuse.py",
                ROOT / "tools/rtl_hdc_v41x_vec_kr_campaign.py", Path(__file__).resolve()]
    sys.argv = [sys.argv[0]] + rest
    rc = D.main()
    # annotate the record(s) the campaign wrote
    out = Path(rest[rest.index("--output") + 1]) if "--output" in rest else D.OUT
    if _issues:
        out.with_name(out.stem + ".issues.json").write_text(json.dumps(_issues) + "\n")
    for p in (out, out.with_name(out.stem + ".single.json")):
        if p.exists():
            rec = json.loads(p.read_text())
            rec["operator_fusion"] = dict(FUSE, swapped_sources={k + ".sv": v + ".sv" for k, v in SWAP.items()},
                                          fused_program=bool(FUSE["sukr"]),
                                          sources_sha256={f"rtl/hdc/v41x/{v}.sv": hashlib.sha256(
                                              (ROOT / f"rtl/hdc/v41x/{v}.sv").read_bytes()).hexdigest()
                                              for v in SWAP.values()})
            p.write_text(json.dumps(rec, indent=2) + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
