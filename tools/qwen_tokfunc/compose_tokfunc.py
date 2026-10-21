#!/usr/bin/env python3
"""compose_tokfunc.py -- TOK-FUNC-QW (10-21): Qwen ROM token composed from the stage benches run on ONE RTL assembly.

The composition engine is the record's toksim_compose (QW-TOKSCHED2 94cd97b7a: 1u 272,641 cyc = 4,403.2 tok/s,
4u 11,750.6; reproduced exactly by `--base-only`).  Every stage that has a PASS result.json from this run replaces
the matching measured term of the record's inputs.json:

    stg   -> dv ages (slice/vec/stn)            xt1  -> tile.ops / tile.far
    xdie  -> attention split + round trip       tp8  -> allreduce.qtp8 (E, LS)
    ovl4u -> multi_user frame                    head -> head.cycles (only if a span was measured)
    kv    -> attention.split.kv_service

Grades in the output: REL = measured in THIS run on the assembly (grade string of the run: "RTL-functional (source
assembly)" or "die-netlist"); terms that were REL in the record but are NOT re-measured here are re-graded DIAG (they
were measured on older RTL).  A stage that FAILs is not composed; the token is then reported as not passing.

usage: compose_tokfunc.py --results DIR --out DIR [--base-rev 94cd97b7a] [--repo /home/ubuntu/OpenTallas] [--base-only]
DIR/<stage>/result.json are the collected stage results.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

BASE_REV = '94cd97b7a'          # claude/qw-toksched2-1020: composition of record (4,403.2 / 11,750.6)
REC = 'results/token_pass/measured_qwen_1019'
# exact dependency set of toksim_compose at BASE_REV (missing optional files silently change the result: e.g. without
# results/rtl/qw_attnret_1019 the attention-return span falls back to the compiled 137 instead of the measured 98)
BASE_PATHS = ['tools', REC, 'rtl/physical',
              'results/arch/qwen_tp8_native_dispatch_1014', 'results/arch/qwen_split_compute_1014/dieplan2_1016',
              'results/rtl/qwen_layer_tput_1018/compiled_L1', 'results/rtl/qwen_layer_tput_1018/ctlm_prog',
              'results/rtl/qwen_q_export_1014/xpf/static', 'results/rtl/qlb_gen_1018/dv2f14bq',
              'results/rtl/qw_attnret_1019']
CLK_HZ = 1e12 / 833.0
STAGES = ['stg', 'xt1', 'xdie', 'tp8', 'ovl4u', 'ctx4u', 'head', 'kv']


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, check=True, **kw)


def build_tree(repo, rev, tree):
    if tree.exists():
        shutil.rmtree(tree)
    tree.mkdir(parents=True)
    sh(f"git -C {repo} archive {rev} {' '.join(BASE_PATHS)} | tar -x -C {tree}")


def run_compose(tree, inputs_rel, out_json):
    r = subprocess.run([sys.executable, '-I', 'tools/qwen_layerbench/toksim_compose.py', '--inputs', inputs_rel,
                        '--out', str(out_json)], cwd=tree, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f'toksim_compose failed rc={r.returncode}\n{r.stderr[-3000:]}')
    return json.loads(r.stdout.strip().splitlines()[-1])


def load_results(d):
    res = {}
    for s in STAGES:
        p = d / s / 'result.json'
        if p.exists():
            res[s] = json.loads(p.read_text())
    return res


def pick(c, *names):
    for n in names:
        if n in c and c[n] is not None:
            return c[n]
    return None


def apply(inp, res, tree, results_dir, grade_label):
    """returns (applied rows, problems)"""
    applied, problems = [], []
    remeasured = set()

    def sgrade(s):
        # REL only when the stage ran on the assembly/netlist with no on-chip stand-in (result 'grade' says so)
        g = str(res[s].get('transport_grade') or res[s].get('grade', ''))
        return 'REL' if g.startswith('RTL-functional') or g.startswith('die-netlist') else 'DIAG'

    def ok(s):
        r = res.get(s)
        if r is None:
            return False
        if str(r.get('verdict', '')).upper() != 'PASS':
            problems.append(f'{s}: verdict {r.get("verdict")} -> not composed')
            return False
        return True

    if ok('stg'):
        c = res['stg']; ages = c.get('ages') or c.get('cycles', {}).get('ages') or {}
        dst = tree / 'results/token_pass/tokfunc_qw/stg'; dst.mkdir(parents=True, exist_ok=True)
        new = {}
        for k in ('slice', 'vec', 'stn'):
            if ages.get(k):
                src = results_dir / 'stg' / ages[k]
                if not src.exists():
                    problems.append(f'stg: ages file {src} missing'); continue
                shutil.copy(src, dst / f'{k}_ages.json'); new[k] = f'results/token_pass/tokfunc_qw/stg/{k}_ages.json'
        if new:
            inp['dv']['ages'] = dict(inp['dv']['ages'], **new); inp['dv']['grade'] = sgrade('stg'); remeasured.add('dv')
            applied.append(f'dv ages {sorted(new)} <- stg')
        else:
            problems.append('stg: PASS but no ages files -> dv stays record')
    if ok('xt1'):
        c = res['xt1']['cycles']; near = c.get('near', c); far = c.get('far')
        ops = {}
        for op in ('qkv', 'o', 'gu', 'down'):
            n = near.get(op)
            if n and all(k in n for k in ('first_rs', 'first_final', 'last_final')):
                ops[op] = {k: int(n[k]) for k in ('first_rs', 'first_final', 'last_final')}
        if len(ops) == 4:
            inp['tile']['ops'] = ops; inp['tile']['grade'] = sgrade('xt1'); remeasured.add('tile')
            if far and far.get('qkv', {}).get('first_rs') is not None:
                inp['tile']['far'] = int(far['qkv']['first_rs']) - ops['qkv']['first_rs']
            applied.append(f"tile ops near + far {inp['tile']['far']} <- xt1")
        else:
            problems.append('xt1: PASS but per-op near edges incomplete -> tile stays record')
    if ok('xdie'):
        c = res['xdie']['cycles']
        c2k = pick(c, 'C2K_cmd', 'c2k_cmd', 'C2K_CMD', 'c2k'); rt = pick(c, 'roundtrip_cmd_to_r31', 'roundtrip_cmd_r31', 'roundtrip', 'roundtrip_cmd_issue_to_r31_land')
        kvs = pick(c, 'kv_service', 'kv_service_cmd_land_to_r31_issue')
        if None not in (c2k, rt, kvs):
            sp = inp['attention'].setdefault('split', {})
            sp.update(c2k=int(c2k), c2k_grade=sgrade('xdie'), k2c_grade=sgrade('xdie'), kv_service=int(kvs))
            inp['attention']['round_trip_plan_cycles'] = int(rt) - 31 + 16
            remeasured.add('attention_link')
            applied.append(f'attention c2k {c2k} kv_service {kvs} roundtrip {rt} -> plan {int(rt) - 15} <- xdie')
        else:
            problems.append(f'xdie: PASS but cycles keys missing ({sorted(c)})')
    if ok('kv'):
        c = res['kv']['cycles']; kvs = pick(c, 'kv_service_u1', 'kv_service', 'u1_service')
        if kvs is not None and res['kv'].get('full_service', True):
            inp['attention'].setdefault('split', {}).update(kv_service=int(kvs), kv_service_grade=sgrade('kv'))
            applied.append(f'kv_service {kvs} <- kv')
            remeasured.add('kv')
    if ok('tp8'):
        c = res['tp8']['cycles']; e = pick(c, 'E', 'AR256_E'); ls = pick(c, 'LS', 'ls')
        if e is not None and ls is not None:
            q = dict(inp['allreduce'].get('qtp8') or {}); q.update(E=int(e), ls_rec=int(ls), ls_bi=int(ls))
            inp['allreduce']['qtp8'] = q; inp['allreduce']['grade'] = sgrade('tp8'); remeasured.add('allreduce')
            applied.append(f'allreduce E {e} LS {ls} <- tp8')
    if ok('ovl4u'):
        c = res['ovl4u']['cycles']; fr = pick(c, 'frame_cycles', 'H_frame'); tpf = pick(c, 'tokens_per_frame')
        if isinstance(tpf, dict):
            tpf = [tpf[k] for k in sorted(tpf, key=int)]
        if fr and tpf:
            g = sgrade('ovl4u')
            mu = inp['multi_user']; mu.update(frame_cycles=int(fr), tokens_per_frame=list(tpf), grade=g, status=g)
            mu['cycles_per_token_by_user'] = [round(int(fr) / t) for t in tpf]
            mu['aggregate_cycles_per_token'] = round(int(fr) / sum(tpf))
            mu['aggregate_tok_s'] = round(CLK_HZ * sum(tpf) / int(fr), 1)
            mu['per_user_tok_s'] = [round(CLK_HZ * t / int(fr), 1) for t in tpf]
            remeasured.add('multi_user'); applied.append(f'4u frame {fr} tokens {tpf} <- ovl4u')
    if ok('head'):
        c = res['head']['cycles']; hs = pick(c, 'head_span', 'lm_head_span', 'lm_head_stage_start_to_END_issue')
        if hs:
            inp['head'].update(cycles=int(hs), grade=sgrade('head')); remeasured.add('head'); applied.append(f'head {hs} <- head')
    # terms that were REL in the record but not re-measured on this assembly -> DIAG (older RTL)
    for key, tag in (('dv', 'dv'), ('tile', 'tile'), ('allreduce', 'allreduce')):
        if tag not in remeasured and inp[key].get('grade') == 'REL':
            inp[key]['grade'] = 'DIAG'; applied.append(f'{key}: not re-measured -> DIAG')
    if 'attention_link' not in remeasured and inp['attention'].get('split'):
        sp = inp['attention']['split']
        for g in ('c2k_grade', 'k2c_grade'):
            if sp.get(g) == 'REL':
                sp[g] = 'DIAG'
        applied.append('attention link legs: not re-measured -> DIAG')
    inp['grades'] = (f'REL = measured in this run on the RTL assembly ({grade_label}); DIAG = measured on older RTL or a '
                     f'stand-in (NOT counted); NEWEST = record NEWEST term not re-run; PRICED = plan/analytic')
    return applied, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path, required=False)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--repo', default='/home/ubuntu/OpenTallas')
    ap.add_argument('--base-rev', default=BASE_REV)
    ap.add_argument('--asm', default='?')
    ap.add_argument('--grade', default='RTL-functional (source assembly)')
    ap.add_argument('--base-only', action='store_true', help='reproduce the record (expect 272,641 / 4,403.2 / 11,750.6)')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    tree = a.out / 'compose_tree'
    build_tree(a.repo, a.base_rev, tree)
    base = run_compose(tree, f'{REC}/inputs.json', a.out / 'cycles_base.json')
    report = dict(schema='opentallas.tokfunc.qwen_rom.v1', base_rev=a.base_rev, asm=a.asm, grade=a.grade,
                  model_of_record=dict(u1_tok_s=4403.2, u4_tok_s=11750.6, cycles=272641), base_reproduced=base)
    if not a.base_only:
        res = load_results(a.results)
        inp = json.loads((tree / REC / 'inputs.json').read_text())
        applied, problems = apply(inp, res, tree, a.results, a.grade)
        inp['release_source'] = f'TOK-FUNC-QW RTL assembly {a.asm} ({a.grade}); composition engine {a.base_rev}'
        (tree / REC / 'inputs_tokfunc.json').write_text(json.dumps(inp, indent=1))
        shutil.copy(tree / REC / 'inputs_tokfunc.json', a.out / 'inputs_tokfunc.json')
        r = run_compose(tree, f'{REC}/inputs_tokfunc.json', a.out / 'cycles_tokfunc.json')
        full = json.loads((a.out / 'cycles_tokfunc.json').read_text())['result']
        verdicts = {s: res[s].get('verdict') for s in res}
        missing = [s for s in STAGES if s not in res]
        diagnostic = [s for s, stage in res.items()
                      if not str(stage.get('transport_grade') or stage.get('grade', '')).startswith(a.grade)]
        token_pass = (not diagnostic and not problems and not missing and all(str(v).upper() == 'PASS' for v in verdicts.values()))
        report.update(stages=verdicts, missing_stages=missing, diagnostic_stages=diagnostic,
                      stage_sources={s: dict(src_commit=v.get('src_commit'), grade=v.get('grade'),
                                            source_note=v.get('source_note')) for s, v in res.items()}, applied=applied, problems=problems,
                      token=r, gaps=full['1u'].get('gaps'),
                      u1=dict(cycles=r['cycles'], tok_s=r['tok_s'], vs_model_pct=round(100 * (r['tok_s'] / 4403.2 - 1), 2)),
                      u4=dict(tok_s=r['u4'], vs_model_pct=round(100 * (r['u4'] / 11750.6 - 1), 2)),
                      verdict='TOKEN PASS (all stages PASS)' if token_pass else 'INCOMPLETE/FAIL (see stages/problems)')
    (a.out / 'report.json').write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report.get(k) for k in ('verdict', 'u1', 'u4', 'stages', 'missing_stages', 'problems')}
                     if not a.base_only else base))


if __name__ == '__main__':
    main()
