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
die_case_v16 (listed).
Boundary (ROOT CLUSTER-FLOW 10-16, shared tools/die_cluster/boundary.py; pilot_SW GRT-0028 + pilot_SW2 GRT-0035/STT-0009):
every placed body is fully inside or fully outside the rect (--body-policy cut (default): each rect edge moves to the
nearest line within 60 um no body crosses, then snap; snap: a straddler moves the least distance to
the side holding its centre, refused on overlap, moves written to boundary.json for the parent; grow = legacy outline
growth; fail).  Every port is pinned ON the outline where the line from its inside pin(s) to its outside pin(s) in the
parent placement crosses it, track-legal, FIXED (place_pin; no place_pins).  The core is inset so repair buffers
legalise inside (detailed_placement after repair), and cluster_bounds.tcl fails the run before GRT if any cell or pin is
outside the die or any port is off the outline.
Flow: place (FIRM, die coordinates - origin) -> boundary pins -> repair_design -max_wire_length REACH (buffers inserted =
residual long wires, reported) -> legalise -> [--cts tritoncts only; default none: DIE-CLOCK regional roots via
tools/die_clock/build.py on out/grt.odb, no die-scale CTS in clusters] -> bounds check -> GRT (congestion report +
gcell map + layout dump) -> TT setup / FF hold STA with boundary IO at 0.2 T (ideal clocks when --cts none).
NOT_A_DIE_RESULT: SYNTH views are estimates.
"""
import argparse, collections, json, re, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from die_cluster import boundary as CB  # noqa: E402
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
    ap.add_argument('--body-policy', choices=('cut', 'snap', 'grow', 'fail'), default='cut')
    ap.add_argument('--cts', choices=('none', 'tritoncts'), default='none',
                    help='none (default, DIE-CLOCK rule: regional roots via tools/die_clock/build.py on the cluster ODB)')
    ap.add_argument('--pin-spacing-tracks', type=int, default=2)
    ap.add_argument('--allowed-edges', default='NESW', help='outline edges that may carry ports (die-edge sides excluded)')
    ap.add_argument('--max-pin-density', type=float, default=6.0)
    ap.add_argument('--allow-boundary-errors', action='store_true', help='write the case although boundary.json has errors')
    a = ap.parse_args()
    C = json.loads(a.contract.read_text())
    man = json.loads((a.case / 'manifest.json').read_text())
    pl = man['placement']
    # every body fully inside or fully outside (pilot SW 10-16: a relay straddling the rect put 1,024 pins outside the
    # die -> GRT-0028); snapped moves go back to the parent plan (boundary.json 'moved')
    rb = CB.resolve_bodies(a.rect, [dict(name=n, master=v['m'], x=v['x'], y=v['y'], w=v['w'], h=v['h'], orient=v['o'])
                                    for n, v in pl.items()], a.body_policy)
    pl = {n: dict(v) for n, v in pl.items()}
    for mv in rb['moved']:
        pl[mv['name']]['x'], pl[mv['name']]['y'] = mv['to']
    inside = {b['name'] for b in rb['inside']}
    x0, y0, x1, y1 = rb['outline']
    I = C['instances']
    # port widths from the contract
    width = {n: {p: d['bits'] for p, d in I[n]['ports'].items()} for n in inside}
    pdir = {n: {p: d['direction'] for p, d in I[n]['ports'].items()} for n in inside}
    pin = lambda n, p, k: f'{p}[{k}]' if width[n][p] > 1 else p
    vd = a.case / 'views'
    lefc = {}
    def lef(m):
        if m not in lefc:
            f = vd / f'{m}.lef'
            lefc[m] = CB.parse_lef_pins(f.read_text()).get(m) if f.exists() else None
        return lefc[m]
    def pxy(n, p, k):
        if n not in pl:
            return None
        v = pl[n]
        nm = f'{p}[{k}]' if I.get(n, {}).get('ports', {}).get(p, {}).get('bits', 1) > 1 else p
        info = lef(v['m'])
        return CB.pin_xy(dict(master=v['m'], x=v['x'], y=v['y'], w=v['w'], h=v['h'], orient=v['o']), nm,
                         {v['m']: info} if info else {})
    pin_in = collections.defaultdict(list); pin_out = collections.defaultdict(list)
    conn = collections.defaultdict(dict)          # inst -> {pin: net}
    ports = {}                                     # port name -> (direction, domain)
    nets = set()
    cross = collections.Counter(); cross_bits = 0; internal_bits = 0
    over_reach = collections.Counter(); max_span = 0.0
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
                    if not pin_in[nm]:
                        pin_in[nm].append(pxy(si, sp, slo + k))
                    q = pxy(ti, tp, tlo + k)
                    if q:
                        pin_out[nm].append(q)
            if tin:
                conn[ti][pin(ti, tp, tlo + k)] = nm
                if not sin:
                    pin_in[nm].append(pxy(ti, tp, tlo + k))
                    if not pin_out[nm]:
                        q = pxy(si, sp, slo + k)
                        if q:
                            pin_out[nm].append(q)
        if sin and tin:
            internal_bits += nb
            for k in (0, nb - 1) if nb > 1 else (0,):  # first/last bit: pin-to-pin span vs the reach (repair load)
                ps, pt = pxy(si, sp, slo + k), pxy(ti, tp, tlo + k)
                span = abs(ps[0] - pt[0]) + abs(ps[1] - pt[1])
                if span > a.reach:
                    over_reach[(re.sub(r'\d', '#', si), re.sub(r'\d', '#', ti))] += nb if k == 0 else 0
                    max_span = max(max_span, span)
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
        if not pin_out[pn] and cr.get('source') and cr['source'][0] in pl:
            src = pl[cr['source'][0]]
            pin_out[pn].append((src['x'] + src['w'] / 2, src['y'] + src['h'] / 2))
        for k in range(cr.get('bits', 1)):
            pin_in[pn].append(pxy(n, cr['port'], k))
            conn[n][pin(n, cr['port'], k) if cr.get('bits', 1) > 1 else cr['port']] = pn
    nets -= set(ports)
    masters = sorted({pl[n]['m'] for n in inside})
    pa = CB.assign_pins(rb['outline'], [dict(name=p, direction=d, inside=[q for q in pin_in[p] if q],
                                             outside=pin_out[p]) for p, (d, _) in sorted(ports.items())],
                        rb['inside'], a.allowed_edges, spacing_tracks=a.pin_spacing_tracks,
                        max_density_per_um=a.max_pin_density)
    berr = rb['errors'] + pa['errors']
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
    (out / 'pins.tcl').write_text(CB.pins_tcl(pa['pins']))
    shutil.copy(CB.bounds_tcl_path(), out / 'cluster_bounds.tcl')
    (out / 'boundary.json').write_text(json.dumps(dict(
        schema='opentallas.die_cluster.boundary.v1', name=a.name, rect=a.rect, outline=rb['outline'],
        body_policy=a.body_policy, inside=len(rb['inside']), cut_shifts=rb['cut_shifts'], moved=rb['moved'],
        pins=pa['report'],
        pin_sample=pa['pins'][:50], errors=berr), indent=1))
    if berr and not a.allow_boundary_errors:
        print(json.dumps(dict(name=a.name, boundary_errors=berr[:10])), file=sys.stderr)
        sys.exit(2)
    plat = '/OpenROAD-flow-scripts/flow/platforms/asap7'
    p_ = 9.6 / 15.0
    plc = '\n'.join(f'place_inst -name {n} -location {{{pl[n]["x"] - x0:.3f} {pl[n]["y"] - y0:.3f}}} -orientation {pl[n]["o"]} -status FIRM'
                    for n in sorted(inside))
    cts = ('' if a.cts == 'none' else
           'set c0 [clock seconds]\n'
           'if {[catch {clock_tree_synthesis -buf_list {BUFx4_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx12_ASAP7_75t_R} '
           '-root_buf BUFx16f_ASAP7_75t_R -sink_clustering_enable} e]} { puts "OT_CTS_FAIL $e" }\n'
           'puts "OT_CTS_S [expr {[clock seconds]-$c0}]"\n' + CB.legalize_tcl('cts') + '\n')
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
{CB.floorplan_tcl(W, H)}
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
source /work/pins.tcl
{CB.bounds_check_tcl('/work/out/cluster_bounds_place.json', 'post_place')}write_db /work/out/place.odb
source {plat}/setRC.tcl
set_wire_rc -clock -layer M8
set_wire_rc -signal -layer M6
{clocks}
estimate_parasitics -placement
set r0 [clock seconds]
repair_design -max_wire_length {a.reach:.0f}
puts "OT_REPAIR_S [expr {{[clock seconds]-$r0}}] insts [llength [get_cells *]]"
{CB.legalize_tcl('repair')}
{cts}{CB.bounds_check_tcl('/work/out/cluster_bounds.json', 'pre_grt')}set_routing_layers -signal M4-M9 -clock M5-M9
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
{'set_propagated_clock [all_clocks]' if a.cts != 'none' else '# --cts none: ideal clocks (regional roots by DIE-CLOCK on out/grt.odb)'}
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
                clock_domains=sorted(doms), straps_open='as die_case_v16', outline=rb['outline'],
                body_policy=a.body_policy, bodies_moved=len(rb['moved']), boundary_errors=len(berr), cts=a.cts,
                pins_per_edge={e: v['ports'] for e, v in pa['report']['edges'].items()},
                crossing_by_family=[[f'{k[0]}->{k[1]}', v] for k, v in cross.most_common(60)],
                internal_bits_over_reach=sum(over_reach.values()), internal_max_span_um=round(max_span, 1),
                over_reach_by_family=[[f'{k[0]}->{k[1]}', v] for k, v in over_reach.most_common(40)],
                label='NOT_A_DIE_RESULT: regional cluster (SYNTH views are estimates)')
    (out / 'cluster.json').write_text(json.dumps(info, indent=1))
    print(json.dumps({k: info[k] for k in ('name', 'instances', 'internal_nets', 'ports', 'internal_bits', 'crossing_bits',
                                           'internal_bits_over_reach', 'internal_max_span_um', 'bodies_moved',
                                           'boundary_errors', 'pins_per_edge', 'clock_domains')}))


if __name__ == '__main__':
    main()
