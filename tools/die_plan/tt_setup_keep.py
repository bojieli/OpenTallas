#!/usr/bin/env python3
"""Keep-or-restore decision of the TT setup repair step (COORD r268/FABLE-FIX-HEAD-TYPES, hd_serdes sd2: in-session -43.92, reloaded DB
-127.85, before -55.88).  usage: tt_setup_keep.py REPAIR_LOG MEASURE_LOG
REPAIR_LOG holds 'OT_TT_SETUP_REPAIR before TT setup wns W tns T' (the input DB, freshly loaded); MEASURE_LOG holds
'OT_TT_SETUP_REPAIR measure TT setup wns W tns T' read from the WRITTEN repaired DB reloaded in a new session (tt_setup_repair.tcl with
OT_TT_SETUP_MEASURE=1), so the number is what every later reader gets, not the in-session one.
exit 0 = keep the repaired DB: reloaded WNS and TNS both no worse than before and at least one better by > 0.01 ps.  exit 1 = restore
the before DB (also when a number is missing).  Prints one OT_TT_SETUP_KEEP line."""
import re
import sys

PAT = r"OT_TT_SETUP_REPAIR {tag} TT setup wns (-?[0-9.]+) tns (-?[0-9.]+)"


def read(path, tag):
    try:
        txt = open(path).read()
    except OSError:
        return None
    m = re.findall(PAT.format(tag=tag), txt)
    return (float(m[-1][0]), float(m[-1][1])) if m else None


def decide(before, after, eps=0.01):
    if before is None or after is None:
        return False, "missing number (before %s, reloaded %s)" % (before, after)
    (w0, t0), (w1, t1) = before, after
    if w1 < w0 - eps or t1 < t0 - eps:
        return False, "reloaded DB is worse (wns %.2f -> %.2f, tns %.2f -> %.2f)" % (w0, w1, t0, t1)
    if w1 > w0 + eps or t1 > t0 + eps:
        return True, "reloaded DB improved (wns %.2f -> %.2f, tns %.2f -> %.2f)" % (w0, w1, t0, t1)
    return False, "no change on the reloaded DB (wns %.2f, tns %.2f)" % (w0, w1)


def main(argv):
    ok, why = decide(read(argv[1], "before"), read(argv[2], "measure"))
    print("OT_TT_SETUP_KEEP %s: %s" % ("KEEP repaired" if ok else "RESTORE before", why))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
