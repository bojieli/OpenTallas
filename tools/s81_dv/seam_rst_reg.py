#!/usr/bin/env python3
"""S81-SEAM-RST-1115 (lever 3): rewrite the locally gated seam writer clear to the registered per-chunk clear.

ot_pl_seam_w_plr #(... .RSREG(1)) -> ot_pl_seam_w_plrc (same ports; rtl/common/landed_parent/ot_pl_seam.sv).
RSREG(0) instances (one chunk, combinational e) are left unchanged.  Usage: seam_rst_reg.py FILE.sv [FILE.sv ...]
(in place, via temp file + rename); prints the number of instances rewritten per file.  Also a library: rewrite(text)."""
import os, re, sys

PAT = re.compile(r'\bot_pl_seam_w_plr(\s*#\([^;]*?\.RSREG\(1\))')


def rewrite(text):
    return PAT.subn(lambda m: 'ot_pl_seam_w_plrc' + m.group(1), text)


def main(argv):
    for f in argv:
        txt = open(f).read()
        new, n = rewrite(txt)
        if n:
            tmp = f + '.srr.tmp'
            open(tmp, 'w').write(new)
            os.replace(tmp, f)
        print(f'{f}: {n} ot_pl_seam_w_plr RSREG(1) -> ot_pl_seam_w_plrc')


if __name__ == '__main__':
    main(sys.argv[1:])
