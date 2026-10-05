#!/usr/bin/env python3
"""Lever item 3: the SU operator-fusion core fork (`_kr`) with its lint failures removed in a successor copy.

    python3 tools/dsrom_lever_su_kr.py lint  [--orig | --pinned] [--cmd-json P]   the campaign's own lint step
            (default: the successors; --orig: the `_kr` fork as committed; --pinned: the original core, no fork)
    python3 tools/dsrom_lever_su_kr.py run --sukr K [--subcast B --suret R] [--pregen DIR] [decode-campaign args,
            e.g. --units he,me,su --single-only --output OUT.json]
    python3 tools/dsrom_lever_su_kr.py images --pregen DIR --sukr K [same campaign args]

`images` runs the campaign's image step only (program, ISA model, golden: needs `tokenizers`, so run it where that is
installed) and saves the image directory + the ISA model's stdout to DIR; `run --pregen DIR` then uses DIR in place
of the image step (a host without `tokenizers`).  Everything else in the campaign is unchanged.

Wraps tools/w11_su_fuse_die.py (unchanged), which wraps tools/rtl_hdc_v41x_decode_campaign.py (unchanged), and
after its source swap replaces two files by their lint successors (same module names; a source list picks one):
  rtl/hdc/v41x/ot_hdc_core_v41x_kr.sv  -> rtl/dsrom_sys/levers/ot_hdc_core_v41x_kr_lv.sv
  rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv -> rtl/dsrom_sys/levers/ot_hdc_v41x_me_adapt_lv.sv
The campaign's lint (LINT_FLAGS, -Wall) is what made the matched fused/unfused pairs `fail` overall
(results/rtl/w11_main_compatible_20261001/u00.json verilator_lint; KR_strict_lint.json).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
LV = ROOT / "rtl/dsrom_sys/levers"
SUCC = {"ot_hdc_core_v41x_kr.sv": LV / "ot_hdc_core_v41x_kr_lv.sv",
        "ot_hdc_v41x_me_adapt.sv": LV / "ot_hdc_v41x_me_adapt_lv.sv"}


def install(D, W, succ=True):
    pinned = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin"
    if pinned.exists():
        os.environ["PATH"] = f"{pinned}:{os.environ.get('PATH', '')}"
    W._swap()
    if succ:
        n = 0
        for k, p in enumerate(D.RTL):
            if p.name in SUCC:
                D.RTL[k] = SUCC[p.name]
                n += 1
        assert n == len(SUCC), n


def lint(orig=False, pinned=False, cmd_json=None):
    import json
    import subprocess
    import rtl_hdc_v41x_decode_campaign as D
    import w11_su_fuse_die as W
    D.UNITS = ("he", "me", "su")
    if pinned:
        p = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin"
        if p.exists():
            os.environ["PATH"] = f"{p}:{os.environ.get('PATH', '')}"
    else:
        install(D, W, succ=not orig)
    I = D.I
    cmd = ["verilator", "--lint-only", *D.LINT_FLAGS, "--top-module", "ot_hdc_core_v41x",
           f"-GSW={I.SU_LANES}", f"-GHHW={D.PARAMS['hhw']}", f"-GMG={D.PARAMS['mg']}",
           f"-GSUN={D.PARAMS['sun']}", f"-GSUM={D.PARAMS['sum']}",
           *[f"-GX_{u.upper()}={2 if u == 'idx' and D.IDX_POOL else int(u in D.UNITS)}" for u in D.X_UNITS],
           "-Wno-TIMESCALEMOD", f"-I{D.SVH.parent}", *map(str, D.rtl_sources())]
    cmd[0] = subprocess.run(["which", "verilator"], capture_output=True, text=True).stdout.strip() or cmd[0]
    if cmd_json:
        Path(cmd_json).write_text(json.dumps(cmd, indent=1) + "\n")
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(" ".join(cmd))
    print(p.stdout + p.stderr)
    print("RC", p.returncode)
    return p.returncode


class _StopAfterImages(Exception):
    pass


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "lint":
        cj = sys.argv[sys.argv.index("--cmd-json") + 1] if "--cmd-json" in sys.argv else None
        return lint("--orig" in sys.argv, "--pinned" in sys.argv, cj)
    mode = sys.argv[1]
    assert mode in ("run", "images")
    argv = sys.argv[2:]
    pregen = None
    if "--pregen" in argv:
        i = argv.index("--pregen")
        pregen = Path(argv[i + 1]).resolve()
        del argv[i:i + 2]
    assert mode == "run" or pregen is not None
    sys.argv = [sys.argv[0]] + argv
    import shutil
    import subprocess as SP
    import rtl_hdc_v41x_decode_campaign as D
    import w11_su_fuse_die as W
    orig_swap = W._swap
    orig_images = W.images

    if mode == "images":
        def images(out, *extra, lanes=None):
            stdout = orig_images(out, *extra, lanes=lanes)
            if pregen.exists():
                shutil.rmtree(pregen)
            shutil.copytree(out, pregen)
            (pregen / "_isa_stdout.txt").write_text(stdout)
            (pregen / "_image_args.json").write_text(__import__("json").dumps(dict(
                extra=list(extra), lanes=lanes, fuse=dict(W.FUSE), params=dict(D.PARAMS), units=list(D.UNITS),
                arith=D.arith())) + "\n")
            raise _StopAfterImages

        class _NoLint:   # the image step needs no lint; the epyc run does it
            def __getattr__(self, k):
                return getattr(SP, k)

            @staticmethod
            def run(cmd, *a, **k):
                if "--lint-only" in cmd:
                    return SP.CompletedProcess(cmd, 0, "", "")
                return SP.run(cmd, *a, **k)
        D.subprocess = _NoLint()
        W.images = images
    elif pregen is not None:
        def images(out, *extra, lanes=None):
            meta = __import__("json").loads((pregen / "_image_args.json").read_text())
            assert meta["extra"] == list(extra) and meta["lanes"] == lanes and meta["fuse"]["sukr"] == W.FUSE["sukr"] \
                and meta["params"] == dict(D.PARAMS) and meta["units"] == list(D.UNITS), (meta, extra, lanes, W.FUSE)
            shutil.copytree(pregen, out)
            return (pregen / "_isa_stdout.txt").read_text()
        W.images = images

    def swap():
        orig_swap()
        for k, p in enumerate(D.RTL):
            if p.name in SUCC:
                D.RTL[k] = SUCC[p.name]
        assert sum(p.parent == LV for p in D.RTL) == len(SUCC)
    W._swap = swap
    D.TOOLS.append(Path(__file__).resolve())
    try:
        rc = W.main()
    except _StopAfterImages:
        print("images saved to", pregen)
        return 0
    return rc


if __name__ == "__main__":
    sys.exit(main())
