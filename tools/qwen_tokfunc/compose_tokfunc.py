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
import os
import re
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
STAGES = ['stg', 'xt1', 'xdie', 'tp8', 'ovl4u', 'ctx4u', 'head', 'kv', 'chain']
# TOKd-QW 10-22: optional gap stages (not required for the stage verdict; they re-measure dv_layer gap items)
#   attnret : rtl/test/qwen_dv/dv_lower_vec_bench.py --mode attn on the stg objects + stg ages (QW-ATTNRET re-bench)
#   xhead   : rtl/test/qwen_dv/xhead_bench.py --calibrate + --run qkv/gu/o/down (+ mutants) (QW-XHEAD x consumer)
OPTIONAL = ['attnret', 'xhead']
ATTNRET_REC = 'results/rtl/qw_attnret_1019/record.json'
CALR_CAP = 'results/rtl/qw_calr_1020/calr_capacity_safe8u_tlprod.json'
# attention-return span compiled in the engine tree with the composed ages, without and with the ledger's PRICED
# successor age deltas (dv_age_deltas): the bench measures the unshifted RTL; the composition carries the shifted one
ATTN_SPAN_PROBE = '''
import json, sys
sys.path.insert(0, 'tools/qwen_layerbench')
import toksim_compose as T
inp = json.load(open(sys.argv[1]))
def span():
    lw = T.L.V.lower_vec('attn', ar_order='slice')
    return max(x['edge_e5'] for x in lw['expected']['x']) - lw['dd_r0']
T.set_dv_ages(inp['dv'].get('ages'))
T.set_age_deltas(None); s0 = span()
dd = T.apply_ledger(inp, None)[2]
T.set_age_deltas(dd); s1 = span(); T.set_age_deltas(None)
print(json.dumps(dict(compiled_unshifted=s0, compiled_priced=s1, priced_delta=s1 - s0)))
'''


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, check=True, **kw)


def build_tree(repo, rev, tree):
    if tree.exists():
        shutil.rmtree(tree)
    tree.mkdir(parents=True)
    sh(f"git -C {repo} archive {rev} {' '.join(BASE_PATHS)} | tar -x -C {tree}")


S8_SC_BLOCK = """CMD_HOP = 2
SC_HOP_BY_SLICE = {'slice2': 2, 's8': 4}   # TOK-QK/S8B 10-25 (= main tools/qwen_layerbench/dv_lower.py)
SLICE_RTL = 's8' if os.environ.get('DV2_S8DIE', '0') == '1' else 'slice2'
SC_HOP = SC_HOP_BY_SLICE[SLICE_RTL]
"""


def s8die_tree(tree):
    """TOK-QK/S8B 10-25 --s8die: the stg ages were measured on the BOUND s8 slice row (tb_qfd_dv2 FACE 3), so
    (1) the engine's dv_lower takes the s8 scalar hop (SC_HOP 4 under DV2_S8DIE=1, the same rule as main's dv_lower) and
    (2) the ledger's PRICED SU8/VM8 successor age delta (dv_age_deltas, owed 'until the DV families are re-measured on
    the slice with su8 / vm8l bound') is dropped: the s8 ages ARE that re-measurement (REL replaces PRICED)."""
    p = tree / 'tools/qwen_layerbench/dv_lower.py'
    src = p.read_text()
    src2, n = re.subn(r'^CMD_HOP, SC_HOP = 2, 2[^\n]*\n', S8_SC_BLOCK, src, flags=re.M)
    if n != 1 or 'import os' not in src2:
        src2 = src2.replace('import math\n', 'import math\nimport os\n', 1)
    if n != 1:
        raise SystemExit('s8die: engine dv_lower SC_HOP line not found')
    p.write_text(src2)
    lp = tree / REC / 'sched/ledger.json'
    lg = json.loads(lp.read_text())
    dropped = lg.pop('dv_age_deltas', None)
    lg['dv_age_deltas_dropped'] = dict(reason='TOK-QK/S8B --s8die: REL s8 ages replace the PRICED SU8/VM8 delta', was=dropped)
    lp.write_text(json.dumps(lg, indent=1))
    os.environ['DV2_S8DIE'] = '1'
    return dict(engine_sc_hop=4, dropped_dv_age_deltas=dict(per_su_command=(dropped or {}).get('per_su_command'),
                                                            vm_write_extra=(dropped or {}).get('vm_write_extra'),
                                                            keys=(dropped or {}).get('keys')))


def run_compose(tree, inputs_rel, out_json):
    r = subprocess.run([sys.executable, '-I', 'tools/qwen_layerbench/toksim_compose.py', '--inputs', inputs_rel,
                        '--out', str(out_json)], cwd=tree, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f'toksim_compose failed rc={r.returncode}\n{r.stderr[-3000:]}')
    return json.loads(r.stdout.strip().splitlines()[-1])


def load_results(d):
    res = {}
    for s in STAGES + OPTIONAL:
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

    stg_functional = ok('stg')
    stg_timing = res.get('stg', {}).get('delivery_timing_qualified') is True
    if 'stg' in res and not stg_timing:
        problems.append('stg: current MAT delivery age UNKNOWN; functional cut checks and legacy schedule anchors do not qualify current token pricing; baseline DV remains historical/DIAG')
    if stg_functional and stg_timing:
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
        c = res['xt1']['cycles']
        c = c.get('landed_nominal_l8_g4', c)
        near = c.get('near', c); far = c.get('far')
        ops = {}
        for op in ('qkv', 'o', 'gu', 'down'):
            n = near.get(op)
            if n and all(k in n for k in ('first_rs', 'first_final', 'last_final')):
                ops[op] = {k: int(n[k]) for k in ('first_rs', 'first_final', 'last_final')}
        if len(ops) == 4:
            inp['tile']['ops'] = ops; inp['tile']['grade'] = sgrade('xt1');
            inp['tile']['source'] = f"TOK-FUNC-QW XT1 landed_nominal_l8_g4 source {res['xt1'].get('src_commit')}; measured near/far edges in stage result.json"; remeasured.add('tile')
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
    if ok('chain'):
        # TOK-FUNC3-QW: the token's real q/k/v through the KV attention RTL, every layer (ctx 8192): the slowest layer's
        # CMD-at-face -> last RESULT beat out is the attention service the static calendar must reserve
        st = (res['chain'].get('cycles', {}).get('kv_attention_u1_ctx8192') or {}).get('start_to_retire') or {}
        if st.get('n') == 36:
            inp['attention'].setdefault('split', {}).update(kv_service=int(st['max']), kv_service_grade=sgrade('chain'))
            remeasured.add('kv'); applied.append(f"kv_service {st['max']} (max of 36 real-token layers) <- chain")
        else:
            problems.append('chain: PASS but per-layer start_to_retire incomplete')
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


def apply_attnret(inp, res, tree, applied, problems):
    """attnret PASS (measured == bench-compiled on the composed ages, mutants FAIL) -> the engine's attention-return
    record = this run's measured span + the ledger's PRICED successor delta (the same shift the compiled span carries),
    so dv_layer's measured-vs-compiled check compares like with like."""
    r = res.get('attnret')
    if not r:
        return None
    if str(r.get('verdict', '')).upper() != 'PASS':
        problems.append(f"attnret: verdict {r.get('verdict')} -> attention-return record unchanged"); return None
    p = tree / 'results/token_pass/measured_qwen_1019/inputs_attnprobe.json'
    p.write_text(json.dumps(inp))
    q = subprocess.run([sys.executable, '-I', '-c', ATTN_SPAN_PROBE, str(p.relative_to(tree))], cwd=tree,
                       capture_output=True, text=True)
    if q.returncode:
        problems.append(f'attnret: span probe failed {q.stderr[-400:]}'); return None
    pr = json.loads(q.stdout.strip().splitlines()[-1])
    m = int(r['measured_span_edges'])
    if pr['compiled_unshifted'] != m or int(r.get('compiled_span_edges', m)) != m:
        problems.append(f"attnret: measured {m} != compiled {pr['compiled_unshifted']} on the composed ages")
        return pr
    rec_p = tree / ATTNRET_REC
    rec = json.loads(rec_p.read_text()) if rec_p.exists() else {}
    rec.update(measured_span_edges=m + pr['priced_delta'], compiled_span_edges=pr['compiled_priced'],
               tokfunc=dict(measured_on_assembly=m, priced_successor_delta=pr['priced_delta'],
                            source=r.get('source'), note='measured + ledger dv_age_deltas (PRICED SU8/VM8 successor)'))
    rec_p.write_text(json.dumps(rec, indent=1))
    applied.append(f"attention return span {m} REL + {pr['priced_delta']} PRICED successor delta <- attnret")
    return pr


def _stg_case(res, cfg, name):
    return ((res.get('stg', {}).get('configs', {}).get(cfg, {}).get('stages', {}) or {}).get(name) or {}).get('verdict')


def reconcile_gaps(gaps, res, repo):
    """dv_layer.py (engine BASE_REV) emits COLUMN-HEAD / TILE DELIVERY / RoPE / AR TAG as FIXED strings and checks the
    image against the legacy CALD store; re-grade each against this run's stage evidence and the current main
    designs.  Returns (open gaps, resolved gaps with evidence)."""
    open_, done = [], []
    st = lambda c, n: str(_stg_case(res, c, n) or '').upper()
    xh = res.get('xhead') or {}
    for g in gaps or []:
        if g.startswith('AR TAG CONTRACT'):
            ok = (st('pos', 'LGPOS_od_arf') == st('pos', 'LGPOS_lm_arf') == 'PASS' and st('rel', 'LGOFF_od_arf') == 'FAIL'
                  and st('mut', 'LGMUT_od_arf') == 'FAIL')
            (done if ok else open_).append(
                'AR TAG CONTRACT: RESOLVED in RTL -- qfd_dv_slice2 ARF 1 (QW-LAYERGAP 6ff5be90f), bound on the release die '
                'by die_params (OT_QWEN_SLICE_LAYERGAP default 1) and the slice2_e / slice2_wh kits; stg pos od/lm --arf PASS, '
                'ARF 0 and ARF 2 mutant FAIL' if ok else g)
        elif g.startswith('PER-TOKEN RoPE ROW'):
            ok = st('pos', 'LGPOS_qk_roperx') == 'PASS' and st('pos', 'LGPOS_qk_roperx_ropelate') == 'FAIL' \
                and st('mut', 'LGMUT_qk_roperx') == 'FAIL'
            if ok:
                done.append('PER-TOKEN RoPE ROW (compute-die consumer): RESOLVED -- qfd_dv_slice2 RP 1 + qfd_dv_vm CRH '
                            '(QW-LAYERGAP) bound by die_params; stg pos qk --rope rx PASS, rope_late / RP 2 mutants FAIL')
                open_.append('PER-TOKEN RoPE ROW (producer -> consumer): the KV-die RoPE OVL producer (qkd_d2d_cal_seq_ovl_rope, '
                             'qkd_kvn_ctx_ovl_rope view, codex/kdie-2000-1021) is not in this token run: stg drives the row '
                             'from the bench; no cross-die co-sim of the row onto the compute-die return chain yet')
            else:
                open_.append(g)
        elif g.startswith('IMAGE CAPACITY'):
            try:
                cap = json.loads(subprocess.run(['git', '-C', repo, 'show', f'origin/main:{CALR_CAP}'], check=True,
                                                capture_output=True, text=True).stdout)
            except Exception:
                cap = {}
            if cap.get('verdict') == 'PASS':
                lg = cap.get('logical', {})
                open_.append(f"IMAGE CAPACITY: legacy CALD check is stale; successor = CALR (QW-CALR/TLPROD: calendar ROM "
                             f"{lg.get('nent')}/{lg.get('nent_max')} entries, per-layer TABLE_REL loads, {CALR_CAP} PASS; "
                             'tt_ctlm hp13 PRIVATE_CALR on main, ledger CALR producer 76/layer PRICED). OPEN: slice-side '
                             'table_req consumer + GEN OT_SPLIT_DV_TREQ (claude/qdie5-tld-1022, not on main) not bound in the '
                             'die and not in this run')
            else:
                open_.append(g)
        elif g.startswith('COLUMN-HEAD x CONSUMER'):
            if str(xh.get('verdict', '')).upper() == 'PASS':
                done.append(f"COLUMN-HEAD x CONSUMER: RESOLVED -- dv_lower_xhead (QW-XHEAD fa577f2ea) lowers XPF arm + go/ib; "
                            f"xhead_bench calibrate + qkv/gu/o/down PASS, mutants FAIL ({xh.get('summary')})")
            else:
                open_.append(g + (f" [xhead stage: {xh.get('verdict')} {xh.get('summary', '')}]" if xh else
                                  ' [lowering exists: dv_lower_xhead fa577f2ea; never benched on the current slice2]'))
        elif g.startswith('TILE DELIVERY'):
            open_.append(g + ' [RTL item: per-slice go delay HGD[s] = 6 s - (hr_at[s] - hr_at[0]) for the AR '
                         'destinations (dv_lower_xhead.tile_delivery); not built in qfd_dv_heads / tt_ctlm; stg od drives the '
                         'stagger from the bench (nostagger mutant FAIL)]')
        else:
            open_.append(g)
    if res.get('attnret') and not any(g.startswith('ATTENTION RETURN') for g in open_):
        r = res['attnret']
        done.append(f"ATTENTION RETURN: RESOLVED -- re-bench on the stg objects: measured {r.get('measured_span_edges')} == "
                    f"compiled {r.get('compiled_span_edges')} (rel + pos), ddwin / ddbase FAIL; the composer's 116 was the "
                    'unshifted measurement vs the PRICED SU8/VM8 successor-shifted compile (+18)')
    return open_, done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path, required=False)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--repo', default='/home/ubuntu/OpenTallas')
    ap.add_argument('--base-rev', default=BASE_REV)
    ap.add_argument('--asm', default='?')
    ap.add_argument('--grade', default='RTL-functional (source assembly)')
    ap.add_argument('--base-only', action='store_true', help='reproduce the record (expect 272,641 / 4,403.2 / 11,750.6)')
    ap.add_argument('--s8die', action='store_true', help='stg ages from the bound s8 slice row (stg_die): engine SC_HOP 4, '
                    'ledger PRICED SU8/VM8 dv_age_deltas dropped (see s8die_tree)')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    tree = a.out / 'compose_tree'
    build_tree(a.repo, a.base_rev, tree)
    base = run_compose(tree, f'{REC}/inputs.json', a.out / 'cycles_base.json')
    report = dict(schema='opentallas.tokfunc.qwen_rom.v1', base_rev=a.base_rev, asm=a.asm, grade=a.grade,
                  clock_period_ps=833.0, clock_hz=CLK_HZ,
                  rate_convention='composer uses rounded 833 ps period (1.200480192 GHz)',
                  model_of_record=dict(u1_tok_s=4403.2, u4_tok_s=11750.6, cycles=272641), base_reproduced=base)
    if not a.base_only:
        if a.s8die:
            report['s8die'] = s8die_tree(tree)
        res = load_results(a.results)
        inp = json.loads((tree / REC / 'inputs.json').read_text())
        applied, problems = apply(inp, res, tree, a.results, a.grade)
        attn_probe = apply_attnret(inp, res, tree, applied, problems)
        inp['release_source'] = f'TOK-FUNC-QW RTL assembly {a.asm} ({a.grade}); composition engine {a.base_rev}'
        (tree / REC / 'inputs_tokfunc.json').write_text(json.dumps(inp, indent=1))
        shutil.copy(tree / REC / 'inputs_tokfunc.json', a.out / 'inputs_tokfunc.json')
        r = run_compose(tree, f'{REC}/inputs_tokfunc.json', a.out / 'cycles_tokfunc.json')
        full = json.loads((a.out / 'cycles_tokfunc.json').read_text())['result']
        verdicts = {s: res[s].get('verdict') for s in STAGES if s in res}
        missing = [s for s in STAGES if s not in res]
        diagnostic = [s for s, stage in res.items() if s in STAGES
                      and not str(stage.get('transport_grade') or stage.get('grade', '')).startswith(a.grade)]
        gaps_open, gaps_resolved = reconcile_gaps(full['1u'].get('gaps'), res, a.repo)
        token_pass = (not diagnostic and not problems and not missing and not gaps_open
                      and all(str(v).upper() == 'PASS' for v in verdicts.values()))
        report.update(stages=verdicts, missing_stages=missing, diagnostic_stages=diagnostic,
                      gap_stages={s: res[s].get('verdict') for s in OPTIONAL if s in res},
                      gaps=gaps_open, gaps_resolved=gaps_resolved,
                      stage_sources={s: dict(src_commit=v.get('src_commit'), grade=v.get('grade'),
                                            source_note=v.get('source_note')) for s, v in res.items()}, applied=applied, problems=problems,
                      token=r, gaps_engine=full['1u'].get('gaps'), attn_span_probe=attn_probe,
                      u1=dict(qualified_full_token=token_pass, scope='stage composition' if token_pass else 'historical model diagnostic; current token price held', cycles=r['cycles'], tok_s=r['tok_s'], vs_model_pct=round(100 * (r['tok_s'] / 4403.2 - 1), 2)),
                      u4=dict(qualified_full_token=token_pass, scope='stage composition' if token_pass else 'historical model diagnostic; isolated OVL transport is not full-token throughput', tok_s=r['u4'], vs_model_pct=round(100 * (r['u4'] / 11750.6 - 1), 2)),
                      verdict='TOKEN PASS (all stages PASS)' if token_pass else 'INCOMPLETE/FAIL (see stages/problems/gaps)')
    if not a.base_only:
        report['current_token_price'] = dict(status='QUALIFIED_STAGE_COMPOSITION' if token_pass else 'HELD',
            reasons=problems + [f'missing stage: {s}' for s in missing] + [f'diagnostic stage: {s}' for s in diagnostic]
            + [f'open gap: {g.split(":")[0]}' for g in report.get('gaps', [])])
        if 'chain' in res:
            c = res['chain']
            report['chain'] = dict(verdict=c.get('verdict'), grade=c.get('grade'), hand_off=c.get('hand_off'),
                                   kv_attention=c.get('cycles', {}).get('kv_attention_u1_ctx8192'),
                                   kv_attention_token_36_layers=c.get('cycles', {}).get('kv_attention_token_36_layers_start_to_status'),
                                   kv_attention_u4_cmd_period=c.get('cycles', {}).get('kv_attention_u4_cmd_period'),
                                   gaps=c.get('gaps'), failures=c.get('failures'))
        if 'ovl4u' in res:
            report['isolated_ovl_transport'] = dict(verdict=res['ovl4u'].get('verdict'),
                scope='compiled fixture exchanges at release master pins; no full-token throughput claim',
                cycles=res['ovl4u'].get('cycles', {}))
    (a.out / 'report.json').write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report.get(k) for k in ('verdict', 'u1', 'u4', 'stages', 'missing_stages', 'problems')}
                     if not a.base_only else base))


if __name__ == '__main__':
    main()
