#!/usr/bin/env python3
"""KV-P3 10-23: KV die plan v3.2 = v3.1 + the generated-die blockers (bind/blockers_v31.json) turned into PLAN objects.

Importing this module patches plan_v31.rewrite_asbuilt / assign_blocks, so every v3.1 script (plan build, emit, census
rows, coverage, L1 cores) sees the v3.2 as-built view:

 (3) PV result T-chain: the 128 qkd_rlyi_258s MUX relays (b <= s ? y : a, registered) are LEAVES, not pass cells.  Each
     relay is a content of the pv partition that holds its local source (y = that row's PV slice result); the chain
     relay -> relay (258 b) and the select s (from the pvw wide ctl in hub_C, through the as-built DL pass relays) are
     edges taken from the bit-level as-built connectivity (bind/bitcon.py: relays are logic there).  The v3.1 'gather'
     rows (slice result -> RH as one select-merged wire) disappear: the chain crossings are ordinary p2p lanes, and the
     per-row select lanes hub_C -> pv rows (absent in v3.1, the census undercounted them) are planned.
 (2) Position IDs that differ between replicas of one partition type become counted ID lanes (no per-instance straps):
     - pc chain per quadrant: hub_Wo/hub_Eo (singletons: the only place a position constant originates, ot_dp_id_src)
       -> hroot_Q (stack id 2 b) -> pc_Q_0 -> ... -> pc_Q_7: {stack 2 b, row4 5 b, PHYS group table 8 x 3 b} = 31 b;
       pc_Q_p binds kvpc pc__pc = row4 + j, hsl lpc = row4 + j (ot_dp_id_add), slg cfg_group = table[0]
       (ot_dp_id_rot), every cfg_stack = stack; hroot esh__stack = stack.
     - astk chain per quadrant: hg_Q_p -> hg_Q_p+1, 5 b = chain position p (ep sq, owner_id; eo computed from sq in the
       qkd_astk_ep_s_e variant); row 0 starts from its type parameter.
     Type-constant straps become content parameters (emit post-pass, see post_v32.py) and chain-head inputs become
     head-form leaf variants (no port): both RTL on claude/kv-p3-rtl-1023.
 (4) Landing faults: the plan removes the qkd_landsh* landing cells, whose fault outputs fed 356 inputs of the hub
     fault OR tree; see fault_tree(): one plan landing check per receiving partition, column OR chains, re-derived tree.
"""
import collections
import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_v31 as pv  # noqa: E402

DATA = HERE / 'bind' / 'v32_inputs.json.gz'      # relays (bitcon conns), landing faults, strap values (bind/prep_v32.py)
QS = ('WS', 'WN', 'ES', 'EN')
STACK = dict(WS=0, WN=1, ES=2, EN=3)
ID_PC_W = 2 + 5 + 8 * 3
ID_HG_W = 5
_orig_rewrite, _orig_assign = pv.rewrite_asbuilt, pv.assign_blocks
SYN = {}                                          # synthetic block -> (partition, local name)


def _ranges(ix):
    return pv.v1_ranges(set(ix))


def _blk(B, n, m, part, loc):
    B[n] = dict(m=m, x=0.0, y=0.0, w=8.64, h=8.64, syn=True)
    SYN[n] = (part, loc)


def rewrite_asbuilt(asb):
    B, moved = _orig_rewrite(asb)
    if asb.get('_v32'):
        return B, moved
    D = json.load(gzip.open(DATA))
    E = asb['edges']
    # ---- (3) relays as leaves
    rl = D['relays']
    fed = {(c['d'], c['dp']) for c in D['relay_conns'] if c['s'] in rl and c['d'] not in rl}
    E[:] = [e for e in E if (e['d'], e['dp']) not in fed]
    for n, r in rl.items():
        _blk(B, n, 'qkd_rlyi_258s', r['part'], 'pv__' + r['loc'])
    for c in D['relay_conns']:
        src = [a for a, _ in c['pairs']]
        E.append(dict(s=c['s'], sp=c['sp'], d=c['d'], dp=c['dp'], bits=len(c['pairs']), stages=0, n_stage_insts=0,
                      sbits=_ranges(src), v32='relay'))
    # ---- (2) counted ID lanes
    for q in QS:
        hub = 'hub_Wo' if q[0] == 'W' else 'hub_Eo'
        _blk(B, f'idsrc_{q}', 'ot_dp_id_src', hub, f'u_idsrc_{q}')
        _blk(B, f'idhr_{q}', 'kvp_id_hroot', f'hroot_{q}', 'u_id')
        E.append(dict(s=f'idsrc_{q}', sp='y', d=f'idhr_{q}', dp='a', bits=2, stages=0, n_stage_insts=0,
                      sbits=[[0, 1]], v32='id'))
        for p in range(8):
            _blk(B, f'idpc_{q}_{p}', 'kvp_id_pc', f'pc_{q}_{p}', 'u_id')
            _blk(B, f'idhg_{q}_{p}', 'kvp_id_hg', f'hg_{q}_{p}', 'u_id')
        E.append(dict(s=f'idhr_{q}', sp='y', d=f'idpc_{q}_0', dp='a', bits=2, stages=0, n_stage_insts=0,
                      sbits=[[0, 1]], v32='id'))
        for p in range(7):
            E.append(dict(s=f'idpc_{q}_{p}', sp='y', d=f'idpc_{q}_{p + 1}', dp='a', bits=ID_PC_W, stages=0,
                          n_stage_insts=0, sbits=[[0, ID_PC_W - 1]], v32='id'))
            E.append(dict(s=f'idhg_{q}_{p}', sp='y', d=f'idhg_{q}_{p + 1}', dp='a', bits=ID_HG_W, stages=0,
                          n_stage_insts=0, sbits=[[0, ID_HG_W - 1]], v32='id'))
    # ---- (4) landing faults -> plan landing checks + per-column fault chains; the hub OR tree is re-derived
    fault_tree(asb, B, D['landing_faults'])
    asb['_v32'] = True
    return B, moved


FT = {}                                           # fault-tree rework report


def fault_tree(asb, B, lf):
    """Every receiving partition D of a removed landing gets ONE plan landing check efault_D (ot_dp_efault over its
    in-lane epochs, sticky).  Row partitions chain their checks toward the centre with one registered OR per partition
    (qkd_hp_or2, the as-built OR leaf): hg_Q_7 -> .. -> hg_Q_0 -> hub; pc_Q_7 -> .. -> pc_Q_0 -> hroot_Q -> hub;
    pv_H_7 -> .. -> pv_H_0 -> hub (a row without a check is crossed as feedthrough).  The as-built hub OR tree
    (qkd_hp_or2 leaves) loses its 356 landing-fed inputs: a leaf with no remaining input is removed, a leaf with one is
    bypassed (iterated), and the chain heads + hub-local checks join the tree root through new OR leaves in the root's
    partition.  Fault latency changes (health flag, sticky; no static-schedule term)."""
    E = asb['edges']
    Ds = sorted({f['dst_parts'][0] for f in lf})
    FT['checks'] = {d: sum(1 for f in lf if f['dst_parts'][0] == d) for d in Ds}
    for d in Ds:
        _blk(B, f'efault_{d}', 'ot_dp_efault', d, 'u_efault')
    heads = []

    def chain(parts):
        """parts ordered tail -> head; returns the head output (block, port)"""
        prev = None
        for p in parts:
            own = (f'efault_{p}', 'fault') if p in Ds else None
            if prev is None:
                prev = own
                continue
            if own is None:
                continue                        # feedthrough row
            _blk(B, f'fch_{p}', 'qkd_hp_or2', p, 'u_fch')
            E.append(dict(s=prev[0], sp=prev[1], d=f'fch_{p}', dp='b', bits=1, stages=0, n_stage_insts=0,
                          sbits=[[0, 0]], v32='fault'))
            E.append(dict(s=own[0], sp=own[1], d=f'fch_{p}', dp='a', bits=1, stages=0, n_stage_insts=0,
                          sbits=[[0, 0]], v32='fault'))
            prev = (f'fch_{p}', 'q')
        return prev
    for q in QS:
        heads.append(chain([f'hg_{q}_{k}' for k in range(7, -1, -1)]))
        heads.append(chain([f'pc_{q}_{k}' for k in range(7, -1, -1)] + [f'hroot_{q}']))
    for h in 'SN':
        heads.append(chain([f'pv_{h}_{k}' for k in range(7, -1, -1)]))
    used = {p for q in QS for p in [f'hg_{q}_{k}' for k in range(8)] + [f'pc_{q}_{k}' for k in range(8)] + [f'hroot_{q}']}
    used |= {f'pv_{h}_{k}' for h in 'SN' for k in range(8)}
    heads += [(f'efault_{d}', 'fault') for d in Ds if d not in used]
    heads = [h for h in heads if h]
    assert set(Ds) - used - {h[0][7:] for h in heads} == set(), 'a check without a path to the tree'
    # collapse the as-built OR tree
    hp = lambda n: B.get(n, {}).get('m') == 'qkd_hp_or2' and not B[n].get('syn')
    removed, bypassed = 0, 0
    while True:
        ins = collections.defaultdict(list)
        outs = collections.defaultdict(list)
        for i, e in enumerate(E):
            if hp(e['d']) and e['dp'] in ('a', 'b'):
                ins[e['d']].append(i)
            if hp(e['s']) and e['sp'] == 'q':
                outs[e['s']].append(i)
        leaves = [n for n in B if hp(n)]
        dead = [n for n in leaves if len(ins[n]) == 0]
        one = [n for n in leaves if len(ins[n]) == 1]
        if not dead and not one:
            break
        drop = set()
        if dead:
            for n in dead:
                drop.update(outs[n])
                drop.update(i for i, e in enumerate(E) if e['d'] == n)     # its clock / reset
                del B[n]
                removed += 1
        else:
            n = one[0]
            src = E[ins[n][0]]
            for i in outs[n]:
                E.append(dict(E[i], s=src['s'], sp=src['sp'], v32='fault_bypass'))
                drop.add(i)
            drop.update(i for i, e in enumerate(E) if e['d'] == n)
            del B[n]
            bypassed += 1
        E[:] = [e for i, e in enumerate(E) if i not in drop]
    # the tree output (-> kvs_attn.ufh); combine its driver with the new heads through new OR leaves
    (oi, oe), = [(i, e) for i, e in enumerate(E) if e['d'] == 'kvs_attn' and e['dp'] == 'ufh']
    root_part = None
    acc = (oe['s'], oe['sp'])
    for k, h in enumerate(heads):
        n = f'hp_v32_{k}'
        _blk(B, n, 'qkd_hp_or2', 'hub_C', f'hp_v32_{k}')
        for dp, sv in (('a', acc), ('b', h)):
            E.append(dict(s=sv[0], sp=sv[1], d=n, dp=dp, bits=1, stages=0, n_stage_insts=0, sbits=[[0, 0]], v32='fault'))
        acc = (n, 'q')
    E[oi] = dict(oe, s=acc[0], sp=acc[1], v32='fault')
    FT.update(heads=[h[0] for h in heads], or_removed=removed, or_bypassed=bypassed,
              or_kept=sum(1 for n in B if hp(n)), or_new=len(heads),
              chain_ors=sum(1 for n in SYN if n.startswith('fch_')))


def assign_blocks(B):
    out = _orig_assign({k: v for k, v in B.items() if not v.get('syn')})
    out.update(SYN)
    return out


pv.rewrite_asbuilt = rewrite_asbuilt
pv.assign_blocks = assign_blocks

if __name__ == '__main__':
    sys.argv[0] = 'plan_v32.py'
    pv.main()
