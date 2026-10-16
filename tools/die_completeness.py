#!/usr/bin/env python3
"""Daily measured completeness tracker for the four dies (owner concern 2026-10-15 21:10 PT: ETAs keep swinging because
die integration keeps uncovering placeholders, missing elements and elements that fail real-view checks).

ETAs must come from the remaining inventory, so this tool reads MEASURED records only and counts, per die:
  1. instances and distinct masters of the current die netlist (newest strict port-bind record of the die);
  2. instances that are not real RTL (stub / non-allowed model / unbound / port-mismatch masters) and instances that
     the latest die-level physical run does NOT place on a real closed view (window / frame / generated abstract);
  3. open bind items: unconnected inputs, width mismatches, undriven bits, exposed / unresolved ports;
  4. the view state of every distinct master: closed + native PASS | closed, native FAIL | closed, native unmeasured |
     routed-failed | in flight | parent (leaves closed, parent not hardened) | RTL only | missing RTL | hard macro;
  5. masters the die contract requires that are absent from the netlist;
  6. die-level runs: latest GEN, GRT overflow, TT/FF STA and whether the views were real.
Then 'remaining work units' = masters not closed+native PASS + placeholders to replace + inputs to bind.

Sources (nothing heavy is launched; remote reads are `ssh cat`/`ls`):
  * die netlist / strict bind: die_port_bind.py v2 records (S81, compute), die_port_bind_kv v1 (KV), HBM v15 source
    contract (no full HBM die netlist exists); newest record per die from the candidate globs in DIES below;
  * view state: fleet-viz element registry (127.0.0.1:8765/api/elements: loop category, jobs, contract roles), and the
    native pin audit (tools/hier_contract/native_pin_audit.audit_one: TT launch O-R <= 220 ps, capture S+R <= 190 ps)
    re-run on each closed master's committed Liberty view at origin/main;
  * contract: results/fleet_viz/die_contracts.json via the registry 'dies' roles (master rows of each design);
  * die runs: chain STATUS.log / run logs on the fleet and committed die-run receipts.

    python3 tools/die_completeness.py [--out results/arch/die_completeness_1015] [--no-native] [--no-remote]
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import fnmatch
import gzip
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'hier_contract'))
REGISTRY_URL = 'http://127.0.0.1:8765/api/elements'
SCHEMA = 'opentallas.die_completeness.v1'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15']

# ------------------------------------------------------------------------------------------------ per-die sources
# bind: candidate records, newest mtime wins (exclude = stale-recipe diagnostics); runs: STATUS logs / run logs parsed
# for GEN / GRT / STA lines (newest first), commit: committed receipts read from origin/main.
DIES = {
    'qwen_compute': dict(
        label='Qwen compute die', lead='Q-COMPUTE-DIE', design='qwen_compute',
        bind=[('ot-epyc4', '/srv/opentallas-scratch/claude/qwen-split-compute/*/chain/port_bind/port_bind.json'),
              ('repo', 'results/arch/qwen_split_compute_1014/c13_smoke/port_bind.json')],
        view_bind='../bind.json',              # opentallas.qwen-tp8.bind-real.v1 next to the chain's port_bind dir
        status='../STATUS.log',
        runs=[('ot-epyc4', '/srv/opentallas-scratch/claude/qwen-split-compute/*/chain/STATUS.log'),
              ('repo', 'results/arch/qwen_split_compute_1014/c16s_terminal/STATUS.log')],
    ),
    'qwen_kvsys': dict(
        label='Qwen KV/system die', lead='Q-KVSYS-DIE', design='qwen_kvsys',
        bind=[('ot-epyc1tb', '/srv/opentallas-scratch/claude/qwen-kvsys/*/port_bind_launch.json'),
              ('ot-epyc1tb', '/srv/opentallas-scratch/claude/qwen-kvsys/*/port_bind.json'),
              ('repo', 'results/arch/qwen_split_1014/kvsys_v1_4_1/port_bind.json')],
        view_classify=('ot-epyc1tb', '/srv/opentallas-scratch/claude/qwen-kvsys/*/classify_*.json'),
        status='STATUS.log',
        runs=[('ot-epyc1tb', '/srv/opentallas-scratch/claude/qwen-kvsys/*/STATUS.log')],
    ),
    's81': dict(
        label='S81 (DeepSeek ROM) die', lead='S-DIE', design='s81',
        bind=[('ot-epyc4', '/srv/opentallas-scratch/claude/s81-die-r10/bind*/port_bind.json'),
              ('ot-epyc4', '/srv/opentallas-scratch/claude/s81-die-iter/*/port_bind.json'),
              ('repo', 'results/arch/s81_canonical_bind_1015/sbind_static_1015/bind5/port_bind.json')],
        # c19b = GEN19rb diagnostic chain (src d8072c747, 07:00) older than bind21 (src dafe35bc0, 13:19)
        exclude=[r'/s81-die-iter/c19b?/'],
        runs=[('ot-epyc4', '/srv/opentallas-scratch/claude/s81-die-iter/*/STATUS.log'),
              ('ot-epyc4', '/srv/opentallas-scratch/claude/s81-die-iter/*/DIAG_STATUS.log')],
        manifest='a_real/manifest.json',      # next to a chain STATUS.log: instances of the GEN'd real case
        grt_logs=('ot-epyc4', '/srv/opentallas-scratch/claude/s81-die-iter/*/grt*/grt.log'),
    ),
    'hbm': dict(
        label='HBM accelerator die', lead='H-DIE', design='hbm',
        contract='results/arch/hbm_die_v15/source_contract/contract.json',
        readiness='results/arch/hbm_die_v15/die_chain_readiness.json',
        exposed='results/arch/hbm_die_v15/views_v5/exposed_inputs_by_owner_1705.json',
        exposed_engine='results/arch/hbm_die_v15/views_v5/exposed_inputs_engine_1815.json',
        inventory='results/arch/hbm_die_v15/views_v5/inventory.json',
        region_run='results/arch/hbm_die_v15/views_v5/pcrow_c_die_clock/run_summary.txt',
        full_grt='results/arch/hbm_die_v15/grt27_collected/receipt.json',
        runs=[('ot-epyc1tb', '/srv/opentallas-scratch/claude/hdie-1705/diecase_*/out/run.log')],
        case_manifest='../manifest.json',
    ),
}
MACRO_FALLBACK = r'^(ot_hbm3e_phy|ot_pdie_|ot_rom_|ot_v41_rom_elem|ot_sram_|ot_rf_|ot_qfd_serdes|ot_qkvd_ucie|ot_qfd_ucie)'

CLASSES = ['closed + native PASS', 'closed, native FAIL', 'closed, native unmeasured', 'routed-failed', 'in flight',
           'parent: leaves closed, not hardened', 'RTL only (no route yet)', 'missing RTL', 'superseded but in netlist',
           'hard macro / PHY (allowed model)']


# ------------------------------------------------------------------------------------------------ IO helpers
def sh(cmd, timeout=90, binary=False):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    return r.stdout if binary else r.stdout.decode(errors='replace')


def repo_read(path, ref='origin/main', binary=False):
    r = subprocess.run(['git', '-C', str(ROOT), 'show', f'{ref}:{path}'], capture_output=True, timeout=120)
    if r.returncode:
        return None
    return r.stdout if binary else r.stdout.decode(errors='replace')


def repo_commit(path, ref='origin/main'):
    return sh(['git', '-C', str(ROOT), 'log', '-1', '--format=%h %cI', ref, '--', path]).strip()


def remote_glob(host, pattern, remote=True):
    """[(path, mtime_epoch)] newest first"""
    if host == 'repo':
        if repo_read(pattern) is None:
            return []
        c = repo_commit(pattern).split()
        t = dt.datetime.fromisoformat(c[1]).timestamp() if len(c) > 1 else 0
        return [(pattern, t)]
    if not remote:
        return []
    out = sh(SSH + [host, f'stat -c "%Y %n" {pattern} 2>/dev/null'], timeout=60)
    res = []
    for ln in out.splitlines():
        p = ln.split(' ', 1)
        if len(p) == 2 and p[0].isdigit():
            res.append((p[1], int(p[0])))
    return sorted(res, key=lambda x: -x[1])


def read(host, path, binary=False):
    if host == 'repo':
        return repo_read(path, binary=binary)
    b = sh(SSH + [host, f'cat {path}'], timeout=180, binary=True)
    if path.endswith('.gz') and b:
        b = gzip.decompress(b)
    return b if binary else (b.decode(errors='replace') if b else None)


def rel(path, sub):
    return str(Path(path).parent / sub) if sub.startswith('..') or '/' not in sub else str(Path(path).parent / sub)


def norm_rel(path, sub):
    p = Path(path).parent
    for part in sub.split('/'):
        p = p.parent if part == '..' else p / part
    return str(p)


def when(t):
    return dt.datetime.fromtimestamp(t).astimezone().strftime('%Y-%m-%d %H:%M %Z') if t else '-'


# ------------------------------------------------------------------------------------------------ bind records
def newest(cands, exclude=(), remote=True):
    allc = []
    for host, pat in cands:
        for p, t in remote_glob(host, pat, remote):
            if any(re.search(x, p) for x in exclude):
                continue
            allc.append((t, host, p))
    allc.sort(key=lambda x: -x[0])
    return allc


def load_bind(cands, exclude=(), remote=True):
    """-> normalized dict(masters={m: dict(instances, kind, open_inputs[], width, port_fault, rtl)}, summary, src)"""
    for t, host, p in newest(cands, exclude, remote):
        txt = read(host, p)
        if not txt:
            continue
        try:
            d = json.loads(txt)
        except ValueError:
            continue
        src = dict(host=host, path=p, mtime=when(t), schema=d.get('schema'), die_v=d.get('die_v'),
                   die_sha256=(d.get('die_sha256') or '')[:16] or None)
        masters = {}
        if d.get('schema') == 'opentallas.die_port_bind.v2':
            for m, r in d['masters'].items():
                masters[m] = dict(instances=r.get('instances', 0), kind=r.get('kind') or ('unbound' if not r.get('rtl') else '?'),
                                  rtl=r.get('rtl'), verdict=r.get('verdict'),
                                  open_inputs=list(r.get('input_unconnected') or []),
                                  width=sorted((r.get('width_mismatch') or {}).keys()),
                                  port_fault=list(r.get('die_port_not_in_rtl') or []), tied=list(r.get('input_tied') or []))
            s = d['summary']
            summ = dict(verdict=d.get('verdict'), masters=s['masters'], instances=s['instances'],
                        unbound_masters=s['unbound_masters'], stub_masters=s['stub_masters'],
                        port_not_in_rtl=s['port_not_in_rtl'], width_mismatch=s['width_mismatch'],
                        input_unconnected=s['input_unconnected'], input_tied=s['input_tied'],
                        undriven_net_bits=s['undriven_net_bits'], multi_driven_net_bits=s['multi_driven_net_bits'],
                        strict=True)
        elif d.get('schema') == 'opentallas.qwen_kv_die_port_bind.v1':
            for m, r in d['masters'].items():
                cls = r.get('cls')
                masters[m] = dict(instances=r.get('n_instances', 0),
                                  kind={'REAL': 'real', 'HARD_PHY': 'model', 'MISMATCH': 'mismatch'}.get(cls, str(cls).lower()),
                                  rtl=r.get('file'), verdict='PASS' if cls in ('REAL', 'HARD_PHY') and not r.get('rtl_inputs_unconnected') else 'FAIL',
                                  open_inputs=list(r.get('rtl_inputs_unconnected') or []),
                                  width=list(r.get('width_or_missing') or []), port_fault=list(r.get('die_ports_not_bound') or []),
                                  tied=[])
            ms = list(masters.values())
            summ = dict(verdict='FAIL' if any(x['verdict'] == 'FAIL' for x in ms) else 'PASS', masters=len(ms),
                        instances=sum(x['instances'] for x in ms), unbound_masters=0, stub_masters=0,
                        port_not_in_rtl=sum(len(x['port_fault']) for x in ms),
                        width_mismatch=sum(len(x['width']) for x in ms),
                        input_unconnected=sum(len(x['open_inputs']) for x in ms), input_tied=None,
                        undriven_net_bits=None, multi_driven_net_bits=None, strict=False,
                        classes=d.get('summary'))
        else:
            continue
        return dict(src=src, masters=masters, summary=summ)
    return None


# ------------------------------------------------------------------------------------------------ die runs
RUN_RE = [
    ('gen', re.compile(r'(GEN_DONE.*|GEN_FAIL.*|real case: OT_LEGAL instances=\d+.*|GEN rc=\d+.*)')),
    ('place', re.compile(r'(PLACE[_ ]?(rc=\d+|FAIL|OK).*|DIAG_PLACE_OK.*)')),
    ('pdn', re.compile(r'(PDN.*)')),
    ('port_bind', re.compile(r'(PORT_BIND.*|DIE_PORT_BIND.*|NATIVE PORT BIND.*)')),
    ('grt', re.compile(r'((?:full-die )?GRT.*overflow[= ]\s*\d+.*|GRT.*(?:FAIL|exit=\d+).*)')),
    ('sta_tt', re.compile(r'(STA tt:.*)')),
    ('sta_ff', re.compile(r'(STA ff:.*)')),
    ('sta_ss', re.compile(r'(STA ss:.*)')),
    ('views', re.compile(r'(real views: .*|OT_VIEW_BINDING .*)')),
    ('src', re.compile(r'start src (\w+)|src[= ](\w{7,40})')),
]


def parse_status(text):
    ev = {}
    for ln in (text or '').splitlines():
        for k, rx in RUN_RE:
            m = rx.search(ln)
            if m:
                ev[k] = (ln[:19] + ' ' + (m.group(1) or m.group(0)) if k != 'src' else (m.group(1) or m.group(2)))[:260]
    def num(k, pat):
        m = re.search(pat, ev.get(k, ''))
        return float(m.group(1)) if m else None
    res = dict(events=ev,
               grt_overflow=num('grt', r'overflow[= ]\s*(\d+)'),
               tt_wns_ps=num('sta_tt', r'wns max (-?[\d.]+)'),
               ff_setup_wns_ps=num('sta_ff', r'wns max (-?[\d.]+)'),
               ff_hold_wns_ps=num('sta_ff', r'worst slack min (-?[\d.]+)'),
               gen_instances=num('gen', r'instances=(\d+)'))
    pdn = ev.get('pdn', '')
    res['pdn_skipped'] = 'SKIP' in pdn.upper() or 'skip' in pdn
    return res


def die_runs(cfg, remote=True):
    runs = []
    for t, host, p in newest(cfg.get('runs', []), cfg.get('run_exclude', ()), remote)[:8]:
        txt = read(host, p)
        if not txt:
            continue
        if p.endswith('run.log'):                                    # ORFS-style die case run (HBM die_case.py)
            r = dict(events={}, grt_overflow=None, tt_wns_ps=None, ff_setup_wns_ps=None, ff_hold_wns_ps=None)
            tot = re.findall(r'^Total\s.*?(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*$', txt, re.M)
            r['grt_overflow'] = float(tot[-1][2]) if tot else None
            r['events'] = {k: ln[:200] for ln in txt.splitlines() for k in ('OT_GRT', 'OT_PATHS', 'tns', 'OT_DONE')
                           if ln.startswith(k)}
            for corner, key in (('tt', 'tt_wns_ps'), ('ff', 'ff_hold_wns_ps')):
                w = read(host, norm_rel(p, f'worst_{corner}_{"max" if corner == "tt" else "min"}.rpt')) or ''
                sl = [float(x) for x in re.findall(r'(-?\d+\.\d+)\s+slack \(', w)]
                if sl:
                    r[key] = min(sl)
            man = read(host, norm_rel(p, '../manifest.json'))
            if man:
                try:
                    mj = json.loads(man)
                    r['case'] = dict(region=mj.get('region'), instances=mj.get('instances'), views=mj.get('views'))
                except ValueError:
                    pass
        else:
            r = parse_status(txt)
            if 'manifest' in DIES_CUR.get('cfg', {}):
                man = read(host, norm_rel(p, DIES_CUR['cfg']['manifest']))
                if man:
                    try:
                        r['gen_instances'] = json.loads(man).get('instances') or r.get('gen_instances')
                    except ValueError:
                        pass
        r.update(host=host, path=p, mtime=when(t))
        src = (r.get('events') or {}).get('src')
        if src:
            c = sh(['git', '-C', str(ROOT), 'log', '-1', '--format=%h %cI', src]).split()
            r['src'] = dict(commit=c[0] if c else src, time=c[1] if len(c) > 1 else None)
        runs.append(r)
    return runs


DIES_CUR = {}


# ------------------------------------------------------------------------------------------------ registry + native
def registry():
    d = json.load(urllib.request.urlopen(REGISTRY_URL, timeout=120))
    return d


class Native:
    """native pin audit (TT launch <= 220 ps, capture <= 190 ps) of a master's committed closed view at origin/main"""

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.cache = {}
        self.libs = collections.defaultdict(list)
        if enabled:
            out = sh(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'origin/main', 'physical/'], timeout=300)
            for p in out.splitlines():
                m = re.search(r'/([^/]+)_tt\.lib(\.gz)?$', p)
                if m and 'asap7_memory_macros' not in p:
                    self.libs[m.group(1)].append(p)
            try:
                import native_pin_audit as NPA  # noqa: E402
                self.NPA = NPA
            except Exception as e:  # noqa: BLE001
                print('native audit unavailable:', e, file=sys.stderr)
                self.enabled = False

    def view_for(self, cell, kit):
        cands = self.libs.get(cell, [])
        if kit:
            k = [p for p in cands if f'/{kit}/' in p]
            if k:
                return k[0], 'registry kit'
        if len(cands) >= 1:
            return sorted(cands)[-1], ('only view' if len(cands) == 1 else f'1 of {len(cands)} views by name')
        return None, None

    def audit(self, cell, kit):
        if not self.enabled:
            return None
        key = (cell, kit)
        if key in self.cache:
            return self.cache[key]
        lib, how = self.view_for(cell, kit)
        if not lib:
            self.cache[key] = dict(verdict='NO_VIEW')
            return self.cache[key]
        vdir = str(Path(lib).parent)
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / vdir
            dst.mkdir(parents=True)
            b = repo_read(lib, binary=True)
            if b is None:
                self.cache[key] = dict(verdict='NO_VIEW')
                return self.cache[key]
            (dst / Path(lib).name).write_bytes(b)
            ij = repo_read(vdir + '/insertion.json', binary=True)
            if ij:
                (dst / 'insertion.json').write_bytes(ij)
            try:
                r = self.NPA.audit_one((td, cell, vdir))
            except Exception as e:  # noqa: BLE001
                r = dict(error=f'{type(e).__name__}: {e}')
        if r.get('error'):
            res = dict(verdict='ERROR', view=vdir, why=r['error'][:160], how=how)
        else:
            res = dict(verdict='PASS' if r['pass'] else 'FAIL', view=vdir, how=how, launch_ps=r.get('launch_ps'),
                       capture_ps=r.get('capture_ps'), spread_ps=r.get('spread_ps'), insertion=r.get('insertion'),
                       why=r.get('fail_why') or '')
        self.cache[key] = res
        return res


def kit_of(row):
    m = re.search(r'kit (\S+)', (row or {}).get('flow_detail') or '')
    return m.group(1) if m else None


def classify(m, row, bindrec, macro_rx, native):
    """-> (class, detail)"""
    if re.search(macro_rx, m) or (bindrec and bindrec.get('kind') == 'model'):
        return 'hard macro / PHY (allowed model)', ''
    if bindrec and (bindrec.get('kind') == 'unbound' or not bindrec.get('rtl')) and bindrec.get('kind') != 'real':
        if bindrec.get('kind') in ('unbound', None, '?'):
            return 'missing RTL', ''
    cat = (row or {}).get('category') or ''
    if cat.startswith('closed'):
        a = native.audit(m, kit_of(row)) if native else None
        if not a or a['verdict'] in ('NO_VIEW', 'ERROR'):
            return 'closed, native unmeasured', (a or {}).get('verdict', 'native audit off')
        if a['verdict'] == 'PASS':
            return 'closed + native PASS', f"launch {a['launch_ps']} / capture {a['capture_ps']}"
        return 'closed, native FAIL', a['why'][:120]
    if cat == 'superseded':
        return 'superseded but in netlist', (row.get('superseded') or {}).get('by', '') if isinstance(row.get('superseded'), dict) else ''
    if cat == 'first trial in flight':
        return 'in flight', f"{row.get('live')} live job(s)"
    if cat in ('failed, re-running', 'flow failure (no live job)', 'needs redesign (no live job)') or \
            (row and row.get('failed') and not row.get('closed_jobs')):
        return 'routed-failed', f"{cat}; {row.get('failed')} failed job(s)"
    via = (row or {}).get('via') or ''
    mv = re.match(r'(\d+) of (\d+) contract leaves closed', via)
    if mv and mv.group(1) == mv.group(2) and int(mv.group(2)) > 0:
        return 'parent: leaves closed, not hardened', via
    if not row:
        return 'RTL only (no route yet)', 'no registry row'
    return 'RTL only (no route yet)', (via or cat)


# ------------------------------------------------------------------------------------------------ per die
def die(name, cfg, reg, native, remote=True):
    DIES_CUR['cfg'] = cfg
    rows = {r['element']: r for r in reg['rows']}
    dc = json.loads(repo_read('results/fleet_viz/die_contracts.json'))
    dcfg = next(x for x in dc['designs'] if x['design'] == cfg['design'])
    macro_rx = '|'.join(s['macro'] for s in dcfg['sources'] if s.get('macro')) or MACRO_FALLBACK
    macro_rx = f'({macro_rx})|{MACRO_FALLBACK}'
    out = dict(die=name, label=cfg['label'], lead=cfg['lead'], contract_revision=dcfg.get('revision'),
               contract_complete=dcfg.get('complete'), unknowns=[])
    bind = None
    phys = {}
    if name == 'hbm':
        c = json.loads(repo_read(cfg['contract']))
        inst = c['instances']
        masters = collections.Counter(v['master'] for v in inst.values())
        bind = dict(src=dict(host='repo', path=cfg['contract'], commit=repo_commit(cfg['contract']), schema=c.get('schema'),
                             die_v='(no full HBM die netlist: v15 source contract instances)'),
                    masters={m: dict(instances=n, kind='real', rtl=next(v['source'] for v in inst.values() if v['master'] == m),
                                     open_inputs=[], width=[], port_fault=[], verdict='?') for m, n in masters.items()},
                    summary=dict(verdict=c.get('status'), masters=len(masters), instances=len(inst),
                                 unbound_source_ports=c.get('unbound_count'),
                                 pin_only_placeholders=c.get('pin_only_placeholder_count'),
                                 service_band_rejections=len(c.get('service_qualification_rejections') or []),
                                 qualification=c.get('qualification'), required_remaining=c.get('required_remaining'),
                                 strict=False))
        for u in c.get('unbound_ports') or []:
            mm = inst.get(u['instance'], {}).get('master')
            if mm and u.get('direction') == 'input':
                bind['masters'][mm]['open_inputs'].append(f"{u['instance']}.{u['port']}[{u.get('unbound_bits')}b]")
        ex = json.loads(repo_read(cfg['exposed']) or '{}')
        exe = json.loads(repo_read(cfg['exposed_engine']) or '{}')
        bind['summary']['exposed_inputs'] = dict(ports=ex.get('total_ports'), bits=ex.get('total_bits'),
                                                 by_owner={k: dict(ports=v.get('ports'), bits=v.get('bits'))
                                                           for k, v in (ex.get('by_stream') or {}).items()},
                                                 src=cfg['exposed'], commit=repo_commit(cfg['exposed']))
        g = exe.get('groups') or {}
        bind['summary']['exposed_inputs_engine_update'] = dict(
            {k: dict(ports=v.get('ports'), bits=v.get('bits'), status=v.get('status')) for k, v in g.items() if isinstance(v, dict)},
            engine_new_inputs=dict(ports=len(exe.get('engine_inputs') or []) if isinstance(exe.get('engine_inputs'), list)
                                   else (exe.get('engine_inputs') or {}).get('ports'),
                                   bits=(exe.get('engine_inputs') or {}).get('bits') if isinstance(exe.get('engine_inputs'), dict) else None),
            src=cfg['exposed_engine'], commit=repo_commit(cfg['exposed_engine']))
        inv = json.loads(repo_read(cfg['inventory']) or '{}')
        phys = dict(src=cfg['inventory'], commit=repo_commit(cfg['inventory']),
                    by_status=inv.get('summary', {}).get('by_status'), area_mm2_by_status=inv.get('area_mm2_by_status')
                    or inv.get('summary', {}).get('area_mm2_by_status'),
                    instances_by_view=inv.get('instances_by_view') or inv.get('summary', {}).get('instances_by_view'))
        rd = json.loads(repo_read(cfg['readiness']) or '{}')
        phys['readiness'] = dict(masters=rd.get('masters'), instances=rd.get('instances'), verdict=rd.get('verdict'),
                                 masters_with_view=rd.get('masters_with_view'),
                                 masters_without_view=len(rd.get('masters_without_view') or []))
        out['unknowns'].append('HBM has no full-die netlist: SM (32 tiles, ~362 mm2), attention halves, LK EP, host/SerDes are '
                               'carried from the v14 die and are not instances of the v15 source contract')
    else:
        bind = load_bind(cfg['bind'], cfg.get('exclude', ()), remote)
        if not bind:
            out['unknowns'].append('no readable bind record')
            return out
        # physical view binding of the latest chain
        if cfg.get('view_bind') and bind['src']['host'] != 'repo':
            vb = read(bind['src']['host'], norm_rel(bind['src']['path'], cfg['view_bind']))
            if vb:
                v = json.loads(vb)
                phys = dict(src=norm_rel(bind['src']['path'], cfg['view_bind']), masters=v.get('masters'),
                            masters_real_view=v.get('masters_bound'), instances=v.get('instances'),
                            instances_real_view=v.get('instances_bound'), no_view=v.get('no_view'),
                            refused=v.get('refused'))
        if cfg.get('view_classify'):
            for t, host, p in newest([cfg['view_classify']], (), remote)[:1]:
                v = json.loads(read(host, p) or '{}')
                rv = v.get('real_views') or []
                ri = sum(bind['masters'].get(m, {}).get('instances', 0) for m in rv)
                phys = dict(src=f'{host}:{p}', mtime=when(t), masters_real_view=len(rv), instances_real_view=ri,
                            note='classify real_views of the latest die STA (frames / relays = assumed single-flop placeholders)')
    out['netlist'] = bind['src']
    out['bind_summary'] = bind['summary']
    # ------------------------------------------------------------------ per-master view state
    contract_masters = {}
    for r in reg['rows']:
        for dd in r.get('dies') or []:
            if dd.get('design') == cfg['design'] and r.get('category') != 'superseded':
                contract_masters[r['element']] = dd.get('role')
    table = []
    for m, b in sorted(bind['masters'].items()):
        row = rows.get(m)
        cls, det = classify(m, row, b, macro_rx, native)
        table.append(dict(master=m, instances=b['instances'], rtl_kind=b.get('kind'), cls=cls, detail=det,
                          registry=(row or {}).get('category'), owner=(row or {}).get('owner_stream') or (row or {}).get('owner'),
                          open_inputs=b['open_inputs'], width=b['width'], port_fault=b['port_fault'],
                          real_view_in_die_run=(None if not phys.get('no_view') else m not in phys['no_view'])))
    netlist_masters = set(bind['masters'])
    missing = []
    for m, role in sorted(contract_masters.items()):
        if role != 'master' or m in netlist_masters or re.search(macro_rx, m):
            continue
        row = rows.get(m)
        cls, det = classify(m, row, None, macro_rx, native)
        missing.append(dict(master=m, cls=cls, registry=(row or {}).get('category'),
                            owner=(row or {}).get('owner_stream') or (row or {}).get('owner'), detail=det))
    dd_raw = repo_read('results/arch/tile_dedupe_1015/dedupe.json')
    ddx = {a['element']: a for a in (json.loads(dd_raw)['actions'] if dd_raw else [])}
    for t in table + missing:
        a = ddx.get(t['master'])
        if a:
            t['dedupe'] = f"ph{a['phase']}: {a['decision'][:80]}"
            t['dedupe_rebind'] = a['phase'] == 1 and a['decision'].startswith(('REPLACE by', 'REBIND NOW', 'MERGE into'))
    out['masters'] = table
    out['contract_missing'] = missing
    cnt = collections.Counter(t['cls'] for t in table)
    out['view_state_masters'] = {k: cnt.get(k, 0) for k in CLASSES}
    out['view_state_instances'] = {k: sum(t['instances'] for t in table if t['cls'] == k) for k in CLASSES}
    nonreal = [t for t in table if t['rtl_kind'] not in ('real', 'model') or t['cls'] == 'missing RTL']
    nonmacro = [t for t in table if t['cls'] != 'hard macro / PHY (allowed model)']
    win_inst = sum(t['instances'] for t in nonmacro if not t['cls'].startswith('closed'))
    out['placeholders'] = dict(
        rtl_nonreal_masters=len(nonreal), rtl_nonreal_instances=sum(t['instances'] for t in nonreal),
        rtl_nonreal=[f"{t['master']} x{t['instances']} ({t['rtl_kind']})" for t in nonreal],
        no_closed_view_masters=sum(1 for t in nonmacro if not t['cls'].startswith('closed')),
        no_closed_view_instances=win_inst,
        die_run_real_view=phys or None)
    open_in = sum(len(t['open_inputs']) for t in table)
    out['bind_open'] = dict(input_ports_unconnected=open_in,
                            masters_with_open_inputs=sum(1 for t in table if t['open_inputs']),
                            width_mismatch=sum(len(t['width']) for t in table),
                            die_port_not_in_rtl=sum(len(t['port_fault']) for t in table))
    # ------------------------------------------------------------------ die runs
    out['die_runs'] = die_runs(cfg, remote)
    if not phys:                                                 # S81: OT_VIEW_BINDING of the newest GEN'd chain
        for r in sorted(out['die_runs'], key=lambda r: ((r.get('src') or {}).get('time') or ''), reverse=True):
            m = re.search(r'OT_VIEW_BINDING (\d+) masters / (\d+) instances', r.get('events', {}).get('views', '') +
                          ' ' + r.get('events', {}).get('gen', ''))
            if m and r.get('gen_instances'):
                phys = dict(src=f"{r['host']}:{r['path']}", masters_real_view=int(m.group(1)),
                            instances_real_view=int(m.group(2)), instances=int(r['gen_instances']),
                            note='OT_VIEW_BINDING of the newest GEN (closed views bound by view_binding.json; every other '
                                 'master is a generated abstract)')
                out['placeholders']['die_run_real_view'] = phys
                break
    if cfg.get('grt_logs'):
        for t, host, p in newest([cfg['grt_logs']], (), remote)[:2]:
            txt = read(host, p) or ''
            tot = re.findall(r'^Total\s.*?(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*$', txt, re.M)
            it = re.findall(r'Start extra iteration (\d+)/(\d+)', txt)
            st = (f'overflow {tot[-1][2]}' if tot and 'GRT-0096' in txt else
                  f'RUNNING (extra iteration {it[-1][0]}/{it[-1][1]})' if it else 'RUNNING / no result')
            out.setdefault('grt_logs', []).append(dict(host=host, path=p, mtime=when(t), status=st))
    for k in ('region_run', 'full_grt'):
        if cfg.get(k):
            txt = repo_read(cfg[k]) or ''
            r = dict(src=cfg[k], commit=repo_commit(cfg[k]), kind=k)
            if k == 'region_run':
                r.update(grt_s=re.findall(r'OT_GRT_S (\d+)', txt)[-1:] or None, tns_max=re.findall(r'tns max (\S+)', txt)[-1:] or None)
            else:
                try:
                    j = json.loads(txt)
                    r.update(status=j.get('status'), overflow=j.get('overflow') or j.get('grt_overflow'))
                except ValueError:
                    pass
            out.setdefault('die_run_receipts', []).append(r)
    # ------------------------------------------------------------------ remaining work units
    not_done = [t for t in nonmacro if t['cls'] != 'closed + native PASS']
    miss_nd = [x for x in missing if x['cls'] != 'closed + native PASS']
    inputs = open_in + out['bind_open']['width_mismatch'] + out['bind_open']['die_port_not_in_rtl']
    out['remaining'] = dict(masters_not_closed_native=len(not_done) + len(miss_nd),
                            of_which_in_netlist=len(not_done), of_which_contract_missing=len(miss_nd),
                            placeholders_to_replace=len(nonreal) + len(missing),
                            inputs_to_bind=inputs,
                            total=len(not_done) + len(miss_nd) + len(nonreal) + len(missing) + inputs)
    if not bind['summary'].get('strict'):
        out['unknowns'].append('the strict die_port_bind.py v2 check (undriven / multi-driven net bits, stub bodies, tied inputs) '
                               'has not been run on this die netlist; the record used is ' + str(bind['src'].get('schema')))
    sta = [r for r in out['die_runs'] if r.get('tt_wns_ps') is not None]
    if not sta:
        out['unknowns'].append('no die-level TT/FF STA exists for the current netlist')
    elif any(r.get('pdn_skipped') for r in sta[:1]):
        out['unknowns'].append('the only die-level STA ran with PDN skipped (diagnostic)')
    un = [t['master'] for t in table if t['cls'] == 'closed, native unmeasured']
    if un:
        out['unknowns'].append(f'{len(un)} closed masters have no committed Liberty view to audit: ' + ', '.join(un[:6]))
    rb = [t for t in not_done + miss_nd if t.get('dedupe_rebind')]
    out['remaining']['dedupe_phase1_rebinds'] = len(rb)
    out['remaining']['masters_not_closed_native_after_dedupe'] = len(not_done) + len(miss_nd) - len(rb)
    if name == 'hbm':
        ex = bind['summary']['exposed_inputs']['ports'] or 0
        out['remaining']['hbm_exposed_input_ports'] = ex
        out['remaining']['hbm_unbound_source_ports'] = bind['summary']['unbound_source_ports']
    return out


# ------------------------------------------------------------------------------------------------ report
def fmt_runs(runs):
    lines = []
    for r in runs[:5]:
        ev = r.get('events', {})
        bits = []
        if r.get('src'):
            bits.append(f"src {r['src']['commit']}")
        if r.get('gen_instances'):
            bits.append(f"GEN {int(r['gen_instances']):,} inst")
        if r.get('case'):
            bits.append(f"case {r['case'].get('region')}: {r['case'].get('instances')}")
        if r.get('grt_overflow') is not None:
            bits.append(f"GRT overflow {int(r['grt_overflow']):,}")
        if r.get('tt_wns_ps') is not None:
            bits.append(f"TT WNS {r['tt_wns_ps']:+.2f} ps")
        if r.get('ff_setup_wns_ps') is not None:
            bits.append(f"FF setup {r['ff_setup_wns_ps']:+.2f}")
        if r.get('ff_hold_wns_ps') is not None:
            bits.append(f"FF hold {r['ff_hold_wns_ps']:+.2f} ps")
        if r.get('pdn_skipped'):
            bits.append('PDN SKIPPED (diagnostic)')
        last = ev.get('sta_ff') or ev.get('sta_tt') or ev.get('grt') or ev.get('pdn') or ev.get('place') or ev.get('gen') \
            or ev.get('OT_DONE') or ''
        lines.append(f"| `{r.get('host')}:{r['path']}` | {r['mtime']} | {'; '.join(bits) or '-'} | {last[:110]} |")
    return lines


def markdown(res):
    L = [f"# Die completeness, {res['date']}", '',
         'Measured inventory per die (tools/die_completeness.py). Every number comes from a bind record, the element registry, '
         'a native pin audit of the committed view, or a die-run log; the source of each is listed. Re-run daily.', '',
         '## Summary', '',
         '| die | netlist instances | distinct masters | non-real-RTL instances | instances without a closed view | open inputs (ports) | '
         'netlist masters closed+native PASS | netlist masters not closed+native | contract masters absent | remaining work units | '
         'masters left after DEDUPE ph-1 rebinds |',
         '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for d in res['dies']:
        if 'remaining' not in d:
            L.append(f"| {d['label']} | ? | ? | ? | ? | ? | ? | ? | ? | ? |")
            continue
        s = d['bind_summary']
        L.append(f"| {d['label']} | {s['instances']:,} | {s['masters']} | {d['placeholders']['rtl_nonreal_instances']:,} | "
                 f"{d['placeholders']['no_closed_view_instances']:,} | {d['bind_open']['input_ports_unconnected']:,}"
                 f"{' (= exposed inputs; ' + format(d['remaining']['hbm_unbound_source_ports'], ',') + ' unresolved ports incl. outputs)' if d['die'] == 'hbm' else ''} | "
                 f"{d['view_state_masters']['closed + native PASS']} | {d['remaining']['of_which_in_netlist']} | "
                 f"{len(d['contract_missing'])} | **{d['remaining']['total']:,}** | "
                 f"{d['remaining']['masters_not_closed_native_after_dedupe']} of {d['remaining']['masters_not_closed_native']} |")
    L += ['', 'Remaining work units = masters not closed + native PASS (netlist and contract-absent, hard macros excluded) '
          '+ placeholders to replace (non-real-RTL masters + contract masters absent from the netlist) + inputs to bind '
          '(unconnected input ports + width mismatches + die ports missing in RTL). A contract master absent from the netlist '
          'counts once to close it (unless already closed + native PASS) and once to integrate it. HBM additionally carries its exposed '
          'input ports and unresolved source ports, listed per die below.', '']
    for d in res['dies']:
        L += [f"## {d['label']} ({d['lead']})", '']
        if 'netlist' not in d:
            L += ['No readable record.', '']
            continue
        n, s = d['netlist'], d['bind_summary']
        L += [f"Contract: {d['contract_revision']} (complete={d['contract_complete']}).",
              f"Netlist / bind: `{n.get('host')}:{n['path']}` ({n.get('mtime') or n.get('commit')}, {n.get('schema')}), "
              f"die.v `{n.get('die_v')}`.", '',
              '| item | value |', '|---|---|',
              f"| (1) instances / distinct masters | {s['instances']:,} / {s['masters']} |",
              f"| bind verdict | {s.get('verdict')} ({'strict die_port_bind v2' if s.get('strict') else 'not the strict v2 bind'}) |",
              f"| (2) non-real-RTL masters (stub / unbound / mismatch / model not allowed) | {d['placeholders']['rtl_nonreal_masters']} "
              f"masters, {d['placeholders']['rtl_nonreal_instances']:,} inst {('- ' + ', '.join(d['placeholders']['rtl_nonreal'][:8])) if d['placeholders']['rtl_nonreal'] else ''} |",
              f"| (2) masters / instances with no closed view (die must window them) | {d['placeholders']['no_closed_view_masters']} / "
              f"{d['placeholders']['no_closed_view_instances']:,} |"]
        pr = d['placeholders'].get('die_run_real_view') or {}
        if pr.get('masters_real_view') is not None:
            L.append(f"| (2) latest die run on real views | {pr.get('masters_real_view')} masters / {pr.get('instances_real_view'):,} inst "
                     f"(of {pr.get('instances') or s['instances']:,}); `{pr.get('src')}` |")
        if pr.get('area_mm2_by_status'):
            L.append(f"| (2) view inventory by status (mm2) | {json.dumps(pr['area_mm2_by_status'])} (`{pr['src']}` {pr.get('commit')}) |")
        if pr.get('readiness'):
            L.append(f"| die chain readiness | {json.dumps(pr['readiness'])[:300]} |")
        b = d['bind_open']
        L.append(f"| (3) unconnected input ports / width mismatches / die ports not in RTL | {b['input_ports_unconnected']} / "
                 f"{b['width_mismatch']} / {b['die_port_not_in_rtl']} (on {b['masters_with_open_inputs']} masters) |")
        if s.get('undriven_net_bits') is not None:
            L.append(f"| (3) undriven / multi-driven net bits, stub masters, unbound masters | {s['undriven_net_bits']} / "
                     f"{s['multi_driven_net_bits']} / {s['stub_masters']} / {s['unbound_masters']} |")
        if d['die'] == 'hbm':
            e = s['exposed_inputs']
            L.append(f"| (3) exposed die inputs (views_v5) | {e['ports']:,} ports / {e['bits']:,} bits; by owner "
                     + '; '.join(f"{k} {v['ports']}/{v['bits']:,}" for k, v in e['by_owner'].items()) + ' |')
            L.append(f"| (3) after the service engine (1815) | {json.dumps({k: v for k, v in s['exposed_inputs_engine_update'].items() if k not in ('src', 'commit')})[:300]} |")
            L.append(f"| (3) unresolved source ports (source contract) | {s['unbound_source_ports']:,}; pin-only placeholders "
                     f"{s['pin_only_placeholders']}; service-band rejections {s['service_band_rejections']} |")
            L.append(f"| contract qualification | {json.dumps(s['qualification'])} |")
        vs = d['view_state_masters']
        L.append('| (4) masters by view state | ' + '; '.join(f"{k} {v}" for k, v in vs.items() if v) + ' |')
        L.append(f"| (5) contract masters absent from the netlist | {len(d['contract_missing'])}: "
                 + ', '.join(f"{x['master']} ({x['cls']})" for x in d['contract_missing'][:14])
                 + (' ...' if len(d['contract_missing']) > 14 else '') + ' |')
        r = d['remaining']
        L.append(f"| remaining work units | **{r['total']:,}** = {r['masters_not_closed_native']} masters not closed+native "
                 f"({r['of_which_in_netlist']} in netlist + {r['of_which_contract_missing']} absent) + "
                 f"{r['placeholders_to_replace']} placeholders + {r['inputs_to_bind']} inputs; DEDUPE phase-1 rebinds to closed "
                 f"standards (GEN work, no route) cover {r['dedupe_phase1_rebinds']} of the masters |")
        L += ['', '(6) Die-level runs (newest first):', '', '| run | time | measured | last event |', '|---|---|---|---|']
        L += fmt_runs(d['die_runs']) or ['| none | | | |']
        for g in d.get('grt_logs', []):
            L.append(f"| `{g['host']}:{g['path']}` | {g['mtime']} | GRT {g['status']} | GRT log |")
        for rr in d.get('die_run_receipts', []):
            L.append(f"| `{rr['src']}` | {rr['commit']} | {json.dumps({k: v for k, v in rr.items() if k not in ('src', 'commit')})[:160]} | committed receipt |")
        L += ['', '<details><summary>Masters not closed + native PASS</summary>', '',
              '| master | inst | state | registry | owner | detail | open inputs | DEDUPE |', '|---|---:|---|---|---|---|---|---|']
        for t in sorted(d['masters'], key=lambda t: (CLASSES.index(t['cls']), -t['instances'])):
            if t['cls'] in ('closed + native PASS', 'hard macro / PHY (allowed model)'):
                continue
            L.append(f"| {t['master']} | {t['instances']} | {t['cls']} | {t['registry'] or '-'} | {t['owner'] or '-'} | "
                     f"{(t['detail'] or '')[:90]} | {', '.join(t['open_inputs'])[:80]} | {t.get('dedupe', '')[:60]} |")
        L += ['', '</details>', '', '<details><summary>Contract masters absent from the netlist</summary>', '',
              '| master | state | registry | owner | detail |', '|---|---|---|---|---|']
        for x in d['contract_missing']:
            L.append(f"| {x['master']} | {x['cls']} | {x['registry'] or '-'} | {x['owner'] or '-'} | {(x['detail'] or '')[:90]} |")
        L += ['', '</details>', '']
        if d['unknowns']:
            L += ['Unknowns: ' + ' | '.join(d['unknowns']), '']
    L += ['## Largest unknowns', ''] + [f'- {u}' for u in res['unknowns']] + ['']
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='results/arch/die_completeness_1015')
    ap.add_argument('--no-native', action='store_true')
    ap.add_argument('--no-remote', action='store_true')
    ap.add_argument('--die', action='append')
    a = ap.parse_args(argv)
    subprocess.run(['git', '-C', str(ROOT), 'fetch', '-q', 'origin'], timeout=300)
    reg = registry()
    native = Native(not a.no_native)
    res = dict(schema=SCHEMA, date=dt.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z'),
               origin_main=sh(['git', '-C', str(ROOT), 'rev-parse', '--short', 'origin/main']).strip(),
               registry_generated=reg.get('generated_at'),
               native_budget=dict(launch_ps=220, capture_ps=190, corner='tt', tool='tools/hier_contract/native_pin_audit.py audit_one'),
               dies=[], unknowns=[])
    for name, cfg in DIES.items():
        if a.die and name not in a.die:
            continue
        print('die', name, file=sys.stderr)
        res['dies'].append(die(name, cfg, reg, native, not a.no_remote))
    res['unknowns'] = UNKNOWNS
    od = ROOT / a.out
    od.mkdir(parents=True, exist_ok=True)
    (od / 'completeness.json').write_text(json.dumps(res, indent=1) + '\n')
    (od / 'COMPLETENESS.md').write_text(markdown(res) + '\n')
    print(markdown(res).split('## Qwen compute')[0])
    return 0


# Largest unknowns (2026-10-15 21:20 PT, from the measured records of this run); edit when a record resolves one.
UNKNOWNS = [
    'HBM: there is no full-die netlist. The v15 source contract has 83 instances / 39 masters; the 32 SM tiles '
    '(~362 mm2), attention halves, LK EP and host/SerDes are carried from v14 and are not instances. Only the PHY + 128 PC '
    'region (53.3 mm2) is on real views; the largest die case (diecase_b, SYNTH ETMs) is TT -237,369 ps. Integration '
    'of the SM has not started, so its failures are not yet visible.',
    'S81: the die physical run binds closed views for only 18 masters / 31,916 of 84,387 instances (OT_VIEW_BINDING); '
    'the other closed masters enter as generated abstracts, so their die-context timing is unmeasured. No S81 die STA '
    'has ever run (c19b GRT in extra iteration 3/12), and the adopted wide hub C5 (rm5_p1973) needs a new GEN, so the netlist '
    'will change again.',
    'Qwen compute: qfd_tile_nk (768 of 1,638 instances) has no closed view and is being re-packed (64 lanes); 71 open '
    'inputs come from 7 producers that are not built; no compute-die STA has ever produced numbers (C16s STA flow error, '
    'C23s in PDN); contract v1.3 predates the fpq_s6 homes, so the 10 contract masters absent from the netlist may be '
    'stale names rather than missing blocks.',
    'Qwen KV/system: the strict die_port_bind.py v2 check has never run on the KV netlist (the KV tool does not count '
    'undriven / multi-driven bits); the measured open inputs are 27 (the logged "25" is arithmetic after the HOST fix, '
    'not a bind). The only die STA is PDN-skipped (TT -1,762.84 ps, 299,285 real-to-real violators). The v1.4.3 '
    'PV-wide pair (new masters, 1,024 SRAM macros) is not yet in the netlist.',
    'Native audit: closed views that fail the native launch/capture budget (compute 1, KV 4, S81 19 in the netlist, '
    'HBM 4) need re-kits; each one found at die level so far has cost a re-route.',
]

if __name__ == '__main__':
    sys.exit(main())
