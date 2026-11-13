#!/usr/bin/env python3
"""Interior pin-site census of every partition type (HEAD-96 11-13, GEOM-VIS-14 / KIT-WAVE GRT-0080 'Invalid pin placement':
hd_spn_end arst_n and rst_o_2 both at M7 (578.4, 1209.632), hd_spn_eshim_rx arst_n and rst_o_0 at (46.99, 8.22)).

Collects the interior pins the kit io.tcl places from the plan (gen_phys: clock / reset taps incl. arst_n and start_i,
reset wavefront outs rst_o_<k> / start_o_<k>, ID / count strap sites, bound reset-spine sites, landing_contract pins on
track) and reports two DIFFERENT pins on one layer at one location (<= SAME_UM): global routing refuses such a pair.

    python3 -I tools/die_plan/pin_sites.py PLAN [--types a,b]      (exit 1 on any duplicate)
check.py runs check(P) as G0 class pin_sites (duplicates ERROR, not computable WARN)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
SAME_UM = 1e-3


def type_pins(P, tn):
    """[(name, layer, x, y, source)] interior plan pins of one type, as gen_phys io.tcl places them."""
    import gen_phys as GP
    import landing_contract as LC
    top = P.layer_budget["partition_signal_max"]
    t = P.types[tn]
    out = [(n, top, float(x), float(y), "tap") for n, x, y in GP.tap_pins(P, tn)]
    out += [(n, top, float(x), float(y), "reset_out") for n, x, y in GP.reset_out_pins(P, tn)]
    out += [(n, ln, x, y, "strap") for n, ln, x, y in GP.strap_pin_sites(P, tn)]
    out += [(n, ln, x, y, "reset_spine") for n, ln, x, y in GP.reset_spine_pin_sites(P, tn)]
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    edge = {e["port"] for e in (t.get("clock") or {}).get("edge_clocks", [])}
    for p in lc.get("pins", []):
        if p["name"] in edge:
            continue
        x, y = LC.on_track(P, p["layer"], *p["xy_um"])
        out.append((p["name"], p["layer"], float(x), float(y), "landing"))
    return out


def duplicates(P, tn):
    """[(layer, x, y, [names])] sites that carry two or more different pins."""
    sites = {}
    for n, ln, x, y, src in type_pins(P, tn):
        key = (ln, round(x / SAME_UM), round(y / SAME_UM))
        sites.setdefault(key, {})[n] = (x, y, src)
    rows = []
    for (ln, _, _), d in sorted(sites.items()):
        if len(d) > 1:
            x, y, _ = next(iter(d.values()))
            rows.append((ln, x, y, sorted(f"{n} ({v[2]})" for n, v in d.items())))
    return rows


def check(P, types=None):
    """(errors, warnings): an error for every type with two different interior pins on one site; a warning for a type
    whose pin set the kit generator itself cannot compute (reported by its own gates)."""
    errs, warns = [], []
    for tn in sorted(types or P.types):
        if P.types[tn].get("hard"):
            continue
        try:
            dups = duplicates(P, tn)
        except Exception as e:                       # a type the kit generator itself refuses is reported elsewhere
            warns.append(f"type {tn}: pin-site census not computable ({type(e).__name__}: {e})")
            continue
        for ln, x, y, names in dups:
            errs.append(f"type {tn}: {len(names)} pins on one {ln} site ({x:.4f}, {y:.4f}): {', '.join(names)} "
                        f"(GRT-0080 'Invalid pin placement')")
    return errs, warns


def main(argv):
    import schema as S
    if not argv:
        print(__doc__); return 2
    types = None
    if "--types" in argv:
        types = argv[argv.index("--types") + 1].split(",")
    P = S.Plan(json.loads(Path(argv[0]).read_text()), argv[0])
    errs, warns = check(P, types)
    print("\n".join(errs + ["WARN " + w for w in warns])); print(json.dumps(dict(duplicates=len(errs), warnings=len(warns))))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
