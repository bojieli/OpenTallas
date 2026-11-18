#!/usr/bin/env python3
"""TAP-CAP-CENSUS (S81-SERDES-GEN 11-17, FABLE-PD-S81-2100 finding 4): per-tap clock sinks of a kit read from its CTS log, against the cap.

usage: tap_cap_census.py KIT_DIR_OR_4_1_cts.log [--cap N] [--json]

Reads the last OT_TAP_BALANCE iteration line of the CTS log ("clk_t42=554(538-715,6502) ..." = mean ps (min-max, sinks)) and the cap from
the kit config.mk (export OT_TAP_MAX_SINKS) unless --cap is given.  Prints every tap over the cap with the number of added taps it needs
(ceil(sinks / cap) - 1 more); exit 1 when any tap is over, 0 otherwise, 2 when no census line / no cap is found.  Measurement only.
"""
import json
import math
import re
import sys
from pathlib import Path

TAP = re.compile(r"\b(clk(?:_t\d+)?)=([-\d.]+)\(([-\d.]+)-([-\d.]+),(\d+)\)")


def find_log(p):
    p = Path(p)
    if p.is_file():
        return p
    for g in sorted(p.glob("run/logs/asap7/*/base/4_1_cts.log")):
        return g
    raise SystemExit(f"no 4_1_cts.log under {p}")


def census(text):
    """{tap: sinks} of the last OT_TAP_BALANCE it<N> line"""
    lines = [l for l in text.splitlines() if l.startswith("OT_TAP_BALANCE it")]
    if not lines:
        return {}
    return {m.group(1): int(m.group(5)) for m in TAP.finditer(lines[-1])}


def cap_of(kit):
    cfg = Path(kit) / "config.mk"
    if not cfg.is_file():
        return None
    m = re.search(r"^export\s+OT_TAP_MAX_SINKS\s*=\s*(\d+)\s*$", cfg.read_text(), re.M)
    return int(m.group(1)) if m else None


def over(sinks, cap):
    return {t: dict(sinks=n, add_taps=max(1, math.ceil(n / cap) - 1)) for t, n in sorted(sinks.items()) if n > cap}


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    cap = None
    if "--cap" in argv:
        cap = int(argv[argv.index("--cap") + 1])
        args = [a for a in args if a != str(cap)]
    kit = Path(args[0])
    log = find_log(kit)
    if cap is None:
        cap = cap_of(kit if kit.is_dir() else kit.parents[5] if len(kit.parents) > 5 else kit)
    sinks = census(log.read_text(errors="replace"))
    if not sinks or not cap:
        print(f"TAP_CAP_CENSUS no census line or no cap (taps {len(sinks)}, cap {cap})")
        return 2
    bad = over(sinks, cap)
    top = sorted(sinks.items(), key=lambda kv: -kv[1])[:3]
    if "--json" in argv:
        print(json.dumps(dict(cap=cap, taps=len(sinks), max=top[0], over=bad)))
    print(f"TAP_CAP_CENSUS cap {cap}: {len(sinks)} taps, max {top[0][0]}={top[0][1]}, over {len(bad)}"
          + "".join(f"; {t}: {v['sinks']} sinks -> add {v['add_taps']} tap(s)" for t, v in bad.items()))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
