"""Conservative L0 dependency schedule; unknown latency never becomes an exact zero."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def solve(nodes):
    """Topological earliest-finish floor and exact finish, with explicit unknowns."""
    result = {}
    for n in nodes:
        deps = [result[d] for d in n['after']]
        floor = max([d['finish_floor'] for d in deps], default=0)
        known = n['cycles'] is not None and all(d['finish_exact'] is not None for d in deps)
        result[n['id']] = dict(start_floor=floor,
                              finish_floor=floor + n['floor'],
                              finish_exact=max([d['finish_exact'] for d in deps], default=0) + n['cycles'] if known else None)
    return result


def parse_numeric(path):
    text = path.read_text()
    line = next(s for s in text.splitlines() if s.startswith('V41XJOB'))
    values = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)}
    for key in ('sc_errors', 'pv_errors', 'faults', 'timeout'):
        assert re.search(rf'\b{key}=0\b', text), f'numeric run failed: {key}'
    # Inclusive accepted-beat windows; they overlap compute and cannot be added.
    values['qk_accept_window'] = values['qk_last'] - values['qk_first'] + 1
    values['pv_accept_window'] = values['pv_last'] - values['pv_first'] + 1
    return values


def build(root=ROOT):
    evidence = root / 'results/contracts/v41_l0_schedule_evidence'
    numeric = {f'T{t}': parse_numeric(evidence / f'{name}.log') for t, name in [(128, 'window128'), (640, 'mixed640')]}
    def n(id, after, floor=0, cycles=None, basis='unknown implementation service'):
        return dict(id=id, after=after, floor=floor, cycles=cycles, basis=basis)
    # Current KVD blocks ME issue until kv_ok; A_LDX only begins after ME go.
    # QK and PV are distinct descriptors; no cross-op stage reuse is credited.
    nodes = [n('upstream_qkv', []), n('packed_write_commit', ['upstream_qkv']),
             n('qk_refill', ['packed_write_commit'], basis='128 rows x17 sectors; live shared-HBM service unknown'),
             n('q_preload', ['qk_refill'], 2048, basis='16x512 FP32 elements / G4 scalar VM ports; drain extra'),
             n('qk_numeric_and_replay', ['q_preload'], basis='stream and arithmetic overlap; synthetic engine interval is separate evidence'),
             n('scale_max', ['qk_numeric_and_replay']), n('exp_sum', ['scale_max']),
             n('pv_refill', ['exp_sum'], basis='second descriptor currently refills; retained-stage reuse not proven'),
             n('p_preload', ['pv_refill'], 512, basis='L0 H16xT128 / G4; not T640 floor2560'),
             n('pv_numeric_and_replay', ['p_preload']),
             n('denominator', ['exp_sum', 'pv_numeric_and_replay'], basis='Conservatively serial until emitted SU issue/resource trace proves overlap'),
             n('divide', ['pv_numeric_and_replay', 'denominator']), n('result_commit', ['divide'])]
    current = solve(nodes)
    fixture = [dict(x) for x in nodes]
    for x in fixture:
        if x['id'] in ('qk_refill', 'pv_refill'):
            x.update(floor=4608, cycles=4608, basis='transferred standalone ideal1-cycle-HBM 128-row gate; not actual shared-HBM duration')
    stream = json.loads((evidence / 'window_stream.json').read_text())
    base, candidate = stream['baseline'][0]['metrics'], stream['ii1'][0]['metrics']
    paths = ['rtl/hdc/v41x/ot_hdc_core_v41x.sv', 'rtl/hdc/v41x/ot_hdc_v41x_att_adapt.sv',
             'rtl/chip/ot_chip_v41x_window_refill_schedule.sv', 'results/rtl/v41x_window_attn_source.json']
    paths += [str(p.relative_to(root)) for p in sorted(evidence.iterdir())]
    return dict(schema='opentallas.v41.l0_dependency_schedule.v1', nodes=nodes,
                current=current, actual_attention_path_cycles=current['result_commit']['finish_exact'],
                current_known_issue_floor=current['result_commit']['finish_floor'],
                transferred_fixture_floor=solve(fixture)['result_commit']['finish_floor'],
                fixture_scope='Two sequential ideal standalone refills plus Q/P scalar issue floors only; neither prediction nor integrated measurement',
                engine_fixture=numeric, engine_verdict_commit='e1ac020d',
                engine_scope='H16D512TD32NL4; synthetic exact engine fixture uses golden P after scores, omits SU, core adapter and HBM; logs recovered from ot-pve2',
                window_candidate=dict(commit='284f2811', baseline_cycles=base['total_cycles'], candidate_cycles=candidate['total_cycles'],
                                      saved_cycles=base['total_cycles']-candidate['total_cycles'],
                                      saved_fraction=(base['total_cycles']-candidate['total_cycles'])/base['total_cycles'],
                                      scope=stream['scope']),
                overlap_legal=[dict(paths=['KV accepted-beat interval', 'QK arithmetic'], proof='same engine run; count last-score completion once'),
                               dict(paths=['PV fill', 'PV arithmetic'], proof='same engine run; stationary-bank control preserves lifetime')],
                overlap_not_credited=['Q preload before kv_ok', 'probability preload before exp/sum writes finish',
                                     'PV refill reuse of QK staging', 'denominator parallel with PV without SU issue/resource trace',
                                     'independent users masking single-user stalls'],
                architectural_priorities=['remove serial refill bottleneck with bounded outstanding requests and exact shared-HBM proof',
                                          'preserve staged generation across QK/PV if lifecycle and capacity permit; requires contract change',
                                          'improve scalar Q/P preload producer near attention; price bank ports and conversion',
                                          'keep16960bitKV and512bitP local; no wide inter-region bus without explicit latency'],
                source_sha256={p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths})

if __name__ == '__main__':
    (ROOT / 'results/contracts/v41_l0_dependency_schedule.json').write_text(json.dumps(build(), indent=2) + '\n')
