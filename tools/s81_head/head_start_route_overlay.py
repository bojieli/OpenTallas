#!/usr/bin/env python3
"""Put mapped, placed HEAD START cells into the reviewed raw clock/signal vehicle.

Inputs are actual synthesis JSON and an exact cell/pin placement manifest. This
writer never substitutes planned flop counts for cells and never launches P&R.
The resulting prototype still uses partition signal abstracts; it is not G4.
"""
import argparse
import json
import math
import re
from pathlib import Path


def word(s):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', s):
        raise ValueError(f'unsupported identifier {s!r}')
    return s


def finite_xy(x):
    if len(x) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in x):
        raise ValueError(f'invalid actual cell/pin coordinate {x!r}')
    return x


def overlay(base_v, base_tcl, mapped, top, stages, physical):
    mod = mapped['modules'][top]
    ports, cells = mod['ports'], mod['cells']
    clocks = {s['clock_port'] for s in stages['stages']}
    local_clocks=physical.get('stage_clock_drivers',{})
    if local_clocks and set(local_clocks)!=clocks:
        raise ValueError('local clock-entry drivers must cover every virtual stage')
    expected = set(ports) - clocks
    if not clocks or not clocks <= set(ports):
        raise ValueError('mapped provider lost declared START clock inputs')
    if set(physical['ports']) != expected:
        raise ValueError('physical START boundary does not cover exact mapped ports')
    if set(physical['cells']) != set(cells):
        raise ValueError('physical START placement does not cover exact mapped cells')
    if physical.get('reset_form') != 'local_wavefront':
        raise ValueError('physical START provider requires local wavefront reset delivery')
    if any(p.startswith(('rst','wrst_')) and physical['ports'][p].get('source_kind') != 'registered_wavefront'
           for p in expected if ports[p]['direction'] == 'input'):
        raise ValueError('START raw reset boundary is not a registered wavefront source')
    mh = re.search(r'module\s+die_combo\s*\(([^)]*)\);', base_v)
    if mh is None:
        raise ValueError('expected one raw die_combo module')
    raw_ports = [p.strip() for p in mh[1].split(',') if p.strip()]
    if not clocks <= set(raw_ports):
        raise ValueError('raw clock vehicle lacks patched physical START clock taps')
    pub = [p for p in raw_ports if p not in clocks]
    decl, extra, place = [], [], []
    bits = set()
    for p, info in ports.items():
        if len(info['bits']) != 1:
            raise ValueError('START overlay currently requires scalar ports')
        if p in clocks:
            if info['direction'] != 'input':
                raise ValueError('START stage clock is not an input')
            continue
        target = word('start_' + p)
        if target in pub:
            raise ValueError('START boundary name collision')
        pub.append(target)
        if info['direction'] not in ('input', 'output'):
            raise ValueError('inout START boundary is not supported')
        decl.append(f"{info['direction']} {target};")
        row = physical['ports'][p]
        x, y = finite_xy(row['xy_um'])
        layer = row['layer']
        if layer not in ('M4', 'M5', 'M6', 'M7'):
            raise ValueError('START/reset partition boundary must use M4-M7')
        place.append(f'place_pin -pin_name {target} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{0.04 0.04}}')
    def net(b):
        if isinstance(b, int):
            bits.add(b)
            return 'start_b_' + str(b)
        if b in ('0', '1'):
            return "1'b" + b
        raise ValueError('unmapped X/Z in synthesized START source')
    for p, info in ports.items():
        b = net(info['bits'][0])
        if p in clocks:
            if p in local_clocks:
                q=local_clocks[p]
                if q['cell']!='BUFx8_ASAP7_75t_R':raise ValueError('unplanned local clock-driver master')
                inst=word(q['inst']);x,y=finite_xy(q['xy_um'])
                extra.append(f'{q["cell"]} {inst} (.A({word(p)}), .Y({b}));')
                place.append(f'ot_place {inst} {x:.3f} {y:.3f} {q.get("orient","R0")}')
            else:
                extra.append(f'assign {b} = {word(p)};')
        elif info['direction'] == 'input':
            extra.append(f'assign {b} = start_{word(p)};')
        else:
            extra.append(f'assign start_{word(p)} = {b};')
    names = {}
    clock_bits = {ports[n]["bits"][0]: n for n in clocks}
    clock_pins = {n: [] for n in clocks}
    ff_count = 0
    for i, (name, cell) in enumerate(sorted(cells.items())):
        typ = cell['type']
        if not re.fullmatch(r'\w+_ASAP7_75t_R', typ) or cell.get('parameters'):
            raise ValueError(f'provider is not flat RVT standard cells: {name} ({typ})')
        pins = []
        for p, conn in sorted(cell['connections'].items()):
            if len(conn) != 1:
                raise ValueError(f'non-scalar mapped cell pin {name}/{p}')
            pins.append(f'.{word(p)}({net(conn[0])})')
        inst = f'start_cell_{i}'
        extra.append(f'{typ} {inst} (' + ', '.join(pins) + ');')
        row = physical['cells'][name]
        x, y = finite_xy(row['xy_um'])
        if row.get('cell') != typ or not row.get('stage'):
            raise ValueError('placement cell master/stage mismatch')
        place.append(f'ot_place {inst} {x:.3f} {y:.3f} {row.get("orient", "R0")}')
        names[name] = inst
        is_ff = typ.startswith(('DFF', 'SDFF'))
        ff_count += is_ff
        if is_ff:
            ck = cell['connections'].get('CLK')
            if not ck or len(ck) != 1 or ck[0] not in clock_bits:
                raise ValueError('actual START FF clock is not a declared stage clock input')
            clock_pins[clock_bits[ck[0]]].append(inst+'/CLK')
    if ff_count != stages['counts']['flops']:
        raise ValueError(f'actual mapped START flop count {ff_count} differs from manifest {stages["counts"]["flops"]}')
    body = base_v[mh.end():base_v.rindex('endmodule')]
    for p in sorted(clocks):
        body, n = re.subn(r'\boutput\s+' + re.escape(p) + r'\s*;', 'wire ' + p + ';', body)
        if n != 1:
            raise ValueError('patched clock tap declaration not unique')
    v = ('module die_combo (' + ', '.join(pub) + ');\n' + '\n'.join(decl) + '\n' + body + '\n' +
         '\n'.join(f'wire start_b_{b};' for b in sorted(bits)) + '\n' + '\n'.join(extra) + '\nendmodule\n')
    t = base_tcl
    t=t.replace('estimate_parasitics -global_routing','estimate_parasitics -global_routing\nwrite_spef /out/paras_$::env(CORNER).spef',1)
    for p in clocks:
        t = re.sub(r'^place_pin -pin_name ' + re.escape(p) + r'\s+.*\n', '', t, flags=re.M)
    marker = 'global_route -congestion_iterations 50'
    if t.count(marker) != 1:
        raise ValueError('expected one reviewed GRT50 route command')
    t = t.replace(marker, '\n'.join(place) + '\n' + marker, 1)
    if any(not q for q in clock_pins.values()):
        raise ValueError('a declared stage clock has no actual mapped FF load')
    # CLK pins carry a synthetic zero-arrival unclocked seed in OpenSTA.
    # Keep only real paths launched by the root port; no new clock or phase
    # constraint is introduced, and the original data-waveform reference stays.
    readout=['proc ot_root_arrival {pin edge mm} {', '  if {$mm eq "min"} {set best 1e30} else {set best -1e30}', '  set seen 0', '  foreach vertex [$pin vertices] {', '    if {$vertex eq "NULL"} {continue}', '    set iter [$vertex path_iterator $edge $mm]', '    while {[$iter has_next]} {', '      set path [$iter next]', '      set start [$path start_path]', '      set name [get_full_name [$start pin]]', '      if {$name ne "root"} {continue}', '      set value [get_property $path arrival]', '      incr seen', '      if {$mm eq "min"} {set best [expr {min($best,$value)}]} else {set best [expr {max($best,$value)}]}', '    }', '    $iter finish', '  }', '  if {!$seen} {error "no actual root-path arrival at [get_full_name $pin] $edge $mm"}', '  return $best', '}']+['set sh [open /out/arr_$::env(CORNER).txt a]']
    for clk, pins in sorted(clock_pins.items()):
        readout += ['set st_late_rise -1e30; set st_early_rise 1e30; set st_late_fall -1e30; set st_early_fall 1e30',
                    'foreach name {'+' '.join(pins)+'} {',
                    '  set p [get_pins $name]; if {[llength $p] != 1} {error "missing actual START FF clock pin $name"}',
                    '  foreach edge {rise fall} {',
                    '    set late [ot_root_arrival $p $edge max]; set early [ot_root_arrival $p $edge min]',
                    '    if {![string is double -strict $late] || ![string is double -strict $early] || [regexp -nocase {inf|nan} "$late $early"]} {error "untimed actual START FF clock pin $name"}',
                    '    set st_late_$edge [expr {max([set st_late_$edge],$late)}]',
                    '    set st_early_$edge [expr {min([set st_early_$edge],$early)}]',
                    '  }', '}',
                    f'puts $sh "T {clk} $st_late_rise $st_early_rise"',
                    f'puts $sh "F {clk} $st_late_fall $st_early_fall"']
    readout.append('close $sh')
    timing_marker='report_check_types -max_slew'
    if t.count(timing_marker)!=1:
        raise ValueError('expected one post-GRT timing readout insertion point')
    t=t.replace(timing_marker,'\n'.join(readout)+'\n'+timing_marker,1)
    receipt = dict(scope='actual mapped START cells and clock loads, raw partition signal abstracts; NOT G4',
                   cells=len(cells)+len(local_clocks), mapped_cells=len(cells), local_clock_drivers=len(local_clocks), flops=ff_count, internal_stage_clocks=len(clocks),
                   boundary_ports=len(expected), cell_names=names, stage_clock_pins=clock_pins, reset_form=physical['reset_form'],
                   physical_timing='NOT RUN', logical_cycles_added=0)
    return v, t, receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ('base', 'mapped', 'top', 'stages', 'physical', 'out'):
        ap.add_argument('--' + n, required=True)
    a = ap.parse_args()
    base, out = Path(a.base), Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    v, t, r = overlay((base/'combo.v').read_text(), (base/'combo.tcl').read_text(),
                      json.loads(Path(a.mapped).read_text()), a.top, json.loads(Path(a.stages).read_text()),
                      json.loads(Path(a.physical).read_text()))
    # Preserve the base's reviewed route recipe; its /out paths refer to this successor.
    (out/'combo.v').write_text(v)
    (out/'combo.tcl').write_text(t)
    (out/'start_overlay.json').write_text(json.dumps(r, indent=1))
    print(json.dumps({k:v for k,v in r.items() if k not in ('cell_names','stage_clock_pins')}))


if __name__ == '__main__':
    main()
