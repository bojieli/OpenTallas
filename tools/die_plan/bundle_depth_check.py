#!/usr/bin/env python3
"""BUNDLE-DEPTH (COORD 11-20, FABLE-FIX-S81-SLICEC): the ports of one valid / data bundle carry ONE relay depth.

plan_j3b / D8i gave dsdv_slice_c1x_C t9 / t10 xr.eg_v D1, eg_c D1, eg_d D2 and dsdv_slice_iq_C t1 cap.cfg_d D1, cfg_v D2:
the 810-um step fell between the pins of one bundle, so the data landed one cycle after its valid.  The strict bind and
LATCHECK both passed it (LATCHECK prices die lanes, not type-internal core-to-core links).  relay_depth.py (main 1889edd4e1e)
now aligns the bundles it generates; this check stops any plan row set that still splits one.

Rule: partition_types[T].relay_depth rows of one (inst, side) whose ports share a stem and end in a bundle suffix
(<stem>_v / _d / _c / _a / _m / _s / _sv / _si: valid, data, control, address, mask, select, the xrt / egg port families)
must carry one D (the largest D over the bit runs of a port).  An unequal set is a FUNCTIONAL error at bind --strict.
Limit: a bundle port with NO row (D 0) next to a port with a row is not visible here (the plan holds rows only); the
generator (relay_depth.py ALIGN_GROUP) covers that case.

    python3 -I bundle_depth_check.py PLAN.json     (exit 1 on any unequal bundle)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BUNDLE_PORT = re.compile(r"^(?P<stem>.+?)_(?P<sfx>v|d|c|a|m|s|sv|si)$")


def check(plan):
    """-> list of error strings, one per unequal bundle"""
    errors = []
    for tn, t in sorted((plan.get("partition_types") or {}).items()):
        groups = defaultdict(dict)
        for r in t.get("relay_depth") or []:
            m = BUNDLE_PORT.match(str(r.get("port", "")))
            if not m:
                continue
            key = (r.get("inst"), r.get("side", "source"), m["stem"])
            groups[key][r["port"]] = max(groups[key].get(r["port"], 0), int(r.get("D", 0)))
        for (inst, side, stem), ports in sorted(groups.items()):
            if len(set(ports.values())) > 1:
                desc = ", ".join(f"{p} D{d}" for p, d in sorted(ports.items()))
                errors.append(f"BUNDLE-DEPTH {tn}: {inst} {side} bundle {stem}_*: {desc} -- one valid / data bundle at unequal "
                              f"relay depth lands data and valid on different cycles (functional); give every port the "
                              f"largest D ({max(ports.values())})")
    return errors


def gate(plan):
    """bind --strict hook -> (errors, summary); always blocking: an unequal bundle is functionally wrong data"""
    errors = check(plan)
    return errors, dict(gate="BLOCKING", errors=len(errors), list=errors[:50])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    errors = check(json.loads(Path(argv[0]).read_text()))
    for e in errors:
        print(e)
    print(f"BUNDLE_DEPTH unequal {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
