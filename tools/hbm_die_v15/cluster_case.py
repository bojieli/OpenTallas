#!/usr/bin/env python3
"""Hardened regional cluster case (H-DIE 2026-10-16 20:55, owner: hierarchical die -- the flat 13M-net die GRT
never finishes; build one regional cluster, replicate, route only inter-cluster relays at die top).

    cluster_case.py --contract C.json --case CASE_DIR --rect X0 Y0 X1 Y1 --name SW --out OUT [--reach 450]

CASE_DIR = a die_case_v16 output (manifest.json placement + views/ LEF/TT/FF actually consumed).
Cluster = every placed instance whose centre lies in the rectangle.  Netlist from the source contract edges (bit
level: one net per driver bit); an edge with one end outside becomes a cluster port (bit-exact, named by edge) with
the edge's clock domain.  Clocks (owner neighbour-relative clocking, DIE-CLOCK METHOD 640fa898f): each domain enters
the cluster as ONE regional-root port clk_<dom>; OpenROAD CTS builds the regional tree inside the cluster.  Resets
enter as rst_<dom> ports (regional reset tree, set_false_path like por_*).  Straps stay open exactly as in
die_case_v16 (listed).  Ports are placed by place_pins on the cluster boundary (die-top relay hand-off).
Flow: place (FIRM, die coordinates - origin) -> repair_design -max_wire_length REACH (buffers inserted = residual
long wires, reported) -> CTS per root -> GRT (congestion report + gcell map + layout dump) -> TT setup / FF hold STA
with boundary IO at 0.2 T.  NOT_A_DIE_RESULT: SYNTH views are estimates.
"""
import argparse, collections, json, re, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PERIOD = dict(stream=833.333, hbm=1024.0, serial=1111.111)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--contract', required=True, type=Path)
    ap.add_argument('--case', required=True, type=Path)
    ap.add_argument('--rect', required=True, type=float, nargs=4)
    ap.add_argument('--name', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--reach', type=float, default=450.0)
    ap.add_argument('--congestion-iterations', type=int, default=10)
    a = ap.parse_args()
    C = json.loads(a.contract.read_text())
    man = json.loads((a.case / 'manifest.json').read_text())
    pl = man['placement']
    x0, y0, x1, y1 = a.rect
    inside = {n for n, v in pl.items() if x0 <= v['x'] + v['w'] / 2 < x1 and y0 <= v['y'] + v['h'] / 2 < y1}
    # an instance is inside by its centre; the cluster outline grows to hold every inside body (pilot SW 10-16: a relay
    # straddling the rect edge put 1,024 pins outside the die -> GRT-0028)
    x0 = min([x0] + [pl[n]['x'] for n in inside]); y0 = min([y0] + [pl[n]['y'] for n in inside])
    x1 = max([x1] + [pl[n]['x'] + pl[n]['w'] for n in inside]); y1 = max([y1] + [pl[n]['y'] + pl[n]['h'] for n in inside])
    I = C['instances']
    # port widths from the contract
    width = {n: {p: d['bits'] for p, d in I[n]['ports'].items()} for n in inside}
    pdir = {n: {p: d['direction'] for p, d in I[n]['ports'].items()} for n in inside}
    pin = lambda n, p, k: f'{p}[{k}]' if width[n][p] > 1 else p
    conn = collections.defaultdict(dict)          # inst -> {pin: net}
    ports = {}                                     # port name -> (direction, domain)
    nets = set()
    cross = collections.Counter(); cross_bits = 0; internal_bits = 0
    for ei, e in enumerate(C['edges']):
        (si, sp, slo, shi), (ti, tp, tlo, thi) = e['source'], e['sink']
        sin, tin = si in inside, ti in inside
        if not sin and not tin:
            continue
        nb = shi - slo
        for k in range(nb):
            if sin:
                nm = f'n_{si}_{sp}_{slo + k}'
            else:
                nm = f'pi_{si}_{sp}_{slo + k}'
                ports[nm] = ('input', e.get('clock') or 'stream')
            if sin:
                conn[si][pin(si, sp, slo + k)] = nm
                if tin:
                    nets.add(nm)
                else:                              # the driver bit leaves the cluster: the net itself is an output port
                    ports[nm] = ('output', e.get('clock') or 'stream')
            if tin:
                conn[ti][pin(ti, tp, tlo + k)] = nm
        if sin and tin:
            internal_bits += nb
        else:
            cross_bits += nb
            other = ti if sin else si
            cross[(re.sub(r'\d', '#', si), re.sub(r'\d', '#', ti))] += nb
    doms = set()
    for cr in C['clock_resets']:
        n = cr['instance']
        if n not in inside:
            continue
        d = cr['domain']; doms.add(d)
        pn = f"{'clk' if cr['kind'] == 'clock' else 'rst'}_{d}"
        ports[pn] = ('input', d)
        for k in range(cr.get('bits', 1)):
            conn[n][pin(n, cr['port'], k) if cr.get('bits', 1) > 1 else cr['port']] = pn
    nets -= set(ports)
    masters = sorted({pl[n]['m'] for n in inside})
    vd = a.case / 'views'
    out = a.out; (out / 'views').mkdir(parents=True, exist_ok=True); (out / 'out').mkdir(exist_ok=True)
    for m in masters:
        for suf in ('.lef', '_tt.lib', '_ff.lib'):
            shutil.copy(vd / f'{m}{suf}', out / 'views' / f'{m}{suf}')
    # verilog
    L = [f'// cluster {a.name} rect {a.rect} from {a.case} / {a.contract} (tools/hbm_die_v15/cluster_case.py) NOT_A_DIE_RESULT',
         f'module cl_{a.name} (' + ', '.join(sorted(ports)) + ');']
    L += [f'  {d} {p};' for p, (d, _) in sorted(ports.items())]
    L += [f'  wire {x};' for x in sorted(nets)]
    nc = 0
    for n in sorted(inside):
        cs = []
        bus = collections.defaultdict(dict); scal = []
        for p, w in width[n].items():
            if w > 1:
                for k in range(w):
                    if f'{p}[{k}]' in conn[n]:
                        bus[p][k] = conn[n][f'{p}[{k}]']
                if bus.get(p):
                    parts = []
                    for k in range(w - 1, -1, -1):
                        if k in bus[p]:
                            parts.append(bus[p][k])
                        else:
                            parts.append(f'nc{nc}'); L.append(f'  wire nc{nc};'); nc += 1
                    cs.append(f'.{p}({{{", ".join(parts)}}})')
            elif p in conn[n]:
                cs.append(f'.{p}({conn[n][p]})')
        L.append(f'  {pl[n]["m"]} {n} (' + ', '.join(cs) + ');')
    L.append('endmodule')
    (out / 'cluster.v').write_text('\n'.join(L) + '\n')
    W, H = x1 - x0, y1 - y0
    plat = '/OpenROAD-flow-scripts/flow/platforms/asap7'
    p_ = 9.6 / 15.0
    plc = '\n'.join(f'place_inst -name {n} -location {{{pl[n]["x"] - x0:.3f} {pl[n]["y"] - y0:.3f}}} -orientation {pl[n]["o"]} -status FIRM'
                    for n in sorted(inside))
    clocks = '\n'.join(f'create_clock -name {d} -period {PERIOD[d]} [get_ports clk_{d}]' for d in sorted(doms))
    io = []
    ins = collections.defaultdict(list); outs = collections.defaultdict(list)
    for p, (d, dom) in ports.items():
        if p.startswith(('clk_', 'rst_')):
            continue
        (ins if d == 'input' else outs)[dom if dom in doms else sorted(doms)[0]].append(p)
    for dom in sorted(set(ins) | set(outs)):
        t = 0.2 * PERIOD[dom]
        (out / f'io_{dom}_in.txt').write_text(' '.join(ins[dom]))
        (out / f'io_{dom}_out.txt').write_text(' '.join(outs[dom]))
        io.append(f'set fi [open /work/io_{dom}_in.txt]; set pi [read $fi]; close $fi\n'
                  f'if {{[llength $pi]}} {{ set_input_delay {t:.1f} -clock {dom} [get_ports $pi] }}\n'
                  f'set fo [open /work/io_{dom}_out.txt]; set po [read $fo]; close $fo\n'
                  f'if {{[llength $po]}} {{ set_output_delay {t:.1f} -clock {dom} [get_ports $po] }}')
    tcl = f'''# cluster {a.name} GRT + CTS + TT/FF STA (tools/hbm_die_v15/cluster_case.py) -- NOT_A_DIE_RESULT
read_lef {plat}/lef/asap7_tech_1x_201209.lef
read_lef {plat}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{chr(10).join(f'read_lef /work/views/{m}.lef' for m in masters)}
define_corners tt ff
{chr(10).join(f'read_liberty -corner {k} /work/views/{m}_{k}.lib' for m in masters for k in ('tt', 'ff'))}
{chr(10).join(f'read_liberty -corner {k} {plat}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_{k.upper()}_nldm_220122.lib.gz' for k in ('tt', 'ff'))}
read_verilog /work/cluster.v
link_design cl_{a.name}
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site asap7sc7p5t
make_tracks M9 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M8 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M7 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064
make_tracks M6 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.016 -y_pitch 0.064
make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048
make_tracks M4 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.012 -y_pitch 0.048
make_tracks M3 -x_offset 0.009 -x_pitch {p_:.3f} -y_offset 0.009 -y_pitch {p_:.3f}
make_tracks M2 -x_offset 0.009 -x_pitch {p_:.3f} -y_offset 0.045 -y_pitch {p_:.3f}
make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
{plc}
place_pins -hor_layers M4 -ver_layers M5 -min_distance 0.2
write_db /work/out/place.odb
source {plat}/setRC.tcl
set_wire_rc -clock -layer M8
set_wire_rc -signal -layer M6
{clocks}
estimate_parasitics -placement
set r0 [clock seconds]
repair_design -max_wire_length {a.reach:.0f}
puts "OT_REPAIR_S [expr {{[clock seconds]-$r0}}] insts [llength [get_cells *]]"
set c0 [clock seconds]
if {{[catch {{clock_tree_synthesis -buf_list {{BUFx4_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx12_ASAP7_75t_R}} -root_buf BUFx16f_ASAP7_75t_R -sink_clustering_enable}} e]}} {{ puts "OT_CTS_FAIL $e" }}
puts "OT_CTS_S [expr {{[clock seconds]-$c0}}]"
set_routing_layers -signal M4-M9 -clock M5-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
set t0 [clock seconds]
global_route -congestion_iterations {a.congestion_iterations} -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
write_db /work/out/grt.odb
set ::env(OT_LAYOUT_OUT) /work/out/layout_dump.json
set ::env(OT_LAYOUT_LINKS) 1
set ::env(OT_LAYOUT_TOP) "hbm cluster {a.name} GRT"
if {{[catch {{source /work/layout_dump.tcl}} e]}} {{ puts "OT_LAYOUT_FAIL $e" }}
if {{[catch {{
  set grid [[ord::get_db_block] getGCellGrid]
  set gx [$grid getGridX]; set gy [$grid getGridY]
  set nx [llength $gx]; set ny [llength $gy]
  set sx [expr {{max(1, $nx / 256)}}]; set sy [expr {{max(1, $ny / 192)}}]
  set out [open /work/out/gcell_usage.txt w]
  puts $out "GRIDX [join $gx ,]"
  puts $out "GRIDY [join $gy ,]"
  puts $out "STRIDE $sx $sy"
  foreach ln {{M4 M5 M6 M7 M8 M9}} {{
    set layer [[ord::get_db_tech] findLayer $ln]
    for {{set j 0}} {{$j < $ny}} {{incr j $sy}} {{
      set row {{}}
      for {{set i 0}} {{$i < $nx}} {{incr i $sx}} {{ lappend row "[$grid getCapacity $layer $i $j]/[$grid getUsage $layer $i $j]" }}
      puts $out "L $ln $j [join $row {{ }}]"
    }}
  }}
  close $out
}} e]}} {{ puts "OT_GCELL_FAIL $e" }}
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
set_clock_groups -asynchronous {' '.join(f'-group {d}' for d in sorted(doms))}
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
{chr(10).join(io)}
if {{[llength [get_ports -quiet rst_*]]}} {{ set_false_path -from [get_ports rst_*] }}
foreach {{c k}} {{tt max ff min}} {{
  report_checks -corner $c -path_delay $k -group_path_count 20 -format full_clock_expanded -fields {{slew cap input_pins nets fanout}} > /work/out/worst_${{c}}_${{k}}.rpt
  report_wns -corner $c > /work/out/wns_${{c}}_${{k}}.rpt
  report_tns -corner $c >> /work/out/wns_${{c}}_${{k}}.rpt
}}
report_clock_skew -setup > /work/out/clock_skew.rpt
report_clock_skew -hold >> /work/out/clock_skew.rpt
puts OT_DONE
'''
    (out / 'run.tcl').write_text(tcl)
    shutil.copy(ROOT / 'tools/ref_tile/layout_dump.tcl', out / 'layout_dump.tcl')
    (out / 'run.sh').write_text('''#!/bin/bash
D=$(cd $(dirname $0) && pwd); N=hcl-$$
docker run --rm --name $N --cpus=${CPUS:-8} --memory=${MEMG:-128}g -v $D:/work -w /work openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/run.tcl > /work/out/run.log 2>&1; rc=\\$?; chmod -R a+rwX /work/out; exit \\$rc"
echo $? > $D/out/run.exit
''')
    info = dict(schema='opentallas.hbm.cluster_case.v1', name=a.name, rect=a.rect, case=str(a.case), contract=str(a.contract),
                instances=len(inside), masters={m: sum(1 for n in inside if pl[n]['m'] == m) for m in masters},
                internal_nets=len(nets), ports=len(ports), internal_bits=internal_bits, crossing_bits=cross_bits,
                clock_domains=sorted(doms), straps_open='as die_case_v16',
                crossing_by_family=[[f'{k[0]}->{k[1]}', v] for k, v in cross.most_common(60)],
                label='NOT_A_DIE_RESULT: regional cluster (SYNTH views are estimates)')
    (out / 'cluster.json').write_text(json.dumps(info, indent=1))
    print(json.dumps({k: info[k] for k in ('name', 'instances', 'internal_nets', 'ports', 'internal_bits', 'crossing_bits', 'clock_domains')}))


if __name__ == '__main__':
    main()
