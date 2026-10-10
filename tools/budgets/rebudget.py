#!/usr/bin/env python3
"""REBUDGET (Claude, 2026-10-08, owner: "follow the hierarchical flow properly"): re-derive the die-link IO budgets from
REAL block models and judge cross-block paths at the die level.  The closure drive redesigns blocks against FIXED link
budgets (link_budget_consistent.sdc: S = R = (T - 60 - 150 skew - 114 link) / 2 for every port of every block); this is
the missing half of the hierarchical flow.

  1. LINK MODEL (`links`).  Every die-level link between hardened blocks, at TT setup and FF hold, from a die STA session
     on the die global-route parasitics (tools/budgets/rebudget_links.tcl, sourced at the end of the S81 die_sta.py kit
     session / the HBM hbm_die_relay_sta.py in-session GRT): the sender's clock->output (its ETM / lib), the die wire +
     relays (GRT RC), the receiver's setup / hold (its ETM), and the clock-plan arrival at both ends (the die kit's
     balanced pin latencies = plan target - the view's own in-arc insertion).  Per link (sender bus -> receiver bus):
        target_x = pin latency_x + in-arc insertion_x                      (the planned flop arrival)
        C (setup capacity for S + R) = T - U_S - W - (target_s - target_r)    U_S = 60 sign-off + 25 plan tolerance
        H (hold credit)              = W_min + (target_s - target_r) - U_H   U_H = 25 sign-off + 25 plan tolerance
     with S = sender reference -> pin, R = pin -> capture flop + setup (both relative to the block's own boundary-
     register mean insertion: the routed-ioref convention), s_min / h = the FF counterparts.  Slab-internal (S81-PH tile)
     hops use the assembled-view glue model (tools/s81/assemble_views.py: composition geometry, analytic wire) and are
     labelled so.  A side with no timing view (black box / placeholder) has no real need: such a link keeps the old budget.
  2. REAL NEEDS (`measure`).  An open block's need is measured on its ROUTED database: meas_resta.py re-times the route
     at TT / FF with io_ref_routed.sdc + physical/common_flow/rebudget_measure.sdc (zero IO budget at the routed
     reference, per port bit).  A closed block's need is its ETM's, read from the die dump (kit).
  3. RE-DERIVE (`derive`).  Each link's real capacity is split between sender and receiver in proportion to their
     needs (S_b = C S/(S+R), R_b = C R/(S+R); hold: the margin s_min + H - h shared equally), never exceeding the link;
     a master port takes the minimum over its links.  RULE (owner 4): a pass never steals from a CLOSED neighbour -- a
     link whose real capacity cannot hold both needs and touches a closed block keeps its old budget.  A port is
     re-budgeted only when every link of it was re-derived.  Output: results/arch/rebudget_<date>/budget_rb<N>/ (one
     SDC per open job, per closed master; links / needs / summary JSON; README).
  4. RE-JUDGE (`rejudge`).  Every NEEDS_RTL job whose routed internals pass (R2R TT / FF >= 0 at zero IO budget) and
     whose block has a routed DB is re-timed with its budget_rb SDC through the closure loop (`closure_loop.py
     rebudget-rejudge`, the routed_ioref re-STA with the SDC appended): flips go back to the verdict (CLOSED, verdict
     text cites budget_rb<N>); the rest stay with the real shortfall per link.

  rebudget.py candidates [--die hbm_r25,s81_r3]          list NEEDS_RTL port-only candidates with a die mapping
  rebudget.py measure  [--jobs a,b] [--parallel 8]       measure real port needs on the routed DBs (remote)
  rebudget.py links    --die s81_r3                      fetch + parse a die link dump -> links_<die>.json
  rebudget.py derive   --rb N                            budgets + SDCs + summary
  rebudget.py rejudge  --rb N [--apply]                  re-STA through the loop (--apply: flip jobs)
  rebudget.py drive    [--apply]                         loop hook: measure new candidates, derive rb<N+1>, rejudge
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
STATE = Path(os.environ.get('CL_STATE', str(Path.home() / '.local/state/closure_loop')))
JOBS = STATE / 'jobs'
OUT = ROOT / 'results/arch/rebudget_20261008'
LOOP = Path(os.environ.get('OT_CLOSURE_LOOP', str(ROOT / 'tools/closure_loop/closure_loop.py')))
MEASURE_SDC = ROOT / 'physical/common_flow/rebudget_measure.sdc'
IOREF_SDC = ROOT / 'physical/common_flow/io_ref_routed.sdc'
MEAS_RESTA = ROOT / 'tools/closure_loop/meas_resta.py'

U_S, U_H = 85.0, 50.0           # die link uncertainty: setup 60 sign-off + 25 plan tolerance; hold 25 + 25 (rule H1)
OLD_S = OLD_R = (833.333 - 60 - 150 - 114) / 2   # link_budget_consistent.sdc default split (reference only)

# Die link dumps (tools/budgets/rebudget_links.tcl output) and their die STA conventions.
DIES = {
    's81_r3': dict(host='ot-epyc3', dump='/srv/opentallas-scratch/claude/rebudget/s81_r3',
                   kit='/srv/opentallas-scratch/claude/s81-die/m221pq_r3/kit_v6', unc=dict(tt=85.0, ff=50.0),
                   desc='DS-V4.1 ROM S81 m221pq_r3: full-die GRT (k=1) parasitics, kit_v6 views (balanced plan latencies)'),
    'hbm_r25': dict(host='ot-epyc1tb', dump='/srv/opentallas-scratch/claude/rebudget/hbm_r25',
                    case='/srv/opentallas-scratch/claude/die-evidence/hbm_r25/grt3', unc=dict(tt=210.0, ff=25.0),
                    desc='HBM accelerator r25: full-die GRT parasitics (grt3 case, in-session global route), relay clock context'),
}


def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def sh(cmd, timeout=600, input=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=input)


def ssh(host, script, timeout=600):
    return sh(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', host, 'bash -s'], timeout=timeout, input=script)


def base(n):
    return re.sub(r'\[\d+\]$', '', n)


# ------------------------------------------------------------------------------------------------ jobs / candidates
def load_jobs():
    out = {}
    for f in JOBS.glob('*.json'):
        try:
            j = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        out[j['name']] = j
    return out


def rr_of(j):
    return j.get('routed_ioref') or (j.get('metrics') or {}).get('routed_ioref') or {}


def port_only_prefilter(j):
    """NEEDS_RTL, routed re-STA available, DRC 0, no failed checks / installed ECO, and the worst TT / FF path is a
    port path (the measure run confirms: R2R at TT and FF >= 0 at zero IO budget)"""
    m, rr = j.get('metrics') or {}, rr_of(j)
    if j['status'] != 'NEEDS_RTL' or not rr.get('available') or m.get('drc') != 0 or j.get('failed_checks'):
        return False, 'not a routed NEEDS_RTL with DRC 0'
    if (j.get('eco') or {}).get('installed'):
        return False, 'an installed ECO replaced the route'
    tt, ff = rr.get('tt'), rr.get('ff')
    if tt is None or ff is None or (tt >= 0 and ff >= 0):
        return False, 'no failure'
    ports_tt = [x for x in (rr.get('tt_i2r'), rr.get('tt_out')) if x is not None]
    if tt < 0 and (not ports_tt or min(ports_tt) > tt + 0.01):
        return False, f'TT worst {tt} is reg-to-reg'
    if ff < 0 and rr.get('ff_r2r') is not None and rr['ff_r2r'] < 0:
        return False, f'FF reg-to-reg {rr["ff_r2r"]}'
    return True, ''


def slab_map():
    """S81-PH tile -> (slab, {slab port: [tile pins]}) from the assembled-view spec"""
    try:
        from s81 import assemble_views as AV
    except Exception:  # noqa: BLE001
        AV = None
    out = {}
    # die-facing tile ports of every S81-PH slab (assembled or partitioned): tools/budgets/tiles.py "inherit" edges
    tj = ROOT / 'results/rtl/budgets_20261006/inputs/tiles.json'
    if tj.exists():
        for t, v in json.loads(tj.read_text())['tiles'].items():
            ent = out.setdefault(t, (v['slab'], {}))
            for e in v.get('edges', []):
                inh = e.get('inherit')
                if inh and inh[1]:
                    tp = [p for p, _ in e['ports']]
                    for sp in inh[1]:
                        ent[1].setdefault(sp, []).extend(x for x in tp if x == sp or len(tp) == len(inh[1]))
    for slab, spec in (AV.SLABS.items() if AV else ()):
        for sp, srcs in spec['ports'].items():
            for t, pins in srcs:
                out.setdefault(t, (slab, {}))[1].setdefault(sp, []).extend(pins)
        for g in spec['glue']:
            for t in (g[0], g[2]):
                out.setdefault(t, (slab, {}))
    return out, AV


def die_masters(die):
    p = OUT / f'masters_{die}.json'
    return json.loads(p.read_text()) if p.exists() else {}


def die_of(master, masters_by_die, tiles):
    """(die, die master, tile or None) for a block master"""
    for die, ms in masters_by_die.items():
        if master in ms:
            return die, master, None
    if master in tiles:
        slab = tiles[master][0]
        for die, ms in masters_by_die.items():
            if slab in ms:
                return die, slab, master
    return None, None, None


def cmd_candidates(a, quiet=False):
    jobs = load_jobs()
    tiles, _ = slab_map()
    mbd = {d: die_masters(d) for d in DIES}
    closed_blocks = {j['spec'].get('block') for j in jobs.values() if j['status'] == 'CLOSED'}
    rows = []
    for n, j in sorted(jobs.items()):
        ok, why = port_only_prefilter(j)
        if not ok:
            continue
        blk = j['spec'].get('block')
        die, dm, tile = die_of(blk, mbd, tiles)
        rr = rr_of(j)
        rows.append(dict(job=n, block=blk, die=die, die_master=dm, tile=tile, host=j['host'], run=j['run'],
                         orfs=(j.get('metrics') or {}).get('orfs_dir'), tt=rr.get('tt'), ff=rr.get('ff'),
                         block_closed_elsewhere=blk in closed_blocks))
    if not quiet:
        for r in rows:
            print(f"{r['job']:62s} {r['block']:40s} die={r['die'] or '-':8s} master={r['die_master'] or '-'}"
                  f"{' tile' if r['tile'] else ''} TT {r['tt']:+.1f} FF {r['ff']:+.1f}{' (block closed elsewhere)' if r['block_closed_elsewhere'] else ''}")
    return rows


# ------------------------------------------------------------------------------------------------ measure (block side)
def parse_ports(log):
    """OT_RB_PORT / OT_RB_REF / OT_RB_DOMAIN lines -> ({port bit: (dir, slack_max, slack_min)}, {clock: {L, T}},
    {bus: domain clock or None})"""
    out, refs, dom = {}, {}, {}
    f = lambda v: None if v == 'INF' else float(v)  # noqa: E731
    for m in re.finditer(r'^OT_RB_PORT (\S+) (in|out) (\S+) (\S+)$', log, re.M):
        out[m.group(1)] = (m.group(2), f(m.group(3)), f(m.group(4)))
    for m in re.finditer(r'^OT_RB_REF (\S+) (\S+) T (\S+) in (\d+) out (\d+)', log, re.M):
        refs[m.group(1)] = dict(L=float(m.group(2)), T=float(m.group(3)))
    for m in re.finditer(r'^OT_RB_DOMAIN (\S+) (in|out) (\S+)$', log, re.M):
        dom[m.group(1)] = None if m.group(3) == '-' else m.group(3)
    for m in re.finditer(r'^OT_RB_FWDCLK (\S+) (\S+) (\S+) (\S+)$', log, re.M):
        refs.setdefault('_fwd', {})[base(m.group(1))] = dict(clock=m.group(2), A=f(m.group(3).replace('NA', 'INF')),
                                                            A_min=f(m.group(4).replace('NA', 'INF')))
    return out, refs, dom


def needs_from(tt_ports, ff_ports, refs, dom):
    """per bus (its clock domain): inputs R (TT, worst bit) / h (FF, worst bit); outputs S (TT) / s_min (FF)"""
    buses = {}
    for p, (d, smax, _) in tt_ports.items():
        bn = base(p)
        dc = dom.get(bn)
        b = buses.setdefault(bn, dict(dir=d, bits=0, clock=dc, T=(refs.get(dc) or {}).get('T')))
        b['bits'] += 1
        if smax is not None and b['T']:
            k = 'R' if d == 'in' else 'S'
            b[k] = max(b.get(k, -1e9), round(b['T'] - smax, 1))
    for p, (d, _, smin) in ff_ports.items():
        b = buses.setdefault(base(p), dict(dir=d, bits=0, clock=dom.get(base(p))))
        if smin is not None and b.get('clock'):
            if d == 'in':
                b['h'] = max(b.get('h', -1e9), round(-smin, 1))
            else:
                b['smin'] = min(b.get('smin', 1e9), round(smin, 1))
    return buses


def measure_job(r):
    """run meas_resta.py on the job's host with io_ref_routed.sdc + rebudget_measure.sdc appended"""
    host, run, orfs = r['host'], r['run'], r['orfs']
    if host in ('localhost', '127.0.0.1'):
        # owner rule: no heavy jobs on localhost (a block re-STA is two docker sessions)
        return dict(job=r['job'], error='route on localhost: not measured (no heavy jobs on localhost)')
    tag = 'rbm'
    for f in (() if r.get('reparse') else (MEAS_RESTA, MEASURE_SDC, IOREF_SDC)):
        p = sh(['scp', '-q', str(f), f'{host}:{run}/cl/{f.name}'], timeout=120)
        if p.returncode:
            return dict(job=r['job'], error=f'scp {f.name}: {p.stderr[-200:]}')
    out = f'{run}/cl/{tag}.json'
    rerun = '' if r.get('reparse') else (f"python3 {run}/cl/meas_resta.py --orfs {shlex.quote(orfs)} --src {run}/src --out {out} "
                                         f"--append {run}/cl/io_ref_routed.sdc --append {run}/cl/rebudget_measure.sdc > {run}/cl/{tag}.out 2>&1; ")
    p = ssh(host, rerun + f"cat {out}; echo; echo '=====TT'; cat {run}/cl/{tag}_meas/meas_ss.log; echo '=====FF'; "
                  f"cat {run}/cl/{tag}_meas/meas_ff.log", timeout=9000)
    s = p.stdout
    try:
        res = json.loads(s.split('\n=====TT')[0].strip())
    except (ValueError, IndexError):
        return dict(job=r['job'], error=f'meas_resta output unreadable (rc {p.returncode}): {s[-300:]}{p.stderr[-200:]}')
    tt_log = s.split('=====TT', 1)[1].split('=====FF', 1)[0] if '=====TT' in s else ''
    ff_log = s.split('=====FF', 1)[1] if '=====FF' in s else ''
    tt_ports, ref_tt, dom = parse_ports(tt_log)
    ff_ports, ref_ff, _ = parse_ports(ff_log)
    fwd = {k: dict(clock=v['clock'], A=v['A'], A_min=(ref_ff.get('_fwd', {}).get(k) or {}).get('A_min'))
           for k, v in ref_tt.pop('_fwd', {}).items()}
    ref_ff.pop('_fwd', None)
    if not ref_tt or not tt_ports:
        return dict(job=r['job'], error='no OT_RB_REF / OT_RB_PORT lines (no reference clock or no data ports)',
                    resta=res)
    rec = dict(schema='opentallas.rebudget.needs.v1', job=r['job'], block=r['block'], die=r.get('die'),
               die_master=r.get('die_master'), tile=r.get('tile'), host=host, run=run, orfs=orfs, measured_at=now(),
               method='meas_resta.py --append io_ref_routed.sdc --append rebudget_measure.sdc (zero IO budget at the '
                      'routed boundary-register mean, no IO uncertainty)',
               ref=dict(tt=ref_tt, ff=ref_ff),
               r2r=dict(tt=res['setup_tt'].get('worst_reg_to_reg_slack_ps'), ff=res['hold_ff'].get('worst_reg_to_reg_slack_ps')),
               errors=(res['setup_tt'].get('errors') or []) + (res['hold_ff'].get('errors') or []),
               ports=needs_from(tt_ports, ff_ports, ref_tt, dom),
               # forwarded-clock outputs: the clock's arrival at the pin vs its reference (TT max / FF min), for the
               # source-synchronous frame of the data buses it travels with (S_fw = S - A, smin_fw = smin - A_min)
               fwd=fwd)
    r2r = rec['r2r']
    rec['internal_ok'] = r2r['tt'] is not None and r2r['ff'] is not None and r2r['tt'] >= 0 and r2r['ff'] >= 0 \
        and not rec['errors']
    return rec


def cmd_measure(a):
    rows = cmd_candidates(a, quiet=True)
    if a.jobs:
        want = set(a.jobs.split(','))
        rows = [r for r in rows if r['job'] in want]
    elif not a.all:
        rows = [r for r in rows if r['die'] in (a.die.split(',') if a.die else DIES)]
    (OUT / 'needs').mkdir(parents=True, exist_ok=True)
    todo = [r for r in rows if a.force or a.reparse or not (OUT / 'needs' / f"{r['job']}.json").exists()]
    for r in todo:
        r['reparse'] = a.reparse
    print(f'measuring {len(todo)} of {len(rows)} candidates')
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        for rec in ex.map(measure_job, todo):
            (OUT / 'needs' / f"{rec['job']}.json").write_text(json.dumps(rec, indent=1) + '\n')
            print(rec['job'], 'ERROR ' + rec['error'] if rec.get('error') else
                  f"r2r TT {rec['r2r']['tt']} FF {rec['r2r']['ff']} ports {len(rec['ports'])}", flush=True)


# ------------------------------------------------------------------------------------------------ die links
def parse_dump(text):
    P, E, L = [], [], {}
    for ln in text.splitlines():
        f = ln.split('\t')
        if f[0] == 'P' and len(f) >= 17:
            x = lambda i: None if len(f) <= i or f[i] == '-' else f[i]  # noqa: E731
            P.append(dict(mm=f[1], inst=f[2], bus=f[3], dir=f[4], start=f[5], end=f[6], sclk=f[7], eclk=f[8],
                          T=float(f[9]), lat_s=float(f[10]), lat_r=float(f[11]), arr_out=float(f[12]),
                          arr_in=float(f[13]), req=float(f[14]), margin=float(f[15]), slack=float(f[16]),
                          cap_time=float(x(17)) if x(17) else None, cap_tr=x(18),
                          fo_arc=float(x(19)) if x(19) else None, fo_pin=x(20)))
        elif f[0] == 'E' and len(f) == 8:
            E.append(dict(mm=f[1], inst=f[2], bus=f[3], dir=f[4], drv=f[5], load=f[6], W=float(f[7])))
        elif f[0] == 'L' and len(f) >= 3:
            L[f[1].split('/')[0]] = float(f[2])
    return P, E, L


def inst_of(pin):
    return pin.rsplit('/', 1)[0]


def kit_context(die, cfg):
    """inst -> master, master -> view kind, in-arc insertion per instance [ss, ff, tt], per-pin planned latency"""
    host = cfg['host']
    if die == 's81_r3':
        k = cfg['kit']
        py = f"""
import json,re
k=json.load(open('{k}/kit.json'))
off=set(k['routed_insertion'].get('masters_offset') or [])
ins={{m:v.get('insertion_in_arcs_ps') for m,v in k['masters'].items() if m in off and v.get('insertion_in_arcs_ps')}}
views={{m:v['view'] for m,v in k['masters'].items()}}
im={{}}
rx=re.compile(r'^\\s*([A-Za-z0-9_]+)\\s+([A-Za-z0-9_\\\\\\[\\]\\.]+)\\s*\\(')
for ln in open('{k}/die.v'):
    m=rx.match(ln)
    if m and m.group(1) in views: im[m.group(2)]=m.group(1)
lat={{}}
for c in ('tt','ff'):
    d={{}}
    for m in re.finditer(r'set_clock_latency ([-\\d.]+) \\[get_pins -quiet \\{{(\\S+?)/', open('{k}/latency_'+c+'.tcl').read()):
        d.setdefault(m.group(2), float(m.group(1)))
    lat[c]=d
print(json.dumps(dict(inst_master=im, views=views, ins_master=ins, lat=lat)))
"""
        p = ssh(host, f"python3 - <<'EOF'\n{py}\nEOF\n", timeout=900)
        ctx = json.loads(p.stdout)
        ctx['ins'] = {i: ctx['ins_master'][m] for i, m in ctx['inst_master'].items() if m in ctx['ins_master']}
        return ctx
    c = cfg['case']
    py = f"""
import json,re
rx=re.compile(r'^\\s*([A-Za-z0-9_]+)\\s+([A-Za-z0-9_\\\\\\[\\]\\.]+)\\s*\\(')
im={{}}
for ln in open('{c}/die.v'):
    m=rx.match(ln)
    if m and m.group(1)!='module': im[m.group(2)]=m.group(1)
import os,glob
libs={{os.path.basename(p)[:-7] for p in glob.glob('{c}/*_tt.lib')}}
views={{m:('relay' if m.startswith('hfd_rly') else 'view' if m in libs else 'none') for m in set(im.values())}}
ctx=json.load(open('{c}/relay_clock_context.json')) if os.path.exists('{c}/relay_clock_context.json') else {{}}
ins={{}}; lat={{'tt':{{}},'ff':{{}}}}
for k,s in list((ctx.get('view_sinks') or {{}}).items())+list((ctx.get('relay_sinks') or {{}}).items()):
    if not isinstance(s,dict): continue
    if s.get('internal_ps'):
        ip=s['internal_ps']; ins[s['instance']]=[ip.get('ss',0),ip.get('ff',0),ip.get('tt',0)]
    for c in ('tt','ff'):
        if (s.get('entry_ps') or {{}}).get(c) is not None: lat[c].setdefault(s['instance'], s['entry_ps'][c])
print(json.dumps(dict(inst_master=im, views=views, ins=ins, lat=lat, ctx_keys=list(ctx))))
"""
    p = ssh(host, f"python3 - <<'EOF'\n{py}\nEOF\n", timeout=900)
    return json.loads(p.stdout)


def context(die, cfg, refresh=False):
    """the die kit context (cached under OUT/ctx_<die>.json.gz) + masters_<die>.json (master -> timing view kind)"""
    import gzip
    p = OUT / f'ctx_{die}.json.gz'
    if p.exists() and not refresh:
        return json.loads(gzip.open(p, 'rt').read())
    ctx = kit_context(die, cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, 'wt') as f:
        json.dump(ctx, f)
    masters = sorted(set(ctx['inst_master'].values()))
    (OUT / f'masters_{die}.json').write_text(json.dumps({m: ctx['views'].get(m) for m in masters}, indent=0) + '\n')
    return ctx


def cmd_masters(a):
    for die in (a.die.split(',') if a.die else DIES):
        ctx = context(die, DIES[die], refresh=True)
        print(die, len(ctx['inst_master']), 'instances,', len(set(ctx['inst_master'].values())), 'masters,',
              len(ctx.get('ins', {})), 'with in-arc insertion')


def build_links(die, cfg, P, E, Lat, ctx):
    """one record per (sender bus, receiver bus): TT setup + FF hold components (see the module doc)"""
    im, ins = ctx['inst_master'], ctx.get('ins', {})
    lat_c = ctx.get('lat', {})
    ci = dict(tt=2, ff=1)
    links = {}
    for p in P:
        c = 'tt' if p['mm'] == 'max' else 'ff'
        si, ri = inst_of(p['start']), inst_of(p['end'])
        key = (si, base(p['start'].rsplit('/', 1)[1]), ri, base(p['end'].rsplit('/', 1)[1]))
        rec = links.setdefault(key, dict(snd_inst=si, snd_master=im.get(si), snd_bus=key[1], rcv_inst=ri,
                                         rcv_master=im.get(ri), rcv_bus=key[3], src='die GRT STA path'))
        if c in rec and rec[c]['slack_die'] <= p['slack']:
            continue
        Ls = (ins.get(si) or [0, 0, 0])[ci[c]]
        Lr = (ins.get(ri) or [0, 0, 0])[ci[c]]
        W = p['arr_in'] - p['arr_out']
        ds = (p['lat_s'] + Ls) - (p['lat_r'] + Lr)
        unc = cfg['unc'][c]
        if p['eclk'].startswith('ot_fw_') and p.get('fo_arc') is not None and p['fo_arc'] > p['T']:
            # a forwarded-clock arc longer than the period is a broken view arc (svc xf: 13 ns): no real model
            rec.setdefault('bad_fwd_arc', p['fo_arc'])
            continue
        if p['eclk'].startswith('ot_fw_') and p.get('fo_arc') is not None:
            # FORWARDED-CLOCK (source-synchronous) hop: captured on the clock the sender forwards (fo_pin), so the
            # common launch latency cancels.  Sender need in the forwarded frame: data pin - forwarded-clock pin.
            # C / H are taken from the die slack (it carries the station check, both wires and the edge relation).
            rec['src'] = 'die GRT STA path (forwarded clock)'
            rec['fwd'] = dict(fo_pin=p['fo_pin'], fo_bus=base(p['fo_pin'].rsplit('/', 1)[1]) if p.get('fo_pin') else None)
            s_fw = round(p['arr_out'] - p['lat_s'] - p['fo_arc'], 1)
            cap = p.get('cap_time')
            if cap is None:
                # the capture edge from the check (OpenSTA's Tcl PathEnd has no edge getter here): setup req = edge +
                # lat_r - unc - margin, hold req = edge + lat_r + unc + margin; snapped to a half period
                raw = p['req'] - p['lat_r'] + (unc + p['margin'] if c == 'tt' else -unc - p['margin'])
                cap = round(round(raw / (p['T'] / 2.0)) * p['T'] / 2.0, 3)
            tr = p.get('cap_tr') or ('fall' if round(cap / (p['T'] / 2.0)) % 2 else 'rise')
            if c == 'tt':
                rec[c] = dict(T=p['T'], T_cap=cap, cap_tr=tr, W=round(W, 1), lat_s=p['lat_s'],
                              lat_r=p['lat_r'], fo_arc=p['fo_arc'], S_kit=s_fw, R_kit=round(p['margin'], 1),
                              C=round(p['slack'] + unc - U_S + s_fw + p['margin'], 1), slack_die=p['slack'], fwd=True)
            else:
                M = p['slack'] + unc - U_H
                # a single-cycle hold check is reported launched one period LATER (data_arrival includes it, the
                # first point's arrival does not): the hold edge relative to the launch is cap - T, the wire W - T
                if W > p['T'] / 2.0:
                    W -= p['T']
                rec[c] = dict(T_hold=round(cap - p['T'], 3), cap_tr=tr, W=round(W, 1), fo_arc=p['fo_arc'],
                              smin_kit=s_fw, h_kit=round(p['margin'], 1), H=round(M - s_fw + p['margin'], 1),
                              slack_die=p['slack'], fwd=True)
            continue
        if c == 'tt':
            rec[c] = dict(T=p['T'], W=round(W, 1), lat_s=p['lat_s'], lat_r=p['lat_r'], L_s=Ls, L_r=Lr, dskew=round(ds, 1),
                          C=round(p['T'] - U_S - W - ds, 1), S_kit=round(p['arr_out'] - p['lat_s'] - Ls, 1),
                          R_kit=round(p['margin'] + Lr, 1), slack_die=p['slack'],
                          # the die STA's own capture adjustment beyond the lib check (OpenSTA 'macro clock tree delay'
                          # on ETM receivers under ideal pin latencies): reported, not used in C / R_kit
                          capture_adj=round(p['T'] + p['lat_r'] - unc - p['margin'] - p['req'], 1))
        else:
            rec[c] = dict(W=round(W, 1), lat_s=p['lat_s'], lat_r=p['lat_r'], L_s=Ls, L_r=Lr, dskew=round(ds, 1),
                          H=round(W + ds - U_H, 1), smin_kit=round(p['arr_out'] - p['lat_s'] - Ls, 1),
                          h_kit=round(p['margin'] - Lr, 1), slack_die=p['slack'],
                          capture_adj=round(p['req'] - p['lat_r'] - unc - p['margin'], 1))
    # buses with no constrained path (a side without a timing view): the wire alone + the planned latencies
    for e in E:
        c = 'tt' if e['mm'] == 'max' else 'ff'
        si, ri = inst_of(e['drv']), inst_of(e['load'])
        key = (si, base(e['drv'].rsplit('/', 1)[1]), ri, base(e['load'].rsplit('/', 1)[1]))
        rec = links.setdefault(key, dict(snd_inst=si, snd_master=im.get(si), snd_bus=key[1], rcv_inst=ri,
                                         rcv_master=im.get(ri), rcv_bus=key[3], src='die GRT wire (no timed path)'))
        if c in rec:
            continue
        ls, lr = Lat.get(si, lat_c.get(c, {}).get(si)), Lat.get(ri, lat_c.get(c, {}).get(ri))
        Ls = (ins.get(si) or [0, 0, 0])[ci[c]]
        Lr = (ins.get(ri) or [0, 0, 0])[ci[c]]
        ds = (ls + Ls - lr - Lr) if ls is not None and lr is not None else None
        if c == 'tt':
            rec[c] = dict(T=833.333, W=e['W'], dskew=ds, C=round(833.333 - U_S - e['W'] - ds, 1) if ds is not None else None)
        else:
            rec[c] = dict(W=e['W'], dskew=ds, H=round(e['W'] + ds - U_H, 1) if ds is not None else None)
    return list(links.values())


def glue_links():
    """S81-PH slab-internal tile hops (assembled-view glue model: composition geometry, analytic wire, intra skew 90)"""
    _, AV = slab_map()
    if AV is None:
        return []
    out = []
    cache = {}

    def lib(t, c):
        if (t, c) not in cache:
            p, fb = AV.lib_for(t, c)
            cache[(t, c)] = (AV.Lib(p), fb) if p.exists() else (None, True)
        return cache[(t, c)]

    def ins(t, c, kind='max'):
        p, _ = AV.lib_for(t, c)
        if not p.exists():
            return 0.0
        m = re.search(kind + r'_clock_tree_path;\s*cell_rise\(scalar\)\s*\{\s*values\("([\d.]+)', p.read_text())
        return float(m.group(1)) if m else 0.0
    for slab, spec in AV.SLABS.items():
        for lt, lp, ct, cp, um, stn, what in spec['glue']:
            r = dict(snd_inst=f'{slab}:{lt}', snd_master=lt, snd_bus=lp, rcv_inst=f'{slab}:{ct}', rcv_master=ct, rcv_bus=cp,
                     slab=slab, src='S81-PH slab glue (assembled-view analytic model)', what=what, length_um=round(um, 1))
            Ll, _ = lib(lt, 'tt')
            Lc, _ = lib(ct, 'tt')
            ratio = 1.0
            try:
                a_, b_ = ins(lt, 'tt'), ins(lt, 'ss')
                ratio = a_ / b_ if a_ and b_ else 1.0
            except Exception:  # noqa: BLE001
                pass
            W = AV.WIRE_SS * ratio * um + AV.RCV
            r['tt'] = dict(T=AV.T_PS, W=round(W, 1), dskew=0.0, C=round(AV.T_PS - AV.UNC_S - AV.SKEW_INTRA - W, 1),
                           S_kit=None if Ll is None else round((AV.arc_of(Ll, lp, 'cq', 'tt') or 0) - ins(lt, 'tt'), 1),
                           R_kit=None if Lc is None else round((AV.arc_of(Lc, cp, 'su', 'tt') or 0) + ins(ct, 'tt'), 1))
            Lf, _ = lib(lt, 'ff')
            Lcf, _ = lib(ct, 'ff')
            r['ff'] = dict(W=round(AV.WIRE_FF_CREDIT * um, 1), dskew=0.0, H=round(AV.WIRE_FF_CREDIT * um - AV.UNC_H, 1),
                           smin_kit=None if Lf is None else round((AV.arc_of(Lf, lp, 'cq', 'ff') or 0) - ins(lt, 'ff', 'min'), 1),
                           h_kit=None if Lcf is None else round((AV.arc_of(Lcf, cp, 'ho', 'ff') or 0) - ins(ct, 'ff', 'min'), 1))
            out.append(r)
    return out


def cmd_links(a):
    OUT.mkdir(parents=True, exist_ok=True)
    for die in a.die.split(','):
        cfg = DIES[die]
        # every dump of this die (links_<c>.tsv = the full scope, links_cand_<c>.tsv = a candidate-only scope run, ...):
        # a link seen in several keeps its worst path
        p = sh(['ssh', cfg['host'], f"cd {cfg['dump']} && for f in links_*tt.tsv links_*ff.tsv; do [ -s $f ] && "
                                    f"{{ echo \"##FILE $f\"; cat $f; }}; done"], timeout=1800)
        P, E, L, files = [], [], {}, []
        for chunk in p.stdout.split('##FILE ')[1:]:
            name, body = chunk.split('\n', 1)
            files.append(name.strip())
            p_, e_, l_ = parse_dump(body)
            P += p_
            E += e_
            L.update(l_)
        if not P and not E:
            raise SystemExit(f'{die}: no link dump on {cfg["host"]}:{cfg["dump"]} (not landed)')
        ctx = context(die, cfg)
        links = build_links(die, cfg, P, E, L, ctx)
        rec = dict(schema='opentallas.rebudget.links.v1', die=die, desc=cfg['desc'], built_at=now(),
                   dump=f"{cfg['host']}:{cfg['dump']}", conventions=dict(U_S=U_S, U_H=U_H, session_unc=cfg['unc']),
                   dump_files=files, counts=dict(paths=len(P), wires=len(E), links=len(links)), links=links)
        (OUT / f'links_{die}.json').write_text(json.dumps(rec, indent=0) + '\n')
        adj = [l_['tt']['capture_adj'] for l_ in links if 'tt' in l_ and 'capture_adj' in l_['tt']]
        print(f"{die}: {len(P)} paths, {len(E)} wire-only buses -> {len(links)} links; capture adj (ps) "
              f"min {min(adj, default=0):.1f} max {max(adj, default=0):.1f}")
    if a.glue:
        g = glue_links()
        (OUT / 'links_s81_glue.json').write_text(json.dumps(dict(schema='opentallas.rebudget.links.v1', die='s81_glue',
            desc='S81-PH slab-internal tile hops (tools/s81/assemble_views.py glue model)', built_at=now(), links=g),
            indent=0) + '\n')
        print(f'glue: {len(g)} slab-internal links')


# ------------------------------------------------------------------------------------------------ derive
def split_setup(s, r, C):
    tot = max(s, 1.0) + max(r, 1.0)
    return C * max(s, 1.0) / tot, C * max(r, 1.0) / tot


def load_links():
    out = []
    for f in sorted(OUT.glob('links_*.json')):
        d = json.loads(f.read_text())
        for l_ in d['links']:
            l_['die'] = d['die']
            out.append(l_)
    return out


def closed_masters(jobs, links_views):
    """masters that count as CLOSED (protected by rule 4): a CLOSED loop job of the block, or a closed / assembled /
    relay / macro timing view on the die that no open candidate replaces"""
    c = {j['spec'].get('block') for j in jobs.values() if j['status'] == 'CLOSED'}
    c |= {m for m, v in links_views.items() if v in ('closed', 'assembled', 'relay', 'view', 'macro')}
    return c


def view_overrides(jobs, views, links):
    """S81-TAIL 2026-10-08: a die master the S81 kit still models with an INTERIM view (no routed timing) gets its REAL
    model from a committed routed die view (physical/s81_die_views/views/<m>/<m>_{tt,ff}.lib, a CLOSED loop job of the
    block) without a kit rebuild: its side of every die link is re-read from that view's ETM arcs, in the die-link
    convention (the link's C / H were computed with no in-arc insertion for the interim side, so the side's need is the
    arc minus the view's own insertion: S = clk->q - ins, R = setup + ins, smin = min clk->q - min ins, h = hold - min ins).
    Marks the master 'closed_view' in views; returns {master: lib dir}.  (dsfd_hstnh_515 g_hco_SW -> bk_collector cSW:
    the colt_lane c_in re-derivation was blocked only by the interim station.)"""
    try:
        from s81 import assemble_views as AV
    except Exception:  # noqa: BLE001
        return {}
    closed_jobs = {j['spec'].get('block') for j in jobs.values() if j['status'] == 'CLOSED'}
    vroot = ROOT / 'physical/s81_die_views/views'
    out = {}
    for m, v in list(views.items()):
        if v not in (None, 'interim', 'none') or m not in closed_jobs:
            continue
        if not all((vroot / m / f'{m}_{c}.lib').exists() for c in ('tt', 'ff')):
            continue
        L = {c: AV.Lib(vroot / m / f'{m}_{c}.lib') for c in ('tt', 'ff')}

        def ins(c, kind):
            t = (vroot / m / f'{m}_{c}.lib').read_text()
            r = re.search(kind + r'_clock_tree_path;\s*cell_rise\(scalar\)\s*\{\s*values\("([\d.]+)', t)
            return float(r.group(1)) if r else 0.0
        it, ifm = ins('tt', 'max'), ins('ff', 'min')
        n = 0
        for l_ in links:
            if l_.get('slab') or (l_.get('tt') or {}).get('fwd'):
                continue
            tt, ff = l_.get('tt') or {}, l_.get('ff') or {}
            if l_.get('snd_master') == m:
                cq, cqf = AV.arc_of(L['tt'], l_['snd_bus'], 'cq', 'tt'), AV.arc_of(L['ff'], l_['snd_bus'], 'cq', 'ff')
                if cq is not None and tt:
                    tt['S_kit_interim'], tt['S_kit'] = tt.get('S_kit'), round(cq - it, 1)
                if cqf is not None and ff:
                    ff['smin_kit_interim'], ff['smin_kit'] = ff.get('smin_kit'), round(cqf - ifm, 1)
            elif l_.get('rcv_master') == m:
                su, ho = AV.arc_of(L['tt'], l_['rcv_bus'], 'su', 'tt'), AV.arc_of(L['ff'], l_['rcv_bus'], 'ho', 'ff')
                if su is not None and tt:
                    tt['R_kit_interim'], tt['R_kit'] = tt.get('R_kit'), round(su + it, 1)
                if ho is not None and ff:
                    ff['h_kit_interim'], ff['h_kit'] = ff.get('h_kit'), round(ho - ifm, 1)
            else:
                continue
            l_['view_override'] = f'{m}: routed die view {vroot.relative_to(ROOT)}/{m} (ins TT {it} / FF min {ifm})'
            n += 1
        views[m] = 'closed_view'
        out[m] = dict(dir=str((vroot / m).relative_to(ROOT)), links=n, ins_tt=it, ins_ff_min=ifm)
        print(f'view override: {m} interim -> routed die view ({n} links re-read)')
    return out


def cmd_derive(a):
    jobs = load_jobs()
    links = load_links()
    tiles, _ = slab_map()
    views = {}
    for die in DIES:
        views.update(die_masters(die))
    needs = {}
    for f in sorted((OUT / 'needs').glob('*.json')):
        d = json.loads(f.read_text())
        if not d.get('error'):
            needs[d['job']] = d
    vov = view_overrides(jobs, views, links)
    closed = closed_masters(jobs, views) | set(vov)
    rb = f'budget_rb{a.rb}'
    od = OUT / rb
    (od / 'sdc').mkdir(parents=True, exist_ok=True)
    procs = MEASURE_SDC.read_text().split('# --- OT_RB_PROCS begin')[1].split('# --- OT_RB_PROCS end ---')[0]
    procs = '# --- OT_RB_PROCS begin' + procs + '# --- OT_RB_PROCS end ---\n'
    per_job = {}
    for jn, nd in needs.items():
        blk, tile = nd['block'], nd.get('tile')
        dm = nd.get('die_master') or blk
        # the open job's ports on die / glue links: (link, side, die-side bus, job ports)
        ports = nd['ports']
        mine = []
        for l_ in links:
            for side in ('snd', 'rcv'):
                m, bus = l_[f'{side}_master'], l_[f'{side}_bus']
                if l_.get('slab'):                       # glue link: tile-level masters
                    if m == blk and bus in ports:
                        mine.append((l_, side, [bus]))
                elif m == dm:
                    if tile:                             # slab die port -> this tile's pins
                        tp = (tiles.get(tile, (None, {}))[1]).get(bus)
                        if tp:
                            mine.append((l_, side, [p for p in tp if p in ports]))
                    elif bus in ports:
                        mine.append((l_, side, [bus]))
        port_rec = defaultdict(lambda: dict(links=[], S_b=None, R_b=None, q=None, I=None, keep=None, fwd=None))
        fwdm = nd.get('fwd') or {}
        link_rows = []
        for l_, side, myports in mine:
            if not myports:
                continue
            other = 'rcv' if side == 'snd' else 'snd'
            om = l_[f'{other}_master']
            o_closed = om in closed and om != blk
            tt, ff = l_.get('tt') or {}, l_.get('ff') or {}
            for p in myports:
                need = dict(ports[p])
                row = dict(port=p, side=side, die=l_['die'], link=f"{l_['snd_inst']}.{l_['snd_bus']} -> {l_['rcv_inst']}.{l_['rcv_bus']}",
                           other_master=om, other_closed=o_closed, src=l_['src'])
                if tt.get('fwd') or ff.get('fwd'):
                    # forwarded-clock hop: the block's need in the forwarded frame (data pin - forwarded-clock pin)
                    fb = (l_.get('fwd') or {}).get('fo_bus')
                    fa = fwdm.get(fb) if side == 'snd' and not tile else None
                    if not fa or fa.get('A') is None or need.get('S') is None:
                        row.update(setup='kept old: forwarded-clock link ' + ('receiver side (not modelled)' if side == 'rcv'
                                   else 'of a slab tile (not mapped)' if tile else f'forwarded clock {fb} not measured'),
                                   hold='kept old (forwarded)')
                        port_rec[p]['keep'] = row['setup']
                        port_rec[p]['links'].append(row)
                        link_rows.append(row)
                        continue
                    need['S'] = round(need['S'] - fa['A'], 1)
                    need['smin'] = round(need['smin'] - fa['A_min'], 1) if need.get('smin') is not None and fa.get('A_min') is not None else None
                    row.update(fwd=dict(fo=fb, A=fa['A'], A_min=fa.get('A_min'), T_cap=tt.get('T_cap'), cap_tr=tt.get('cap_tr'),
                                        T_hold=ff.get('T_hold')))
                    if port_rec[p]['fwd'] and port_rec[p]['fwd']['fo'] != fb:
                        row.update(setup='kept old: data bus on two forwarded clocks', hold='kept old (forwarded)')
                        port_rec[p]['keep'] = row['setup']
                    else:
                        port_rec[p]['fwd'] = row['fwd']
                if 'kept old' in row.get('setup', ''):
                    port_rec[p]['links'].append(row)
                    link_rows.append(row)
                    continue
                # ---- setup at TT
                mine_need = need.get('S' if side == 'snd' else 'R')
                o_need = tt.get('R_kit' if side == 'snd' else 'S_kit')
                C = tt.get('C')
                if C is None or mine_need is None or o_need is None or (views.get(om) in (None, 'interim', 'none', 'partitioned') and not l_.get('slab')):
                    row.update(setup='kept old: ' + ('no capacity (no timed path / latency)' if C is None else
                                                      'no real model of the other side' if o_need is None or views.get(om) in (None, 'interim', 'none', 'partitioned')
                                                      else 'port not measured'))
                    port_rec[p]['keep'] = row['setup']
                else:
                    s, r = (mine_need, o_need) if side == 'snd' else (o_need, mine_need)
                    sb, rb_ = split_setup(s, r, C)
                    short = s + r - C
                    row.update(C=C, need=mine_need, other_need=o_need, short=round(max(0.0, short), 1))
                    if short > 0 and o_closed:
                        row.update(setup=f'kept old: link short by {short:.1f} ps and the {other} side ({om}) is CLOSED (rule 4)')
                        port_rec[p]['keep'] = row['setup']
                    else:
                        mb = sb if side == 'snd' else rb_
                        row.update(setup='re-derived', budget=round(mb, 1), slack_pred=round(mb - mine_need, 1),
                                   other_budget=round(rb_ if side == 'snd' else sb, 1))
                        k = 'S_b' if side == 'snd' else 'R_b'
                        port_rec[p][k] = mb if port_rec[p][k] is None else min(port_rec[p][k], mb)
                # ---- hold at FF
                mine_h = need.get('smin' if side == 'snd' else 'h')
                o_h = ff.get('h_kit' if side == 'snd' else 'smin_kit')
                H = ff.get('H')
                if H is not None and mine_h is not None and o_h is not None and 'kept old' not in row.get('setup', 'kept old'):
                    smin, h = (mine_h, o_h) if side == 'snd' else (o_h, mine_h)
                    M = smin + H - h
                    if M < 0 and o_closed:
                        row.update(hold=f'kept old: hold margin {M:.1f} ps and the {other} side is CLOSED (rule 4)')
                        port_rec[p]['keep'] = row['hold']
                    else:
                        q = smin - M / 2.0
                        I = h + M / 2.0
                        row.update(hold='re-derived', H=H, M=round(M, 1), q_s=round(q, 1), I_min=round(I, 1))
                        if side == 'snd':
                            port_rec[p]['q'] = q if port_rec[p]['q'] is None else max(port_rec[p]['q'], q)
                        else:
                            port_rec[p]['I'] = I if port_rec[p]['I'] is None else min(port_rec[p]['I'], I)
                elif 'hold' not in row:
                    row.update(hold='kept old (no hold model)')
                    if 'kept old' not in row.get('setup', ''):
                        port_rec[p]['keep'] = row['hold']
                port_rec[p]['links'].append(row)
                link_rows.append(row)
        rebudgeted = {p: v for p, v in port_rec.items() if not v['keep'] and ports[p].get('clock') and
                      (v['R_b'] is not None and v['I'] is not None if ports[p]['dir'] == 'in' else v['S_b'] is not None and v['q'] is not None)}
        T = {k: x.get('T') for k, x in (nd['ref'].get('tt') or {}).items()}
        sdc = None
        if rebudgeted:
            lines = [f'# {rb} for {jn} (block {blk}{", tile of " + dm if tile else ""}), tools/budgets/rebudget.py derive {now()}',
                     '# Re-derived IO budget from the REAL die links (die GRT parasitics / slab glue model) and REAL block needs',
                     '# (routed DB, zero-budget re-STA).  Read LAST (after io_ref_routed.sdc in a sign-off session).',
                     f'# Ports re-budgeted: {len(rebudgeted)} of {len(port_rec)} linked ({len(ports)} measured).  U_S {U_S:g} / U_H {U_H:g} are in the budget.',
                     procs,
                     'set ot_rb_refs [ot_rb_reference]',
                     'if {[llength $ot_rb_refs]} {',
                     '  ot_rb_vclocks $ot_rb_refs',
                     '  set u [sta::time_sta_ui 1e-12]',
                     '  set ot_rb_real [lmap r $ot_rb_refs {lindex $r 0}]']
            for p, v in sorted(rebudgeted.items()):
                d, ck = ports[p]['dir'], ports[p].get('clock')
                tgt = f'[get_ports -quiet {{{p} {p}[*]}}]'
                lines.append(f'  # {p} ({d}, {ck}): ' + '; '.join(f"{x['link']} C {x.get('C')} need {x.get('need')} -> "
                                                                   f"{x.get('budget')}" for x in v['links'])[:900])
                lines.append(f'  if {{[lsearch -exact $ot_rb_real {ck}] >= 0}} {{')
                lines.append(f'    set T [expr {{[get_property [get_clocks {ck}] period] / $u}}]')
                lines.append(f'    foreach ot_p {tgt} {{ ot_rb_unset $ot_p {d} }}')
                vc = f'ot_rb_v_{ck}'
                fw = v.get('fwd')
                if fw and d == 'out' and fw.get('T_cap') is not None and fw.get('T_hold') is not None:
                    # source-synchronous output: budget against the clock the block forwards on port {fo}, at the
                    # station's capture edge (falling for dsfd_stn*: T_cap = T/2, hold edge = -T/2)
                    fo = fw['fo']
                    gc = f'ot_rb_fwo_{fo}'
                    fall = ' -clock_fall' if fw.get('cap_tr') == 'fall' else ''
                    # on the pin that drives the port (a generated clock ON an output port leaves a phantom port slack,
                    # hq_SW fo -575 with no path); the port itself when no such pin
                    lines.append(f'    if {{![llength [get_clocks -quiet {gc}]]}} {{')
                    lines.append(f'      set ot_fw_d [get_pins -quiet -of_objects [get_nets -quiet {{{fo} {fo}[*]}}] -filter "direction==output"]')
                    lines.append(f'      if {{![llength $ot_fw_d]}} {{ set ot_fw_d [get_ports {{{fo} {fo}[*]}}] }}')
                    lines.append(f'      create_generated_clock -name {gc} -source [lindex [get_property [get_clocks {ck}] sources] 0] '
                                 f'-divide_by 1 $ot_fw_d; set_propagated_clock [get_clocks {gc}]')
                    lines.append('    }')
                    lines.append(f"    set_output_delay -max [expr {{{fw['T_cap'] - v['S_b']:.1f} * $u}}] -clock {gc}{fall} {tgt}")
                    lines.append(f"    set_output_delay -min [expr {{{fw['T_hold'] - v['q']:.1f} * $u}}] -clock {gc}{fall} {tgt}")
                    lines.append(f'  }} else {{ puts "OT_REBUDGET skip {p}: no clock {ck}" }}')
                    continue
                if d == 'in':
                    lines.append(f"    set_input_delay -max [expr {{($T - {v['R_b']:.1f}) * $u}}] -clock {vc} {tgt}")
                    lines.append(f"    set_input_delay -min [expr {{{v['I']:.1f} * $u}}] -clock {vc} {tgt}")
                else:
                    lines.append(f"    set_output_delay -max [expr {{($T - {v['S_b']:.1f}) * $u}}] -clock {vc} {tgt}")
                    lines.append(f"    set_output_delay -min [expr {{{-v['q']:.1f} * $u}}] -clock {vc} {tgt}")
                lines.append(f'  }} else {{ puts "OT_REBUDGET skip {p}: no clock {ck}" }}')
            lines += [f'  puts "OT_REBUDGET {rb} {jn} ports {len(rebudgeted)}"', '}']
            sdc = od / 'sdc' / f'{jn}.sdc'
            sdc.write_text('\n'.join(lines) + '\n')
        pred = [x.get('slack_pred') for x in link_rows if x.get('slack_pred') is not None]
        per_job[jn] = dict(block=blk, die_master=dm, tile=tile, internal_ok=nd.get('internal_ok'), r2r=nd.get('r2r'),
                           T=T, ports_measured=len(ports), ports_linked=len(port_rec), ports_rebudgeted=len(rebudgeted),
                           worst_pred_setup=min(pred) if pred else None, sdc=str(sdc.relative_to(ROOT)) if sdc else None,
                           links=link_rows)
    n_links = len({(r['link']) for v in per_job.values() for r in v['links'] if r.get('setup') == 're-derived'})
    summ = dict(schema='opentallas.rebudget.summary.v1', rb=rb, derived_at=now(), conventions=dict(U_S=U_S, U_H=U_H,
                rule='split proportional to need (setup), equal margin share (hold); a master port = min over its links; '
                     'a short link touching a CLOSED block keeps its old budget (owner rule 4)'),
                link_files=[f.name for f in sorted(OUT.glob('links_*.json'))], links_total=len(links),
                links_rederived=n_links, view_overrides=vov, jobs=per_job)
    (od / 'summary.json').write_text(json.dumps(summ, indent=1) + '\n')
    cur = OUT / 'current.json'
    c = json.loads(cur.read_text()) if cur.exists() else dict(blocks={})
    for jn, v in per_job.items():
        if v['sdc'] and v['internal_ok']:
            b = c['blocks'].get(v['block'])
            if not b or b.get('rb') != rb or (v['worst_pred_setup'] or -1e9) > (b.get('worst_pred_setup') or -1e9):
                c['blocks'][v['block']] = dict(rb=rb, job=jn, sdc=v['sdc'], worst_pred_setup=v['worst_pred_setup'])
    c.update(rb=rb, updated=now())
    cur.write_text(json.dumps(c, indent=1) + '\n')
    if not a.no_publish:
        # the loop's view (closure_loop.install_rebudget): absolute copies under STATE, so the daemon's checkout need
        # not carry this pass
        import shutil
        sd = STATE / 'rebudget' / rb
        sd.mkdir(parents=True, exist_ok=True)
        pub = dict(rb=rb, updated=now(), source=str(OUT.relative_to(ROOT)), blocks={})
        for blk, v in c['blocks'].items():
            dst = sd / Path(v['sdc']).name
            if (ROOT / v['sdc']).exists():
                shutil.copy(ROOT / v['sdc'], dst)
                pub['blocks'][blk] = dict(v, sdc=str(dst))
        (STATE / 'rebudget' / 'current.json').write_text(json.dumps(pub, indent=1) + '\n')
    print(f'{rb}: {len(links)} links on file, {n_links} re-derived for {len(per_job)} measured jobs; '
          f'{sum(1 for v in per_job.values() if v["sdc"])} SDCs -> {od.relative_to(ROOT)}')
    for jn, v in sorted(per_job.items()):
        print(f"  {jn:62s} internal_ok={v['internal_ok']} ports {v['ports_rebudgeted']}/{v['ports_linked']}/{v['ports_measured']} "
              f"worst pred {v['worst_pred_setup']}")


# ------------------------------------------------------------------------------------------------ rejudge
def cmd_rejudge(a):
    rb = f'budget_rb{a.rb}'
    summ = json.loads((OUT / rb / 'summary.json').read_text())
    todo = [(jn, v) for jn, v in summ['jobs'].items() if v['sdc'] and v['internal_ok']]
    print(f'{rb}: re-judging {len(todo)} jobs through the closure loop ({"APPLY" if a.apply else "dry: no job change"})')
    res = {}

    import shutil
    sd = STATE / 'rebudget' / rb
    sd.mkdir(parents=True, exist_ok=True)

    def one(x):
        jn, v = x
        # the job keeps a path to its budget SDC (later re-STAs re-read it): a stable copy under the loop state, not
        # this checkout (a worktree is removed after the merge)
        dst = sd / Path(v['sdc']).name
        shutil.copy(ROOT / v['sdc'], dst)
        cmd = [sys.executable, str(LOOP), 'rebudget-rejudge', jn, '--rb', rb, '--sdc', str(dst)]
        if not a.apply:
            cmd.append('--dry')
        p = sh(cmd, timeout=14400)
        return jn, (p.stdout.strip().splitlines() or [''])[-1] + (p.stderr[-300:] if p.returncode else '')
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        for jn, line in ex.map(one, todo):
            res[jn] = line
            print(line, flush=True)
    (OUT / rb / ('rejudge.json' if a.apply else 'rejudge_dry.json')).write_text(json.dumps(res, indent=1) + '\n')


def cmd_drive(a):
    """loop hook (BRIEF.md drive step): when a die dump or new candidates landed, measure, derive rb<N+1>, rejudge"""
    cur = OUT / 'current.json'
    n = int(re.sub(r'\D', '', json.loads(cur.read_text()).get('rb', 'budget_rb0'))) if cur.exists() else 0
    # a die dump that landed after its links file (HBM r25 grt3, Qwen r21b when added to DIES, an S81 refresh)
    for die, cfg in DIES.items():
        lf = OUT / f'links_{die}.json'
        p = ssh(cfg['host'], f"stat -c %Y {cfg['dump']}/links_*tt.tsv 2>/dev/null | sort -n | tail -1", timeout=120)
        try:
            t = int(p.stdout.strip())
        except ValueError:
            continue
        if not lf.exists() or t > lf.stat().st_mtime:
            print(f'{die}: new die dump -> links')
            cmd_links(argparse.Namespace(die=die, glue=die == 's81_r3'))
    a.jobs, a.all, a.force, a.reparse = None, False, False, False
    cmd_measure(a)
    a.rb, a.no_publish = n + 1, False
    cmd_derive(a)
    cmd_rejudge(a)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('candidates'); c.add_argument('--die')
    ms = sub.add_parser('masters'); ms.add_argument('--die')
    m = sub.add_parser('measure'); m.add_argument('--jobs'); m.add_argument('--die'); m.add_argument('--all', action='store_true')
    m.add_argument('--force', action='store_true'); m.add_argument('--reparse', action='store_true'); m.add_argument('--parallel', type=int, default=8)
    l_ = sub.add_parser('links'); l_.add_argument('--die', required=True); l_.add_argument('--glue', action='store_true')
    d = sub.add_parser('derive'); d.add_argument('--rb', type=int, required=True); d.add_argument('--no-publish', action='store_true')
    r = sub.add_parser('rejudge'); r.add_argument('--rb', type=int, required=True); r.add_argument('--apply', action='store_true')
    r.add_argument('--parallel', type=int, default=6)
    dr = sub.add_parser('drive'); dr.add_argument('--apply', action='store_true'); dr.add_argument('--die')
    dr.add_argument('--parallel', type=int, default=6)
    a = ap.parse_args()
    dict(candidates=cmd_candidates, masters=cmd_masters, measure=cmd_measure, links=cmd_links, derive=cmd_derive, rejudge=cmd_rejudge,
         drive=cmd_drive)[a.cmd](a)


if __name__ == '__main__':
    main()
