#!/usr/bin/env python3
"""hold_sdc_check: HOLD-SDC-1116.  A kit fails when a repair_timing -hold stage can read a different SDC than sign-off.

Sign-off STA reads the kit's constraint.sdc (signoff.py discover: kit/constraint.sdc).  The kit config.mk records its sha256 as
OT_SIGNOFF_SDC_SHA; hold_sdc_guard.tcl (copied into every kit, sourced by hold_pad_hb4.tcl and by the stand-alone hold stages) hashes the golden SDC
at every repair_timing -hold and re-applies the golden set_input_delay / set_output_delay (-min / -max) the session lacks.  This check judges the kit
files before any run:

  HOLD-SDC-NOHASH      config.mk has no OT_SIGNOFF_SDC_SHA, or it is not the sha256 of constraint.sdc (stale: the SDC changed after config.mk)
  HOLD-SDC-NOGUARD     a kit file with a repair_timing -hold call neither sources hold_sdc_guard.tcl / hold_pad_hb4.tcl nor is one of them
  HOLD-SDC-FOREIGN     a kit stage reads an SDC other than constraint.sdc (read_sdc of a literal other file) without the guard
  HOLD-SDC-HASH        compare mode: the repair-stage SDC and the sign-off SDC differ in sha256

CLI: hold_sdc_check.py kit KITDIR | compare REPAIR_SDC SIGNOFF_SDC      exit 0 clean, 1 findings."""
import hashlib
import re
import sys
from pathlib import Path

GUARD = "hold_sdc_guard.tcl"
HOLD_RE = re.compile(r"repair_timing[^\n#]*-hold|repair_timing_helper\s+-hold")
READ_RE = re.compile(r"^\s*read_sdc\s+(?:-\S+\s+\S+\s+)*(\S+)", re.M)
SHA_RE = re.compile(r"^\s*export\s+OT_SIGNOFF_SDC_SHA\s*=\s*([0-9a-f]+)\s*$", re.M)
EXT = (".tcl", ".sh", ".mk", ".py")
SELF_OK = {GUARD, "hold_pad_hb4.tcl"}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def strip_comments(t):
    return "\n".join(l for l in t.splitlines() if not l.lstrip().startswith("#"))


def kit_findings(kit):
    kit = Path(kit)
    out = []
    sdc = kit / "constraint.sdc"
    if not sdc.is_file():
        return out                                       # not a gen_phys type kit: nothing to compare
    cfg = kit / "config.mk"
    m = SHA_RE.search(cfg.read_text()) if cfg.is_file() else None
    if not m or not sha256(sdc).startswith(m.group(1)) or len(m.group(1)) < 16:
        out.append(f"HOLD-SDC-NOHASH {kit.name}: config.mk OT_SIGNOFF_SDC_SHA {m.group(1)[:16] if m else 'absent'} is not the sha256 of constraint.sdc "
                   f"({sha256(sdc)[:16]}): the repair stages and sign-off could read different constraints")
    for f in sorted(kit.iterdir()):
        if not f.is_file() or f.suffix not in EXT or f.name in SELF_OK:
            continue
        try:
            body = strip_comments(f.read_text(errors="replace"))
        except OSError:
            continue
        if HOLD_RE.search(body):
            guarded = GUARD in body or "hold_pad_hb4.tcl" in body
            if not guarded:
                out.append(f"HOLD-SDC-NOGUARD {kit.name}/{f.name}: repair_timing -hold without hold_sdc_guard.tcl / hold_pad_hb4.tcl: "
                           f"the stage may repair against IO constraints that sign-off does not use")
                continue
        for r in READ_RE.findall(body):
            r = r.strip("{}\"'")
            if r.startswith("$") or r.startswith("[") or not HOLD_RE.search(body):
                continue
            if Path(r).name not in ("constraint.sdc", "core_taps_ff.sdc", "golden.sdc") and not (GUARD in body or "hold_pad_hb4.tcl" in body):
                out.append(f"HOLD-SDC-FOREIGN {kit.name}/{f.name}: hold stage reads {r}, not the sign-off constraint.sdc")
    return out


def compare(repair_sdc, signoff_sdc):
    a, b = sha256(repair_sdc), sha256(signoff_sdc)
    return [] if a == b else [f"HOLD-SDC-HASH repair-stage SDC {repair_sdc} sha {a[:16]} != sign-off SDC {signoff_sdc} sha {b[:16]}"]


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if len(a) == 2 and a[0] == "kit":
        f = kit_findings(a[1])
    elif len(a) == 3 and a[0] == "compare":
        f = compare(a[1], a[2])
    else:
        print(__doc__)
        return 2
    print("\n".join(f) if f else "hold_sdc_check: clean")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
