#!/usr/bin/env python3
"""S81 event TAPWIN-PORT-1105 (DIE-S81-65, COORD 2026-11-05 17:4x, slice_station cross-tap hold).

Adds clock.tap_window.per_port_ps (KW-FIX-4-SDC measured per-port kit window, gen_phys.tap_window_port_table) for the
OPEN slice_station types, from die_sta_related --kit-window-out on the S81 G50 die GRT proof (kit_window_g50_station.json
next to this script: TT+FF, ceil 1 ps, no margin).  Types with a SIGNED view keep the flat per_type_ps W_t (no entry =
byte-identical tap-window SDC).  An entry is refused if any port would RISE above the type's W_t.
Plan text is edited in place (only the tap_window block); every other byte is unchanged.

usage: delta_tapwin_port_1105.py PLAN_JSON [--check]
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIGNED = ("slice_station__t12", "slice_station__t20", "slice_station__t23", "slice_station__t7__cl945bc067")
NOTE = (" DIE-S81-65 TAPWIN-PORT-1105 (COORD 2026-11-05 17:4x): per_port_ps = measured per-port kit window (KW-FIX-4-SDC,"
        " die_sta_related --kit-window-out, S81 G50 die GRT proof, plan fbec14146454, TT+FF, ceil 1 ps, no margin) for the"
        " open slice_station types; signed t12/t20/t23/t7__cl945bc067 keep per_type_ps (byte-identical SDC). Station"
        " partitions moved by translation since G50 (+613.44/+319.68 um y): the die STA kit-contract check proves the table"
        " on the next S81 die proof; fallback = HB4 pad by construction on cross-tap ft bits.")


def main():
    plan = Path(sys.argv[1])
    s = plan.read_text()
    d = json.loads(s)
    tw = d["clock"]["tap_window"]
    if "per_port_ps" in tw:
        raise SystemExit("plan already has clock.tap_window.per_port_ps")
    tab = json.loads((HERE / "kit_window_g50_station.json").read_text())["per_port_ps"]
    W0, pt = float(tw["window_ps"]), tw.get("per_type_ps") or {}
    new = {}
    for t in sorted(tab):
        if t in SIGNED:
            continue
        if t not in d["partition_types"]:
            raise SystemExit(f"{t}: not a plan type")
        wt = float(pt.get(t, W0))
        rise = {p: v for p, v in tab[t].items() if float(v) > wt}
        if rise:
            raise SystemExit(f"{t}: ports would rise above W_t {wt:g}: {rise}")
        new[t] = {p: (int(v) if float(v).is_integer() else float(v)) for p, v in sorted(tab[t].items())}
    # text edit: the per_type_ps block ends with "\n   }\n  },\n  \"landing_network\"" (1-space plan indent)
    i = s.index('  "tap_window": {')
    j = s.index('\n   }\n  },', s.index('"per_type_ps": {', i))
    body = ",\n   \"per_port_ps\": {\n" + ",\n".join(
        f"    \"{t}\": {{\n" + ",\n".join(f"     \"{p}\": {v}" for p, v in ports.items()) + "\n    }"
        for t, ports in new.items()) + "\n   }"
    s2 = s[:j + len('\n   }')] + body + s[j + len('\n   }'):]
    # note: append once
    m = re.search(r'(  "tap_window": \{\n   "window_ps": [^\n]*\n   "note": "(?:[^"\\]|\\.)*)(")', s2)
    s2 = s2[:m.end(1)] + NOTE + s2[m.end(1):]
    d2 = json.loads(s2)
    assert d2["clock"]["tap_window"]["per_port_ps"] == new
    d2["clock"]["tap_window"].pop("per_port_ps"); d2["clock"]["tap_window"]["note"] = tw["note"]
    assert d2 == d, "only per_port_ps + note may change"
    print(f"TAPWIN-PORT-1105: {len(new)} types, {sum(len(v) for v in new.values())} ports; skipped signed {list(SIGNED)}")
    if "--check" not in sys.argv:
        plan.write_text(s2)


if __name__ == "__main__":
    main()
