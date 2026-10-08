#!/usr/bin/env python3
"""Snapshot the existing VM8 physical contract; never qualify pending routes."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('physical/hbm_accel_die_views/vm/split8')
OUT = Path('results/physical/hbm_vm8_contract_20261007')


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def build():
    recovery = json.loads((ROOT / 'results/rtl/hbm_vm8_recovery_20261007.json').read_text())
    jobs = {j['name'].split('_')[2]: j for j in recovery['jobs']}
    masters = {}
    sources = {}
    pin_pattern = re.compile(r'place_pin -pin_name \{(\w+)\[(\d+)\]\} -layer (\w+) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}')
    for q in ('sw', 'nw', 'se', 'ne'):
        for half in ('s', 'n'):
            name = f'hfd_vm_{q}_{half}'
            record_path = BASE / 'ports' / name / 'ports.json'
            pin_path = record_path.with_name('io_place.tcl')
            rtl_path = BASE / f'{name}.sv'
            record = json.loads((ROOT / record_path).read_text())
            rtl = (ROOT / rtl_path).read_text()
            declarations = {n: (d, int(hi) - int(lo) + 1) for d, hi, lo, n in re.findall(r'(input|output) wire \[(\d+):(\d+)\] (\w+)', rtl)}
            assert declarations == {n: (p['direction'], p['bits']) for n, p in record['ports'].items()}, name
            pins = {}
            for port, bit, layer, x, y, w, h in pin_pattern.findall((ROOT / pin_path).read_text()):
                key = f'{port}[{bit}]'
                assert key not in pins, key
                pins[key] = [layer, float(x), float(y), float(w), float(h)]
            expected = {f'{n}[{i}]' for n, p in record['ports'].items() for i in range(p['bits'])}
            assert set(pins) == expected, name
            assert all(0 <= p[1] <= record['w_um'] and 0 <= p[2] <= record['h_um'] for p in pins.values())
            job = jobs[q + half]
            for p in (record_path, pin_path, rtl_path):
                sources[str(p)] = digest(p)
            masters[name] = dict(width_um=record['w_um'], height_um=record['h_um'], ports=record['ports'],
                pin_encoding=['layer', 'center_x_um', 'center_y_um', 'width_um', 'height_um'], pins=pins,
                rtl_source=dict(path=str(rtl_path), sha256=digest(rtl_path), commit=job['source_commit']),
                clock=dict(port='ck[0]', domain='streaming', period_ns=0.833, setup_uncertainty_ps=60, hold_uncertainty_ps=25),
                route_job=job['name'], physical_qualification='PENDING_REAL_ROUTE_AND_DIE_BUDGET')
    latency_path = BASE / 'bench_654733cc5/m2_8vs4.check'
    paths = {}
    for line in (ROOT / latency_path).read_text().splitlines():
        if ': ' not in line:
            continue
        name, value = line.split(': ', 1)
        ranges = []
        for hi, lo, delay in re.findall(r'\[(\d+):(\d+)\]=(\d+|clk)', value):
            ranges.append(dict(msb=int(hi), lsb=int(lo), added_cycles=None if delay == 'clk' else int(delay), forwarded_clock=delay == 'clk'))
        assert ranges, line
        paths[name] = ranges
    sources[str(latency_path)] = digest(latency_path)
    bench_path = BASE / 'bench_654733cc5/vm8_bench.log'
    log = (ROOT / bench_path).read_text()
    for required in ('VM_SPLIT8_BENCH PASS', 'VM_SPLIT8_NEG_XBUS_DETECTED', 'VM_SPLIT8_NEG_SEAM_DETECTED', 'VM_PORT_DEPTH_NEG_DETECTED', 'unmatched_bits=0'):
        assert required in log, required
    sources[str(bench_path)] = digest(bench_path)
    return dict(schema='opentallas.hbm.vm8.contract.v1', adopted=False, masters=masters, sources_sha256=sources,
        pins_scope='Exact committed requested pin placement, not a harvested routed LEF.',
        geometry=dict(parent_height_um=1000.056, child_height_um=500.04, current_north_offset_um=500.016,
                      current_outline_overlap_um=0.024, minimum_nonoverlap_height_um=1000.08),
        measured_latency=dict(reference='four quadrant VM', seam_cycles=2, paths=paths,
            note='Per-bit measured increments; do not substitute a uniform +2 or multiply all bits into token latency. Forwarded clocks have no data latency.'),
        exactness=dict(positive_event_counts=[40,55,60], structural_cycles=442, unmatched_bits=0,
            negatives=['cross_bus', 'seam', 'monolithic_write_port_depth_skew'],
            scope='Historical preserved component evidence; final scheduler/CDC joins still require qualification.'),
        adoption_blockers=['Eight terminal SS/FF routed views and DRC evidence', 'Die-specific IO budgets and clock arrival qualification',
            'Resolve 0.024 um half-outline overlap', 'Price transaction-specific +0/+2/+4/+8 paths using actual schedule',
            'Qualify complete control/data alignment and protection at the die join'])


if __name__ == '__main__':
    out = ROOT / OUT / 'contract.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    contract = build()
    out.write_text(json.dumps(contract, separators=(',', ':')) + '\n')
    print(json.dumps(dict(path=str(out.relative_to(ROOT)), masters=len(contract['masters']), pins=sum(len(m['pins']) for m in contract['masters'].values()), adopted=False)))
