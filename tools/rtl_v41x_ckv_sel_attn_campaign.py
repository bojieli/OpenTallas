#!/usr/bin/env python3
"""Selected-CKV path of an indexed DeepSeek-V4.1 layer: ID stream -> owned-row fetch -> all-gather -> merger ->
attention engine, exact against the golden (Verilator 5.050).

Bench: rtl/test/tb_chip_v41x_ckv_sel_attn.sv; vectors: tools/v41_ckv_sel_attn_vectors.py.
  build   --build DIR [--engine 0|1] [--param NAME=VALUE ...]   copy + pin sources, build (engine: hierarchical flow
          with results/rtl/v41_attention_elaboration_archive/tools/v41_attention_hierarchy.vlt, as the full-geometry
          attention gate tools/v41_full_attention_numeric_build.py)
  run     --exe EXE --vectors DIR --out DIR [--cases a,b] [--plusarg lat=100 ...] [--tag NAME]
  mutate  --exe EXE --vectors DIR --out DIR   negative controls on full1m (corrupted HBM row, unsorted selection,
          wrong published count): each must be caught (row mismatch or a module fault)
  record  --runs DIR [DIR ...] --out results/rtl/v41x_ckv_sel_attn.json   (never overwrites a failed verdict)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH_SOURCES = ['rtl/chip/ot_chip_v41x_ckv_fp4_decode.sv', 'rtl/chip/ot_chip_v41x_ckv_selected_dma.sv',
                'rtl/chip/ot_chip_v41x_ckv_sel_ids.sv', 'rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv',
                'rtl/chip/ot_chip_v41x_ckv_sel_collect.sv', 'rtl/chip/ot_chip_v41x_ckv_stream_merge.sv']
ENGINE_SOURCES = ['rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv', 'rtl/hdc/v41x/ot_hdc_v41x_attn.sv',
                  'rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv',
                  'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',
                  'rtl/hdc/ot_hdc_fastfp.sv']
TB = 'rtl/test/tb_chip_v41x_ckv_sel_attn.sv'
HIER = 'results/rtl/v41_attention_elaboration_archive/tools/v41_attention_hierarchy.vlt'
HARNESS = 'rtl/test/hdc_v41_harness.cpp'
TOOLS = ['tools/v41_ckv_sel_attn_vectors.py', 'tools/rtl_v41x_ckv_sel_attn_campaign.py',
         'tools/hdc_golden_v41.py', 'tools/rtl_hdc_v41x_attn_campaign.py', 'runtime/prefill/v41_main_kv_row.py']
VERILATOR = Path(os.environ.get('OPENTALLAS_TOOL_ROOT', Path.home() / '.local/opentallas-tools')) / \
    'verilator-5.050/bin/verilator'
FIELD = re.compile(r'(\w+)=(-?\d+)')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(a):
    b = a.build.resolve()
    b.mkdir(parents=True, exist_ok=True)
    srcs = PATH_SOURCES + (ENGINE_SOURCES if a.engine else []) + [TB]
    pins = {}
    for rel in srcs + ([HIER] if a.engine else []) + [HARNESS]:
        dst = b / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dst)
        pins[rel] = sha(dst)
    params = [f'-GENGINE={1 if a.engine else 0}', '-GNHBM=32768', *[f'-G{x}' for x in a.param]]
    if a.engine:
        params += ['-GH=16', '-GD=512', '-GTD=32', '-GNL=4', '-GTROWS=640', '-GPWORDS=2']
    cmd = [str(VERILATOR), '--cc', '--exe', '--build', '--top-module', 'tb_chip_v41x_ckv_sel_attn', '--prefix', 'Vtb',
           '-Mdir', str(b / 'obj'), '-j', str(a.jobs), '-Wno-fatal', '-Wno-WIDTH', '-Wno-TIMESCALEMOD', *params]
    if a.engine:
        cmd += ['--output-split', '20000', '--output-split-cfuncs', '2000', '--unroll-count', '1',
                '--unroll-limit', '131072', '--hierarchical', str(b / HIER)]
    cmd += [str(b / s) for s in srcs] + [str(b / HARNESS), '-CFLAGS', '-O1']
    t0 = time.time()
    with (b / 'build.log').open('w') as log:
        r = subprocess.run(cmd, cwd=b, stdout=log, stderr=subprocess.STDOUT)
    exe = b / 'obj' / 'Vtb'
    st = dict(command=cmd, source_sha256=pins, engine=bool(a.engine), params=params, returncode=r.returncode,
              elapsed_s=round(time.time() - t0, 1), executable_sha256=sha(exe) if exe.is_file() else None,
              verilator=subprocess.check_output([str(VERILATOR), '--version'], text=True).strip(),
              status='build_pass' if r.returncode == 0 and exe.is_file() else 'build_fail')
    (b / 'status.json').write_text(json.dumps(st, indent=2) + '\n')
    print(json.dumps({k: v for k, v in st.items() if k != 'command'}))
    raise SystemExit(0 if st['status'] == 'build_pass' else 1)


def parse(out):
    rec = {}
    for tag in ('CKVSEL', 'CKVROWS', 'V41XATTN'):
        ls = [x for x in out.splitlines() if x.startswith(tag + ' ')]
        rec[tag] = {k: int(v) for k, v in FIELD.findall(ls[-1])} if ls else {}
    return rec


def verdict(f, case, engine):
    s, r, e = f['CKVSEL'], f['CKVROWS'], f['V41XATTN']
    ok = bool(s) and s.get('faults') == 0 and s.get('hbm_missing') == 0 and r.get('errors') == 0 and \
        r.get('checked') == case['T'] and e.get('timeout') == 0 and s.get('t_last_staged', -1) >= 0 and \
        r.get('id_fc') == 0 and r.get('f_fc') == 0 and r.get('c_fc') == 0 and r.get('m_fc') == 0
    if engine:
        x = case['expected']
        ok = ok and e.get('jobs') == 1 and e.get('sc_errors') == 0 and e.get('pv_errors') == 0 and \
            e.get('sc_checked') == x['scores'] and e.get('pv_checked') == x['pv'] and \
            e.get('faults') == x['score_faults'] + x['pv_faults']
    return ok


def run(a):
    st = json.loads((a.exe.resolve().parents[1] / 'status.json').read_text())
    man = json.loads((a.vectors / 'manifest.json').read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    results = []
    for c in man['cases']:
        if a.cases and c['name'] not in a.cases.split(','):
            continue
        d = (a.vectors / c['name']).resolve()
        for n, h in c['images'].items():
            assert sha(d / n) == h, (c['name'], n)
        t0 = time.monotonic()
        p = subprocess.run([str(a.exe.resolve()), f'+dir={d}', *('+' + x for x in a.plusarg)], capture_output=True,
                           text=True, timeout=a.timeout)
        name = c['name'] + (('.' + a.tag) if a.tag else '')
        (a.out / (name + '.log')).write_text(p.stdout + p.stderr)
        f = parse(p.stdout)
        ok = p.returncode == 0 and verdict(f, c, st['engine'])
        s = f['CKVSEL']
        cyc = dict(fetch_latency_last_id_to_last_row_staged=s.get('fetch_latency'),
                   last_id=s.get('t_last_id'), first_row_arrived=s.get('t_first_row'),
                   all_rows_arrived=s.get('t_all_rows'), first_ckv_row_staged=s.get('t_first_ckv_staged'),
                   last_row_staged=s.get('t_last_staged'), first_qk=s.get('t_first_qk'), last_qk=s.get('t_last_qk'),
                   qk_beats=s.get('qk_beats'), qk_beats_before_last_row_staged=s.get('qk_beats_before_last_staged'),
                   staging_overlaps_qk=(s.get('qk_beats_before_last_staged', 0) > 0) if st['engine'] else None,
                   last_score=s.get('t_last_score'), last_pv=s.get('t_last_pv'))
        results.append(dict(case=c['name'], tag=a.tag, plusargs=a.plusarg, pass_=ok, returncode=p.returncode,
                            n_sel=c['n_sel'], T=c['T'], owned_rows_per_die=c['owned_rows_per_die'],
                            owners_die_stack=len(c['owners_die_stack']), cycles=cyc, fields=f,
                            wall_s=round(time.monotonic() - t0, 1)))
        print(name, 'PASS' if ok else 'FAIL', json.dumps(cyc), flush=True)
    res = dict(executable_sha256=sha(a.exe), build_status=st, manifest_sha256=sha(a.vectors / 'manifest.json'),
               manifest=man, results=results, status='pass' if results and all(r['pass_'] for r in results) else 'fail')
    fn = a.out / (f'result.{a.tag}.json' if a.tag else 'result.json')
    fn.write_text(json.dumps(res, indent=2) + '\n')
    raise SystemExit(0 if res['status'] == 'pass' else 1)


def mutate(a):
    src = a.vectors / 'full1m'
    a.out.mkdir(parents=True, exist_ok=True)
    muts = []

    def one(name, fn):
        d = a.out / ('mut_' + name)
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(src, d)
        fn(d)
        p = subprocess.run([str(a.exe.resolve()), f'+dir={d.resolve()}', '+lat=100'], capture_output=True, text=True,
                           timeout=a.timeout)
        f = parse(p.stdout)
        caught = f['CKVROWS'].get('errors', 0) > 0 or f['CKVSEL'].get('faults', 0) > 0 or \
            f['CKVSEL'].get('hbm_missing', 0) > 0 or f['V41XATTN'].get('timeout', 0) == 1 or \
            f['V41XATTN'].get('sc_errors', 0) > 0
        muts.append(dict(mutation=name, caught=caught, fields=f))
        print(name, 'caught' if caught else 'MISSED', flush=True)

    def hbm_flip(d):                  # flip one code byte of the first selected row's first sector (die/stack copy)
        sel0 = int((d / 'sel.hex').read_text().split()[0], 16)
        cfg = [int(x, 16) for x in (d / 'cfg.hex').read_text().split()]
        die, stack, local = (sel0 >> 4) & 3, (sel0 >> 6) & 3, ((sel0 >> 8) << 4) | (sel0 & 15)
        key = (die << 32) | (stack << 30) | (cfg[9 + stack] + 9 * local)
        keys = [int(x, 16) for x in (d / 'hkey.hex').read_text().split()]
        dat = (d / 'hdat.hex').read_text().split()
        i = keys.index(key)
        dat[i] = f'{int(dat[i], 16) ^ 0x5a:064x}'
        (d / 'hdat.hex').write_text(''.join(x + '\n' for x in dat))

    def unsorted(d):                  # swap two selected ids inside quarter 0
        ids = (d / 'sel.hex').read_text().split()
        ids[3], ids[4] = ids[4], ids[3]
        (d / 'sel.hex').write_text(''.join(x + '\n' for x in ids))

    def unpublished(d):               # published count below the largest selected id
        cfg = (d / 'cfg.hex').read_text().split()
        ids = [int(x, 16) for x in (d / 'sel.hex').read_text().split()]
        cfg[2] = f'{max(ids):08x}'
        (d / 'cfg.hex').write_text(''.join(x + '\n' for x in cfg))

    one('hbm_row_corrupted', hbm_flip)
    one('selection_unsorted', unsorted)
    one('source_unpublished', unpublished)
    res = dict(executable_sha256=sha(a.exe), build_status=json.loads((a.exe.resolve().parents[1] /
                                                                      'status.json').read_text()),
               mutations=muts, status='pass' if all(m['caught'] for m in muts) else 'fail')
    (a.out / 'mutations.json').write_text(json.dumps(res, indent=2) + '\n')
    raise SystemExit(0 if res['status'] == 'pass' else 1)


def record(a):
    runs, muts = [], []
    for d in a.runs:
        for f in sorted(Path(d).glob('result*.json')):
            runs.append(json.loads(f.read_text()))
        if (Path(d) / 'mutations.json').is_file():
            muts.append(json.loads((Path(d) / 'mutations.json').read_text()))
    if a.out.is_file():
        old = json.loads(a.out.read_text())
        if old.get('status') != 'pass':
            raise SystemExit(f'{a.out} holds a failed verdict; write a new record instead')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--', *PATH_SOURCES, *ENGINE_SOURCES, TB,
                                     *TOOLS], cwd=ROOT, text=True).strip()
    pins = {}
    for r in runs + muts:
        for rel, h in r['build_status']['source_sha256'].items():
            assert pins.setdefault(rel, h) == h, rel
    current = {rel: sha(ROOT / rel) for rel in sorted(set(pins) | set(TOOLS))}
    stale = sorted(rel for rel, h in pins.items() if current[rel] != h)
    exact = [r for run in runs if run['build_status']['engine'] for r in run['results']]
    rows = [r for run in runs if not run['build_status']['engine'] for r in run['results']]
    rec = dict(
        schema='v41x_ckv_sel_attn/1',
        scope=('Selected compressed-KV path of an indexed DeepSeek-V4.1 layer on one die of tensor group 4: the final '
               'select output -> selected-ID table with owned-rank lists -> four dies\' owned-row fetch (PIPE '
               'selected-CKV DMA slots, behavioural HBM stacks) -> behavioural all-gather links -> in-order collector '
               '-> streaming merger -> ot_hdc_v41x_attn at H16 D512 TD32 NL4 TROWS640 PWORDS2. Exact: q.k scores and '
               'p.v of Model.attend on the golden rows (probabilities synthetic, as '
               'results/rtl/v41_full_attention_numeric). Behavioural HBM (fixed latency, one 32-B sector per stack '
               'per cycle, the DMA port) and links (latency + row interval); no softmax, window HBM path or physical '
               'claim.'),
        git_head=head, sources_dirty_at_record=bool(dirty), source_sha256=pins, current_sha256=current,
        stale_sources=stale,
        exact_full_geometry=exact, rows_only_reduced=rows,
        negative_controls=[m for x in muts for m in x['mutations']],
        status='pass' if exact and all(r['pass_'] for r in exact) and all(r['pass_'] for r in rows) and not stale
        and all(x['status'] == 'pass' for x in muts) else 'fail')
    a.out.write_text(json.dumps(rec, indent=2) + '\n')
    print(rec['status'], len(exact), len(rows), stale)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    b = sp.add_parser('build')
    b.add_argument('--build', type=Path, required=True)
    b.add_argument('--engine', type=int, default=1)
    b.add_argument('--param', action='append', default=[])
    b.add_argument('--jobs', type=int, default=8)
    r = sp.add_parser('run')
    r.add_argument('--exe', type=Path, required=True)
    r.add_argument('--vectors', type=Path, required=True)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--cases', default='')
    r.add_argument('--plusarg', action='append', default=[])
    r.add_argument('--tag', default='')
    r.add_argument('--timeout', type=int, default=7200)
    m = sp.add_parser('mutate')
    m.add_argument('--exe', type=Path, required=True)
    m.add_argument('--vectors', type=Path, required=True)
    m.add_argument('--out', type=Path, required=True)
    m.add_argument('--timeout', type=int, default=7200)
    c = sp.add_parser('record')
    c.add_argument('--runs', type=Path, nargs='+', required=True)
    c.add_argument('--out', type=Path, default=ROOT / 'results/rtl/v41x_ckv_sel_attn.json')
    a = ap.parse_args()
    {'build': build, 'run': run, 'mutate': mutate, 'record': record}[a.cmd](a)


if __name__ == '__main__':
    main()
