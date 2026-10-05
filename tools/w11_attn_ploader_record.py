#!/usr/bin/env python3
"""Assemble results/rtl/w11_attn_ploader.json from the W11 two-word probability-loader runs.

Inputs (--runs, copied back from the simulation host):
  full_p1/status.json, full_p2/status.json      full-geometry builds (tools/v41_full_attention_numeric_build.py)
  res_p1/result.json                              PWORDS=1 at the default supply
  res_p2/result.json, res_p2_psup1/result.json    PWORDS=2 at 2 and at 1 upstream words/cycle
  tile.json, eng_h16d128.json, eng_h8d64.json    reduced benches (tools/w11_attn_ploader.py)
  v6_p1/status.json, v6_p2/status.json            verify-6 builds (NJOBMAX=6 capacities)
  v6_p1.json, v6_p2.json, v6vec/manifest.json     MTP verify-6 runs (tools/w11_attn_ploader.py --part verify6)
Refuses to overwrite an existing record.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/rtl/w11_attn_ploader.json'
BASELINE = ROOT / 'results/rtl/v41_full_attention_numeric/result.json'
SOURCES = ['rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv', 'rtl/hdc/v41x/ot_hdc_v41x_attn.sv',
           'rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv',
           'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',
           'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/test/tb_hdc_v41x_attn.sv', 'rtl/test/tb_hdc_v41x_attn_tile.sv',
           'rtl/test/hdc_v41_harness.cpp',
           'results/rtl/v41_attention_elaboration_archive/tools/v41_attention_hierarchy.vlt',
           'tools/v41_full_attention_numeric_prepare.py', 'tools/v41_full_attention_numeric_build.py',
           'tools/v41_full_attention_numeric_run.py', 'tools/w11_attn_ploader.py', 'tools/w11_attn_ploader_record.py',
           'tools/rtl_hdc_v41x_attn_campaign.py', 'tools/hdc_golden_v41.py', 'tests/test_w11_attn_ploader.py',
           'results/rtl/v41_full_attention_numeric/vector_manifest.json']
H, D, TD, NL = 16, 512, 32, 4
NT = NL * D // TD


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def case_view(r):
    f, j = r['fields'], r.get('job_fields', {})
    v = dict(name=r['name'], pass_=r['pass_'], exact=r['pass_'] and f.get('sc_errors') == 0 and
             f.get('pv_errors') == 0, sc_checked=f.get('sc_checked'), sc_errors=f.get('sc_errors'),
             pv_checked=f.get('pv_checked'), pv_errors=f.get('pv_errors'), faults=f.get('faults'),
             job_cycles=f.get('cycles'), T=j.get('T'), qk_first=j.get('qk_first'), qk_last=j.get('qk_last'),
             qk_beats=j.get('qk_beats'), pv_first=j.get('pv_first'), pv_last=j.get('pv_last'),
             pv_beats=j.get('pv_beats'), last_score=j.get('last_score'), last_p=j.get('last_p'),
             last_pv=j.get('last_pv'), plusargs=r.get('plusargs', []), wall_seconds=round(r['wall_seconds'], 1))
    if j:
        v['qk_window'] = j['qk_last'] - j['qk_first'] + 1
        v['pv_window'] = j['pv_last'] - j['pv_first'] + 1
        v['pv_bubbles'] = v['pv_window'] - j['pv_beats']
        v['pv_first_after_last_score'] = j['pv_first'] - j['last_score']
    return v


def storage(pwords):
    nbank = 4 if pwords == 2 else 3
    bits = NT * nbank * H * TD * 16
    return dict(NBANK=nbank, stationary_bits=bits, stationary_bytes=bits // 8,
                p_ingress_bits=pwords * TD * 16,
                tile_load_register_bits=NT * pwords * TD * 16,        # r_ld_w in every tile
                engine_boundary_register_bits=pwords * TD * 16)       # e_p_w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=Path, required=True)
    a = ap.parse_args()
    if OUT.exists():
        raise SystemExit(f'{OUT} exists; records are never overwritten')
    R = a.runs
    load = lambda p: json.loads((R / p).read_text())
    base = json.loads(BASELINE.read_text())
    full = {}
    for key, build, res in (('pwords1_psup1', 'full_p1', 'res_p1'), ('pwords2_psup2', 'full_p2', 'res_p2'),
                            ('pwords2_psup1', 'full_p2', 'res_p2_psup1')):
        st, rr = load(f'{build}/status.json'), load(f'{res}/result.json')
        assert rr['executable_sha256'] == st['executable_sha256'], key
        full[key] = dict(build=dict(status=st['status'], pwords=st['pwords'], elapsed_s=round(st['elapsed'], 1),
                                    max_rss_kib=st['max_rss_kib'], executable_sha256=st['executable_sha256'],
                                    verilator=st['verilator_version'], command_tail=st['command'][4:33]),
                         manifest_sha256=rr['manifest_sha256'], status=rr['status'],
                         cases=[case_view(x) for x in rr['results']])
    for key in full:
        for c in full[key]['cases']:
            assert c['T'] is not None, (key, c['name'])
    # PWORDS=1 identity with the committed baseline (e1ac020d numeric gate)
    bl = {r['name']: r['fields'] for r in base['results']}
    identity = {c['name']: dict(baseline_cycles=bl[c['name']]['cycles'], cycles=c['job_cycles'],
                                identical_fields=all(bl[c['name']][k] == c[k2] for k, k2 in (
                                    ('cycles', 'job_cycles'), ('sc_checked', 'sc_checked'), ('pv_checked', 'pv_checked'),
                                    ('sc_errors', 'sc_errors'), ('pv_errors', 'pv_errors'), ('faults', 'faults'))))
                for c in full['pwords1_psup1']['cases']}
    by = {k: {c['name']: c for c in v['cases']} for k, v in full.items()}
    m1, m2, m21 = by['pwords1_psup1']['mixed640'], by['pwords2_psup2']['mixed640'], by['pwords2_psup1']['mixed640']
    reduced = dict(tile=load('tile.json'), engine_h8d64=load('eng_h8d64.json'))
    if (R / 'eng_h16d128.json').is_file():
        reduced['engine_h16d128'] = load('eng_h16d128.json')
    else:
        reduced['engine_h16d128_not_run'] = ('flat (non-hierarchical) Verilator build of H16/D128 had compiled 1,011 of '
                                             '4,155 objects after 5 h on a loaded host; its geometry (H16/TD32, 16 words '
                                             'per block, DPT 8) is covered by the full-geometry hierarchical runs.')
    eng_keys = [k for k in ('engine_h16d128', 'engine_h8d64') if k in reduced]
    reduced['tile']['note'] = ('The tile bench does not read rtl/test/tb_hdc_v41x_attn.sv; its pin here predates the '
                               'bounded-supply edit of that engine bench. Every source the tile runs read is unchanged '
                               'in sources_sha256.')
    for k in eng_keys:
        for r in reduced[k]['results']:
            r.pop('expected', None)
    all_exact = all(c['exact'] for v in full.values() for c in v['cases']) and \
        all(r['status'] == 'pass' for r in reduced['tile']['results']) and \
        all(r['exact'] for k in eng_keys for r in reduced[k]['results'])
    target = m2['pv_beats'] == 160 and m2['pv_window'] <= 170
    verify6 = {}
    for pw in (1, 2):
        if not (R / f'v6_p{pw}.json').is_file():
            continue
        st, v = load(f'v6_p{pw}/status.json'), load(f'v6_p{pw}.json')
        r = v['results'][0]
        assert r['executable_sha256'] == st['executable_sha256'] and st['pwords'] == pw
        verify6[f'pwords{pw}'] = dict(build=dict(status=st['status'], params=st.get('params'),
                                                  elapsed_s=round(st['elapsed'], 1), max_rss_kib=st['max_rss_kib'],
                                                  executable_sha256=st['executable_sha256']),
                                      **{k: r[k] for k in ('psup', 'jobs', 'scores_checked', 'score_errors',
                                                           'pv_checked', 'pv_errors', 'faults', 'total_cycles',
                                                           'timeout', 'exact', 'manifest_sha256', 'per_position')})
    verify6['vectors_manifest'] = load('v6vec/manifest.json')
    verify6['vectors_manifest'].pop('images', None)
    verify6['note'] = ('6 jobs of T=640 back to back, each with its own 16-word q load and probabilities, over the same '
                       'KV rows. The engine has no KV-reuse mode: every job re-streams its 640 rows into the staging '
                       'buffer (overlapped with q.k at NL rows/cycle), and a job starts only after the previous '
                       "job's final p.v issue (job_ready = !act), so positions do not overlap.")
    all_exact = all_exact and all(v['exact'] for k, v in verify6.items() if k.startswith('pwords'))
    rec = dict(
        record='W11 attention probability loader PWORDS=2 (two BF16 words per p handshake, 4 stationary banks)',
        scope=('Standalone full-geometry numerical attention engine (H16/D512/TD32/NL4/TROWS640) on the synthetic '
               'golden vectors of results/rtl/v41_full_attention_numeric; probabilities come from the golden via the '
               'bench, not from the SU. Cycle counts are bench cycles incl. driver and barriers; no frequency, '
               'physical or token-rate claim.'),
        proposal='results/rtl/v41_attention_elaboration_archive/PV_TWO_WORD_PROPOSAL.md',
        git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        sources_sha256={s: sha(ROOT / s) for s in SOURCES},
        parameters=dict(H=H, D=D, TD=TD, NL=NL, TROWS=640, NT=NT, DPT=D // NT, words_per_block=H,
                        GUARD_P={'1': 16, '2': 18}, countdown_threshold={'1': 5, '2': 3}, GUARD_Q=20),
        storage={'pwords1': storage(1), 'pwords2': storage(2),
                 'delta_stationary_bits': storage(2)['stationary_bits'] - storage(1)['stationary_bits']},
        full_geometry=full, pwords1_identity_with_baseline=identity,
        summary=dict(
            mixed640=dict(
                pwords1=dict(job=m1['job_cycles'], qk_window=m1['qk_window'], pv_window=m1['pv_window'],
                             pv_beats=m1['pv_beats'], pv_first=m1['pv_first'], pv_last=m1['pv_last']),
                pwords2_supply2=dict(job=m2['job_cycles'], qk_window=m2['qk_window'], pv_window=m2['pv_window'],
                                     pv_beats=m2['pv_beats'], pv_first=m2['pv_first'], pv_last=m2['pv_last']),
                pwords2_supply1=dict(job=m21['job_cycles'], qk_window=m21['qk_window'], pv_window=m21['pv_window'],
                                     pv_beats=m21['pv_beats'], pv_first=m21['pv_first'], pv_last=m21['pv_last']))),
        reduced=reduced,
        mtp_verify6=verify6,
        verdict=dict(
            exact_all=all_exact,
            pwords1_cycle_identical=all(v['identical_fields'] for v in identity.values()),
            pv_target_met_at_supply2=target,
            status='pass' if all_exact and target and all(v['identical_fields'] for v in identity.values())
            else 'fail',
            caveat=('The gain needs the upstream SU/VM to deliver 2 words (4 rows x 16 heads BF16) per cycle; at 1 '
                    'word/cycle the p.v window is back at the single-word figure (pwords2_supply1). Physical cost '
                    '(1024-bit broadcast to 64 tiles, 4th bank) is not closed here.')))
    OUT.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec['summary'], indent=1), json.dumps(rec['verdict']))


if __name__ == '__main__':
    main()
