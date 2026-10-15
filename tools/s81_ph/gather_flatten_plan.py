#!/usr/bin/env python3
"""Gather FLATTEN plan (S81 die lead decision 2026-10-15 05:13, option A): the die places the 214 CLOSED gather children
directly, no hardened dsfd_sp_gather_c parent.  This tool turns the wires-only cluster RTL into what the die needs:

  * children  : 214 instances (master, closed view, LEF sha, origin in the slot frame, orient, clock entry + pin)
  * die_ports : every former slot port bit -> the child pin(s) it lands on (slot-frame xy), plus the v21 candidate slot
                pin as reference.  Under FLATTEN the die net runs from its source straight to these child pins.
  * nets      : every child->child net (driver pin -> sink pins, Manhattan length in um)
  * checks    : netlist = exactly the 214 children (no parent logic), no constant / undriven child input, no multi-driver,
                every layout child bound, every child view file present.

Connectivity comes from Yosys elaborating rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_gather_c_cl.sv (children as -lib
blackboxes, the die defines S81PH_GTH_HARD / DIE_CLOCKS / CONTROL_STRIP), never from a hand list.
Usage: gather_flatten_plan.py --out physical/s81_die_pins/v21_gather_transverse_candidate/gather_flatten_plan.json
"""
import argparse, hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gather_parent_spec as gps  # noqa: E402

CAND = "physical/s81_die_pins/v21_gather_transverse_candidate"
P, G = "rtl/dsrom_sys/s81_ph", "rtl/dsrom_sys/s81_glue"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def elaborate(tmp):
    lib = " ".join(f"{ROOT}/{f}" for f in (f"{P}/ot_s81ph_root_leaf.sv", f"{P}/dsfd_gth_ctl.sv", f"{G}/dsfd_rly_masters.sv",
                                            f"{G}/dsfd_rly_masters_gth_lane.sv", f"{G}/dsfd_rly_masters_gth_res.sv",
                                            f"{G}/dsfd_rly_masters_gth_strip.sv"))
    top = f"{ROOT}/{P}/ctrl_c/dsfd_sp_gather_c_cl.sv {ROOT}/{P}/dsfd_gth_strip.sv"
    d = "-DS81PH_GTH_LOCAL_BANKS -DS81PH_GTH_SSA2"
    ys = (f"read_verilog -sv -lib {d} -DSYNTHESIS {lib}\n"
          f"read_verilog -sv -DS81PH_GTH_HARD -DS81PH_GTH_DIE_CLOCKS -DS81PH_GTH_CONTROL_STRIP {d} {top}\n"
          f"hierarchy -top dsfd_sp_gather_c\nproc; flatten; opt_clean\nwrite_json {tmp}/net.json\n")
    Path(tmp, "y.ys").write_text(ys)
    subprocess.run(["yosys", "-q", f"{tmp}/y.ys"], check=True, capture_output=True)
    return json.loads(Path(tmp, "net.json").read_text())["modules"]["dsfd_sp_gather_c"]


def lef_pins(path):
    """pin bit name -> (layer, x, y) at the centre of its first RECT, plus SIZE."""
    txt = Path(path).read_text()
    size = tuple(map(float, re.search(r"SIZE\s+(\S+)\s+BY\s+(\S+)", txt).groups()))
    pins = {}
    for m in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$", txt, re.S | re.M):
        lay = re.search(r"LAYER\s+(\S+)", m[2]); r = re.search(r"RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", m[2])
        if lay and r:
            x0, y0, x1, y1 = map(float, r.groups())
            pins[m[1].replace("\\", "")] = (lay[1], (x0 + x1) / 2, (y0 + y1) / 2)
    return size, pins


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--out", required=True)
    a.add_argument("--plan", default="physical/s81_ph_views/gather/v21/strip_plan.json")
    a.add_argument("--layout", default=f"{CAND}/layout_gather.json")
    a.add_argument("--slot", default=f"{CAND}/dsfd_sp_gather_c.json")
    args = a.parse_args()
    layout = json.loads((ROOT / args.layout).read_text())
    plan = json.loads((ROOT / args.plan).read_text())
    slot = json.loads((ROOT / args.slot).read_text())
    with tempfile.TemporaryDirectory() as t:
        mod = elaborate(t)
    cells = {k.replace("\\", ""): v for k, v in mod["cells"].items()}
    errors = []
    strip = {r["instance"]: r for r in plan["relay_children"]}
    children, pinxy, lefcache = {}, {}, {}
    for inst, c in sorted(layout["children"].items()):
        m = c["master"]
        if inst in strip:
            r = strip[inst]
            view, orient, at = r["view"], r["orient"], r["origin_um"]
            lef = ROOT / r["lef"]
            for p, v in r["pins"].items():
                pinxy[(inst, p)] = (v["layer"], v["x"], v["y"])
            clk = r["clock_entry"]["port"]
        else:
            view = f"physical/ref_tile/{gps.kit_of(m)}/views/{m}"
            orient, at, clk = "R0", c["at"], c["clock"]
            lef = ROOT / view / f"{m}.lef"
            if not lef.is_file():
                errors.append(f"missing LEF {lef.relative_to(ROOT)}"); continue
            if lef not in lefcache:
                lefcache[lef] = lef_pins(lef)
            for p, (lay, x, y) in lefcache[lef][1].items():
                pinxy[(inst, p)] = (lay, round(at[0] + x, 3), round(at[1] + y, 3))
        for f in ("insertion.json", f"{Path(view).name}_tt.lib", f"{Path(view).name}_ff.lib", f"{Path(view).name}.lef"):
            if not (ROOT / view / f).is_file():
                errors.append(f"missing {view}/{f}")
        ab = ROOT / view / "abstract.json"
        route = json.loads(ab.read_text()).get("orfs_dir", "") if ab.is_file() else ""
        children[inst] = {"master": m, "view": view, "lef_sha256": sha(lef), "at_um": at, "orient": orient,
                          "clock_entry": clk, "clock_pin": f"{inst}/ck", "route": Path(route).name if route else None}
        if inst not in cells:
            errors.append(f"layout child {inst} not in the RTL cluster")
        elif cells[inst]["type"] != m:
            errors.append(f"{inst}: RTL type {cells[inst]['type']} != layout master {m}")
    extra = sorted(set(cells) - set(layout["children"]))
    if extra:
        errors.append(f"RTL cluster has {len(extra)} cells beyond the 214 children (parent logic): {extra[:5]}")
    # bit -> endpoints
    drv, sinks = {}, {}
    for pn, p in mod["ports"].items():
        for i, b in enumerate(p["bits"]):
            nm = f"{pn}[{i}]" if len(p["bits"]) > 1 else pn
            (drv if p["direction"] == "input" else sinks).setdefault(b, []).append(("PORT", nm))
    for inst, c in cells.items():
        for pn, bits in c["connections"].items():
            d = c.get("port_directions", {}).get(pn)
            for i, b in enumerate(bits):
                nm = f"{pn}[{i}]" if len(bits) > 1 else pn
                if isinstance(b, str):
                    if d == "input":
                        errors.append(f"constant {b} on child input {inst}/{nm} (tied functional port)")
                    continue
                (drv if d == "output" else sinks).setdefault(b, []).append((inst, nm))
    for b, s in sinks.items():
        n = len(drv.get(b, []))
        if n != 1:
            errors.append(f"bit {b} sinks {s[:2]} has {n} drivers")
    unloaded = sorted(f"{i}/{p}" for b, d in drv.items() for (i, p) in d if b not in sinks and i != "PORT")

    def xy(e):
        i, p = e
        v = pinxy.get((i, p)) or pinxy.get((i, p.split("[")[0])) if i != "PORT" else None
        return v

    slot_pins = {}
    for pn, v in slot.get("ports", {}).items():
        pb = v.get("per_bit") or []
        for i, bit in enumerate(pb):
            nm = f"{pn}[{i}]" if v.get("bits", 1) > 1 else pn
            slot_pins[nm] = {"face": bit[0], "layer": bit[1], "xy_um": bit[2:4]}
    die_ports, nets, missing_xy = {}, [], set()
    lengths = []
    for b in set(drv) | set(sinks):
        ends = drv.get(b, []) + sinks.get(b, [])
        ports = [p for (i, p) in ends if i == "PORT"]
        kids = [e for e in ends if e[0] != "PORT"]
        for e in kids:
            if xy(e) is None:
                missing_xy.add(f"{e[0]}/{e[1]}")
        if ports:
            for p in ports:
                die_ports[p] = {"child_pins": [{"pin": f"{i}/{q}", "xy_um": (xy((i, q)) or [None] * 3)[1:],
                                                "layer": (xy((i, q)) or [None])[0]} for (i, q) in kids],
                                "v21_slot_pin": slot_pins.get(p)}
        elif kids:
            d = drv[b][0]
            dx = xy(d)
            ss = []
            for s in sinks.get(b, []):
                sx = xy(s)
                L = round(abs(dx[1] - sx[1]) + abs(dx[2] - sx[2]), 3) if dx and sx else None
                ss.append({"pin": f"{s[0]}/{s[1]}", "manhattan_um": L})
                if L is not None:
                    lengths.append(L)
            nets.append({"driver": f"{d[0]}/{d[1]}", "sinks": ss})
    if missing_xy:
        errors.append(f"{len(missing_xy)} child pins without a LEF / plan location, e.g. {sorted(missing_xy)[:3]}")
    nets.sort(key=lambda n: n["driver"])
    lengths.sort()
    clk_ports = sorted({c["clock_entry"] for c in children.values()})
    out = {
        "schema": "opentallas.s81.gather_flatten.v1",
        "decision": "S81 die lead 2026-10-15 05:13 FLATTEN=YES: die places the 214 CLOSED children, no gather parent route",
        "case": "v21_gather_transverse", "slot_outline_um": slot.get("outline_um"),
        "frame": "slot frame (origin = lower-left of the v21 sp_gather slot, 1728 x 1045.44); die xy = slot origin + at",
        "sources": {"rtl": f"{P}/ctrl_c/dsfd_sp_gather_c_cl.sv", "rtl_sha256": sha(ROOT / P / "ctrl_c/dsfd_sp_gather_c_cl.sv"),
                    "layout": args.layout, "layout_sha256": sha(ROOT / args.layout), "strip_plan": args.plan,
                    "strip_plan_sha256": sha(ROOT / args.plan), "slot": args.slot, "slot_sha256": sha(ROOT / args.slot)},
        "counts": {"children": len(children), "rtl_cells": len(cells), "die_port_bits": len(die_ports),
                   "child_nets": len(nets), "clock_entries": len(clk_ports), "unloaded_child_outputs": len(unloaded)},
        "child_net_manhattan_um": {"max": lengths[-1] if lengths else None,
                                   "p99": lengths[int(.99 * (len(lengths) - 1))] if lengths else None,
                                   "over_500": sum(L > 500 for L in lengths)},
        "unloaded_child_outputs": unloaded, "errors": errors,
        "verdict": "FLATTEN_PLAN OK" if not errors else "FLATTEN_PLAN FAIL",
        "children": children, "die_ports": dict(sorted(die_ports.items())), "nets": nets}
    Path(args.out).write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(out["verdict"], json.dumps(out["counts"]), json.dumps(out["child_net_manhattan_um"]), f"errors {len(errors)}")
    for e in errors[:15]:
        print("  ", e)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
