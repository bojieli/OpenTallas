#!/usr/bin/env python3
"""Additive H6 configured-controller binding proposal; never adopt a view or edit source S.

The candidate preserves every existing signal edge, clock/reset binding and instance
name. It replaces the P/PHASE wrapper with the actual cfg master and explicit
source-derived straps. Routed native qualification and clock compensation stay open.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import textbook_lint as TL

OLD = 'ot_hbm_svc_pc_ctrl_leaf'
NEW = 'ot_hbm_svc_pc_ctrl_leaf_cfg'
BASE = 'rtl/hbm_accel/loader/service_native/'
CFG = BASE + NEW + '.sv'
WRAPPER = BASE + OLD + '.sv'
PARAMS = dict(OREG=1, KREG=1, KRREG=1, RREG=1, WPAY=1)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source(commit, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{commit}:{path}'])


def build(contract, contract_sha, rtl_commit, source_commit):
    rtl_commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', rtl_commit], text=True).strip()
    text = source(rtl_commit, CFG).decode()
    wrapper = source(rtl_commit, WRAPPER).decode()
    body = TL.rtl_modules([text])[NEW]
    widths, dirs = TL.module_ports(body), TL.module_port_dirs(body)
    ports = {n: dict(direction=dirs[n], bits=w[0]) for n, w in widths.items()}
    assert all(p['bits'] is not None for p in ports.values()), 'unknown port width'
    assert ports['pc_id'] == dict(direction='input', bits=5)
    assert ports['refresh_reload'] == dict(direction='input', bits=8)
    # The probe compiles the literal expressions extracted from the actual wrapper,
    # independently of the Python arithmetic used to emit the candidate straps.
    rp = re.search(r'localparam integer RP=(.*?);', wrapper).group(1)
    reload = re.search(r'localparam integer RELOAD=(.*?);', wrapper).group(1)
    assert '.pc_id(5\'(PC_STRAP)),.refresh_reload(8\'(REF_STRAP))' in wrapper
    assert 'localparam integer PC_STRAP=P;' in wrapper
    assert 'localparam integer REF_STRAP=RELOAD;' in wrapper
    spec = json.loads(source(rtl_commit, 'physical/ref_tile/hdie_pc_ctrl_cfg/spec.json'))
    deps = {p: sha(source(rtl_commit, p)) for p in spec['sources']}
    deps[WRAPPER] = sha(source(rtl_commit, WRAPPER))
    functional_macro = ('physical/asap7_memory_macros_v2/'
                        'ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v')
    deps[functional_macro] = sha(source(rtl_commit, functional_macro))
    clock_file = 'tools/hbm_die_v15/die_case.py'
    clock_source = source(source_commit, clock_file)
    period_line = re.search(r'^PERIOD\s*=\s*dict\(([^\n]+)\)', clock_source.decode(), re.M).group(1)
    hbm_period = float(re.search(r'\bhbm\s*=\s*([\d.]+)', period_line).group(1))
    instances = sorted((n, v) for n, v in contract['instances'].items() if v['master'] == OLD)
    assert len(instances) == 128, f'expected 128 controllers, got {len(instances)}'
    assert collections.Counter(v['params']['P'] for _, v in instances) == {p: 4 for p in range(32)}
    candidate = copy.deepcopy(contract)
    records = []
    probe = ['module pcctrl_strap_probe;', 'initial begin']
    for name, old in instances:
        p, phase = old['params']['P'], old['params'].get('PHASE', 0)
        assert set(old['params']) <= {'P', 'PHASE'}, f'{name}: unexpected parameter'
        assert isinstance(p, int) and 0 <= p < 32 and isinstance(phase, int) and 0 <= phase < 118
        shared = {n: v for n, v in ports.items() if n not in ('pc_id', 'refresh_reload')}
        assert old['ports'] == shared, f'{name}: cfg changes an existing typed interface'
        r = (phase + p * 118 // 32) % 118
        refresh = 118 + r + ((r + 118 + p) % 2)
        clocks = [copy.deepcopy(x) for x in contract['clock_resets'] if x['instance'] == name]
        assert {(x['port'], x['domain'], x['kind']) for x in clocks} == {
            ('clk', 'hbm', 'clock'), ('rst_n', 'hbm', 'reset')}
        edges = [copy.deepcopy(x) for x in contract['edges']
                 if x['source'][0] == name or x['sink'][0] == name]
        coverage = {port: set() for port in shared if port not in ('clk', 'rst_n')}
        for edge in edges:
            for endpoint in ('source', 'sink'):
                ep = edge[endpoint]
                if ep[0] != name:
                    continue
                assert ep[1] in shared, f'{name}: unknown existing edge port {ep}'
                assert ep[3] - ep[2] == edge['bits']
                assert 0 <= ep[2] < ep[3] <= shared[ep[1]]['bits']
                coverage[ep[1]].update(range(ep[2], ep[3]))
        gaps = {port: sorted(set(range(shared[port]['bits'])) - bits)
                for port, bits in coverage.items() if len(bits) != shared[port]['bits']}
        straps = []
        for port, width, value in [('pc_id', 5, p), ('refresh_reload', 8, refresh)]:
            straps.append(dict(inst=name, master=NEW, port=port, lo=0, hi=width,
                               value=value, verilog=f"{width}'d{value}",
                               net=f'{name}__{port}_strap',
                               bit_constants=[(value >> b) & 1 for b in range(width)],
                               reason='literal P/PHASE wrapper replacement, held through reset'))
        new = candidate['instances'][name]
        new.update(master=NEW, source=CFG, params=copy.deepcopy(PARAMS), ports=copy.deepcopy(ports))
        new['cfg_candidate_origin'] = dict(master=OLD, params=old['params'], source=old['source'])
        candidate.setdefault('straps', []).extend(copy.deepcopy(straps))
        records.append(dict(old_name=name, old_master=OLD, old_params=old['params'],
                            new_master=NEW, source=CFG, source_commit=rtl_commit,
                            params=copy.deepcopy(PARAMS), typed_ports=copy.deepcopy(ports),
                            explicit_straps=straps, signal_nets=edges, clock_reset_nets=clocks,
                            preserved_source_port_gaps=gaps,
                            clock_reference=dict(domain='hbm', period_ps=hbm_period,
                              leaf_qualification_period_ps=833.333, delivery='phi - R',
                              R_source='final routed view insertion.json tt.boundary.mean',
                              R_ps=None, status='OPEN_UNTIL_ROUTED_NATIVE_QUALIFICATION',
                              view='physical/ref_tile/hdie_pc_ctrl_cfg/views/' + NEW),
                            dependency_sha256=deps))
        probe += [f'begin : {name}', f'localparam integer P={p},PHASE={phase};',
                  f'localparam integer RP={rp};', f'localparam integer RELOAD={reload};',
                  f'$display("STRAP {name} %0d %0d", P, RELOAD);', 'end']
    probe += ['$finish;', 'end', 'endmodule']
    assert candidate['edges'] == contract['edges'], 'signal edges must remain byte-equivalent'
    assert candidate['clock_resets'] == contract['clock_resets'], 'clock/reset sources must stay'
    candidate['masters'] = dict(collections.Counter(v['master'] for v in candidate['instances'].values()))
    meta = dict(status='UNADOPTED_CFG_BINDING_CANDIDATE', source_contract_sha256=contract_sha,
                generating_source_commit=source_commit, cfg_rtl_commit=rtl_commit,
                source_S_unchanged=True, alias_legacy_master=False,
                qualification=['H6 detailed route/native audit OPEN',
                               'final routed clock compensation OPEN',
                               'candidate die elaboration/strict port bind OPEN'],
                physical_footprint=dict(w_um=185.76, h_um=164.16, instances=128,
                  added_area_32pc_mm2=.113467392, added_area_128pc_mm2=.453869568))
    candidate['pcctrl_cfg_candidate'] = meta
    binding = dict(schema='opentallas.pcctrl-cfg-binding-candidate.v1', **meta,
                   strap_formula=dict(RP=rp, RELOAD=reload),
                   clock_period_source=dict(commit=source_commit, path=clock_file,
                                            sha256=sha(clock_source), hbm_period_ps=hbm_period),
                   source_dependencies_sha256=deps, instances=records)
    return candidate, binding, '\n'.join(probe) + '\n'


def validate_probe(binding, log):
    for row in binding['instances']:
        for strap in row['explicit_straps']:
            width = row['typed_ports'][strap['port']]['bits']
            value = strap['value']
            assert strap['hi'] - strap['lo'] == width and 0 <= value < 1 << width
            assert strap['bit_constants'] == [(value >> b) & 1 for b in range(width)]
            assert strap['verilog'] == f"{width}'d{value}"
    actual = {}
    for name, pc, refresh in re.findall(r'^STRAP (\S+) (\d+) (\d+)$', log, re.M):
        assert name not in actual, f'duplicate elaborated instance {name}'
        actual[name] = (int(pc), int(refresh))
    expected = {r['old_name']: tuple(s['value'] for s in r['explicit_straps']) for r in binding['instances']}
    assert actual == expected, 'source-elaborated wrapper constants disagree with binding map'
    return dict(status='PASS_MAPPING_ONLY', instances=len(actual),
                proof='Icarus evaluates literal expressions extracted from source-pinned RTL wrapper',
                not_qualification='No controller compute is substituted or qualified by this constant probe')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract', type=Path, required=True)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--rtl-commit', default='6a9d24cd2')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    data = args.contract.read_bytes()
    candidate, binding, probe = build(json.loads(data), sha(data), args.rtl_commit, args.source_commit)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, value in [('candidate_contract.json', candidate), ('binding.json', binding)]:
        (args.out / name).write_text(json.dumps(value, indent=2) + '\n')
    (args.out / 'strap_probe.sv').write_text(probe)
    print(f'PCCTRL_CFG_CANDIDATE instances={len(binding["instances"])} source_S_sha256={sha(data)}')


if __name__ == '__main__':
    main()
