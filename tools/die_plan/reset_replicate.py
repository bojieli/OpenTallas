#!/usr/bin/env python3
"""S81-COLGEN-1 11-14 (FABLE-TYPES-S81-COL C2): per-region replication of a reset / flush fan-out driver in a bound type.

Why: in col_h9_r2 one register (`u_d7_6_Y`, last stage of a 7-stage 1-bit ot_dp_dly, 114 loads over the whole partition)
launches the flush / reset of every core in ONE cycle: worst setup endpoint u_e13e.u_view.u_c/rst_n_pin, GRT -360 ps.

What: plan `partition_types[T].reset_replicate` = [{"driver": "u_d7_6_Y"            exact bound instance name, or
                                                    "driver_re": "u_d\\d+_6_Y",      fullmatch regex,
                                                    "region_re": "^u_(.*?)(?:_\\d+|_sk)?$",   optional, group 1 = region
                                                    "grid_um": 300,                  optional, see below
                                                    "optional": true}]               a type without the driver is a no-op
The driver `ot_dp_dly #(.W(1), .D(n)) u_x (.clk, .d(S), .q(x))` becomes

    ot_dp_dly #(.W(1), .D(n-1)) u_x (.clk, .d(S), .q(x))          common part (absent when n == 1: S feeds the copies)
    ot_dp_rrelay u_x_r<k> (.clk(clk), .d(x[0] | S), .q(x_r<k>))   one kept flop per region (keep_hierarchy: no opt_merge)

and every load of x is re-pointed to the copy of ITS region.  Total stages from S to every load stay n: LATENCY IS EQUAL
(checked here, again by bind_verify's transport model: ot_dp_rrelay counts 1).  A load outside any instance (an `assign`)
gets the region "rest".  Region of a sink instance: with grid_um and a position for the instance (hard core origin from the
plan, `positions`) the grid cell "g<ix>_<iy>" = core-tap neighbourhood; else the regex group (default: the instance name
without its trailing relay index _<n> / _sk, so the legs u_y_rt_24a_0.._5 of one relay group share one copy).
W must be 1 (a reset / flush level).  Pure text transform of the module `emit_type` returns; nothing happens unless the plan
type carries the key (absent = byte-identical).
usage: reset_replicate.py BOUND.sv SPEC.json [--positions POS.json] [-o OUT.sv]   (smoke / kit use)
       reset_replicate.py plan PLAN.json OUT.json TYPE_RE --driver-re RE [--grid-um N] [--region-re RE] [--optional]
           (writes the plan key partition_types[T].reset_replicate on every type matching TYPE_RE)
"""
import json
import re
import sys

DLY = re.compile(r"^(?P<ind>\s*)ot_dp_dly\s*#\(\s*\.W\((?P<W>\d+)\)\s*,\s*\.D\((?P<D>\d+)\)\s*\)\s+(?P<inst>\S+)\s*"
                 r"\(\s*\.clk\((?P<clk>[^)]*)\)\s*,\s*\.d\((?P<d>.*)\)\s*,\s*\.q\((?P<q>\w+)\)\s*\)\s*;(?P<tail>.*)$")
HDR = re.compile(r"^\s*(?P<mod>[A-Za-z_]\w*)\s*(?:#\(.*\))?\s+(?P<inst>\\?[\w$]+)\s*\(\s*$")
DEFAULT_REGION_RE = r"^(.*?)(?:_\d+|_sk)?$"
CELL = "ot_dp_rrelay"


class ReplicateError(ValueError):
    pass


def _sid(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def _region_of(inst, spec, positions):
    grid = spec.get("grid_um")
    if grid and positions and inst in positions:
        x, y = positions[inst]
        return f"g{int(x // grid)}_{int(y // grid)}"
    m = re.match(spec.get("region_re") or DEFAULT_REGION_RE, inst)
    if not m:
        raise ReplicateError(f"region_re {spec.get('region_re')!r} does not match sink instance {inst}")
    return _sid(m.group(1 if m.groups() else 0))


def apply(text, specs, positions=None):
    """text of one bound module -> (new text, [report row per replicated driver]).  Raises ReplicateError."""
    lines = text.split("\n")
    report = []
    for spec in specs:
        drv, drv_re = spec.get("driver"), spec.get("driver_re")
        if not drv and not drv_re:
            raise ReplicateError("reset_replicate entry needs driver or driver_re")
        hits = []
        for i, ln in enumerate(lines):
            m = DLY.match(ln)
            if m and (m["inst"] == drv if drv else re.fullmatch(drv_re, m["inst"])):
                hits.append((i, m))
        if not hits and spec.get("optional"):
            report.append(dict(driver=drv or drv_re, copies=0, note="driver absent in this type (optional)"))
            continue
        if not hits:
            raise ReplicateError(f"reset_replicate driver {drv or drv_re!r}: no ot_dp_dly instance of that name")
        for i, m in hits:
            lines, row = _one(lines, i, m, spec, positions)
            report.append(row)
    return "\n".join(lines), report


def _one(lines, di, m, spec, positions):
    W, D, inst, q, dexpr, clk = int(m["W"]), int(m["D"]), m["inst"], m["q"], m["d"], m["clk"].strip()
    if W != 1:
        raise ReplicateError(f"{inst}: W={W}; only a 1-bit reset / flush level is replicated")
    use = re.compile(r"\b" + re.escape(q) + r"\b")
    decl = re.compile(r"^\s*wire\s*(?:\[[^\]]*\])?\s*" + re.escape(q) + r"\s*;")
    di_decl, cur, uses = None, None, []        # uses: (line index, enclosing instance or None)
    for i, ln in enumerate(lines):
        h = HDR.match(ln)
        if h and not ln.lstrip().startswith(("assign", "wire", "//", "ot_dp_")):
            cur = h["inst"]
        elif ln.strip().startswith(");"):
            cur = None
        if i == di:
            continue
        if decl.match(ln):
            di_decl = i
            continue
        if use.search(ln):
            uses.append((i, None if ln.lstrip().startswith("assign") else cur))
    if not uses:
        raise ReplicateError(f"{inst}: q wire {q} has no load")
    regions = {}
    for i, c in uses:
        regions.setdefault("rest" if c is None else _region_of(c, spec, positions), []).append(i)
    if len(regions) < 2:
        return lines, dict(driver=inst, depth=D, regions=len(regions), copies=0, loads=len(uses), note="one region: unchanged")
    names = {r: f"{inst}_r{k}" for k, r in enumerate(sorted(regions))}
    src = f"{q}[0]" if D > 1 else dexpr
    new = []
    for r in sorted(regions):
        wn = names[r].replace("u_", "", 1) if names[r].startswith("u_") else names[r]
        for i in regions[r]:
            lines[i] = use.sub(wn, lines[i])
        new.append(f"    wire [0:0] {wn};")
        new.append(f"    {CELL} {names[r]} (.clk({clk}), .d({src}), .q({wn}[0]));  // S81-COLGEN-1 C2: region {r}"
                   f" ({len(regions[r])} load(s)); {D} stage(s) total")
    if D > 1:
        lines[di] = (f"{m['ind']}ot_dp_dly #(.W(1), .D({D - 1})) {inst} (.clk({clk}), .d({dexpr}), .q({q}));"
                     f"{m['tail']}  // S81-COLGEN-1: common part, last stage replicated per region")
    else:
        lines[di] = f"{m['ind']}// S81-COLGEN-1: {inst} replaced by {len(regions)} region copies (1 stage, same d)"
        if di_decl is not None:
            lines[di_decl] = ""
    lines[di + 1:di + 1] = new
    # equal latency: every load sees (D-1 common) + 1 copy = D stages
    row = dict(driver=inst, depth=D, common_depth=D - 1, copy_depth=1, regions=len(regions), copies=len(regions),
               loads=len(uses), region_names=sorted(regions), loads_per_region={r: len(v) for r, v in sorted(regions.items())})
    return lines, row


def positions_from_plan(t):
    """{bound instance name: (x, y)} of a plan type's hard cores ('u_' + last component of the plan instance path)."""
    out = {}
    for c in (t.get("hard_cores") or []):
        o = c.get("origin_um")
        if o and c.get("inst"):
            out["u_u_" + c["inst"].split(".")[-1].replace("u_", "", 1)] = (o[0], o[1])
            out["u_" + c["inst"].split(".")[-1]] = (o[0], o[1])
    return out


def plan_keys(plan, type_re, spec):
    """set partition_types[T].reset_replicate = [spec] on every type whose name matches type_re; returns the names"""
    names = [tn for tn in sorted(plan["partition_types"]) if re.search(type_re, tn)]
    for tn in names:
        plan["partition_types"][tn]["reset_replicate"] = [dict(spec)]
    return names


def main(argv):
    if len(argv) > 1 and argv[1] == "plan":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("plan")
        ap.add_argument("out")
        ap.add_argument("type_re")
        ap.add_argument("--driver-re", required=True)
        ap.add_argument("--grid-um", type=float)
        ap.add_argument("--region-re")
        ap.add_argument("--optional", action="store_true")
        a = ap.parse_args(argv[1:])
        spec = {"driver_re": a.driver_re}
        for k, v in (("grid_um", a.grid_um), ("region_re", a.region_re), ("optional", a.optional or None)):
            if v is not None:
                spec[k] = v
        plan = json.load(open(a.plan))
        names = plan_keys(plan, a.type_re, spec)
        json.dump(plan, open(a.out, "w"), indent=1)
        print(f"reset_replicate: {len(names)} type(s) of {a.type_re}: {spec}")
        return 0
    if len(argv) < 3:
        print(__doc__)
        return 2
    txt = open(argv[1]).read()
    specs = json.load(open(argv[2]))
    pos = None
    if "--positions" in argv:
        pos = {k: tuple(v) for k, v in json.load(open(argv[argv.index("--positions") + 1])).items()}
    new, rep = apply(txt, specs, pos)
    if "-o" in argv:
        open(argv[argv.index("-o") + 1], "w").write(new)
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
