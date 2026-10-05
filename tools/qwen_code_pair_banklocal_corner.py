#!/usr/bin/env python3
"""Time the protected pair with real macro views and inspect its capture pins.

Reuses the routed SS/FF reader. Capture distances are geometric lower bounds,
not routed wire lengths or substitutes for extracted timing.
"""
import argparse
import json
from pathlib import Path
import qwen_code_pair_directcapture_corner as sta


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--orfs-dir', type=Path, required=True)
    ap.add_argument('--source-dir', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    work = args.orfs_dir.resolve()
    bindings = json.loads((work / 'capture_bindings.json').read_text())
    targets = {(t['column'], t['bank'], t['coded_bit']): t for t in
               json.loads((work / 'slot/capture_bit_locality.json').read_text())}
    assert len(bindings) == len(targets) == 2880
    original_script = sta.script
    lines = ['set block [ord::get_db_block]',
             'set units [$block getDbUnitsPerMicron]',
             'set out [open /work/capture_positions.tsv w]',
             'proc xy {inst pin} {',
             ' set term [$inst findITerm $pin]',
             ' if {$term eq "NULL" || $term eq ""} {error "Missing actual pin $pin"}',
             ' set pos [$term getAvgXY]',
             ' if {[llength $pos]!=3 || ![lindex $pos 0]} {error "Missing pin geometry $pin"}',
             ' return [lrange $pos 1 2]',
             '}']
    for b in bindings:
        key = b['column'], b['bank'], b['coded_bit']
        target = targets[key]
        # Names come from the retained mapped netlist, never inferred ordering.
        lines += [f'set inst [$block findInst {{{b["synthesized_cell"]}}}]',
                  'if {$inst eq "NULL" || $inst eq ""} {error "Missing retained capture FF"}',
                  'set pos [xy $inst D]',
                  'set box [$inst getBBox]',
                  f'set prefix "{key[0]}\t{key[1]}\t{key[2]}"',
                  'set row [list $prefix [expr {[lindex $pos 0]/double($units)}] [expr {[lindex $pos 1]/double($units)}] [expr {[$box xMin]/double($units)}] [expr {[$box yMin]/double($units)}] [expr {[$box xMax]/double($units)}] [expr {[$box yMax]/double($units)}]]']
        pin = target['source_pin']
        if pin is not None:
            lines += [f'set macro [$block findInst {{{pin["instance"]}}}]',
                      f'set src [xy $macro {{{pin["pin"]}}}]',
                      'lappend row [expr {[lindex $src 0]/double($units)}] [expr {[lindex $src 1]/double($units)}]']
        lines += ['puts $out [join $row "\t"]']
    lines += ['close $out']

    def script(corner, base, macros):
        text = original_script(corner, base, macros)
        return text.replace('\nexit\n', '\n' + '\n'.join(lines) + '\nexit\n') if corner == 'ss' else text

    sta.ROOT = args.source_dir.resolve()
    sta.script = script
    sta.main(['--orfs-dir', str(work), '--output', str(args.output),
              '--macro', 'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2',
              '--macro', 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2'])
    positions = work / 'capture_positions.tsv'
    result = {'expected_capture_bits': 2880, 'checked_capture_bits': 0,
              'outside_bank_fence': [], 'source_pin_distance_lower_bound_exceeds_budget': [],
              'distance_scope': 'Actual routed ODB pin Manhattan distance; lower bound only, not routed copper length.'}
    if positions.exists():
        for row in positions.read_text().splitlines():
            fields = row.split('\t')
            p, b, bit = map(int, fields[:3])
            dx, dy, xmin, ymin, xmax, ymax = map(float, fields[3:9])
            target = targets[p, b, bit]
            fx, fy = 185.544 + p * 473.472, 8.64 + b * 96.66
            result['checked_capture_bits'] += 1
            if xmin < fx - 1e-6 or xmax > fx + 17.28 + 1e-6 or ymin < fy - 1e-6 or ymax > fy + 51.84 + 1e-6:
                result['outside_bank_fence'].append([p, b, bit])
            if target['source_pin'] is not None:
                sx, sy = map(float, fields[9:11])
                distance = abs(sx - dx) + abs(sy - dy)
                if distance > target['required_data_route_length_um']:
                    result['source_pin_distance_lower_bound_exceeds_budget'].append(
                        dict(column=p, bank=b, coded_bit=bit, minimum_um=distance,
                             budget_um=target['required_data_route_length_um']))
    result['all_capture_bits_present_in_bank_fence'] = result['checked_capture_bits'] == 2880 and not result['outside_bank_fence']
    (work / 'capture_locality.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
