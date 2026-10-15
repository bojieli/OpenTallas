#!/usr/bin/env python3
"""GLOBAL-FP-H candidate driver: build one named candidate, legalize, score against the current-layout reference.

  python3 tools/hbm_globalfp_run.py --graph graph.json --geo <hbm_system_geometry_1015> --cand NAME --seed S --iters N --out DIR
"""
import argparse, copy, json, math, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hbm_globalfp as F

QS = F.QS


def t_quad_drain(G):
    """STRUCTURAL: ATT query/output per field from/to the field's own quadrant VM (bank pair 0) instead of NE:
    four quadrant drains = new VM allocation + compiler record split; no area change."""
    G = copy.deepcopy(G)
    for l in G['links']:
        if l['cls'] == 'ATT_Q':
            f = int(l['dst'][-1]); b = int(l['src'][-1]) % 2
            l['src'] = f'vmb_{QS[f]}{b}'; l['id'] = f"{l['src']}>{l['dst']}:ATT_Q"; l['provenance'] += ' | STRUCTURAL quad_drain'
        if l['cls'] == 'ATT_O':
            f = int(l['src'][-1]); b = int(l['dst'][-1]) % 2
            l['dst'] = f'vmb_{QS[f]}{b}'; l['id'] = f"{l['src']}>{l['dst']}:ATT_O"; l['provenance'] += ' | STRUCTURAL quad_drain'
    G['structural'] = G.get('structural', []) + ['quad_drain: ATT query/output per field to own-quadrant VM (new allocation, compiler record split, 0 area)']
    return G


def t_hc_per_quadrant(G):
    """STRUCTURAL: one HC arithmetic engine per quadrant (+3 x 1.0 mm2 estimate) instead of a single NE engine"""
    G = copy.deepcopy(G)
    base = G['nodes'].pop('hc_eng')
    for q in QS:
        n = dict(base, id=f'hc_eng_{q}', quadrant=q, provenance=base['provenance'] + ' | STRUCTURAL replicated per quadrant')
        G['nodes'][f'hc_eng_{q}'] = n
    for l in G['links']:
        if l['dst'] == 'hc_eng':
            q = l['src'][3:5]; l['dst'] = f'hc_eng_{q}'; l['id'] = f"{l['src']}>{l['dst']}:HC_ENG"
    G['structural'] = G.get('structural', []) + ['hc_per_quadrant: +3.0 mm2 (estimate), HC kernel join per quadrant']
    return G


def t_noatt(G):
    """OWNER 10:30 comparison: no dedicated ATT tiles; attention on the SMs (KV streamed from each SM's own stack like
    weights) + softmax on SU/SFU. Removes every att_* block and ATT link; adds KV bytes to PC->SM (and PHY->PC),
    scores/P round trips to the SU LG traffic, q/out to SM x-load/out. Link widths unchanged (no new ports priced)."""
    G = copy.deepcopy(G)
    TQ, TD = G['traffic_classes']['qwen'], G['traffic_classes']['ds']
    G['nodes'] = {k: v for k, v in G['nodes'].items() if not k.startswith('att_')}
    G['links'] = [l for l in G['links'] if not (l['src'].startswith('att_') or l['dst'].startswith('att_'))]
    sc = {'qwen': 8192 * 8 * 4 * 36 * 3, 'ds': 640 * 16 * 4 * 40 * 3}      # scores write + read + P write, FP32 (estimate)
    for l in G['links']:
        if l['cls'] in ('SM_HBM', 'HBM_K'):
            l['bytes_per_token']['qwen'] += TQ['KV_hbm'] / 32; l['bytes_per_token']['ds'] += TD['KV_hbm'] / 32
            l['provenance'] += ' | noatt: + KV/32 per SM'
        if l['cls'] == 'LG_SU':
            l['bytes_per_token']['qwen'] += sc['qwen'] / 32; l['bytes_per_token']['ds'] += sc['ds'] / 32
        if l['cls'] == 'SM_X':
            l['bytes_per_token']['qwen'] += TQ['ATT_q'] / 8; l['bytes_per_token']['ds'] += TD['ATT_q'] / 8
    G['structural'] = G.get('structural', []) + ['noatt: ATT tiles removed (-42.5 mm2 incl. estimates); attention on SM + SU/SFU softmax; cycle cost to be priced by H-ATTQ']
    return G


def t_npg4(G):
    """SW/SE engines with 4 bank-pair port groups (like NW/NE) instead of 5: tests whether the 5th group is needed
    once the bank slice is compact (slice areas re-split 4 ways)."""
    G = copy.deepcopy(G)
    for q in ('SW', 'SE'):
        for eng in ('su', 'sfu', 'hc'):
            tot = sum(G['nodes'][f'{eng}_{q}{k}']['area_mm2'] for k in range(5))
            del G['nodes'][f'{eng}_{q}4']
            side = (tot / 4) ** 0.5 * 1000
            for k in range(4):
                G['nodes'][f'{eng}_{q}{k}'].update(w=round(side, 3), h=round(side, 3), area_mm2=round(tot / 4, 4))
    out = []
    for l in G['links']:
        for end in ('src', 'dst'):
            v = l[end]
            if v[:-1] in ('su_SW', 'su_SE', 'sfu_SW', 'sfu_SE', 'hc_SW', 'hc_SE', 'quant_SW') and l['cls'] not in ('SU_CORE', 'SFU_CORE', 'HC_CORE'):
                if l['cls'].startswith(('LG_', 'QUANT')):
                    b = int(l['src'][-1]); l[end] = v[:-1] + str(b // 2)
        if l['cls'] in ('SU_CORE', 'SFU_CORE', 'HC_CORE') and l['src'].endswith('4') and l['src'][:-1] in ('su_SW', 'su_SE', 'sfu_SW', 'sfu_SE', 'hc_SW', 'hc_SE'):
            continue
        l['id'] = f"{l['src']}>{l['dst']}:{l['cls']}"
        out.append(l)
    G['links'] = out
    G['structural'] = G.get('structural', []) + ['npg4: SW/SE engines 4 bank-pair port groups (BANK_GROUP 0x33221100), no 5th group']
    return G


def skeleton_only(P, keep_prefix):
    return {k: v for k, v in P.items() if k.startswith(keep_prefix)}


def run(a):
    G = json.load(open(a.graph))
    ref = json.load(open(a.ref)) if a.ref and os.path.exists(a.ref) else None
    geo = a.geo
    fwd, pch = os.path.join(geo, a.fwd), os.path.join(geo, 'physical_assignments/native_PC_340cfd747.json')
    name, seed = a.cand, a.seed
    if a.die_h:
        F.set_die(a.die_h)
    for t in a.transform:
        G = {'quad_drain': t_quad_drain, 'hc_quad': t_hc_per_quadrant, 'noatt': t_noatt, 'npg4': t_npg4}[t](G)
    regions = F.quadrant_regions(G)
    regions.update(F.shoreline_regions(G))
    band = 1198.8 + F.HALO
    for k in G['nodes']:            # PHY row band reserved for PHY, PC, SerDes, endpoints
        if not k.startswith(('phy_', 'pc_', 'lk_', 'ep_')):
            r = regions.get(k, (0, 0, F.W_DIE, F.H_DIE))
            regions[k] = (r[0], max(r[1], band), r[2], min(r[3], F.H_DIE - band))
    groups = F.default_groups(G)
    log = open(os.path.join(a.out, f'{a.tag}.log'), 'w')
    t0 = time.time()
    if a.start == 'current':
        P = F.current(G, fwd, pch)
        imputed = {k for k, v in P.items() if v.get('imputed') or v.get('moved_by_legalize')}
    elif a.start == 'spine':
        P = F.arch_spine(G)
        P = F.complete(G, P, regions=regions)
        imputed = None
    elif a.start == 'template':
        kw = json.loads(a.template)
        P = F.arch_template(G, **kw)
        P = F.complete(G, P, regions=regions)
        imputed = None
    elif a.start == 'rtlmp':
        P = json.load(open(a.start_file))
        P = {k: v for k, v in P.items() if k in G['nodes']}
        P = F.legalize(G, F.complete(G, P, regions=regions), fixed={k for k in P if k.startswith('phy_')})
        imputed = None
    elif a.start == 'file':
        P = json.load(open(a.start_file))
        P = F.complete(G, {k: v for k, v in P.items() if k in G["nodes"]}, regions=regions)
        imputed = None
    if ref is None:
        m = F.score(G, P)
        ref = {k: m[k] for k in ('sum_bits_mm', 'traffic_mm_qwen', 'traffic_mm_ds', 'relay_flops')}
    if a.iters > 0:
        only = None
        if a.only == 'imputed':
            only = imputed
        elif a.only == 'nonskeleton':
            only = {k for k in G['nodes'] if not k.startswith(('phy_', 'pc_', 'sm_', 'lk_', 'vmb_'))}
        A = F.Annealer(G, P, ref, regions=regions, seed=seed, groups=groups)
        swap_only = ()
        if a.only == 'template':
            only = {k for k in G['nodes'] if not k.startswith(('phy_', 'pc_', 'sm_'))}
            swap_only = {k for k in G['nodes'] if k.startswith(('pc_', 'sm_'))}
        A.run(iters=a.iters, t0=a.t0, step0=a.step0, log=log, only=only, swap_only=swap_only)
        P = A.placement()
    fixedset = {k for k in P if k.startswith(('phy_', 'sm_', 'pc_', 'lk_'))} if a.only == 'template' else {k for k in P if k.startswith(('phy_', 'lk_'))}
    P = F.legalize(G, P, fixed=fixedset, regions=regions)
    m = F.score(G, P, ref)
    m['runtime_s'] = round(time.time() - t0, 1)
    m['candidate'] = name; m['seed'] = seed; m['start'] = a.start; m['transforms'] = a.transform; m['only'] = a.only; m['iters'] = a.iters
    m['structural'] = G.get('structural', [])
    m['area_mm2'] = round(sum(n['area_mm2'] for n in G['nodes'].values()), 3)
    m['die_h'] = F.H_DIE; m['die_mm2'] = round(F.W_DIE * F.H_DIE / 1e6, 2)
    m['attention'] = (G.get('attention') or {}).get('mode', 'att'); m['kv_home'] = (G.get('attention') or {}).get('kv_home')
    json.dump(P, open(os.path.join(a.out, f'{a.tag}.P.json'), 'w'))
    if a.save_ref:
        json.dump({k: m[k] for k in ('sum_bits_mm', 'traffic_mm_qwen', 'traffic_mm_ds', 'relay_flops')}, open(a.save_ref, 'w'), indent=1)
    mm = {k: v for k, v in m.items() if not k.startswith('_')}
    json.dump(mm, open(os.path.join(a.out, f'{a.tag}.metrics.json'), 'w'), indent=1, default=float)
    print(a.tag, 'J', round(m['J'], 4), 'bits_mm', round(m['sum_bits_mm']), 'tq', f"{m['traffic_mm_qwen']:.3e}", 'td', f"{m['traffic_mm_ds']:.3e}",
          'relay', int(m['relay_flops']), 'over500', int(m['bits_over_500']), 'fr', m['fixed_return_violations'], 'cut', m['worst_cut']['ratio'],
          'ov', m['overlaps'], 'out', m['outside'], f"{m['runtime_s']}s", file=log, flush=True)
    print(open(os.path.join(a.out, f'{a.tag}.log')).read().splitlines()[-1])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', required=True); ap.add_argument('--geo', required=True); ap.add_argument('--ref')
    ap.add_argument('--cand', required=True); ap.add_argument('--tag'); ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--start', default='current'); ap.add_argument('--start-file')
    ap.add_argument('--transform', action='append', default=[])
    ap.add_argument('--template', default='{}')
    ap.add_argument('--fwd', default='forward_D_geometry.json')
    ap.add_argument('--only', default=None); ap.add_argument('--iters', type=int, default=0)
    ap.add_argument('--t0', type=float, default=0.02); ap.add_argument('--step0', type=float, default=3000.0)
    ap.add_argument('--out', required=True)
    ap.add_argument('--die-h', type=float, default=None, help='compact outline height (um); default v15 25,980.528')
    ap.add_argument('--save-ref', default=None, help='write this run\'s raw metrics as the J reference')
    a = ap.parse_args()
    a.tag = a.tag or f'{a.cand}_s{a.seed}'
    os.makedirs(a.out, exist_ok=True)
    run(a)
