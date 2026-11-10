#!/usr/bin/env python3
"""DS85 CLKDIE-S81 (DO_NOT_COUNT): CLOCK-ONLY die route target on a die_trial kit = clock_grt_probe.build with
(1) the signal netlist reduced to the placed partition abstracts (no die signal nets: clock-only), and
(2) the plan's landing network (clock.landing_network edges of kind 'clock', fclk_out -> fclk_in) as routed nets:
    each edge = one BUFx24 (the kits' own cland_fwd_* driver master) placed at the fclk_out pin, driving a die net to
    an output port placed on the fclk_in pin (M7, the landing_contract layer).  Its routed RC gives the die share of
    t_fwd; the driver delay itself is already in the source type's fclk_out arrival (measured into 2 fF), so the
    die share = arr(port) - arr(fd/Y) + [arr(fd/Y) - arr(fd_ref/Y)] with fd_ref an identical BUFx24 into 2 fF.

Everything else (floorplan, partition placement at plan origins, PG/reserve obstructions, clock NDRs 4W/8W, M8-M9
clock layers, GRT, estimate_parasitics -global_routing, tap/node arrival readout) is clock_grt_probe.build.

  ds85_combo.py KIT CLOCK OUT --plan PLAN [--legalize]
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def pin_xy(P, part, name):
    t = P["partition_types"][P["_parts"][part]["type"]]
    for q in t["clock"]["landing_contract"]["pins"]:
        if q["name"] == name:
            return q
    raise KeyError((part, name))


def to_die(P, part, xy):
    p = P["_parts"][part]
    w, h = P["partition_types"][p["type"]]["outline_um"]
    x, y = xy
    o = p.get("orient", "R0")
    X, Y = {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]
    return p["origin_um"][0] + X, p["origin_um"][1] + Y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kit", type=Path)
    ap.add_argument("clock", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--tools", type=Path, required=True)
    ap.add_argument("--legalize", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, str(a.tools))
    import clock_grt_probe as CGP
    P = json.loads(a.plan.read_text())
    P["_parts"] = {p["name"]: p for p in P["partitions"]}
    a.out.mkdir(parents=True, exist_ok=True)
    # (1) clock-only signal stand-in: partition instances with no connections
    rv = (a.kit / "grt" / "route.v").read_text()
    m = re.search(r"\s*module\s+(\w+)\s*\(([^)]*)\);", rv)
    insts = re.findall(r"^\s+(\S+)\s+(\S+)\s*\((?:.|\n)*?\);", rv[m.end():rv.rindex("endmodule")], flags=re.M)
    parts = set(P["_parts"])
    keep = [(mod, inst) for mod, inst in insts if inst.lstrip("\\").strip() in parts or inst in parts]
    if len(keep) != len(parts):
        raise SystemExit(f"partition instances {len(keep)} != plan parts {len(parts)}")
    # (2) landing network clock edges
    edges = [e for e in P["clock"]["landing_network"]["edges"] if e["kind"] == "clock"]
    fd = []
    for i, e in enumerate(sorted(edges, key=lambda e: e["id"])):
        so, si = pin_xy(P, e["src"]["part"], e["src"]["bus"]), pin_xy(P, e["dst"]["part"], e["dst"]["bus"])
        xo, yo = to_die(P, e["src"]["part"], so["xy_um"])
        xi, yi = to_die(P, e["dst"]["part"], si["xy_um"])
        fd.append(dict(i=i, id=e["id"], src=xo, srcy=yo, dst=xi, dsty=yi, layer=si.get("layer", "M7"),
                       hop_um=round(abs(xo - xi) + abs(yo - yi), 3)))
    # GRT rejects two pins at one position (GRT-0031 -> GRT-0080): two plan landing edges share one fclk_in xy (plan
    # pin overlap, reported in combo_build.json); the later ones move 0.5 um along the pin edge per duplicate
    seen, dup = {}, []
    for d in fd:
        k = (round(d["dst"], 3), round(d["dsty"], 3))
        if k in seen:
            n = seen[k] = seen[k] + 1
            d["dst"] += 0.5 * n
            dup.append(dict(id=d["id"], shares_with_xy=list(k), moved_um=0.5 * n))
        else:
            seen[k] = 0
    sig = [f"module {m.group(1)} (rst_n, lnd_ref_in, lnd_ref_out, " + ", ".join(f"lnd_in_{d['i']}, lnd_out_{d['i']}" for d in fd) + ");",
           "  input rst_n;", "  input lnd_ref_in;", "  output lnd_ref_out;"]
    for d in fd:
        sig += [f"  input lnd_in_{d['i']};", f"  output lnd_out_{d['i']};"]
    sig += [f"  {mod} {inst} ();" for mod, inst in keep]
    sig += ["  BUFx24_ASAP7_75t_R fd_ref (.A(lnd_ref_in), .Y(lnd_ref_out));"]
    sig += [f"  BUFx24_ASAP7_75t_R fd_{d['i']} (.A(lnd_in_{d['i']}), .Y(lnd_out_{d['i']}));" for d in fd]
    sig += ["endmodule"]
    kit2 = a.out / "kit_clockonly"
    (kit2 / "grt").mkdir(parents=True, exist_ok=True)
    (kit2 / "grt" / "route.v").write_text("\n".join(sig) + "\n")
    # grt.tcl / obs.tcl / tracks.tcl stay the kit's (read via /work); clock_grt_probe reads route.v + grt.tcl from kit
    (kit2 / "grt" / "grt.tcl").write_text((a.kit / "grt" / "grt.tcl").read_text())
    res = CGP.build(kit2, a.clock, a.out, a.plan if a.legalize else None)
    t = (a.out / "combo.tcl").read_text()
    # landing drivers: placed on legal-ish sites next to the fclk_out pin; ports on the fclk_in pin (M7) and a
    # floating input pin at the driver
    W = P["die"]["outline_um"][0] if isinstance(P["die"], dict) else None
    add = []
    sx, sy = 0.054, 0.27
    x0, y0 = fd[0]["src"] + 3.0, fd[0]["srcy"]   # reference driver 3 um off fd_0 (distinct pin position)
    add.append(f"place_inst -name fd_ref -location {{{round(round(x0 / sx) * sx, 3)} {round(round(y0 / sy) * sy, 3)}}} -orient R0 -status FIRM")
    add.append(f"place_pin -pin_name lnd_ref_in -layer M7 -location {{{x0:.3f} {y0:.3f}}} -pin_size {{0.08 0.432}}")
    add.append(f"place_pin -pin_name lnd_ref_out -layer M7 -location {{{x0 + 1.0:.3f} {y0:.3f}}} -pin_size {{0.08 0.432}}")
    for d in fd:
        bx, by = round(round(d["src"] / sx) * sx, 3), round(round(d["srcy"] / sy) * sy, 3)
        add.append(f"place_inst -name fd_{d['i']} -location {{{bx} {by}}} -orient R0 -status FIRM")
        add.append(f"place_pin -pin_name lnd_in_{d['i']} -layer M7 -location {{{d['src']:.3f} {d['srcy']:.3f}}} -pin_size {{0.08 0.432}}")
        add.append(f"place_pin -pin_name lnd_out_{d['i']} -layer {d['layer']} -location {{{d['dst']:.3f} {d['dsty']:.3f}}} -pin_size {{0.08 0.432}}")
    marker = "create_clock -name dck"
    t = t.replace(marker, "\n".join(add) + "\n" + marker, 1)
    # landing nets: die signal layers M4-M7 (12.1c preferred range; set_routing_layers -signal M4-M9 already lets
    # the router use leftover M8/M9) -- no NDR; they are scalar clock nets of the landing contract
    t = t.replace("set_input_delay 0 -clock vclk [get_ports root]",
                  "set_input_delay 0 -clock vclk [get_ports root]\n"
                  "set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports lnd_*in*]\n"
                  "set_input_delay 0 -clock vclk [get_ports lnd_*in*]\n"
                  "set_load 2.0 [get_ports lnd_*out*]\n"
                  "set_output_delay 0 -clock vclk [get_ports lnd_*out*]")
    # die tree cells of a die_trial kit are b*/r*/p* (not die_clock's n*): read every clock cell's output arrival
    t = t.replace("foreach i [get_cells ck_n*]", "foreach i [get_cells ck_*]", 1)
    t = t.replace("close $fh",
                  "foreach p [get_ports lnd_*out*] {puts $fh \"L [get_full_name $p] [expr {833.000-[get_property $p slack_max_rise]}] [get_property $p slack_min_rise]\"}\n"
                  "foreach i [get_cells fd_*] {set q [get_pins [get_full_name $i]/Y]; set q2 [get_pins [get_full_name $i]/A]; puts $fh \"D [get_full_name $i] [get_property $q arrival_max_rise] [get_property $q2 arrival_max_rise]\"}\n"
                  "close $fh", 1)
    t = t.replace("write_db /out/combo_$::env(CORNER).odb",
                  "estimate_parasitics -global_routing -spef_file /out/combo_$::env(CORNER).spef\n"
                  "write_db /out/combo_$::env(CORNER).odb")
    (a.out / "combo.tcl").write_text(t)
    (a.out / "landing_nets.json").write_text(json.dumps(fd, indent=0) + "\n")
    res.update(partitions=len(keep), landing_clock_nets=len(fd),
               landing_hop_um_max=max(d["hop_um"] for d in fd), landing_hop_over_405=sum(d["hop_um"] > 405 for d in fd), shared_fclk_in_xy=dup)
    (a.out / "combo_build.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
