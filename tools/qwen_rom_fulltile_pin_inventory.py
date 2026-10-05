#!/usr/bin/env python3
"""Read-only actual mapped pin loads. Pin capacitance is not routed timing."""
import argparse, collections, hashlib, json, re
from pathlib import Path
from qwen_rom_fulltile_mapped_gate import TOP
from qwen_rom_hold_capture_loaded_map import block

def caps(text):
    if not re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)', text):
        raise ValueError('require actual fF units')
    result = {}
    for c in re.finditer(r'\bcell\s*\(([^)]+)\)', text):
        body = block(text, c.start())
        for p in re.finditer(r'\bpin\s*\(([^)]+)\)', body):
            pb = block(body, p.start())
            v = re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)', pb)
            if v:
                result[(c[1].strip().strip('"'), p[1].strip().strip('"'))] = float(v[1])
    return result

def inventory(work):
    net = json.loads((work/'mapped.json').read_text())['modules'][TOP]
    libraries = caps((work/'ss_merged.lib').read_text())
    portable = json.loads((work/'portable_inputs.json').read_text())
    for source, rel in portable.items():
        if 'asap7_memory_macros' in source and source.endswith('_ss.lib'):
            libraries.update(caps((work/rel).read_text()))
    boundary = collections.defaultdict(list)
    for name, p in net['ports'].items():
        if p['direction'] == 'input':
            for i, b in enumerate(p['bits']): boundary[b].append(f'{name}[{i}]')
    counts = collections.Counter()
    for name, cell in net['cells'].items():
        if cell['type'] == '$scopeinfo': continue
        for pin, bits in cell['connections'].items():
            if cell['port_directions'][pin] != 'input': continue
            for b in bits:
                if pin in ('CLK','RESETN') or pin == 'clk' or b in boundary:
                    key = (cell['type'], pin, str(b), tuple(boundary.get(b, [])))
                    if (cell['type'], pin) not in libraries: raise ValueError('unknown actual pin capacitance '+str(key))
                    counts[key] += 1
    rows = [dict(cell=c, pin=p, net=n, parent_input_bits=list(ports), sinks=k,
                 ss_pin_cap_fF=libraries[c,p], ss_total_pin_cap_fF=k*libraries[c,p])
            for (c,p,n,ports),k in sorted(counts.items())]
    return dict(schema='QWEN_ACTUAL_FULLTILE_PIN_LOADS_V1',
        mapped_sha256=hashlib.sha256((work/'mapped.json').read_bytes()).hexdigest(),
        clock_sinks=sum(r['sinks'] for r in rows if r['pin'].lower()=='clk'),
        async_reset_sinks=sum(r['sinks'] for r in rows if r['pin']=='RESETN'),
        rows=rows, corner='ss', pin_only=True, asbuilt_replica_gate='FAIL',
        ff_corner_capacitance=None, wire_capacitance=None, CTS=None,
        actual_parent_min_max_arrivals=None, contextual_SSFF=False,
        selected_corridor_um=96.768, selected_complete_cell_ceiling_um2=125000)

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists(): raise SystemExit('refuse overwrite')
    a.out.write_text(json.dumps(inventory(a.work),indent=2)+'\n')
