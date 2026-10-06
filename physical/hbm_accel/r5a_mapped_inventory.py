#!/usr/bin/env python3
"""Join actual loaded-ODB rows to SS/FF Liberty pin caps; no STA or synthesis."""
import argparse
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group(text, start):
    begin = text.index('{', start)
    depth = 1
    end = begin + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[begin + 1:end - 1]


def caps(paths):
    result = {}
    for path in paths:
        raw = path.read_bytes()
        text = (gzip.decompress(raw) if path.suffix == '.gz' else raw).decode()
        if not re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)', text):
            raise ValueError('Liberty must declare fF: ' + str(path))
        for cell in re.finditer(r'\bcell\s*\(([^)]+)\)', text):
            body = group(text, cell.start())
            for pin in re.finditer(r'\b(?:pin|bus)\s*\(([^)]+)\)', body):
                value = re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)', group(body, pin.start()))
                if value:
                    key = (cell[1].strip().strip('"'), pin[1].strip().strip('"'))
                    cap = float(value[1])
                    if key in result and result[key] != cap:
                        raise ValueError('ambiguous actual pin capacitance: ' + str(key))
                    result[key] = cap
    return result


def inventory(rows_path, libraries, expected_macros):
    rows = collections.defaultdict(list)
    for line in rows_path.read_text().splitlines():
        kind, *fields = [bytes.fromhex(x).decode() for x in line.split('\t')]
        rows[kind].append(fields)
    units = int(rows['db_units_per_micron'][0][0])
    masters = [dict(master=n, count=int(c), type=t,
                    width_um=int(w)/units, height_um=int(h)/units,
                    total_area_um2=int(c)*int(w)*int(h)/units**2)
               for n, c, t, w, h in rows['master']]
    macros = sum(r['count'] for r in masters if r['type'] == 'BLOCK')
    if macros != expected_macros:
        raise ValueError(f'actual macro inventory {macros} != {expected_macros}')

    def pin_cap(master, pin, corner):
        lib = libraries[corner]
        key = (master, pin)
        if key not in lib:
            key = (master, re.sub(r'\[\d+\]$', '', pin))
        return lib[key]  # Unknown is fatal, never a zero or guessed cap.

    clocks = []
    for name, master, pin, net, domains in rows['clock_sink']:
        clocks.append(dict(instance_pin=name, master=master, pin=pin, net=net,
                           declared_clocks=domains.split(',') if domains else [],
                           pin_cap_fF={c:pin_cap(master, pin, c) for c in libraries}))
    macro_clocks = sum(r['master'].startswith('ot_sram_') for r in clocks)
    if macro_clocks != expected_macros:
        raise ValueError(f'actual SRAM clock inventory {macro_clocks} != {expected_macros}')
    inputs = collections.defaultdict(lambda: collections.Counter())
    for port, inst, master, pin, net in rows['input_sink']:
        inputs[port][(master, pin)] += 1
    input_loads = [dict(port=p, direct_sink_count=sum(counts.values()),
                        pin_cap_fF={c:sum(n*pin_cap(m, pin, c) for (m, pin), n in counts.items())
                                    for c in libraries}) for p, counts in sorted(inputs.items())]
    return dict(mapped_masters=masters, macro_count=macros,
                standard_cell_area_um2=sum(r['total_area_um2'] for r in masters if r['type'] != 'BLOCK'),
                macro_area_um2=sum(r['total_area_um2'] for r in masters if r['type'] == 'BLOCK'),
                clock_sinks=clocks, clock_roots=rows['clock_root'],
                clock_drivers=rows['clock_driver'], capture_output_nets=rows['capture_output'],
                direct_input_pin_loads=input_loads, ports=rows['port'],
                macro_clock_sinks=macro_clocks,
                pin_only=True, routed_wire_capacitance=None, measured_CTS_insertion=None,
                actual_parent_boundary_minmax=None, physical_qualification=False,
                protection='bench applied-fault evidence retained; inspect actual capture nets for rail/state survival; this inventory grants no protection waiver')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rows', type=Path, required=True)
    ap.add_argument('--ss-lib', type=Path, action='append', required=True)
    ap.add_argument('--ff-lib', type=Path, action='append', required=True)
    ap.add_argument('--expected-macros', type=int, default=96)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--odb', type=Path, required=True)
    ap.add_argument('--sdc', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    result = inventory(a.rows, {'ss':caps(a.ss_lib), 'ff':caps(a.ff_lib)}, a.expected_macros)
    result.update(source_commit=a.source_commit,
                  sha256={str(p):sha(p) for p in [a.rows, a.odb, a.sdc, *a.ss_lib, *a.ff_lib]},
                  helper_sha256={p:sha(ROOT/p) for p in (
                      'physical/hbm_accel/r5a_mapped_inventory.py',
                      'physical/hbm_accel/r5a_mapped_inventory.tcl',
                      'tools/run_abi3_physical.py', 'tools/orfs_allcorner_spef.py')})
    with a.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
