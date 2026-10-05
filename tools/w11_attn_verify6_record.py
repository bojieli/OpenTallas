#!/usr/bin/env python3
"""Assemble results/rtl/w11_attn_verify6.json: the position-interleaved MTP verify mode (ILV) of the V4.1
attention engine, from the runs of tools/w11_attn_verify6.py and tools/v41_full_attention_numeric_{build,run}.py.

--runs DIR must hold:
  full_ilv1/status.json, full_ilv0/status.json   full-geometry builds (PWORDS=2, NJOBMAX=6 capacities; ILV=1 with the
                                                  simulation-only set checker, ILV=0 without)
  vec_full/manifest.json                          the verify vectors (T_k = 635 .. 640)
  ilv1.json, ilv0.json                            `w11_attn_verify6.py run` at every L0 (ILV=1 interleaved, ILV=0 serial)
  std_ilv0/result.json                            the four standard single-job cases on the ILV=0 build
  h4.json h4b.json h4n4.json h4n4b.json           reduced benches (`reduced`, BUB 0 / 20, NL 1 / 4)
  negative.json                                   `negative`: the p-load guard relaxed by one cycle is caught
  ident/run.log                                   old (98200f25) vs new engine+bench, ILV=0, small config
Refuses to overwrite an existing record.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/rtl/w11_attn_verify6.json'
SU = ROOT / 'results/rtl/w11_su_spec.json'
PLOADER = ROOT / 'results/rtl/w11_attn_ploader.json'
SOURCES = ['rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv', 'rtl/hdc/v41x/ot_hdc_v41x_attn.sv',
           'rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv',
           'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',
           'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/test/tb_hdc_v41x_attn.sv', 'rtl/test/hdc_v41_harness.cpp',
           'results/rtl/v41_attention_elaboration_archive/tools/v41_attention_hierarchy.vlt',
           'tools/v41_full_attention_numeric_build.py', 'tools/v41_full_attention_numeric_run.py',
           'tools/w11_attn_verify6.py', 'tools/w11_attn_verify6_record.py', 'tools/rtl_hdc_v41x_attn_campaign.py',
           'tools/hdc_golden_v41.py', 'tests/test_w11_attn_verify6.py', 'results/rtl/w11_su_spec.json',
           'results/rtl/w11_attn_ploader.json']
H, D, TD, NL, NT = 16, 512, 32, 4, 64


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def su_latency():
    su = json.loads(SU.read_text())
    ch = su['configs']['N1024_M256_B4R5']['cases']['T640']['chained']
    ops = {o['op']: o for o in ch['ops']}
    rowmax_done = ops['scale+row max']['result']['last']
    exp_first = ops['exp(s-max)+row sum']['write']['first']
    exp_last = ops['exp(s-max)+row sum']['write']['last']
    return dict(source='results/rtl/w11_su_spec.json configs.N1024_M256_B4R5.cases.T640.chained (BCAST/RET 4:5)',
                chain_end_cycle=ch['end_cycle'], row_max_done=rowmax_done,
                exp_accept=ops['exp(s-max)+row sum']['accept'], exp_first_write=exp_first, exp_last_write=exp_last,
                L0=exp_first,
                L0_rule=('cycles from the chain start (the position\'s last score, or the end of the previous '
                         'position\'s probability stream) to the first probability write: the row max completes at '
                         f'{rowmax_done}, the exp op accepts at {ops["exp(s-max)+row sum"]["accept"]} and writes its '
                         f'first result at {exp_first}'),
                L0_root_figure=355,
                stream=('modelled rate: PWORDS = 2 words of 512 b per cycle = 1,024 b/cycle of BF16 probabilities '
                        '(4 rows x 16 heads, 64 values per cycle), 160 handshakes at T = 640. The measured exp op '
                        f'writes its 10,240 values in {exp_last - exp_first + 1} write cycles (~213 values/cycle), so '
                        'the SU can sustain the modelled rate if its exp results reach the engine as BF16 at >= '
                        '1,024 b/cycle; that SU-to-engine path is not measured here'),
                engine_clock=('L0 = 188 is in SU cycles (w11_su_spec clock_ghz 1.034); the engine runs in the 1.2 GHz '
                              'streaming domain, so the same latency is 188 x 1.2 / 1.034 = 218 engine cycles (run as '
                              'L0 = 218). The SU -> p-word path is being widened to 1,536 b per slow cycle through a '
                              'ratio FIFO (root); the bench models 1,024 b per engine cycle, i.e. 2 words/cycle.'),
                not_modelled=('the sink denominator and the post-p.v divide of the same chain (the SU is free for the '
                              'next chain once the probability stream has ended, per the adopted rule)'))


def summary(run):
    per = run['per_position']
    return dict(total=run['total_cycles'], exact=run['exact'], tile_utilisation=run['tile_utilisation'],
                setcheck=run.get('setcheck'),
                positions=[dict(T=p['T'], qk=[p['qk_first'], p['qk_last']], qk_window=p['qk_window'],
                                pv=[p['pv_first'], p['pv_last']], pv_window=p['pv_window'],
                                last_score=p['last_score'], last_pv=p['last_pv'],
                                **({k: p[k] for k in ('accept', 'su_start', 'p_first', 'p_last') if k in p}))
                           for p in per])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=Path, required=True)
    a = ap.parse_args()
    if OUT.exists():
        raise SystemExit(f'{OUT} exists; records are never overwritten')
    R = a.runs
    load = lambda p: json.loads((R / p).read_text())
    su = su_latency()
    man = load('vec_full/manifest.json')
    builds = {}
    for k in ('full_ilv1', 'full_ilv0'):
        st = load(f'{k}/status.json')
        assert st['status'] == 'build_pass'
        for rel, d in st['source_sha256'].items():
            assert sha(ROOT / rel) == d, (k, rel)
        builds[k] = dict(status=st['status'], pwords=st['pwords'], params=st['params'], defines=st.get('defines', []),
                         elapsed_s=round(st['elapsed'], 1), max_rss_kib=st['max_rss_kib'],
                         executable_sha256=st['executable_sha256'], verilator=st['verilator_version'])
    ilv1 = [r for f in sorted(R.glob('ilv1*.json')) for r in json.loads(f.read_text())['runs']]
    ilv0 = [r for f in sorted(R.glob('ilv0*.json')) for r in json.loads(f.read_text())['runs']]
    for r in ilv1:
        assert r['executable_sha256'] == builds['full_ilv1']['executable_sha256'] and r['ILV'] == 1
    for r in ilv0:
        assert r['executable_sha256'] == builds['full_ilv0']['executable_sha256'] and r['ILV'] == 0
    std = load('std_ilv0/result.json')
    assert std['executable_sha256'] == builds['full_ilv0']['executable_sha256']
    pl = json.loads(PLOADER.read_text())
    ref = {c['name']: c for c in pl['full_geometry']['pwords2_psup2']['cases']}
    identity = {r['name']: dict(ploader_cycles=ref[r['name']]['job_cycles'], cycles=r['fields']['cycles'],
                                exact=r['pass_'],
                                identical=(r['pass_'] and r['fields']['cycles'] == ref[r['name']]['job_cycles'] and
                                           all(r['job_fields'].get(k) == ref[r['name']][k] for k in (
                                               'qk_first', 'qk_last', 'pv_first', 'pv_last', 'last_pv'))))
                for r in std['results']}
    ident_lines = [x for x in (R / 'ident/run.log').read_text().splitlines() if x.startswith('PWORDS=')]
    reduced = {k: load(f'{k}.json') for k in ('h4', 'h4b', 'h4n4', 'h4n4b')}
    for v in reduced.values():
        v.pop('manifest', None)
    neg = load('negative.json')
    by1 = {r['L0']: r for r in ilv1}
    by0 = {r['L0']: r for r in ilv0}
    L0s = sorted(by1)
    table = {str(l): dict(serial=by0[l]['total_cycles'], interleaved=by1[l]['total_cycles'],
                          serial_utilisation=by0[l]['tile_utilisation'],
                          interleaved_utilisation=by1[l]['tile_utilisation']) for l in L0s if l in by0}
    nbank = {'ilv0': 4, 'ilv1': 5}
    storage = {k: dict(NBANK=n, stationary_bytes=NT * n * H * TD * 2) for k, n in nbank.items()}
    storage['delta_bytes'] = storage['ilv1']['stationary_bytes'] - storage['ilv0']['stationary_bytes']
    storage['kv_reuse'] = 'zero storage: the staging buffer (TROWS = 640) keeps its rows; job_t[15] skips the reload'
    storage['control'] = ('back-job T/nblk (32 b), reuse flag, one-cycle p.v issue delay (bank, block, dim, final: '
                          '~30 b), 3-bit bank index, lowest-free-bank encoders over 5 banks')
    all_exact = (all(r['exact'] for r in ilv1 + ilv0) and all(v['exact'] for v in identity.values()) and
                 all(r['exact'] for v in reduced.values() for r in v['runs']))
    setchk_clean = all(r['setcheck']['errors'] == 0 and r['setcheck']['reads'] > 0 for r in ilv1) and \
        all(r['setcheck']['errors'] == 0 for v in reduced.values() for r in v['runs'])
    rec = dict(
        record='W11 attention engine: position-interleaved MTP verify mode (ILV = 1), 6 positions at T = 635..640',
        scope=('Standalone full-geometry numerical attention engine H16/D512/TD32/NL4/TROWS640, PWORDS = 2, on '
               'synthetic golden vectors; probabilities come from the golden through a bench SU model, not from the '
               'SU RTL. Bench cycles incl. driver; no frequency, physical or token-rate claim.'),
        git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        sources_sha256={s: sha(ROOT / s) for s in SOURCES},
        design=dict(
            parameter='ILV (default 0 = the previous engine, bit- and cycle-identical)',
            kv_reuse='job_t[15]: the job keeps the staged rows; rows past the retained count are appended (lane '
                     'mask per row), so position k streams only its own new row',
            contexts=('front job: q set, KV rows, q.k; back job: p blocks, transposer fills, p.v. A front job whose '
                      'q.k has issued moves to the back when the back is free; the front then takes the next job'),
            arbitration=dict(tile_issue='p.v first when ready, else q.k (a p.v beat enters the E register one cycle '
                                        'after its decision, as a q.k beat does, so the two never meet there)',
                             buffer_read_port='transposer fill first (at most two blocks ahead of p.v), else q.k',
                             stationary_load_port=('p word first, else q word (q_ready is low in a cycle a p word '
                                                   'is accepted: a combinational p_v -> q_ready path)'),
                             banks='lowest free bank whose guard has expired (q: counter 0; p: counter <= GUARD_Q - '
                                   'GUARD_P + 1 = 3)'),
            guards=dict(GUARD_Q=20, GUARD_P=18, p_load_threshold=3,
                        qk_issue_sets=21, pv_issue_sets='21 in ILV (20 + the one-cycle issue delay), 20 otherwise',
                        derivation=('same per-position lifetime derivation as the PWORDS=2 proposal: a bank is '
                                    're-loaded only after the counter set by its last read beat has expired; the '
                                    'ILV p.v read is one cycle later, so its counter starts one higher'),
                        check=('exhaustive over every executed read: a simulation-only stationary-set checker '
                               '(OT_ATTN_SETCHECK) replays tile 0\'s load and skewed-read timing and compares the '
                               'set id each non-pad read sees with the beat\'s; zero violations in every ILV run, '
                               'and the guard is tight: one cycle less (negative) is caught by the checker and by '
                               'numeric errors')),
            causal_rule=('rows ordered with the verify positions\' own rows last; position k attends rows [0, T_k), '
                         'T_k = 640 - (5 - k); each position is checked against its own golden (scores dots(q, kvm), '
                         'pv dots(p, kvm.T), Model.attend\'s R-ARITH order) on its rows. This orders the draft '
                         'rows after the selected rows, which is not Model.attend\'s window-first row order.')),
        su_model=su,
        vectors=dict(manifest_sha256=sha(R / 'vec_full/manifest.json'), T=man['T'], counts=man['counts'],
                     expected=man['expected']),
        builds=builds,
        full_geometry=dict(interleaved=[summary(r) | dict(L0=r['L0']) for r in ilv1],
                           serial=[summary(r) | dict(L0=r['L0']) for r in ilv0]),
        verify6_cycles=table,
        default_identity=dict(full_geometry_pwords2=identity, small_config_old_vs_new=ident_lines),
        reduced=reduced, negative=neg, storage=storage,
        verdict=dict(exact_all=all_exact, setcheck_clean=setchk_clean, guard_tight=neg['caught'],
                     default_identical=all(v['identical'] for v in identity.values()) and
                     all(' identical ' in x for x in ident_lines),
                     status='pass' if all_exact and setchk_clean and neg['caught'] and
                     all(v['identical'] for v in identity.values()) and all(' identical ' in x for x in ident_lines)
                     else 'fail'))
    OUT.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(verify6_cycles=table, verdict=rec['verdict']), indent=1))


if __name__ == '__main__':
    main()
