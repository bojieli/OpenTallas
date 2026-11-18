#!/usr/bin/env python3
"""Keep-or-restore of the hold-after-TT step (HOLD-AFTER-TT 11-17).  usage: hold_after_tt_keep.py BEFORE.txt AFTER.txt [SETUP_TOL_PS]
each file: "<FF hold wns ps> <TT setup wns ps>" (postcts_gate.tcl, GRT RC).  exit 0 = keep the re-repaired DB: FF hold wns improved by > 0.01 ps
and TT setup wns not below its before value by more than the tolerance (the setup guard).  exit 1 = restore.  Prints one OT_HOLD_AFTER_TT line."""
import sys


def decide(before, after, tol=0.5, eps=0.01):
    if before is None or after is None:
        return False, "missing number (before %s, after %s)" % (before, after)
    (h0, s0), (h1, s1) = before, after
    if s1 < s0 - tol:
        return False, "TT setup fell %.2f -> %.2f (guard %.2f ps)" % (s0, s1, tol)
    if h1 <= h0 + eps:
        return False, "FF hold did not improve (%.2f -> %.2f)" % (h0, h1)
    return True, "FF hold %.2f -> %.2f, TT setup %.2f -> %.2f" % (h0, h1, s0, s1)


def read(path):
    try:
        a = open(path).read().split()
        return float(a[0]), float(a[1])
    except (OSError, ValueError, IndexError):
        return None


if __name__ == "__main__":
    ok, why = decide(read(sys.argv[1]), read(sys.argv[2]), float(sys.argv[3]) if len(sys.argv) > 3 else 0.5)
    print("OT_HOLD_AFTER_TT %s: %s" % ("KEEP re-repaired" if ok else "RESTORE before", why))
    sys.exit(0 if ok else 1)
