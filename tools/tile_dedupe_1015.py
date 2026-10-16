#!/usr/bin/env python3
"""DEDUPE 2026-10-15: consolidate near-duplicate tile masters across Qwen ROM, S81 DeepSeek ROM and the HBM accelerator.

Owner rule 2026-10-15 19:50 PT (RELAUNCH_1405.md 'OWNER RULES 19:50', memory pin-registers-and-few-tiles-1015):
fewer distinct tiles -- quantize widths to a few sizes, replicate one hardened master, pin registers on every port of a
new tile, no new master variant without checking the registry for a hardened master that can be replicated or padded.

Inputs (all on main, or snapshotted next to the output):
  * the fleet-viz element registry (127.0.0.1:8765/api/elements), snapshotted to inputs/registry_rows.json
    (element, target, category, area, purpose, dies, jobs, best job, live) -- state, footprint, die membership;
  * results/fleet_viz/die_contracts.json and every source it names (port_bind / slots / instances) -- instance counts;
  * the RTL of every master on main (module body, comments stripped, module name masked) -- exact-clone and
    parameter-only-clone identity (sha1 of the body, and of the body with every number replaced by '#');
  * a closure-loop status snapshot (inputs/closure_live_jobs.txt) -- which open masters have a live job and at what stage.

Output: results/arch/tile_dedupe_1015/dedupe.json (+ README.md written by hand from it).
Usage:  tools/tile_dedupe_1015.py [--registry URL|FILE] [--status FILE] [--out DIR]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/arch/tile_dedupe_1015'
DESIGNS = {'qwen_compute': 'Qwen ROM', 'qwen_kvsys': 'Qwen ROM', 's81': 'DeepSeek ROM (S81)', 'hbm': 'HBM accelerator'}
T2D = {'Qwen ROM': 'qwen_kvsys', 'DeepSeek ROM': 's81', 'HBM accelerator': 'hbm'}
OPEN = {'failed, re-running', 'first trial in flight', 'needs redesign (no live job)', 'not started (open)',
        'flow failure (no live job)'}
MACRO = re.compile(r'phy|ckbump|pllm|fwdbump|^ot_rom_|^ot_pdie_|^ot_sram_|^ot_rf_')


def state(cat: str | None) -> str:
    if not cat:
        return 'PLACED (no registry row)'
    if cat.startswith('closed'):
        return 'CLOSED'
    if cat in ('first trial in flight', 'failed, re-running'):
        return 'IN FLIGHT'
    if cat == 'not started (open)':
        return 'NOT STARTED'
    if cat in OPEN:
        return 'OPEN (no live job)'
    if cat == 'superseded':
        return 'PLACED (registry: superseded)'
    return cat


# ----------------------------------------------------------------------------------------------------------- inputs
def load_registry(src: str) -> list[dict]:
    if src.startswith('http'):
        rows = json.load(urllib.request.urlopen(src, timeout=60))['rows']
    else:
        rows = json.loads(Path(src).read_text())
        rows = rows['rows'] if isinstance(rows, dict) else rows
    keep = ('element', 'target', 'category', 'purpose', 'jobs', 'live', 'failed', 'closed_jobs', 'owner')
    out = []
    for x in rows:
        r = {k: x.get(k) for k in keep}
        r['area_um2'] = (x.get('area') or {}).get('die')
        r['best_job'] = (x.get('best') or {}).get('job')
        r['dies'] = [d['design'] for d in (x.get('dies') or [])]
        out.append(r)
    return out


def j(p):
    return json.loads((ROOT / p).read_text())


def instances() -> tuple[dict, dict]:
    """design -> master -> instance count on the die top (or slot count), and design -> master -> outline um"""
    inst = collections.defaultdict(dict)
    outl = collections.defaultdict(dict)
    pb = j('results/arch/qwen_split_compute_1014/c13_smoke/port_bind.json')
    for m, v in pb['masters'].items():
        inst['qwen_compute'][m] = v.get('instances')
    k = j('results/arch/qwen_split_1014/kvsys_v1_4_1/contract.json')
    for m, v in k['slots'].items():
        inst['qwen_kvsys'][m] = v.get('count')
        outl['qwen_kvsys'][m] = v.get('outline_um')
    s = j('results/arch/s81_canonical_bind_1015/sbind_static_1015/bind5/port_bind.json')
    for m, v in s['masters'].items():
        inst['s81'][m] = v.get('instances')
    g = j('results/arch/hier_contract_1011/s81_v21_gen18.json')
    for m in g['relay_masters']['masters']:
        inst['s81'].setdefault(m['master'], m['instances'])
        outl['s81'][m['master']] = [m['outline']['w'], m['outline']['h']]
    h = j('results/arch/hbm_die_v15/source_contract_v151/contract.json')
    for m, n in collections.Counter(v['master'] for v in h['instances'].values()).items():
        inst['hbm'][m] = n
    for m in h['registered_station_masters']:
        inst['hbm'].setdefault(m['master'], None)
    return inst, outl


# -------------------------------------------------------------------------------------------------------- RTL identity
def module_index() -> dict:
    out = subprocess.run(['git', '-C', str(ROOT), 'grep', '-n', '-E', r'^\s*module\s+[A-Za-z_0-9]+', 'HEAD', '--',
                          'rtl', 'physical'], capture_output=True, text=True).stdout
    mods = collections.defaultdict(list)
    for ln in out.splitlines():
        m = re.match(r'HEAD:([^:]+):\d+:\s*module\s+(\w+)', ln)
        if m:
            mods[m.group(2)].append(m.group(1))
    return mods


_FC: dict = {}


def rtl_identity(name: str, mods: dict) -> dict:
    c = [p for p in mods.get(name, []) if 'mutant' not in p and '_sim' not in p] or mods.get(name, [])
    if not c:
        return {'rtl': None, 'exact': None, 'param': None}
    p = sorted(c, key=lambda q: (not q.startswith('rtl/'), len(q)))[0]
    if p not in _FC:
        _FC[p] = (ROOT / p).read_text(errors='replace') if (ROOT / p).exists() else ''
    m = re.search(r'\bmodule\s+' + re.escape(name) + r'\b(.*?)\bendmodule\b', _FC[p], re.S)
    if not m:
        return {'rtl': p, 'exact': None, 'param': None}
    b = re.sub(r'\s+', ' ', re.sub(r'//[^\n]*|/\*.*?\*/', '', m.group(1), flags=re.S)).strip().replace(name, '@M')
    ws = sorted({int(a) + 1 for a in re.findall(r'\[(\d+):0\]', b)}, reverse=True)
    return {'rtl': p, 'exact': hashlib.sha1(b.encode()).hexdigest()[:12],
            'param': hashlib.sha1(re.sub(r'\d+', '#', b).encode()).hexdigest()[:12], 'max_port_bits': ws[0] if ws else None}


# ----------------------------------------------------------------------------------------------------- family rules
# Relay / station families: (family id, regex -> (width, side/flow, lanes), standard ladder per side, note)
LADDERS = {
    'S81-HSTN': dict(
        rx=r'^dsfd_hstn([hv])_(\d+)$', side=lambda m: m.group(1).upper(), width=lambda m: int(m.group(2)),
        name=lambda side, w: f'dsfd_hstn{side.lower()}_{w}',
        ladder={'H': [20, 85, 128, 514, 761, 1029], 'V': [20, 85, 515, 759, 1029, 2204]},
        function='common-clock register station: W bits, one rising-edge flop per bit, no reset '
                 '(rtl/dsrom_sys/s81_station_native/gen18r/dsfd_hstn<h|v>_<W>.sv); H = E/W pin faces, V = N/S',
        depth=1),
    'S81-STN': dict(
        rx=r'^dsfd_stn([hv])_(\d+)x(\d+)$', side=lambda m: m.group(1).upper(), width=lambda m: int(m.group(2)),
        lanes=lambda m: int(m.group(3)), name=lambda side, w: f'dsfd_stn{side.lower()}_{w}x1',
        ladder={'H': [10, 86, 293, 566, 1026], 'V': [10, 86, 293, 566, 1026]},
        function='forwarded-clock link stage ot_fwd_link_stage #(W) per lane (clock rides with the data); '
                 'Wx<k> = k lanes side by side', depth=1),
    'S81-RLY': dict(
        rx=r'^dsfd_rly_(\d+)_([NSEW]{2})$', side=lambda m: m.group(2), width=lambda m: int(m.group(1)),
        name=lambda side, w: f'dsfd_rly_{w}_{side}',
        ladder=None,  # per flow: widest CLOSED narrow width (all W <= 68 share the 15.12 x 15.12 um outline) + 283
        function='relay register ot_s81_rly #(W): one stage, async-clear rs, ck/rs on the third face, flops at the '
                 'pins + outhold BUF-HB4-BUF (rtl/dsrom_sys/s81_glue/dsfd_rly_masters*.sv); <flow> = in-face, out-face',
        depth=1),
    'HBM-RLY': dict(
        rx=r'^hbfd_rly_(\d+)_([NSEW]{2})$', side=lambda m: m.group(2), width=lambda m: int(m.group(1)),
        name=lambda side, w: f'hbfd_rly_{w}_{side}',
        ladder={f: [48, 136, 304, 624, 1136] for f in ('WE', 'EW', 'SN', 'NS')},
        function='HBM width-class relay (tools/hbm_die_rly_kits.py): flops at the pins, ck/rs third face, '
                 'M5 cap, 21.6 um deep; classes 8/48/136 share the 21.6 x 21.6 um outline', depth=1),
    'FENCE-BANK': dict(
        rx=r'^ot_hbm_native_fence_bank(\d+)$', side=lambda m: '-', width=lambda m: int(m.group(1)),
        name=lambda side, w: f'ot_hbm_native_fence_bank{w}', ladder={'-': [32, 128]},
        function='native visibility-fence bank (physical/hbm_native_fence_banks_1014): N entries; '
                 'N = 1..32 share the 21.6 x 21.6 um outline; used by S81 and HBM', depth=1),
}

# exact-RTL-clone groups are found automatically; these name the families they belong to
CLONE_FAMILY = [
    (r'^dsfd_(m2l|l2r|r2l)_', 'S81-NET', 'static-network lane ends (m2l/l2r/r2l): forwarded-clock pin register -> '
                                         'ot_s81_static_lane_end -> output pin flop (rtl/dsrom_sys/s81_static_net/gen)'),
    (r'^dsfd_node_', 'S81-NET-NODE', 'static-network merge node (a/b -> o, 66 b)'),
    (r'^dsfd_lkck_', 'S81-LKCK', 'per-quadrant link clock cell'),
    (r'^dsfd_mtp_hrow_cb', 'S81-MTP-HROW', 'MTP head-row column buffer (E/W copies)'),
    (r'^hfd_hgi_vm_calendar_', 'HBM-VM-CAL', 'HBM VM static calendar per quadrant'),
    (r'^ot_hbm_accel_smh_', 'HBM-SMH', 'HBM SM head east/west copies'),
    (r'^hfd_svc_v15_', 'HBM-SVC-V15', 'HBM v15 service slice (per quadrant / PC group)'),
]

# parameter-only families (bodies identical except numbers): ID constants that a reset-loaded config register can carry
PARAM_FAMILIES = [
    dict(fid='S81-VM-READ', rx=r'^dsfd_vm_static_read_[qv]\d(_p)?$', stds=4,
         function='S81 static VM read quartets q0..q7 / v0..v7 and their _p variants: same structure, per-bank constants',
         action='CLOSED: keep (no re-route). Next RTL revision: bank index as a pin-registered config input loaded by '
                'the static schedule at reset -> one master per role (q, q_p, v, v_p)'),
    dict(fid='S81-VM-RETURN', rx=r'^dsfd_vm_static_return_bank8_l\d(_p)?$', stds=2,
         function='S81 static VM return bank8 lanes l0..l3 (+_p): per-lane constants',
         action='CLOSED: keep. Next revision: lane index config register -> 2 masters'),
    dict(fid='S81-VM-FSR', rx=r'^dsfd_vm_static_fsr_b\d$', stds=1, function='S81 VM fsr banks b0..b3',
         action='CLOSED: keep. Next revision: bank index config register -> 1 master'),
    dict(fid='S81-HC-CTNL', rx=r'^ot_s81_hc_ctnl_l\d$', stds=1, function='S81 HC ctnl lanes l0..l3',
         action='CLOSED: keep. Next revision: lane index register -> 1 master'),
    dict(fid='S81-PQ-QB', rx=r'^ot_s81_pq_qb_bank\d_native$', stds=1, function='S81 PQ qb banks 0..3',
         action='CLOSED: keep. Next revision: bank index register -> 1 master (bankx stays: different body)'),
    dict(fid='S81-PQ-BC', rx=r'^ot_s81_pq_bc_slice\d$', stds=1, function='S81 PQ bc slices 0..3',
         action='CLOSED: keep. Next revision: slice index register -> 1 master'),
    dict(fid='HBM-VMS-STATIC', rx=r'^hfd_hgi_vms_static_(NE|NW|SE|SW)$', stds=1, pre_route=True, std_rx=r'_NE$',
         function='HBM VM static slice per quadrant (NE = SE and NW = SW up to constants)',
         action='NOT STARTED: write ONE RTL master with the quadrant index as a registered config input; place it '
                'R0 / MY / MX / R180 (pins symmetric on track) -> 4 quadrants = 1 route instead of 4'),
    dict(fid='HBM-VMS-BANK-ID', rx=r'^hfd_vms_bank_identity_q\d_b\d$', stds=3, pre_route=True, rtl_only=True, std_rx=r'_b0$',
         function='HBM VM bank cores q0..q3 x b0..b7 (32 RTL modules): ot_vms_bank_static_identity '
                  '#(BANK_ID, SLICE_ID, RG, WG); banks differ only in BANK_ID/SLICE_ID, quadrants in RG (5/4/6/6)',
         action='4 b0 jobs RUNNING (vm_identity_q*_b0): LET FINISH. Before any b1..b7 route: make BANK_ID/SLICE_ID '
                'a pin-registered config input (loaded once by the static schedule) so every bank is a replica: '
                '32 modules -> 3 masters (RG 4 / 5 / 6), or 1 if RG is padded to 6'),
    dict(fid='QWEN-PORT-TILES', rx=r'^qfd_port_tiles_\d(_f1)?$', stds=2, pre_route=True, std_rx=r'_0(_f1)?$',
         function='Qwen compute-die port tile clusters 0/1/2 (+ f1): identical up to constants',
         action='NOT STARTED: one RTL per kind (plain / f1) with the tile index registered -> 6 -> 2 routes'),
    dict(fid='HBM-SFU-CTL', rx=r'^ot_hgi_sfu_ctl(60hi|75hi|75lo)$', stds=1, pre_route=True, std_rx=r'75lo$',
         function='HBM SFU control split variants 60hi / 75hi / 75lo (all NEEDS REDESIGN)',
         action='redesign as ONE controller with the split point in a config register -> 3 -> 1'),
]

# mirror / quadrant pairs with no RTL yet or identical function (merge before the first route)
MIRROR_PAIRS = [
    ('qwen_kvsys', ['qkd_astk', 'qkd_astk_n'], 'KV attention stack S / N copy'),
    ('qwen_kvsys', ['qkd_land', 'qkd_land_n'], 'KV landing strip S / N copy'),
    ('qwen_kvsys', ['qkd_hslice', 'qkd_hslice_dn'], 'KV H-slice up / down copy'),
    ('qwen_compute', ['qfd_xcol_e', 'qfd_xcol_w'], 'compute-die x-column E / W copy'),
]

# cross-design replica map: Qwen KV relays (no RTL, not started) and HBM v15 registered stations -> closed hbfd_rly
CROSS = {'qkd_rly': dict(rx=r'^qkd_rly_(\d+)$', design='qwen_kvsys', to='HBM-RLY'),
         'hfd_stn_v15': dict(rx=r'^hfd_stn_v15_cc(\d+)$', design='hbm', to='HBM-RLY')}


def area_of(reg, m):
    r = reg.get(m)
    return r['area_um2'] if r else None


def best_cover(w, ladder, area):
    """cheapest cover of a w-bit bus by standard widths: smallest std >= w, or k x max (+ smallest std >= rest)"""
    ladder = sorted(ladder)
    opts = []
    for s in ladder:
        if s >= w:
            opts.append([s])
            break
    mx = ladder[-1]
    if w > mx:
        k = w // mx
        rest = w - k * mx
        if rest == 0:
            opts.append([mx] * k)
        else:
            opts.append([mx] * (k + 1))
            nx = next((s for s in ladder if s >= rest), None)
            if nx:
                opts.append([mx] * k + [nx])
    def cost(o):
        a = [area(s) for s in o]
        return sum(x for x in a if x is not None) if all(x is not None for x in a) else 1e18 + sum(o)
    return min(opts, key=lambda o: (cost(o), sum(o)))


# ---------------------------------------------------------------------------------------------------------- analysis
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--registry', default='http://127.0.0.1:8765/api/elements')
    ap.add_argument('--status', default=str(OUT / 'inputs/closure_live_jobs.txt'))
    ap.add_argument('--out', default=str(OUT))
    a = ap.parse_args(argv)
    out = Path(a.out)
    (out / 'inputs').mkdir(parents=True, exist_ok=True)
    regrows = load_registry(a.registry)
    if a.registry.startswith('http'):
        (out / 'inputs/registry_rows.json').write_text(json.dumps(regrows, indent=0, sort_keys=True) + '\n')
    reg = {r['element']: r for r in regrows}
    inst, outl = instances()
    live = {}
    if Path(a.status).exists():
        for ln in Path(a.status).read_text().splitlines():
            f = ln.split()
            if len(f) >= 3:
                live.setdefault(f[0], (f[1], f[2]))
    mods = module_index()

    # ---- universe: distinct masters per design
    U = collections.defaultdict(dict)
    for r in regrows:
        if r['category'] == 'superseded':
            continue
        ds = list(r['dies'])
        if not ds and r['category'] in OPEN and r['target'] in T2D:
            ds = [T2D[r['target']]]          # open element outside the contract lists (loose) -> its design
        for d in ds:
            U[d][r['element']] = r
    for d in DESIGNS:
        for m in inst[d]:
            if m not in U[d] and not MACRO.search(m):
                U[d][m] = reg.get(m) or {'element': m, 'category': None, 'area_um2': None, 'purpose': None}
    masters = {}
    for d, ms in U.items():
        for m, r in ms.items():
            e = masters.setdefault(m, {'element': m, 'designs': [], 'state': state(r.get('category')),
                                       'registry_category': r.get('category'), 'footprint_um2': r.get('area_um2'),
                                       'function': (r.get('purpose') or '')[:200], 'instances': {},
                                       'jobs_so_far': r.get('jobs')})
            e['designs'].append(d)
            e['instances'][d] = inst[d].get(m)
            if m in outl.get(d, {}) and outl[d][m]:
                e['outline_um'] = outl[d][m]
                if not e['footprint_um2']:
                    e['footprint_um2'] = round(outl[d][m][0] * outl[d][m][1], 2)
    for m, e in masters.items():
        e.update({k: v for k, v in rtl_identity(m, mods).items()})
        e['live_jobs'] = None
    # live-job attach by family-specific prefixes (closure-loop names differ from master names)
    jobmap = {r'^s81fill_(hstn[hv]_\d+|stn[hv]_\d+x\d+)-': 'dsfd_{}',
              r'^s81net_(\w+?)-n\d+-': 'dsfd_{}', r'^vm_identity_(q\d_b\d)_': 'hfd_vms_bank_identity_{}'}
    for jn, (st, sg) in live.items():
        if st not in ('RUNNING', 'READY', 'ECO', 'QUEUED'):
            continue
        for rx, tpl in jobmap.items():
            mm = re.match(rx, jn)
            if mm:
                cand = tpl.format(mm.group(1))
                hit = next((k for k in masters if k.lower() == cand.lower()), None)
                if hit:
                    masters[hit]['live_jobs'] = sorted(set((masters[hit]['live_jobs'] or []) + [f'{jn} {st}/{sg}']))
                elif cand.startswith('hfd_vms_bank_identity'):
                    masters.setdefault(cand, {'element': cand, 'designs': ['hbm'], 'state': 'IN FLIGHT',
                                              'instances': {'hbm': None}, 'footprint_um2': None})
                    masters[cand]['live_jobs'] = [f'{jn} {st}/{sg}']

    def is_closed(m):
        return m in masters and masters[m]['state'] == 'CLOSED' or (reg.get(m) or {}).get('category', '').startswith('closed')

    def jobs_mean(names):
        v = [reg[n]['jobs'] for n in names if n in reg and reg[n].get('jobs') and is_closed(n)]
        return round(sum(v) / len(v), 1) if v else None

    fam_out, actions = [], []

    def act(m, fid, decision, target=None, copies=1, area_delta=None, flops=None, routes=0, phase=None, note=''):
        e = masters.get(m, {})
        actions.append(dict(element=m, family=fid, designs=e.get('designs'), state=e.get('state'),
                            instances=e.get('instances'), decision=decision, target=target, copies=copies,
                            area_delta_um2_die=area_delta, extra_flops_die=flops, routes_avoided=routes,
                            phase=phase, live_jobs=e.get('live_jobs'), note=note))

    # ---- ladder families
    for fid, F in LADDERS.items():
        members = {}
        for m in masters:
            mm = re.match(F['rx'], m)
            if mm:
                members[m] = (F['side'](mm), F['width'](mm), F.get('lanes', lambda _m: 1)(mm))
        if not members:
            continue
        hc = collections.Counter(masters[m].get('param') for m in members if masters[m].get('param'))
        major = hc.most_common(1)[0][0] if hc else None
        other = sorted(m for m in members if major and masters[m].get('param') and masters[m]['param'] != major)
        for m in other:
            act(m, fid, 'KEEP (different RTL body from the family generator; not merged)', phase=0)
            members.pop(m)
        ladder = F['ladder']
        if ladder is None:   # S81 rly: per flow and size class (<=16 b / 17-283 b), each width -> the smallest-footprint CLOSED master >= W (ties: widest)
            closed_w = collections.defaultdict(list)
            for m, (side, w, _) in members.items():
                if is_closed(m):
                    closed_w[side].append(w)
            ladder = {}
            for side, ws in closed_w.items():
                img = set()
                for w in ws:
                    cands = [c for c in ws if c >= w and (c <= 16) == (w <= 16)]   # keep a <=16 b class per flow
                    img.add(min(cands, key=lambda c: (area_of(reg, F['name'](side, c)) or 1e9, -c)))
                ladder[side] = sorted(img)
        stds = {F['name'](s, w) for s, ws in ladder.items() for w in ws}
        per_design = collections.defaultdict(lambda: dict(area=0.0, flops=0, routes=0))
        for m, (side, w, lanes) in sorted(members.items(), key=lambda z: (z[1][0], z[1][1])):
            e = masters[m]
            lad = ladder.get(side)
            if not lad:
                act(m, fid, 'KEEP (no standard for this flow yet)', phase=0)
                continue
            area_fn = lambda s, side=side: area_of(reg, F['name'](side, s))
            cover = best_cover(w, lad, area_fn) * lanes
            tnames = [F['name'](side, s) for s in cover]
            if m in stds and lanes == 1:
                act(m, fid, 'STANDARD (keep, replicate)', target=m, phase=0)
                continue
            n = sum(v or 0 for v in e['instances'].values())
            own = e.get('footprint_um2')
            tarea = [area_of(reg, t) for t in tnames]
            ad = round((sum(tarea) - (own or 0)) * n, 1) if own and all(tarea) else None
            fl = (sum(cover) - w * lanes) * n
            tclosed = all(is_closed(t) for t in tnames)
            tgt = ' + '.join(f'{c} x {t}' for t, c in collections.Counter(tnames).items())
            st = e['state']
            if st == 'CLOSED':
                free = ad is not None and ad <= 0.01e6 * 0.0 + max(0.0, 0.002 * (own or 0) * n) + 0.5
                act(m, fid, ('REBIND NOW to ' if free else 'REBIND AT NEXT TOUCH to ') + tgt,
                    target=tnames, copies=len(tnames), area_delta=ad, flops=fl, phase=1 if free else 2,
                    note='closed view kept; die GEN binds the standard instead (no route)' if free else
                    'closed view kept until the die names this master again (re-pin / hold / re-route): then the '
                    'standard replica replaces it instead of a re-close')
            elif e.get('live_jobs'):
                stage = ' '.join(e['live_jobs'])
                near = any(s in stage for s in ('collect', 'hold_eco', 'READY'))
                act(m, fid, ('LET FINISH (near closure); if it closes the view stands (non-standard, phase 2), '
                             'if it fails retire it and bind ' if near else 'LET FINISH; on FAIL retire (no '
                             're-submit) and bind ') + tgt, target=tnames, copies=len(tnames), area_delta=ad, flops=fl,
                    phase=1, routes=0, note='' if tclosed else 'standard itself not closed yet')
            elif st.startswith('PLACED'):
                act(m, fid, 'REBIND NOW to ' + tgt, target=tnames, copies=len(tnames), area_delta=ad, flops=fl,
                    phase=1, note='placed by the current die bind, no route planned (registry: ' + st + ')')
            else:
                act(m, fid, ('REPLACE by replica ' if tclosed else 'REPLACE once standard closes: ') + tgt,
                    target=tnames, copies=len(tnames), area_delta=ad, flops=fl, phase=1, routes=1)
        fam_out.append(dict(family=fid, kind='width ladder', function=F['function'], depth_stages=F['depth'],
                            members=sorted(members), n_members=len(members),
                            standard={s: [F['name'](s, w) + ('' if is_closed(F['name'](s, w)) else ' (NOT CLOSED)')
                                          for w in ws] for s, ws in ladder.items()},
                            n_standard=len(stds), mean_jobs_per_closed_member=jobs_mean(members)))

    # ---- cross-design replicas (Qwen KV relays, HBM v15 stations) onto HBM-RLY
    hb = LADDERS['HBM-RLY']
    for cid, C in CROSS.items():
        mem = {m: int(re.match(C['rx'], m).group(1)) for m in masters if re.match(C['rx'], m)}
        for m, w in sorted(mem.items(), key=lambda z: z[1]):
            e = masters[m]
            cover = best_cover(w, [48, 136, 304, 624, 1136], lambda s: area_of(reg, hb['name']('WE', s)))
            tnames = [hb['name']('<flow>', s) for s in cover]
            n = sum(v or 0 for v in e['instances'].values())
            own = e.get('footprint_um2')
            tarea = sum(area_of(reg, hb['name']('NS', s)) for s in cover)   # NS/SN is the larger outline
            ad = round((tarea - own) * n, 1) if own else None
            act(m, 'HBM-RLY (cross-design)', 'REPLACE by replica ' + ' + '.join(
                f'{c} x {t}' for t, c in collections.Counter(tnames).items()), target=tnames, copies=len(cover),
                area_delta=ad, flops=(sum(cover) - w) * n if n else None, phase=1, routes=1,
                note='<flow> = WE/EW/SN/NS by the slot orientation; a per-bit-direction bundle splits into one '
                     'relay per direction (2 x copies, area still below the 52.656 um slot)' if cid == 'qkd_rly' else
                     'v15 registered station (1 cycle, 2,224 / 2,248 b): two hbfd_rly_1136 side by side, 1 cycle')
        fam_out.append(dict(family=f'{cid} -> HBM-RLY', kind='cross-design replica',
                            function='die-top relay register, 1 stage' + (' (Qwen KV die, no RTL yet)' if cid == 'qkd_rly'
                                                                          else ' (HBM v15 contract)'),
                            depth_stages=1, members=sorted(mem), n_members=len(mem),
                            standard={'flows WE/EW/SN/NS': ['hbfd_rly_48', 'hbfd_rly_136', 'hbfd_rly_304', 'hbfd_rly_624', 'hbfd_rly_1136']},
                            n_standard=0, mean_jobs_per_closed_member=jobs_mean([f'hbfd_rly_{w}_{f}' for w in
                                                                                 (8, 48, 136, 304, 624, 1136) for f in hb['ladder']])))

    # ---- exact RTL clones
    ex = collections.defaultdict(list)
    covered = {x['element'] for x in actions}
    for m, e in masters.items():
        if e.get('exact') and m not in covered:
            ex[e['exact']].append(m)
    for h, grp in ex.items():
        if len(grp) < 2:
            continue
        fid, fn = next(((f, d) for rx, f, d in CLONE_FAMILY if re.match(rx, grp[0])), ('CLONE', 'exact RTL clone'))
        closed = [m for m in grp if masters[m]['state'] == 'CLOSED']
        pool = closed or grp
        canon = max(pool, key=lambda m: ((masters[m].get('footprint_um2') or 0), m))
        for m in sorted(grp):
            e = masters[m]
            if m == canon:
                act(m, fid, 'CANONICAL (keep, replicate)', target=m, phase=0)
                continue
            n = sum(v or 0 for v in e['instances'].values()) or 1
            ad = round(((masters[canon].get('footprint_um2') or 0) - (e.get('footprint_um2') or 0)) * n, 1) \
                if e.get('footprint_um2') and masters[canon].get('footprint_um2') else None
            if e['state'] == 'CLOSED':
                act(m, fid, f'REBIND NOW to {canon} (identical RTL)', target=[canon], area_delta=ad, flops=0, phase=1,
                    note='mirror (MY / MX) where the slot faces the other way; pins on track checked by the die GEN'
                    + ('; the live re-route of this name is redundant: let it finish, do not resubmit'
                       if e.get('live_jobs') else ''))
            elif e.get('live_jobs'):
                act(m, fid, f'LET FINISH, then bind {canon} (identical RTL; this route is redundant)', target=[canon],
                    area_delta=ad, flops=0, phase=1)
            else:
                act(m, fid, f'REPLACE by replica of {canon} (identical RTL)', target=[canon], area_delta=ad, flops=0,
                    phase=1, routes=1 if e['state'] in ('NOT STARTED', 'OPEN (no live job)') else 0)
        fam_out.append(dict(family=fid, kind='exact RTL clone group', function=fn, members=sorted(grp),
                            n_members=len(grp), standard={'canonical': [canon]}, n_standard=1,
                            mean_jobs_per_closed_member=jobs_mean(grp)))

    # ---- parameter-only families
    for P in PARAM_FAMILIES:
        grp = sorted(m for m in set(masters) | ({f'hfd_vms_bank_identity_q{q}_b{b}' for q in range(4) for b in range(8)}
                                                 if P['fid'] == 'HBM-VMS-BANK-ID' else set()) if re.match(P['rx'], m))
        grp = [m for m in grp if m not in covered and m not in {x['element'] for x in actions}]
        if not grp:
            continue
        pre = P.get('pre_route')
        for m in grp:
            if m not in masters:
                masters[m] = {'element': m, 'designs': ['hbm'], 'state': 'RTL only', 'instances': {'hbm': 1},
                              'live_jobs': None}
            st = masters[m]['state']
            if st == 'CLOSED' or not pre:
                act(m, P['fid'], P['action'], phase=2 if st == 'CLOSED' else 1)
            elif re.search(P['std_rx'], m):
                act(m, P['fid'], 'LET FINISH (family representative)' if masters[m].get('live_jobs')
                    else 'STANDARD (route once, replicate)', phase=1)
            else:
                act(m, P['fid'], 'MERGE into the family master (no route of its own); ' + P['action'], phase=1,
                    routes=1, target=[max((c for c in grp if re.search(P['std_rx'], c)),
                                          key=lambda c: len(os.path.commonprefix([c, m])))])
        fam_out.append(dict(family=P['fid'], kind='parameter-only clones (ID constants)', function=P['function'],
                            members=grp, n_members=len(grp), standard={'after': [f"{P['stds']} master(s)"]},
                            n_standard=P['stds'], proposal=P['action']))

    # ---- mirror pairs
    for d, grp, fn in MIRROR_PAIRS:
        grp = [m for m in grp if m in masters]
        if len(grp) < 2:
            continue
        for i, m in enumerate(grp):
            st = masters[m]['state']
            act(m, 'MIRROR-PAIR', 'STANDARD (route once)' if i == 0 else
                f'REPLACE by {grp[0]} mirrored (MX/MY), the second copy needs no RTL of its own',
                target=[grp[0]], phase=1, routes=0 if i == 0 or st == 'CLOSED' else 1)
        fam_out.append(dict(family='MIRROR-PAIR ' + grp[0], kind='mirror/quadrant copy, not started', function=fn,
                            members=grp, n_members=len(grp), standard={'canonical': [grp[0]]}, n_standard=1))

    # ---------------------------------------------------------------------------------------------------- totals
    acted = collections.defaultdict(list)
    for x in actions:
        acted[x['element']].append(x)
    summ = {}
    for d in DESIGNS:
        ms = {m for m, e in masters.items() if d in (e.get('designs') or []) and e.get('state') != 'RTL only'}
        retired1 = {x['element'] for x in actions if d in (x['designs'] or []) and x['phase'] == 1 and
                    x['decision'].startswith(('REBIND NOW', 'REPLACE', 'MERGE'))}
        retired_f = {x['element'] for x in actions if d in (x['designs'] or []) and x['decision'].startswith(
            ('REBIND NOW', 'REBIND AT NEXT', 'REPLACE', 'MERGE', 'LET FINISH;', 'LET FINISH, then bind'))}
        new_std = {t for x in actions if d in (x['designs'] or []) and x['phase'] == 1 and x['target']
                   for t in x['target'] if t not in ms and '<flow>' not in t}
        cross = {t.replace('<flow>', f) for x in actions if d in (x['designs'] or []) and x['target']
                 for t in x['target'] if '<flow>' in t for f in ('WE', 'EW', 'SN', 'NS')}
        p1 = [x for x in actions if d in (x['designs'] or []) and x['phase'] == 1]
        p2 = [x for x in actions if d in (x['designs'] or []) and x['phase'] == 2]
        summ[d] = dict(
            label=DESIGNS[d], masters_before=len(ms),
            masters_after_phase1=len(ms - retired1) + len(new_std) + (len(cross) if cross else 0),
            masters_after_full=len(ms - retired_f) + len(new_std) + (len(cross) if cross else 0)
            - sum(max(0, f['n_members'] - f['n_standard']) for f in fam_out
                  if f['kind'].startswith('parameter') and any(d in (masters.get(m, {}).get('designs') or [])
                                                                 for m in f['members']) and all(
                      masters.get(m, {}).get('state') == 'CLOSED' for m in f['members'])),
            needs_closure_before=sum(1 for m in ms if masters[m]['state'] != 'CLOSED'),
            needs_closure_after_phase1=sum(1 for m in ms - retired1 if masters[m]['state'] != 'CLOSED')
            + sum(1 for t in new_std if not is_closed(t)),
            routes_avoided=sum(x['routes_avoided'] for x in actions if d in (x['designs'] or [])),
            area_delta_mm2_phase1=round(sum(x['area_delta_um2_die'] or 0 for x in p1) / 1e6, 4),
            area_delta_mm2_phase2=round(sum(x['area_delta_um2_die'] or 0 for x in p2) / 1e6, 4),
            extra_flops_phase1=sum(x['extra_flops_die'] or 0 for x in p1),
            extra_flops_phase2=sum(x['extra_flops_die'] or 0 for x in p2),
            cross_design_masters_added=sorted(cross) if cross else [])
    res = dict(schema='opentallas.tile_dedupe.v1', date='2026-10-15', owner_rule=__doc__.split('\n')[2:5],
               generator='tools/tile_dedupe_1015.py', registry_rows=len(regrows),
               phases={'0': 'standard / canonical master (keep, replicate)',
                       '1': 'now: open masters replaced by replicas of CLOSED standards (route avoided); closed '
                            'masters rebound by the die GEN where area and RTL are equal (no route)',
                       '2': 'closed masters with an area / RTL cost: kept until the die names them again; then the '
                            'standard replaces them instead of a re-close'},
               summary=summ, families=fam_out, actions=actions,
               masters=sorted(masters.values(), key=lambda e: (e.get('designs') or ['~'])[0] + e['element']))
    (out / 'dedupe.json').write_text(json.dumps(res, indent=1, sort_keys=False, default=str) + '\n')
    for d, s in summ.items():
        print(d, {k: v for k, v in s.items() if k != 'cross_design_masters_added'}, len(s['cross_design_masters_added']))
    print('routes avoided total', sum(s['routes_avoided'] for s in summ.values()))


if __name__ == '__main__':
    main()
