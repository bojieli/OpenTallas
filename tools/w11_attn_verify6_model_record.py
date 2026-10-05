#!/usr/bin/env python3
"""Assemble results/rtl/w11_attn_verify6_model.json: MTP verify-6 in MODEL row order on the V4.1 attention
engine with two ping-pong staging buffers (ILV = 1, NSTAGE = 2) and the timing variant REPL = 1 (per-tile
transposer index copies, 2-entry p-word skid).  Replaces the withdrawn rows-last claim of
results/rtl/w11_attn_verify6.json.

--runs DIR must hold:
  full_a/status.json   ILV=1 REPL=1 NSTAGE=2 PWORDS=2 build (+ OT_ATTN_SETCHECK), NJOBMAX=6 capacities
  full_b/status.json   ILV=0 PWORDS=2 build (serial reference + default-mode identity)
  vec_full/manifest.json          model-order vectors (tools/w11_attn_verify6.py vectors --order model)
  ilv1*.json, ilv0*.json          `w11_attn_verify6.py run` outputs on full_a / full_b
  std_b/result.json               the four standard single-job cases on full_b
  h4*.json                        reduced model-order runs (`reduced --order model --nstage 2`)
  negative.json                   the p-load guard relaxed by one cycle is caught (REPL, NSTAGE = 2)
  ident.log                       old (98200f25) vs new engine+bench, ILV = 0, small config
Refuses to overwrite an existing record.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/rtl/w11_attn_verify6_model.json'
SU = ROOT / 'results/rtl/w11_su_spec.json'
PLOADER = ROOT / 'results/rtl/w11_attn_ploader.json'
SOURCES = ['rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv', 'rtl/hdc/v41x/ot_hdc_v41x_attn.sv',
           'rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv',
           'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',
           'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/test/tb_hdc_v41x_attn.sv', 'rtl/test/hdc_v41_harness.cpp',
           'results/rtl/v41_attention_elaboration_archive/tools/v41_attention_hierarchy.vlt',
           'tools/v41_full_attention_numeric_build.py', 'tools/v41_full_attention_numeric_run.py',
           'tools/w11_attn_verify6.py', 'tools/w11_attn_verify6_model_record.py',
           'tools/rtl_hdc_v41x_attn_campaign.py', 'tools/hdc_golden_v41.py', 'results/rtl/w11_su_spec.json',
           'results/rtl/w11_attn_ploader.json']
H, D, TD, NL, NT = 16, 512, 32, 4, 64


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def summary(run):
    return dict(L0=run['L0'], total=run['total_cycles'], exact=run['exact'], tile_utilisation=run['tile_utilisation'],
                setcheck=run.get('setcheck'),
                positions=[dict(T=p['T'], qk=[p['qk_first'], p['qk_last']], qk_window=p['qk_window'],
                                pv=[p['pv_first'], p['pv_last']], pv_window=p['pv_window'],
                                last_score=p['last_score'], last_pv=p['last_pv'], position_cycles=p['position_cycles'],
                                **({k: p[k] for k in ('accept', 'su_start', 'p_first', 'p_last') if k in p}))
                           for p in run['per_position']])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=Path, required=True)
    a = ap.parse_args()
    if OUT.exists():
        raise SystemExit(f'{OUT} exists; records are never overwritten')
    R = a.runs
    load = lambda p: json.loads((R / p).read_text())
    su = json.loads(SU.read_text())
    ch = su['configs']['N1024_M256_B4R5']['cases']['T640']['chained']
    L0 = ch['ops'][1]['write']['first']
    man = load('vec_full/manifest.json')
    assert man['order'] == 'model'
    builds = {}
    for k in ('full_a', 'full_b'):
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
        assert r['executable_sha256'] == builds['full_a']['executable_sha256'] and r['ILV'] == 1
    for r in ilv0:
        assert r['executable_sha256'] == builds['full_b']['executable_sha256'] and r['ILV'] == 0
    std = load('std_b/result.json')
    assert std['executable_sha256'] == builds['full_b']['executable_sha256']
    pl = json.loads(PLOADER.read_text())
    ref = {c['name']: c for c in pl['full_geometry']['pwords2_psup2']['cases']}
    identity = {r['name']: dict(ploader_cycles=ref[r['name']]['job_cycles'], cycles=r['fields']['cycles'],
                                exact=r['pass_'],
                                identical=(r['pass_'] and r['fields']['cycles'] == ref[r['name']]['job_cycles'] and
                                           all(r['job_fields'].get(k) == ref[r['name']][k] for k in (
                                               'qk_first', 'qk_last', 'pv_first', 'pv_last', 'last_pv'))))
                for r in std['results']}
    ident_lines = [x for x in (R / 'ident.log').read_text().splitlines() if x.startswith('PWORDS=')]
    reduced = {f.stem: json.loads(f.read_text()) for f in sorted(R.glob('h4*.json'))}
    for v in reduced.values():
        v.pop('manifest', None)
    neg = load('negative.json')
    by1, by0 = {r['L0']: r for r in ilv1}, {r['L0']: r for r in ilv0}
    table = {str(l): dict(serial=by0[l]['total_cycles'], interleaved=by1[l]['total_cycles'],
                          serial_utilisation=by0[l]['tile_utilisation'],
                          interleaved_utilisation=by1[l]['tile_utilisation']) for l in sorted(by1) if l in by0}
    stat = lambda n: NT * n * H * TD * 2
    staging_macros = 4 * ((16 * 265 + 255) // 256)
    storage = dict(stationary_banks=dict(NBANK=5, bytes=stat(5), delta_vs_pwords2_bytes=stat(5) - stat(4)),
                   staging=dict(buffers=2, rows_each=640, bytes_each=640 * 16 * 265 // 8,
                                sram_macros=2 * staging_macros, delta_macros=staging_macros,
                                note='ASAP7 256x256 macros, results/rtl/hdc_v41x_attn_macro_stage.json basis'),
                   p_skid_bits=2 * 1024,
                   per_tile_copies_bits=NT * (1 + 1 + 8 + NL + 1 + 8 + 1))
    all_exact = (all(r['exact'] for r in ilv1 + ilv0) and all(v['exact'] for v in identity.values()) and
                 all(r['exact'] for v in reduced.values() for r in v['runs']))
    setchk = all(r['setcheck']['errors'] == 0 and r['setcheck']['reads'] > 0 for r in ilv1)
    ok_ident = all(v['identical'] for v in identity.values()) and len(ident_lines) == 8 and \
        all(' identical ' in x for x in ident_lines)
    rec = dict(
        record=('W11 attention: MTP verify-6 in model row order, ILV = 1 with two ping-pong staging buffers '
                '(NSTAGE = 2) and REPL = 1, full geometry'),
        supersedes='results/rtl/w11_attn_verify6.json (rows-last synthetic rule; withdrawn for real MTP)',
        scope=('Standalone full-geometry numerical attention engine H16/D512/TD32/NL4/TROWS640, PWORDS = 2, on '
               'synthetic golden inputs in model row order; probabilities from the golden through the bench SU '
               'model. Bench cycles; no frequency, physical or token-rate claim.'),
        git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        sources_sha256={s: sha(ROOT / s) for s in SOURCES},
        model_order=dict(
            rule=('Model.forward_positions: verify position k attends its OWN row list, its sliding window (128 '
                  'rows ending at its own row, oldest first) followed by its OWN indexer selection (512 compressed '
                  'rows, the selector\'s order); each position is checked against Job.expected on exactly that list '
                  '(scores dots(q, kvm), pv dots(to_bf16(p), kvm.T), Model.attend\'s single-block R-ARITH order)'),
            vectors=dict(manifest_sha256=sha(R / 'vec_full/manifest.json'), T=man['T'], counts=man['counts'],
                         expected=man['expected'], seed=man['seed']),
            staging=('each position streams its own 640 rows into the front staging buffer while the back job '
                     'fills from the other buffer; q.k and fill read concurrently; no row is shared or reused')),
        su_model=dict(L0=L0, source='w11_su_spec.json N1024_M256_B4R5 T640 chained: first exp write',
                      L0_engine_cycles=218, stream='2 words (1,024 b) per engine cycle',
                      rule=('position k\'s chain starts at max(its last score, the end of position k-1\'s stream); '
                            'first word L0 cycles later')),
        builds=builds,
        full_geometry=dict(interleaved=[summary(r) for r in ilv1], serial=[summary(r) for r in ilv0]),
        verify6_cycles=table,
        default_identity=dict(full_geometry_pwords2=identity, small_config_old_vs_new=ident_lines),
        reduced=reduced, negative=neg, storage=storage,
        verdict=dict(exact_all=all_exact, setcheck_clean=setchk, guard_tight=neg['caught'], default_identical=ok_ident,
                     status='pass' if all_exact and setchk and neg['caught'] and ok_ident else 'fail'))
    OUT.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(verify6_cycles=table, verdict=rec['verdict']), indent=1))


if __name__ == '__main__':
    main()
