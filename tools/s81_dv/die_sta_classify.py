#!/usr/bin/env python3
"""GAP-SKQ / GSKQ-CLASS (10-21): READER of an S81 real-view die run (dv_rvcase.py case: run_all.sh -> GRT -> die STA
TT/FF(/SS) -> die_clock_check -> classify.py).  It is NOT a gate and adds no check: it only reads what the existing die
flow already wrote and sorts every failing endpoint / audit into the known die failure classes so a die result is
triaged in minutes.  Extends the per-element table of the case's own classify.py (sta/classes.json) with:

  * failure classes: frame_clock_model, landing_reset, reset_station, forward_enable, block_reset, relay_reset,
    relay_data|<link cls>, landing_data|<link cls>, block_in|<element>|<view>, other   (setup and hold per corner)
  * per class: n / violators / WNS / TNS / ALL-ENDPOINTS flag + top offenders (endpoint, master, view closed|standin,
    owner = element or link src->dst from case.json, startpoint when the path appears in <c>_<tag>.paths.rpt)
  * non-path results: forwarded-clock audit (die_repeaters.fclk*.json), die_clock_check per corner, landed/frame-lane/
    unlanded-pair judge (classes.json), DRV counts, IR drop, GRT overflow (+ by plan region from grt_congestion.rpt)
  * pre-GRT stage status when the chain stopped early: steps.log, strict port bind (port_bind.json/.log),
    reset reach, landing reset check, gen_safety.
SS rows are kept in the json but printed as headline only (sensitivity, owner option B).

    python3 tools/s81_dv/die_sta_classify.py RUN [--out DIR] [--top 8]
RUN = die run dir or its case/ dir, local or host:/path (fetched read-only with rsync, big tsv/odb skipped)."""
import argparse
import collections
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

T_PS = 833.333          # dv_rvcase.T_PS (S81 die clock)
CACHE = Path(os.environ.get('OT_DIECLASS_CACHE', '/home/ubuntu/scratch/die_sta_classify'))
FETCH = ['steps.log', 'bind.log', 'case_gen.log', 'chain.log', 'snapshot.refs',
         'bind/bind/port_bind.json', 'bind/bind/port_bind.log', 'bind/bind/landing_reset_check.json',
         'bind/out/reset_reach_gate*',
         'case/case.json', 'case/run_all.log', 'case/run_all.done', 'case/gen_safety.json', 'case/NOT_A_DIE_RESULT',
         'case/die_repeaters.fclk.post_grt.json', 'case/die_repeaters.fclk.pre_eq.json', 'case/die_repeaters.post_grt.json',
         'case/out/run.log', 'case/out/run.exit', 'case/out/grt_congestion.rpt', 'case/ir_drop.log',
         'case/ir_drop/ir_drop.json', 'case/sta/*.end.rpt', 'case/sta/*.paths.rpt', 'case/sta/*_drv.rpt',
         'case/sta/classes.json', 'case/sta/die_clock_check_*.json', 'case/sta/link_*.rpt', 'case/sta/sta_*.log',
         'case/sta/run.exit']


def fetch(run):
    """host:/path -> local read-only mirror of the small result files; local path -> itself."""
    if ':' not in run or os.path.exists(run):
        return Path(run).resolve()
    host, path = run.split(':', 1)
    path = path.rstrip('/')
    ssh = 'ssh -o ControlPath=none -o ConnectTimeout=20'
    probe = subprocess.run(ssh.split() + [host, f'test -f {path}/case.json && echo case || echo run'],
                           capture_output=True, text=True, timeout=120)
    if probe.stdout.strip() == 'case':      # given the case dir itself: mirror it as <run>/case
        path, sub = os.path.dirname(path), os.path.basename(path)
    else:
        sub = 'case'
    dst = CACHE / (host + '_' + re.sub(r'[^\w.-]+', '_', path.strip('/')))
    dst.mkdir(parents=True, exist_ok=True)
    pats = [p.replace('case/', sub + '/', 1) for p in FETCH]
    inc = ['--include=*/'] + [f'--include={p}' for p in pats] + ['--exclude=*']
    subprocess.run(['rsync', '-a', '--prune-empty-dirs', '-m', '-e', ssh] + inc + [f'{host}:{path}/', f'{dst}/'],
                   check=False, timeout=1800)
    if sub != 'case' and (dst / sub).exists() and not (dst / 'case').exists():
        (dst / 'case').symlink_to(sub)
    plan = None
    try:
        plan = json.load(open(dst / 'case' / 'case.json')).get('plan')
    except Exception:
        pass
    if plan and (dst / 'case' / 'out' / 'grt_congestion.rpt').exists():
        subprocess.run(['rsync', '-a', '-e', ssh, f'{host}:{plan}', str(dst / 'plan.json')], check=False, timeout=600)
    return dst


def jload(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def tail(p, n=20):
    try:
        return open(p, errors='replace').read().splitlines()[-n:]
    except OSError:
        return []


# ------------------------------------------------------------------ endpoint classes
class Classifier:
    def __init__(self, case):
        self.chains = {c['link']: c for c in (case or {}).get('chains', [])}
        self.land = {v['inst']: k for k, v in (case or {}).get('landings', {}).items() if v.get('inst')}

    def link_of(self, name):
        if name in self.chains:
            return name
        m = re.match(r'(.+)_(\d+)$', name)
        return m.group(1) if m and m.group(1) in self.chains else None

    def owner(self, inst):
        for pre in ('st_', 'ld_', 'fwd_'):
            if inst.startswith(pre):
                lk = self.link_of(inst[len(pre):]) or self.land.get(inst)
                if lk and lk in self.chains:
                    c = self.chains[lk]
                    return f"{c['cls']}:{lk} {c['src']}->{c['dst']}"
        if inst.startswith(('u_', 'rinv_')):
            return inst.split('_', 1)[1]
        return inst

    def klass(self, ep, master, slack, tag):
        inst, _, pin = ep.rpartition('/')
        pinb = pin.split('[')[0]
        view = 'standin' if master.startswith('rv_') else 'closed'
        if inst.startswith('u_f_') and (pinb in ('xk', 'xok', 'clk', 'cr', 'cr_s') or pinb.startswith('ck')
                                        or (tag == 'setup' and slack < -T_PS)):
            return 'frame_clock_model'
        if inst.startswith('fwd_') or pinb in ('ENA', 'GATE', 'SE'):
            return 'forward_enable'
        if re.match(r'(st_rs[a-z]*_|rst_root)', inst):
            return 'reset_station'
        if inst.startswith('ld_') and re.fullmatch(r'rs|rst_?n?|rs_?n', pinb):
            return 'landing_reset'
        if inst.startswith('rinv_') or (inst.startswith('u_') and re.fullmatch(r'rst_?n?|rs|reset_?n?', pinb)):
            return 'block_reset'
        if inst.startswith('st_') and re.fullmatch(r'rs|rst_?n?', pinb):
            return 'relay_reset'
        if inst.startswith('st_'):
            lk = self.link_of(inst[3:])
            return 'relay_data|' + (self.chains[lk]['cls'] if lk else inst[3:].split('_')[0])
        if inst.startswith('ld_'):
            lk = self.land.get(inst) or self.link_of(inst[3:])
            return 'landing_data|' + (self.chains[lk]['cls'] if lk in self.chains else inst[3:].split('_')[0])
        if inst.startswith('u_'):
            return f"block_in|{re.sub(r'_?[0-9]+[A-Z]*[0-9]*$', '', inst[2:]) or inst[2:]}|{view}"
        return 'other|' + inst.split('_')[0]


def parse_paths(p):
    """<c>_<tag>.paths.rpt -> {(endpoint inst, slack rounded): startpoint text}"""
    out = {}
    try:
        txt = open(p, errors='replace').read()
    except OSError:
        return out
    for blk in txt.split('Startpoint: ')[1:]:
        sp = blk.split('\n', 1)[0].strip()
        m = re.search(r'Endpoint: (\S+)', blk)
        s = re.search(r'(-?\d+\.?\d*)\s+slack', blk)
        if m and s:
            out.setdefault((m.group(1), round(float(s.group(1)))), sp)
    return out


def classify_sta(sta, cl, top):
    res = {}
    order = {'tt': 0, 'ff': 1, 'ss': 2}
    for rpt in sorted(glob.glob(str(sta / '*_*.end.rpt')),
                      key=lambda p: (order.get(Path(p).name.split('_')[0], 9), Path(p).name)):
        corner, tag = Path(rpt).name.split('.')[0].split('_', 1)
        starts = parse_paths(sta / f'{corner}_{tag}.paths.rpt')
        agg = collections.defaultdict(lambda: dict(n=0, viol=0, wns=None, tns=0.0, top=[]))
        group = None
        for line in open(rpt, errors='replace'):
            if 'group' in line and line.startswith(('max_delay', 'min_delay')):
                group = line.split()[-1]
                continue
            f = line.replace('(VIOLATED)', '').replace('(MET)', '').split()
            if len(f) < 4 or '/' not in f[0]:
                continue
            try:
                slack = float(f[-1])
            except ValueError:
                continue
            master = f[1].strip('()') if f[1].startswith('(') else '?'
            k = cl.klass(f[0], master, slack, tag)
            a = agg[k]
            a['n'] += 1
            if a['wns'] is None or slack < a['wns']:
                a['wns'] = slack
            if slack < 0:
                a['viol'] += 1
                a['tns'] += slack
                a['top'].append((slack, f[0], master, group))
                if len(a['top']) > 4 * top:
                    a['top'] = sorted(a['top'])[:top]
        for k, a in agg.items():
            rows = []
            for slack, ep, master, group in sorted(a['top'])[:top]:
                inst = ep.rpartition('/')[0]
                rows.append(dict(slack=slack, endpoint=ep, master=master, clock=group,
                                 view='standin' if master.startswith('rv_') else 'closed', owner=cl.owner(inst),
                                 start=starts.get((inst, round(slack)))))
            a['top'] = rows
            a['tns'] = round(a['tns'], 1)
            a['systemic'] = a['n'] >= 50 and a['viol'] >= 0.9 * a['n']     # whole class fails: model/structure, not a few paths
        res[f'{corner}_{tag}'] = dict(sorted(agg.items(), key=lambda kv: kv[1]['wns'] if kv[1]['wns'] is not None else 1e9))
    return res


# ------------------------------------------------------------------ non-path results
def grt_summary(case, plan_path):
    log = case / 'out' / 'run.log'
    out = dict(rc=(open(case / 'out' / 'run.exit').read().strip() if (case / 'out' / 'run.exit').exists() else None))
    try:
        txt = open(log, errors='replace').read()
    except OSError:
        txt = ''
    m = re.search(r'Final congestion report:.*?\n(.*?)\n\s*\n', txt, re.S)
    if m:
        tot = [ln for ln in m.group(1).splitlines() if ln.startswith('Total')]
        if tot:
            hv = re.findall(r'(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*$', tot[0])
            if hv:
                out['overflow_H_V_total'] = [int(x) for x in hv[0]]
        out['per_layer'] = {ln.split()[0]: ln.split('%')[-1].strip() for ln in m.group(1).splitlines()
                            if re.match(r'M\d', ln) and not re.search(r'\b0 /\s+0 /\s+0\s*$', ln)}
    for key in ('OT_GRT_S', 'OT_DIE_REP PASS', 'OT_DIE_REP FAIL', 'OT_DIE_REP post-GRT violators', 'OT_DIE_REP_FCLK fclk',
                'OT_DONE', 'GRT-0116', 'ERROR'):
        hits = [ln.strip()[:200] for ln in txt.splitlines() if key in ln]
        if hits:
            out[key] = hits[-1]
    rpt = case / 'out' / 'grt_congestion.rpt'
    if rpt.exists():
        blocks = (jload(plan_path) or {}).get('blocks', []) if plan_path else []

        def where(x, y):
            for b in blocks:
                if b['x'] <= x <= b['x'] + b['w'] and b['y'] <= y <= b['y'] + b['h']:
                    return f"over:{b.get('kind', '?')}:{b['name']}"
            if blocks:
                b = min(blocks, key=lambda b: abs(x - b['x'] - b['w'] / 2) + abs(y - b['y'] - b['h'] / 2))
                return f"channel@{b.get('group') or b['name']}"
            return f'grid1mm:{int(x // 1000)},{int(y // 1000)}'
        reg, nets, ov = collections.Counter(), collections.Counter(), 0
        src = []
        for line in open(rpt, errors='replace'):
            line = line.strip()
            if line.startswith('srcs:'):
                src = [s[4:] for s in line.split()[1:] if s.startswith('net:')]
            elif line.startswith('comment:'):
                mm = re.search(r'congestion:\s*(\d+)', line)
                ov = int(mm.group(1)) if mm else 1
            elif line.startswith('bbox'):
                v = [float(q) for q in re.findall(r'-?\d+\.?\d*', line.split('=', 1)[-1])[:4]]
                if len(v) == 4:
                    reg[where((v[0] + v[2]) / 2, (v[1] + v[3]) / 2)] += ov
                    for n in src:
                        nets[re.sub(r'\d+', 'N', n.split('[')[0])] += 1
        out['congestion_by_region'] = dict(reg.most_common(25))
        out['congestion_net_classes'] = dict(nets.most_common(15))
    return out


def fclk_summary(case):
    out = {}
    for nm in ('die_repeaters.fclk.post_grt.json', 'die_repeaters.fclk.pre_eq.json'):
        j = jload(case / nm)
        if j:
            out[nm] = {k: j.get(k) for k in ('verdict', 'hops_judged', 'mismatch_over_1', 'pairing_errors', 'vacuous',
                                             'broadcast_fclk_nets')}
            ex = j.get('examples') or []
            out[nm]['owners'] = dict(collections.Counter(
                re.sub(r'_\d+$', '', (e.split()[1].split('->')[0] if len(e.split()) > 1 else e)) for e in ex))
            out[nm]['examples'] = ex[:5]
    return out


def clock_summary(sta):
    out = {}
    for p in sorted(glob.glob(str(sta / 'die_clock_check_*.json'))):
        j = jload(p) or {}
        c = Path(p).stem.rsplit('_', 1)[-1]
        nc = j.get('noncommon') or {}
        ins = j.get('insertion') or {}
        out[c] = dict(neighbour_check=j.get('neighbour_check'), threshold=j.get('threshold'),
                      pairs=nc.get('pairs'), no_common_root=nc.get('no_common_root'),
                      unmatched_pairs=nc.get('unmatched_pairs'),
                      sta_skew_max_ps=(nc.get('sta_skew_ps') or {}).get('max'),
                      insertion_sta_max_ps=(ins.get('sta_max_ps') or {}).get('max'),
                      roots=len((j.get('counts') or {}).get('roots', [])))
    cj = jload(sta / 'classes.json') or {}
    judge = cj.get('judge') or {}
    for k in ('landed', 'frame_lanes', 'unlanded_pairs'):
        if k in judge:
            out[k] = {kk: judge[k].get(kk) for kk in ('n', 'verdicts', 'max_tt_ff_drift_ps', 'worst') if kk in judge[k]}
            if out[k].get('worst'):
                out[k]['worst'] = out[k]['worst'][:5]
    if judge.get('regional_roots'):
        out['regional_roots'] = judge['regional_roots']
    return out


def drv_summary(sta):
    out = {}
    for p in sorted(glob.glob(str(sta / '*_drv.rpt'))):
        c = Path(p).name.split('_')[0]
        cur, cnt, worst = None, collections.Counter(), {}
        for line in open(p, errors='replace'):
            if line.startswith('max '):
                cur = line.strip()
            elif '(VIOLATED)' in line and cur:
                cnt[cur] += 1
                try:
                    s = float(line.split()[-2])
                    if s < worst.get(cur, (0,))[0]:
                        worst[cur] = (s, line.split()[0])
                except ValueError:
                    pass
        out[c] = {k: dict(n=v, worst=worst.get(k)) for k, v in cnt.items()}
    return out


def stage_status(run, case):
    st = dict(steps=[ln[:140] for ln in tail(run / 'steps.log', 60) if re.search(r'_RC |_DONE|FAIL|PASS', ln)][-12:],
              run_all=tail(case / 'run_all.log', 12))
    pb = jload(run / 'bind' / 'bind' / 'port_bind.json')
    if pb:
        st['port_bind'] = dict(verdict=pb.get('verdict'), failing=pb.get('failing'),
                               unresolved_children=(pb.get('child_closure') or {}).get('unresolved_children'),
                               unread_classes=list((pb.get('unread_classes') or {}))[:8],
                               fail_lines=[ln for ln in tail(run / 'bind' / 'bind' / 'port_bind.log', 400)
                                           if ln.startswith(('FAIL', 'DIE_PORT_BIND'))][-12:])
    lr = jload(run / 'bind' / 'bind' / 'landing_reset_check.json')
    if lr:
        st['landing_reset_check'] = dict(verdict=lr.get('verdict'), mismatch=lr.get('mismatch', [])[:5],
                                         unresolved=lr.get('unresolved', [])[:5])
    try:
        bl = open(run / 'bind.log', errors='replace').read()
        m = re.findall(r'"reach_gate": "(\w+)"', bl)
        s = re.findall(r'"sinks": (\d+)', bl)
        if m:
            st['reset_reach'] = dict(verdict=m[-1], sinks=int(s[-1]) if s else None)
    except OSError:
        pass
    gs = jload(case / 'gen_safety.json')
    if gs:
        st['gen_safety'] = dict(verdict=gs.get('verdict'), fails=(gs.get('fails') or [])[:8])
    if (case / 'NOT_A_DIE_RESULT').exists():
        st['NOT_A_DIE_RESULT'] = tail(case / 'NOT_A_DIE_RESULT', 8)
    ir = jload(case / 'ir_drop' / 'ir_drop.json')
    if ir:
        st['ir_drop'] = {k: ir.get(k) for k in ('verdict', 'worst_mV', 'limit_mV', 'max_drop_mv') if k in ir}
    return st


# ------------------------------------------------------------------ main
def headline(res):
    """one line per (corner, check): worst classes with WNS (violators, ALL = every endpoint of the class fails)."""
    rows = []
    for ck, classes in res.items():
        bad = [(k, a) for k, a in classes.items() if a['viol']]
        if not bad:
            w = min((a['wns'] for a in classes.values() if a['wns'] is not None), default=None)
            rows.append(f'{ck:9s} PASS  wns={w}')
            continue
        rows.append(f"{ck:9s} FAIL  " + '; '.join(f"{k} {a['wns']:.1f} ({a['viol']}{' ALL' if a.get('systemic') else ''})"
                                                for k, a in bad[:7]) + ('  [SS = sensitivity only]' if ck.startswith('ss') else ''))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run', help='die run dir or case dir, local or host:/path')
    ap.add_argument('--out', type=Path, help='output dir for die_class.json / die_class.txt (default: <mirror>/)')
    ap.add_argument('--top', type=int, default=8)
    a = ap.parse_args(argv)
    run = fetch(a.run)
    if (run / 'case.json').exists() and not (run / 'case').exists():
        case = run
        run = run.parent
    else:
        case = run / 'case'
    cj = jload(case / 'case.json')
    cl = Classifier(cj)
    sta = case / 'sta'
    plan = run / 'plan.json' if (run / 'plan.json').exists() else (cj or {}).get('plan')
    res = dict(schema='opentallas.s81_dv.die_sta_classify.v1', run=a.run, local=str(run),
               label=(cj or {}).get('label', '')[:300], die_um=(cj or {}).get('die_um'),
               standin_instances=(cj or {}).get('standin_instances'),
               stages=stage_status(run, case), grt=grt_summary(case, plan),
               sta=classify_sta(sta, cl, a.top) if sta.exists() else {},
               fclk_audit=fclk_summary(case), clock=clock_summary(sta), drv=drv_summary(sta))
    res['headline'] = headline(res['sta'])
    out = a.out or (run if str(run).startswith(str(CACHE)) else CACHE / re.sub(r'[^\w.-]+', '_', str(run).strip('/')))
    out.mkdir(parents=True, exist_ok=True)
    (out / 'die_class.json').write_text(json.dumps(res, indent=1, default=str) + '\n')
    s = res['stages']
    L = [f"# die_sta_classify {a.run}", f"label: {res['label'][:160]}",
         'stages: ' + (' | '.join(x[:60] for x in s['steps'][-8:]) or '-'),
         'run_all: ' + (' | '.join(s['run_all']) or '-')]
    for k in ('port_bind', 'reset_reach', 'landing_reset_check', 'gen_safety', 'ir_drop'):
        if k in s:
            v = s[k]
            L.append(f"  {k}: {v.get('verdict')} " + json.dumps({kk: vv for kk, vv in v.items()
                                                               if kk not in ('verdict', 'fail_lines')}, default=str)[:300])
            for fl in v.get('fail_lines', [])[:12]:
                L.append(f'    {fl[:160]}')
    g = res['grt']
    L.append(f"GRT: rc={g.get('rc')} overflow(H/V/T)={g.get('overflow_H_V_total')} "
             f"{g.get('OT_DIE_REP PASS', g.get('OT_DIE_REP FAIL', ''))[:90]}")
    if g.get('per_layer'):
        L.append(f"  congested layers: {g['per_layer']}")
    for k, v in (g.get('congestion_by_region') or {}).items():
        L.append(f'  overflow {v:7d} {k}')
    L.append('STA headline:')
    L += ['  ' + r for r in res['headline']]
    for ck, classes in res['sta'].items():
        if ck.startswith('ss'):
            continue        # SS: sensitivity only (owner option B); full rows in die_class.json
        for k, x in classes.items():
            if not x['viol']:
                continue
            L.append(f"  [{ck}] {k:34s} viol={x['viol']:7d}/{x['n']:<7d} wns={x['wns']:9.1f} tns={x['tns']:12.1f}"
                     + ('  ALL-ENDPOINTS' if x.get('systemic') else ''))
            for r in x['top'][:3]:
                L.append(f"      {r['slack']:9.1f} {r['endpoint']:44s} {r['master']:22s} {r['view']:7s} {r['owner'][:44]}"
                         + (f"  <- {r['start'][:60]}" if r['start'] else ''))
    for nm, v in res['fclk_audit'].items():
        L.append(f"fclk audit {nm}: {v.get('verdict')} mismatch>1={v.get('mismatch_over_1')}/{v.get('hops_judged')} "
                 f"pairing={v.get('pairing_errors')} vacuous={v.get('vacuous')} owners={v.get('owners')}")
    for c, v in res['clock'].items():
        L.append(f'clock {c}: ' + json.dumps(v, default=str)[:260])
    for c, v in res['drv'].items():
        L.append(f'drv {c}: ' + json.dumps(v, default=str)[:260])
    txt = '\n'.join(L) + '\n'
    (out / 'die_class.txt').write_text(txt)
    try:
        print(txt + f'-> {out}/die_class.json')
    except BrokenPipeError:
        pass


if __name__ == '__main__':
    sys.exit(main())
