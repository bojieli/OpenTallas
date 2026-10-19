#!/usr/bin/env python3
"""HBM-RTL5 2026-10-18 (coordinator 0fi): d4g host leaf map r2 -- SE / NE leaves re-hardened at NT21/NF30 and NT17/NF27 so
the six new E-quadrant targets of the d4g L1 layer and the two wbk_<E> faults report THROUGH their quadrant leaf.

    host_cfg_leaf_map_r2.py [--base results/arch/hbm_b_rtl1_host_1017/host_cfg_leaf_map_d4g.json]
                            [--out results/arch/hbm_rtl5_host_1018/host_cfg_leaf_map_d4g_r2.json]

Input = the r1 map (d4f-derived: 69 targets / 107 fault bits).  Output = the same map with
  leaves.SE / leaves.NE: master ot_hbm_host_cfg_leaf_{se,ne}2, kit hdie_host_cfg_leaf_{se,ne}_r2, NT/NF widened; the new
    status sources APPENDED to *_order as [k, null, 'inst.pin[0]', tgt] (k = r1 width + i; bits below unchanged), in
    F20 target-id order (x-load ctlx 101/103, DMA/write-back hb_dbk 105/107, refresh refcfg 128/129), the wbk_<E> fault
    (status only) last;
  join_d4g_r2: host_status at NT 75 / NF 115 = leaf outputs only, SW, SE, NW, NE, each leaf's bits in its order; TGTS
    for the 75 ready/active slots (r1 slots keep their target id, the new slots carry the new F20 ids).  GUARD 12 =
    8 + CFG_LAT 2 + ST_LAT 2 (+ the relay layer's ingress->leaf and leaf->join lane edges), as r1.
join_d4g (the GEN0 / d4f-index description the L1 layer checks GEN0 against) is kept unchanged.
"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QS = ('SW', 'SE', 'NW', 'NE')
# per E quadrant: (instance, F20 tgt or None, ready pin, active pin, fault pins) -- names as the d4g L1 layer creates them
NEW = {q: [(f'xl_{q}_ctl', {'SE': 101, 'NE': 103}[q], 'configured', 'active', ['fault']),
           (f'hb_dbk_{q}', {'SE': 105, 'NE': 107}[q], 'cp_configured', 'cp_active', ['cp_fault']),
           (f'refcfg_{q}', {'SE': 128, 'NE': 129}[q], 'ready', 'active', ['fault']),
           (f'wbk_{q}', None, None, None, ['fault'])] for q in ('SE', 'NE')}
R2 = {'SE': ('ot_hbm_host_cfg_leaf_se2', 'hdie_host_cfg_leaf_se_r2', 21, 30),
      'NE': ('ot_hbm_host_cfg_leaf_ne2', 'hdie_host_cfg_leaf_ne_r2', 17, 27)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', default=str(ROOT / 'results/arch/hbm_b_rtl1_host_1017/host_cfg_leaf_map_d4g.json'))
    ap.add_argument('--out', default=str(ROOT / 'results/arch/hbm_rtl5_host_1018/host_cfg_leaf_map_d4g_r2.json'))
    a = ap.parse_args()
    M = json.load(open(a.base))
    J = M['join_d4g']
    tg_r1 = int(J['TGTS'].split("'h")[1], 16)
    # r1 slot -> target id (r1 join order = leaf SW, SE, NW, NE)
    off, tgt_of = 0, {}
    for q in QS:
        for k in range(M['leaves'][q]['NT']):
            tgt_of[(q, k)] = (tg_r1 >> (8 * (off + k))) & 0xff
        off += M['leaves'][q]['NT']
    for q, new in NEW.items():
        lf = M['leaves'][q]
        mod, kit, nt, nf = R2[q]
        r = [x for x in new if x[1] is not None]
        assert lf['NT'] + len(r) == nt and lf['NF'] + sum(len(x[4]) for x in new) == nf, (q, lf['NT'], lf['NF'])
        k, kf = lf['NT'], lf['NF']
        for inst, tgt, rp, ap_, fps in new:
            if tgt is not None:
                lf['t_ready_order'].append([k, None, f'{inst}.{rp}[0]', tgt])
                lf['t_active_order'].append([k, None, f'{inst}.{ap_}[0]', tgt])
                tgt_of[(q, k)] = tgt
                k += 1
                lf['targets'].append(inst)
            else:
                lf['status_only_sources'].append(inst)
            for fp in fps:
                lf['t_fault_order'].append([kf, None, f'{inst}.{fp}[0]', tgt])
                kf += 1
        lf.update(master=mod, kit=kit, NT=nt, NF=nf)
        lf['r1'] = dict(master=mod[:-1], kit=kit.replace('_r2', '_r1'), NT=lf['NT'] - len(r), NF=lf['NF'] - sum(len(x[4]) for x in new))
    slots = [(q, k) for q in QS for k in range(M['leaves'][q]['NT'])]
    fslots = [(q, k) for q in QS for k in range(M['leaves'][q]['NF'])]
    tg = 0
    for j, s in enumerate(slots):
        tg |= tgt_of[s] << (8 * j)
    nt, nf = len(slots), len(fslots)
    M['join_d4g_r2'] = dict(
        note='host_status (d4g GEN1, r2 leaves): t_ready/t_active input j = leaf output slot t_ready_slots[j] = [quadrant, leaf bit]; '
             't_fault input j = t_fault_slots[j]; leaf outputs only (no direct target bits), SW, SE, NW, NE. GUARD 12 + lane relay edges '
             '(ingress->leaf + leaf->join), as r1. Earlier-layer direct slots (if any) follow the leaf block.',
        NT=nt, NF=nf, TGTS=f"{nt * 8}'h{tg:0{nt * 2}x}", GUARD=12, t_ready_slots=slots, t_fault_slots=fslots,
        new_slots=dict(t_ready=[j for j, s in enumerate(slots) if s[0] in NEW and s[1] >= M['leaves'][s[0]]['r1']['NT']],
                       t_fault=[j for j, s in enumerate(fslots) if s[0] in NEW and s[1] >= M['leaves'][s[0]]['r1']['NF']]))
    M['schema'] = 'opentallas.hbm_d4g.host_cfg_leaf_map.v2'
    M['basis'] = M['basis'] + ' + HBM-RTL5 r2 (SE NT21/NF30, NE NT17/NF27: d4g L1 new E targets through the leaves)'
    M['leaf_bind_note'] = (M['leaf_bind_note'] + ' r2: *_order rows [k, null, pin, tgt] are d4g-only sources (no d4f index); '
                           'host_status takes join_d4g_r2 (leaf outputs only).')
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(M, open(a.out, 'w'), indent=1)
    print(json.dumps(dict(out=a.out, NT=nt, NF=nf, widths={q: [M['leaves'][q]['NT'], M['leaves'][q]['NF']] for q in QS},
                          new_slots=M['join_d4g_r2']['new_slots'])))


if __name__ == '__main__':
    main()
