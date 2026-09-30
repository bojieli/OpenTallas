#!/usr/bin/env python3
"""Images for a user's SECOND decode step (W11 die multi-user gate).

tools/hdc_program_v41.py decodes the last token of the oracle prompt (optionally
cycled to --context N tokens).  A user's next step decodes the token its first
step produced, one position later: the prompt extended by that token.  This
wrapper runs hdc_program_v41 unchanged, in process, with the prompt source
replaced by the extended prompt, then hdc_images_v41x, exactly as
rtl_hdc_v41x_decode_campaign.images() runs them (same environment).  The ISA
model and the golden prefill of the extended prompt produce the expectations,
so a die run that carries the user's state over from its first step is checked
against an independent recomputation.

    python3 tools/w11_die_ring_mu_images.py --out DIR [--context N] --append TOK [--append TOK ...]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--context", type=int, help="cycle the oracle prompt to N tokens first (as --context)")
    ap.add_argument("--append", type=int, action="append", required=True, help="token(s) the user generated")
    a = ap.parse_args()
    import rtl_hdc_v41x_decode_campaign as core
    import rtl_chip_v41x_die_smoke as ds
    ds.setup("dpi")
    env = dict(os.environ, HDC_SW=str(core.I.SU_LANES), HDC_V41_ARITH=core.arith(),
               HDC_V41_IDX_FUSED=str(int("idx" in core.UNITS)))
    code = (
        "import sys; sys.path.insert(0, {tools!r}); sys.argv = ['hdc_program_v41.py', '--out', {out!r}, '--hbm']\n"
        "import hdc_program_v41 as hp\n"
        "prompt, expected = hp.V.prompt_and_expected()\n"
        "ctx = {ctx!r}\n"
        "prompt = list(prompt)\n"
        "if ctx: prompt = (prompt * (-(-ctx // len(prompt))))[:ctx]\n"
        "ext = prompt + {app!r}\n"
        "hp.V.prompt_and_expected = lambda: (ext, expected)\n"
        "raise SystemExit(hp.main())\n").format(tools=str(ROOT / "tools"), out=str(a.out), ctx=a.context,
                                               app=list(a.append))
    a.out.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stderr.write(r.stderr)
        return r.returncode
    r2 = subprocess.run([sys.executable, str(ROOT / "tools/hdc_images_v41x.py"), "--out", str(a.out),
                         "--hhw", str(core.PARAMS["hhw"]), "--mg", str(core.PARAMS["mg"])],
                        capture_output=True, text=True, env=env)
    sys.stdout.write(r2.stdout)
    if r2.returncode:
        sys.stderr.write(r2.stderr)
    return r2.returncode


if __name__ == "__main__":
    raise SystemExit(main())
