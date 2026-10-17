#!/usr/bin/env python3
"""F1 forwarded-clock relay views (H-NETLIST 2026-10-16, DIE-CLOCK requirement): the die STA needs, per corner, BOTH the
clk_in -> register CK insertion R and the clk_in -> clk_out forwarding delay of every hbfd_rly_*_fc tile, and the tile
liberty must carry a clk_in -> clk_out arc (the ETM export writes a meaningless self-related clk_out arc).

  measure  --base <route results base dir with 6_final.odb/.sdc/.spef> --output fwd.json     (runs on the route host:
           docker openroad/orfs per ss/tt/ff, raw source latency 0, propagated clocks, routed SPEF)
  patch    --views <views/<master> dir> --fwd fwd.json   adds insertion.json "forwarded_clock" and rewrites each corner
           lib's clk_out timing to rising_edge + falling_edge arcs from clk_in (forwarding delay + transition, scalar)

The forwarding delay is the arrival of the clk_in rising (falling) edge at the clk_out port with the source latency
zeroed: CTS buffers (if any) + the kept BUFx12f + the routed wire to the pin.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"


def tcl(corner):
    C = corner.upper()
    return f"""
foreach l [glob {PLAT}/lib/NLDM/*RVT_{C}*] {{ read_liberty $l }}
foreach l [glob {PLAT}/lib/NLDM/*_LVT_{C}_* {PLAT}/lib/NLDM/*_SLVT_{C}_*] {{ if {{![string match *FAKE* $l]}} {{ read_liberty $l }} }}
read_db /base/6_final.odb
read_sdc /base/6_final.sdc
read_spef /base/6_final.spef
set_propagated_clock [all_clocks]
foreach c [all_clocks] {{ if {{[llength [get_property $c sources]]}} {{ set_clock_latency -source 0 $c }} }}
report_checks -path_delay max -group_path_count 1 > /dev/null
set y [lindex [get_pins -hierarchical *u_fcb_ck*/Y] 0]
if {{![llength $y]}} {{ error "no clk_out buffer Y pin" }}
foreach k {{arrival_max_rise arrival_min_rise arrival_max_fall arrival_min_fall slew_max_rise slew_max_fall}} {{
  puts "OT_FWD bufy $k [get_property $y $k]"
}}
set r {{}}
set ot_n 0
foreach p [all_registers -clock_pins] {{ set v [get_property $p arrival_max_rise]; if {{[string is double -strict $v]}} {{ lappend r $v }} }}
puts "OT_FWD period [get_property [get_clocks core_clk] period]"
puts "OT_FWD R [llength $r] [tcl::mathfunc::min {{*}}$r] [tcl::mathfunc::max {{*}}$r] [expr {{[tcl::mathop::+ {{*}}$r] / double([llength $r])}}]"
report_checks -through [get_ports clk_out] -unconstrained -format full_clock_expanded -fields {{slew cap}} -digits 2
exit
"""


def measure(a):
    base = Path(a.base).resolve()
    rec = dict(schema="opentallas.hbm.rly_fc_forwarded_clock.v1", base=str(base))
    for corner in ("ss", "tt", "ff"):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "s.tcl").write_text(tcl(corner))
            r = subprocess.run(["docker", "run", "--rm", "-v", f"{base}:/base:ro", "-v", f"{td}:/t:ro", a.image, "bash", "-lc",
                                "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/s.tcl"],
                               capture_output=True, text=True)
        out = r.stdout
        if r.returncode:
            raise SystemExit(f"{corner}: replay failed\n{out[-2000:]}\n{r.stderr[-2000:]}")
        c = {}
        for m in re.finditer(r"^OT_FWD (port|bufy) (\S+) (\S+)", out, re.M):
            try:
                c.setdefault(m[1], {})[m[2]] = round(float(m[3]), 2)
            except ValueError:
                c.setdefault(m[1], {})[m[2]] = None
        m = re.search(r"^OT_FWD R (\d+) (\S+) (\S+) (\S+)", out, re.M)
        if m:
            c["R"] = dict(n=int(m[1]), min=round(float(m[2]), 1), max=round(float(m[3]), 1), mean=round(float(m[4]), 1))
        src = dict(c.get("bufy", {}))
        mp = re.search(r"^OT_FWD period (\S+)", out, re.M)
        half = float(mp[1]) / 2 if mp else 0.0
        for k in ("arrival_max_fall", "arrival_min_fall"):      # the fall edge of clk_in is at T/2: report the delay
            if src.get(k) is not None and src[k] > half:
                src[k] = round(src[k] - half, 2)
        c["period_ps"] = 2 * half
        c["clk_in_to_clk_out_ps"] = dict(rise_max=src.get("arrival_max_rise"), rise_min=src.get("arrival_min_rise"),
                                         fall_max=src.get("arrival_max_fall"), fall_min=src.get("arrival_min_fall"),
                                         slew_rise=src.get("slew_max_rise"), slew_fall=src.get("slew_max_fall"),
                                         measured_at="clk_out buffer Y pin (drives the clk_out port)")
        if c["clk_in_to_clk_out_ps"]["rise_max"] is None:
            raise SystemExit(f"{corner}: no clk_out arrival\n{out[-3000:]}")
        c["report_tail"] = out[-2500:]
        rec[corner] = c
    Path(a.output).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: (v["clk_in_to_clk_out_ps"], v.get("R")) for k, v in rec.items() if k in ("ss", "tt", "ff")}))


def patch(a):
    views = Path(a.views)
    fwd = json.loads(Path(a.fwd).read_text())
    ins = views / "insertion.json"
    rec = json.loads(ins.read_text())
    rec["forwarded_clock"] = dict(
        schema=fwd["schema"], base=fwd["base"], rule="F1 (DIE-CLOCK): clk_out = clk_in through one kept BUFx12f; "
        "die STA uses R (clk_in -> register CK) and D (clk_in -> clk_out) per corner",
        **{k: dict(clk_in_to_clk_out_ps=fwd[k]["clk_in_to_clk_out_ps"], R_all=fwd[k].get("R")) for k in ("ss", "tt", "ff")})
    ins.write_text(json.dumps(rec, indent=1) + "\n")
    for corner in ("ss", "tt", "ff"):
        libs = list(views.glob(f"*_{corner}.lib"))
        if len(libs) != 1:
            raise SystemExit(f"{corner}: expected one lib in {views}, found {libs}")
        lib = libs[0]
        t = lib.read_text()
        d = fwd[corner]["clk_in_to_clk_out_ps"]
        fr = d["fall_max"] if d["fall_max"] is not None else d["rise_max"]
        sr = d["slew_rise"] or 10.0
        sf = d["slew_fall"] or sr
        # the forwarded clock as the ETM exporter writes a clock output (and native_pin_audit classifies a pin with both
        # edges of one clock as 'clock_out', not a data launch / combinational pin): rising_edge (clk_in rise -> clk_out
        # rise) and falling_edge (clk_in fall -> clk_out fall) arcs from clk_in; the die STA takes D from insertion.json.
        arc = ''.join(
            '      timing() {\n        related_pin : "clk_in";\n'
            f'        timing_type : {tt};\n'
            f'        {ck}(scalar) {{ values("{dv:.4f}"); }}\n'
            f'        {tr}(scalar) {{ values("{sv:.4f}"); }}\n'
            '      }\n'
            for tt, ck, tr, dv, sv in (("rising_edge", "cell_rise", "rise_transition", d["rise_max"], sr),
                                       ("falling_edge", "cell_fall", "fall_transition", fr, sf)))
        m = re.search(r'pin\("?clk_out(\[0\])?"?\)\s*\{', t)
        if not m:
            raise SystemExit(f"{lib}: no clk_out pin group")
        # the pin group body: from '{' to its matching '}'
        i = m.end(); depth = 1
        while depth:
            depth += {"{": 1, "}": -1}.get(t[i], 0); i += 1
        body = t[m.end():i - 1]
        body = re.sub(r"\n\s*timing\(\)\s*\{", "\n      timing() {", body)
        # drop every existing timing group of the pin
        out, j = [], 0
        for tm in re.finditer(r"timing\(\)\s*\{", body):
            if tm.start() < j:
                continue
            out.append(body[j:tm.start()])
            k = tm.end(); dd = 1
            while dd:
                dd += {"{": 1, "}": -1}.get(body[k], 0); k += 1
            j = k
        out.append(body[j:])
        nb = "".join(out).rstrip() + "\n" + arc + "    "
        lib.write_text(t[:m.end()] + nb + t[i - 1:])
        print(f"{lib.name}: clk_out arc clk_in rise {d['rise_max']} fall {d['fall_max']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    m = sp.add_parser("measure"); m.add_argument("--base", required=True); m.add_argument("--output", required=True)
    m.add_argument("--image", default="openroad/orfs:latest")
    p = sp.add_parser("patch"); p.add_argument("--views", required=True); p.add_argument("--fwd", required=True)
    a = ap.parse_args()
    measure(a) if a.cmd == "measure" else patch(a)


if __name__ == "__main__":
    main()
