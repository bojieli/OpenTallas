#!/usr/bin/env python3
"""Check proposed static-frame/FEC composition capacity from exact RTL ports.

This is a necessary boundary check, not a physical or production qualification.
No existing composition is asserted: callers supply both source revisions.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FEC = 'rtl/hbm_accel/io_native_20261014/hfd_serdes487_rooted.sv'
LINK = 'rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_link_seq.sv'


def read_source(revision, path):
    data = subprocess.check_output(['git', '-C', str(ROOT), 'show', revision+':'+path])
    return data, hashlib.sha256(data).hexdigest()


def port_width(data, direction, name):
    # These exact source ABIs have literal ANSI wire/reg vectors. Unsupported
    # declarations fail rather than being assigned an assumed transport size.
    text = re.sub(r'//[^\n]*|/\*.*?\*/', '', data.decode(), flags=re.S)
    header = text.split(');', 1)[0]
    p = rf'\b{direction}\s+(?:wire|reg)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*{name}\b'
    matches = re.findall(p, header)
    if len(matches) != 1:
        raise ValueError(f'expected one explicit {direction} wire/reg vector for {name}')
    high, low = map(int, matches[0])
    return abs(high-low)+1


def audit(fec, link, requested):
    transport = port_width(fec, 'input', 'tx')
    if transport != port_width(fec, 'output', 'rx'):
        raise ValueError('asymmetric FEC transport requires separate direction budgets')
    frame = port_width(link, 'output', 'tx_pin_flit')
    if frame != port_width(link, 'input', 'rx_pin_flit'):
        raise ValueError('asymmetric frame transport requires separate budgets')
    capacity = Fraction(transport, frame)
    return {
        'scope': 'proposed boundary composition, same core-cycle frequency; no integration inferred',
        'fec_payload_bits_per_cycle': transport,
        'endpoint_frame_bits': frame,
        'requested_frames_per_cycle': str(requested),
        'ideal_packed_max_frames_per_cycle': str(capacity),
        'ideal_packed_superframe': {'frames': capacity.numerator, 'transport_cycles': capacity.denominator},
        'necessary_capacity_pass': requested <= capacity,
        'direct_wires_compatible': transport == frame,
        'qualified': False,
        'open': [
            'Actual fixed-cycle gearbox and exact reservation calendar',
            'Valid/idle representation, framing, epoch and reset alignment',
            'Source-bound link clock ratios and immutable production bandwidth',
            'Actual FEC/recovered-clock, SRAM, retry and HOST composition',
            'Assigned slots, registered boundary pins and routed TT/FF/DRC',
        ],
        'limits': 'Ideal bit packing only; framing/idle overhead can lower capacity. A different clock ratio needs an explicit separate proof.',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fec-revision', required=True)
    p.add_argument('--link-revision', required=True)
    p.add_argument('--required-frames-per-cycle', type=Fraction, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.required_frames_per_cycle <= 0:
        p.error('required frame rate must be positive')
    f, fs = read_source(a.fec_revision, FEC)
    l, ls = read_source(a.link_revision, LINK)
    result = audit(f, l, a.required_frames_per_cycle)
    result['source'] = {FEC: {'revision': a.fec_revision, 'sha256': fs}, LINK: {'revision': a.link_revision, 'sha256': ls}}
    result['checker_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('fec_payload_bits_per_cycle', 'endpoint_frame_bits', 'ideal_packed_max_frames_per_cycle', 'necessary_capacity_pass')}))
    return 0 if result['necessary_capacity_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
