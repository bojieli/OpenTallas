#!/usr/bin/env python3
"""Emit the gather v4 'direct' cluster parent spec (dsfd_sp_gather_c_strip); refuse runnable emission with missing views.

Children (wires only at the parent; every child pin is a register):
  32 leaves dsfd_gth_rw (W half, g 0..3) / dsfd_gth_re (E half, g 4..7) at (12.96 + 216 g, 61.632 + 184.32 k)
  24 lane relays  dsfd_rly_276_WE / _EW (23.76 x 30.24) in the 25.92-um column channels next to the outer leaves:
       W row k: c2 stage 0 and c3 stage 0 in channel g0|g1 (x 204.048), c3 stage 1 in channel g1|g2 (x 420.048)
       E row k: mirrored (x 1500.048 = channel g7|g6, x 1284.048 = channel g6|g5)
  24 result relays dsfd_rly_214_NS (34.56 x 19.44) in the 20.16-um row channels of column g:
       k2 stage 0 and k3 stage 1 in channel row0|row1 (y 226.08), k3 stage 0 in channel row1|row2 (y 410.4)
  ctl dsfd_gth_ctl (129.6 x 43.2) at (1598.4, 8.64); 133 strip relays from the strip plan (tools/s81_ph/gather_strip_plan.py)
Clock entries (one per child, no parent tree): ck (ctl), ck_l[0..31] (leaves), ck_q[0..47] (lane / result relays, the
clock index order of tools/s81_ph/gen_gather_cl.py), ck_r[0..131] (strip, stream) + ckv, ck_r[132] (serial).
No generated substitute views or assumed clock insertion: --require-bound refuses while any view file is missing.
"""
import argparse, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
V19_LEAF_H = 164.16          # original v19 leaf height (both halves)
ROW_CHANNEL = 20.16          # row channel between leaf rows (result relays 19.44 high)
ROW_Y0, TOP_MARGIN = 61.632, 24.768
LEAF_X = [12.96 + 216 * g for g in range(8)]
ROW_Y = [ROW_Y0 + (V19_LEAF_H + ROW_CHANNEL) * k for k in range(4)]
# Assigned-pin routes a bound leaf view may come from (abstract.json orfs_dir).  Legacy g1..g6
# face-region views carry the same top name but different pins and are refused.
BOUND_ROUTE_TAGS = {"dsfd_gth_rw": ("dsfd_gth_rw_v19_", "dsfd_gth_rw_pin_repair_1015_"),
                    "dsfd_gth_re": ("dsfd_gth_re_v19_", "dsfd_gth_re_transverse_1015_")}


def lef_size(path):
    m = re.search(r"SIZE\s+(\S+)\s+BY\s+(\S+)", Path(path).read_text())
    return float(m[1]), float(m[2])


def leaf_heights(root=ROOT):
    """Actual leaf heights from the bound LEFs (rw, re); a missing LEF is an error, never a guess."""
    out = {}
    for m in ("dsfd_gth_rw", "dsfd_gth_re"):
        w, h = lef_size(root / f"physical/ref_tile/{m}/views/{m}/{m}.lef")
        assert abs(w - 190.08) < 1e-6, (m, w)
        out[m] = h
    return out


def geometry(leaf_h=None):
    """Row origins, row height and parent outline height for the actual leaf heights.
    Every row is as tall as the tallest leaf (all leaves sit at the row bottom so the closed lane-relay
    li offset leaf y + 40.32 stays exact); v19 (164.16) reproduces the original 803.52 slot."""
    h = max((leaf_h or {}).values(), default=V19_LEAF_H)
    pitch = h + ROW_CHANNEL
    rows = [round(ROW_Y0 + pitch * k, 3) for k in range(4)]
    return {"row_y": rows, "row_h": h, "outline_h": round(rows[3] + h + TOP_MARGIN, 3)}


def relay_children(geo=None):
    geo = geo or geometry()
    ROW_Y, H = geo["row_y"], geo["row_h"]
    out, q = [], 0
    for h, (hn, m) in enumerate((("W", "dsfd_rly_276_WE"), ("E", "dsfd_rly_276_EW"))):
        near, far = ((204.048, 420.048) if h == 0 else (1500.048, 1284.048))
        for k in range(4):
            for c in range(4):
                for st in range((0, 0, 1, 2)[c]):
                    x, dy = ((near, 40.32) if c == 2 else (near, 93.6)) if st == 0 else (far, 40.32)
                    out.append({"master": m, "inst": f"u_rq_{hn}{k}_{c}_{st}", "at": [x, round(ROW_Y[k] + dy, 3)], "clock": f"ck_q[{q}]"})
                    q += 1
    for g in range(8):
        for k in range(4):
            for st in range((0, 0, 1, 2)[k]):
                ch01, ch12 = round(ROW_Y[0] + H + .288, 3), round(ROW_Y[1] + H + .288, 3)  # 226.08 / 410.4 at v19
                if k == 2:
                    x, y = LEAF_X[g] + 30.24, ch01
                elif st == 0:
                    x, y = LEAF_X[g] + 95.04, ch12
                else:
                    x, y = LEAF_X[g] + 95.04, ch01
                out.append({"master": "dsfd_rly_214_NS", "inst": f"u_rq_c{g}_{k}_{st}", "at": [round(x, 3), y], "clock": f"ck_q[{q}]"})
                q += 1
    assert q == 48
    return out


def kit_of(master):
    return {"dsfd_gth_rw": "dsfd_gth_rw", "dsfd_gth_re": "dsfd_gth_re", "dsfd_gth_ctl": "dsfd_gth_ctl"}.get(
        master, "s81_rly_" + master[len("dsfd_rly_"):].lower())


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--plan", required=True, help="strip plan JSON (tools/s81_ph/gather_strip_plan.py)")
    a.add_argument("--out", required=True)
    a.add_argument("--io-tcl", default="physical/s81_die_pins/v19/dsfd_sp_gather_c.tcl", help="die-assigned slot pins")
    a.add_argument("--name", default="dsfd_sp_gather_c_strip", help="kit name (top stays dsfd_sp_gather_c)")
    a.add_argument("--require-bound", action="store_true")
    args = a.parse_args()
    plan = json.loads(Path(args.plan).read_text())
    geo = geometry(leaf_heights())
    ROW_Y = geo["row_y"]
    if [round(x, 3) for x in plan["outline_um"]] != [1728, geo["outline_h"]]:
        raise SystemExit(f"GATHER_PARENT REFUSED: strip plan outline {plan['outline_um']} != actual-leaf outline "
                         f"[1728, {geo['outline_h']}] (regenerate it with tools/s81_ph/gather_strip_plan.py)")
    children = []
    for g in range(8):
        for k in range(4):
            m = "dsfd_gth_rw" if g < 4 else "dsfd_gth_re"
            children.append({"view": f"physical/ref_tile/{kit_of(m)}/views/{m}", "count": 1, "inst": f"u_l_{g}_{k}",
                             "at": [round(LEAF_X[g], 3), round(ROW_Y[k], 3)], "orient": "R0"})
    children.append({"view": "physical/ref_tile/dsfd_gth_ctl/views/dsfd_gth_ctl", "count": 1, "inst": "u_ctl",
                     "at": [1598.4, 8.64], "orient": "R0"})
    for r in relay_children(geo):
        children.append({"view": f"physical/ref_tile/{kit_of(r['master'])}/views/{r['master']}", "count": 1,
                         "inst": r["inst"], "at": r["at"], "orient": "R0"})
    for r in plan["relay_children"]:
        children.append({"view": r["view"], "count": 1, "inst": r["instance"], "at": r["origin_um"], "orient": r["orient"]})
    core = ["ck"] + [f"ck_l[{i}]" for i in range(32)] + [f"ck_q[{i}]" for i in range(48)] + [f"ck_r[{i}]" for i in range(132)]
    serial = ["ckv", "ck_r[132]"]
    cps = core + serial
    assert len(cps) == 215
    missing = []
    for ch in children:
        view = ROOT / ch["view"]
        for name in ("insertion.json", view.name + ".lef", view.name + "_tt.lib", view.name + "_ss.lib", view.name + "_ff.lib"):
            if not (view / name).is_file():
                missing.append(str((view / name).relative_to(ROOT)))
    # The exporter publishes under the RTL top, even when the routed kit is
    # suffixed _v19. Require its source receipt, not a guessed output directory:
    # an older face-region g5 view has the same top but different assigned pins.
    for master in ("dsfd_gth_rw", "dsfd_gth_re"):
        receipt = ROOT / f"physical/ref_tile/{master}/views/{master}/abstract.json"
        if receipt.is_file():
            recorded = json.loads(receipt.read_text())
            if not any(tag in recorded.get("orfs_dir", "") for tag in BOUND_ROUTE_TAGS[master]):
                missing.append(str(receipt.relative_to(ROOT)) + ": assigned-pin route required " + str(BOUND_ROUTE_TAGS[master]))
        else:
            missing.append(str(receipt.relative_to(ROOT)))
    if not (ROOT / args.io_tcl).exists():
        missing.append(args.io_tcl)
    bench = "SSA2=1 LOCAL_BANKS=1 CONTROL_STRIP=1 DIE_CLOCKS=1 SS=8 J=4 bash rtl/dsrom_sys/s81_ph/test/run_gather_cl.sh $PWD {RUN}/%s rtl/dsrom_sys/s81_ph/test/real_order_trace.json '2 20'"
    spec = {
        "name": args.name, "top": "dsfd_sp_gather_c", "kind": "cluster",
        "sources": ["rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_gather_c_cl.sv", "rtl/dsrom_sys/s81_ph/dsfd_gth_strip.sv"],
        "defines": ["S81PH_GTH_HARD", "S81PH_GTH_DIE_CLOCKS", "S81PH_GTH_CONTROL_STRIP"], "params": {},
        "outline": {"w": 1728, "h": geo["outline_h"]}, "clock": "entries", "clock_port": "ck", "clock_ports": cps,
        "clock_entry_domains": {
            "core": {"ratio": [1, 1], "ports": core, "inputs": ["rst", "rW*", "rE*", "c_cmd"], "outputs": ["t_capture", "t_xgo", "c_done", "c_st"]},
            "serial": {"ratio": [4, 3], "ports": serial, "inputs": ["rsv", "f_vm", "f_cd"], "outputs": []}},
        "reset_ports": ["rst", "rsv"], "children": children, "child_lattice_um": .144, "io_tcl": args.io_tcl,
        "pins": {"W": [f"rW{i}" for i in range(6)],
                 "E": [f"rE{i}" for i in range(6)] + ["ck", "ckv", "rst", "rsv", "f_vm", "c_cmd", "c_done", "c_st", "t_xgo"],
                 "S": ["t_capture", "f_cd"], "ANY": ["ck_l", "ck_q", "ck_r"]},
        "recipe": 2, "inhold": False, "outhold": False, "io_flop_at_pins": False, "route": {"pd": .5, "threads": 16},
        "job": {"owner": "Claude:S-GATHER", "branch": "claude/s81-gather-r3-1014", "tag": "v4",
                "purpose": ("S81 gather v4 'direct' cluster parent: 32 4-root leaves + 48 lane / result relays + ctl + 133 "
                            "strip relays, wires only, one compensated clock entry per child (215); every leaf takes only "
                            "its own lanes and returns only its own results (no through-leaf chain)."),
                "benches": [{"name": "gather_cl_gate", "cmd": bench % "gcl", "expect": "pass", "pass_regex": "GATHER_CL_GATE PASS",
                             "threads": 24, "peak_ram_gb": 64, "needs": ["verilator"]},
                            {"name": "gather_cl_neg_lane", "cmd": "RAW=1 MODES=lane " + bench % "gclm", "expect": "fail",
                             "fail_regex": "GATHER_CL_NEGATIVE FAIL_AS_REQUIRED", "threads": 4, "peak_ram_gb": 32, "needs": ["verilator"]}],
                "extra_paths": ["rtl/dsrom_sys/s81_ph", "rtl/dsrom_sys/s81_ctrl", "rtl/dsrom_sys/s81_glue", "physical/s81_ph_views",
                                "tools/s81_ph", "results/rtl/s81_ph_20261006/gather"]},
        "geometry": {"row_y_um": ROW_Y, "row_h_um": geo["row_h"], "leaf_h_um": leaf_heights()},
        "missing_bound_artifacts": sorted(set(missing)),
        "qualification": "OPEN_DRAFT" if missing else "BOUND"}
    if args.require_bound and missing:
        raise SystemExit("GATHER_PARENT REFUSED: missing actual bound artifacts " + str(len(set(missing))))
    Path(args.out).write_text(json.dumps(spec, indent=2) + "\n")
    print(f"GATHER_PARENT {'DRAFT' if missing else 'BOUND'} {len(children)} children / {len(cps)} clock entries; "
          f"missing {len(set(missing))} bound artifacts")


if __name__ == "__main__":
    main()
