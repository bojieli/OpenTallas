#!/usr/bin/env python3
"""Lower the REGISTERED_BOUNDARY station sources for the host synthesis flow.

Only package imports are replaced by the identical static W6 functions already
used by every routed W2 station (bank_legacy_static.sv); no logic changes.
"""
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LEGACY = ROOT/'physical/hbm_w2_check_station_20261006/bank_legacy_static.sv'
BANK = ROOT/'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank_veto.sv'
STATION = ROOT/'physical/hbm_die_abstracts_20261006/links/native_quarter/ot_hbm_native_frame_station_rb.sv'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def functions():
    text = LEGACY.read_text()
    out = {}
    for name in ('encode64', 'raw64', 'check72'):
        m = re.findall(r'function automatic[^;]*\b'+name+r'\([^;]*;.*?endfunction', text, re.S)
        assert len(m) == 1, name
        out[name] = m[0]
    return out


def main():
    f = functions()
    both = '\n'.join([f['encode64'], f['raw64'], f['check72']])
    bank = BANK.read_text()
    two = ' import ot_gpu_w6_secded_pkg::*;\n import ot_hbm_w2_boundary_pkg::*;'
    one = ' import ot_gpu_w6_secded_pkg::*;'
    assert bank.count(two) == 1
    bank = bank.replace(two, both)
    assert bank.count(one) == 1
    bank = bank.replace(one, f['encode64'])
    (HERE/'bank_veto_static.sv').write_text(bank)
    station = STATION.read_text()
    assert station.count(one) == 1
    (HERE/'station_rb_static.sv').write_text(station.replace(one, f['encode64']))
    generated = ['bank_veto_static.sv', 'station_rb_static.sv']
    (HERE/'sources.json').write_text(json.dumps(dict(
        schema='w2-rb-station-physical-v1', top='ot_hbm_native_frame_station_rb',
        parameters=dict(ENABLE=1, NO=2),
        source_pins={str(p.relative_to(ROOT)): sha(p) for p in (BANK, STATION, LEGACY)},
        generated_pins={g: sha(HERE/g) for g in generated},
        lowering='package imports replaced by the static W6 functions of bank_legacy_static.sv'), indent=2)+'\n')
    print('prepared', *generated)


if __name__ == '__main__':
    main()
