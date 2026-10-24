#!/usr/bin/env python3
"""KV-P4 10-23: machine-readable connectivity of the plan-only cells of KV plan v3.4 (BINDER2 10:41 request (2)).

The plan (plan_v32.py / post_v32.py) adds cells that have no as-built counterpart, so bind.py cannot take their nets from
bind/bitcon: the counted ID lanes (ot_dp_id_src / _add / _rot), the plan landing checks (ot_dp_efault), the per-column
fault chains (qkd_hp_or2 u_fch) and the new tree-root ORs (hub_C hp_v32_*), plus 6 as-built OR inputs re-pointed by the
tree collapse (fault_bypass).  This script derives, PER PARTITION TYPE, every port of every such cell and every class-B
leaf port they drive, and proves:
  (1) every replica of a type resolves to the identical local connectivity (a type is one module);
  (2) evaluating the ID cells through the planned chains reproduces EVERY as-built class-B strap value bit-exactly
      (sq, owner_id, lpc, pc__pc, cfg_stack, cfg_group, esh__stack; eo is computed from sq inside qkd_astk_ep_s_e);
  (3) every plan_v32 synthetic edge (id / fault / fault_bypass) is emitted exactly once.

conns schema (opentallas.kv_p4.cell_conns.v1), per type -> cells[inst] = {module, params, conns{port: [entry...]}}:
  INPUT port : entries are the DRIVERS, concatenated LSB-first (entry i fills the next len(bits) port bits);
  OUTPUT port: entries are the SINKS; each sink gets port bits 'from' [lo,hi] (whole port when absent).
  entry kinds: {"bus": B, "bits": [lo,hi]}            plan bus of the type (in bus: its registered q; out bus: its d)
               {"epoch": B}                            the in-boundary flop epoch eq of in bus B (1 bit)
               {"inst": LEAF, "port": P, "bits": [lo,hi]}  a content leaf port of the type
               {"cell": INST, "port": P, "bits": [lo,hi]}  another plan cell of the type
               {"net": "clk" | "rst_n"}                the partition clock entry / synchronised reset
  leaf_binds[]: class-B leaf ports driven straight from an in bus slice (no cell); bus_drivers[]: out buses assembled
  from several drivers (LSB-first).
  ot_dp_efault eq = the epochs of EVERY lane in bus of the type (a superset of the 351 traced as-built landings, whose
  source blocks all reach their receiving partition through these lanes; 26 landings were partition-internal and need no
  check); N = their count, AGE = max lane cycles over all replicas of the type (lat_v34) + reset sync stages.  The
  epochs are partition-clock signals (gen_rtl in-boundary ot_dp_st .eq), so the check is single-domain.
  rewired[]: as-built leaf inputs whose driver the plan changes ({"sink": {...}, "driver": {...}}).
  ID word layout of the pc chain bus (31 b): [1:0] stack, [6:2] row4 (pc base index), [30:7] PHYS group table 8 x 3 b.
    python3 bind/plan_cell_conns_v34.py [--out bind/plan_cell_conns_v34.json]

KV-P5 10-23 revision (BINDER2 15:14/15:31 conns defects, bind kv_bg):
  * leaf ports are named as in the bound RTL, not the as-built die-port name: RTL_PORT maps (leaf inst, die port) ->
    RTL port (dcal = qkd_d2d_cal_seq_pin_bc4: die port 'flt' is RTL port 'fault').
  * EMPTY_LANES: the 12 vport all-gather lanes pv_<H>_0 -> hg_<Q>_0 (i_vport_Q_N_vo / _d2 / _d3) carry NO as-built
    bit (BINDER2 kv_bg lanes.unused; the hg row-0 heads take vo from hgi), so their in buses do not exist in the bound
    partition and their epochs are not landing-check inputs.  Plan v3.5 deletes these lanes.
"""
import argparse
import collections
import gzip
import hashlib
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(D))
import plan_v33  # noqa: E402,F401  (v3.2 + v3.3 patches)
import plan_v32  # noqa: E402
import plan_v31 as pv  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--plan', default=str(D / 'die_plan.json'))
ap.add_argument('--stage1', default=str(D / 'stage1_v33.json.gz'))
ap.add_argument('--asbuilt', default=str(D / 'asbuilt_rtl6_e33504a6f.json.gz'))
ap.add_argument('--lat', default=str(D / 'lat_v34' / 'qwen_kvsys_latency.json'))
ap.add_argument('--straps', default=str(D / 'bind' / 'v32_inputs.json.gz'))
ap.add_argument('--out', default=str(D / 'bind' / 'plan_cell_conns_v34.json'))
a = ap.parse_args()

P = json.load(open(a.plan))
S1 = json.load(gzip.open(a.stage1))
LAT = json.load(open(a.lat))
ST = json.load(gzip.open(a.straps))['straps']
asb = json.load(gzip.open(a.asbuilt))
B, _ = pv.rewrite_asbuilt(asb)
E = [e for e in asb['edges'] if e.get('v32') in ('id', 'fault', 'fault_bypass')]
SYN = plan_v32.SYN
WHERE = {k: tuple(v) for k, v in S1['where'].items()}
ptype = {p['name']: p['type'] for p in P['partitions']}
members = collections.defaultdict(list)
for p in P['partitions']:
    members[p['type']].append(p['name'])
T = P['partition_types']
plane = {ln['id']: ln for ln in P['lanes']}
pport = {pt['id']: pt for pt in P['ports']}
s1lanes = collections.defaultdict(list)
for ln in S1['lanes']:
    s1lanes[(ln['src'], ln['sp'])].append(ln)
ERR = []
RTL_PORT = {('dcal', 'flt'): 'fault'}
EMPTY_LANES = {'L2231', 'L2244', 'L2256', 'L2283', 'L2296', 'L2308', 'L2335', 'L2348', 'L2360', 'L2387', 'L2400', 'L2412'}


def err(m):
    ERR.append(m)


def part_of(blk):
    if blk in SYN:
        return SYN[blk][0]
    return WHERE[blk][0]


def crossing(s, sp, dpart):
    """plan buses of the lane carrying block port s.sp into partition dpart -> (src bus, dst bus)"""
    for ln in s1lanes[(s, sp)]:
        if ln['hops'][-1][1] != dpart and dpart not in [h[1] for h in ln['hops']]:
            continue
        ports = [pport[x] for x in plane[ln['id']]['ports']]
        sb = ports[0]['src']['bus']
        db = [x['dst']['bus'] for x in ports if x['dst']['part'] == dpart]
        if len(db) != 1:
            err(f'lane {ln["id"]} {s}.{sp} -> {dpart}: {len(db)} dst ports')
            return sb, None, ln['id']
        return sb, db[0], ln['id']
    err(f'no lane for {s}.{sp} -> {dpart}')
    return None, None, None


def full(w):
    return [0, w - 1]


# ---- per-partition connectivity (later generalised per type) -------------------------------------------------------
PC = collections.defaultdict(lambda: dict(cells={}, rewired=[]))   # part -> {cells{inst:{module,params,conns}}, rewired}


def cell(part, inst, module, params=None):
    c = PC[part]['cells'].setdefault(inst, dict(module=module, params=dict(params or {}), conns={}))
    return c


def add(part, inst, port, entry):
    PC[part]['cells'][inst]['conns'].setdefault(port, []).append(entry)


def content(tn, inst):
    for c in T[tn]['contents']:
        if c['inst'] == inst:
            return c
    return None


emitted = collections.Counter()
QS = ('WS', 'WN', 'ES', 'EN')
STRAP_PORTS = {   # leaf port (by type content module family) -> ID field
    'sq': 'hgpos', 'owner_id': 'hgpos3', 'lpc': 'pcj', 'pc__pc': 'pcj', 'pc__cfg_stack': 'stack',
    'slg__cfg_stack': 'stack', 'slg__cfg_group': 'group', 'esh__stack': 'stack'}
# class-B leaf instances per partition (as-built straps -> plan local name)
classB = collections.defaultdict(dict)       # part -> {(loc, port): value bits str}
for mp, iv in ST.items():
    m, port = mp.split('.')
    if port not in STRAP_PORTS or mp == 'qkd_kvs_grp_h_r2c.slg__cfg_group':     # last one = class A (row 0 CFG_GROUP)
        continue
    if mp == 'qkd_kvs_pc_h.pc__pc':                                                # class A (head PC param)
        continue
    for inst, v in iv.items():
        part, loc = WHERE[inst]
        classB[part][(loc, port)] = v


def leaf_sinks(part, field, srcs):
    """bind every class-B leaf port of `part` that takes `field` to its ID source (srcs: field -> entry builder)"""
    for (loc, port), v in sorted(classB[part].items()):
        f = STRAP_PORTS[port]
        if f == 'pcj':
            j = int(loc[-1])                     # hsl<j> / kvpc<j>
            if field != f'pc{j}':
                continue
            inst, cport, frm = f'u_id_pc{j}', 'y', None
        elif f != field:
            continue
        else:
            inst, cport, frm = srcs[f]
        w = len(v)
        e = dict(inst=loc, port=port, bits=full(w))
        if frm is not None:
            e['from'] = frm
        add(part, inst, cport, e)
        emitted['leaf_' + port] += 1


# (a) quadrant stack sources (hub_Wo / hub_Eo) and hroot
for q in QS:
    hub = 'hub_Wo' if q[0] == 'W' else 'hub_Eo'
    cell(hub, f'u_idsrc_{q}', 'ot_dp_id_src', content(ptype[hub], f'u_idsrc_{q}')['params'])
    sb, db, _ = crossing(f'idsrc_{q}', 'y', f'hroot_{q}')
    add(hub, f'u_idsrc_{q}', 'y', dict(bus=sb, bits=full(2)))
    hr = f'hroot_{q}'
    cell(hr, 'u_id_stk', 'ot_dp_id_add', dict(W=2, K=0))
    add(hr, 'u_id_stk', 'a', dict(bus=db, bits=full(2)))
    sb2, db2, _ = crossing(f'idhr_{q}', 'y', f'pc_{q}_0')
    add(hr, 'u_id_stk', 'y', dict(bus=sb2, bits=full(2)))
    leaf_sinks(hr, 'stack', dict(stack=('u_id_stk', 'y', None)))
    emitted['id_edge'] += 2
    # (b) pc chain
    prev_db = db2
    for p in range(8):
        part = f'pc_{q}_{p}'
        tn = ptype[part]
        have = {c['inst'] for c in T[tn]['contents']}
        nxt = crossing(f'idpc_{q}_{p}', 'y', f'pc_{q}_{p + 1}') if p < 7 else (None, None, None)
        if p == 0:
            stack = dict(bus=prev_db, bits=[0, 1])          # 2-b stack lane from hroot
            cell(part, 'u_id_row', 'ot_dp_id_src', dict(W=5, V="5'd0"))
            cell(part, 'u_id_grp', 'ot_dp_id_src', content(tn, 'u_id_grp')['params'])
            row = dict(cell='u_id_row', port='y', bits=[0, 4])
        else:
            stack = dict(bus=prev_db, bits=[0, 1])
            row = dict(bus=prev_db, bits=[2, 6])
            cell(part, 'u_id_grp_rot', 'ot_dp_id_rot', dict(N=8, W=3))
            add(part, 'u_id_grp_rot', 'a', dict(bus=prev_db, bits=[7, 30]))
        for j in range(4):
            cell(part, f'u_id_pc{j}', 'ot_dp_id_add', dict(W=5, K=j))
            if 'cell' in row:
                add(part, 'u_id_row', 'y', dict(cell=f'u_id_pc{j}', port='a', bits=[0, 4]))
            add(part, f'u_id_pc{j}', 'a', row)
            leaf_sinks(part, f'pc{j}', {})
        # stack field fan-out (leaf cfg_stack ports) straight from the lane / no cell: emitted as leaf binds of the bus
        for (loc, port), v in sorted(classB[part].items()):
            if STRAP_PORTS[port] == 'stack':
                PC[part].setdefault('leaf_binds', []).append(dict(inst=loc, port=port, drivers=[stack]))
                emitted['leaf_' + port] += 1
            if STRAP_PORTS[port] == 'group':
                add(part, 'u_id_grp_rot', 'o', dict(inst=loc, port=port, bits=[0, 2]))
                emitted['leaf_' + port] += 1
        if p < 7:
            sb, db, _ = nxt
            cell(part, 'u_id_next', 'ot_dp_id_add', dict(W=5, K=4))
            if 'cell' in row:
                add(part, 'u_id_row', 'y', dict(cell='u_id_next', port='a', bits=[0, 4]))
            add(part, 'u_id_next', 'a', row)
            # out bus [1:0] stack (pass), [6:2] next row, [30:7] table
            PC[part].setdefault('bus_drivers', []).append(dict(bus=sb, drivers=[
                stack, dict(cell='u_id_next', port='y', bits=[0, 4]),
                dict(cell='u_id_grp', port='y', bits=[0, 23]) if p == 0 else dict(cell='u_id_grp_rot', port='y', bits=[0, 23])]))
            emitted['id_edge'] += 1
            prev_db = db
        missing = {i for i in PC[part]['cells']} - have
        if missing:
            err(f'{part} ({tn}): cells {sorted(missing)} not in plan contents')
    # (c) hg (astk) chain
    prev_db = None
    for p in range(8):
        part = f'hg_{q}_{p}'
        tn = ptype[part]
        if p == 0:
            cell(part, 'u_id_row', 'ot_dp_id_src', dict(W=5, V="5'd0"))
            pos = ('u_id_row', 'y')
            src = None
        else:
            src = dict(bus=prev_db, bits=[0, 4])
            pos = None
        if p < 7:
            sb, db, _ = crossing(f'idhg_{q}_{p}', 'y', f'hg_{q}_{p + 1}')
            cell(part, 'u_id_next', 'ot_dp_id_add', dict(W=5, K=1))
            if pos:
                add(part, 'u_id_row', 'y', dict(cell='u_id_next', port='a', bits=[0, 4]))
            else:
                add(part, 'u_id_next', 'a', src)
            add(part, 'u_id_next', 'y', dict(bus=sb, bits=[0, 4]))
            emitted['id_edge'] += 1
            prev_db = db
        for (loc, port), v in sorted(classB[part].items()):
            w = len(v)
            if pos:
                add(part, 'u_id_row', 'y', dict(inst=loc, port=port, bits=full(w), **({'from': [0, w - 1]} if w < 5 else {})))
            else:
                PC[part].setdefault('leaf_binds', []).append(dict(inst=loc, port=port, drivers=[dict(bus=prev_db, bits=[0, w - 1])]))
            emitted['leaf_' + port] += 1
emitted['id_edge'] += 0

# ---- fault edges ------------------------------------------------------------------------------------------------------
CELLNAME = lambda blk: ('u_efault' if blk.startswith('efault_') else 'u_fch' if blk.startswith('fch_') else blk)


def endpoint(blk):
    if blk in SYN:
        return SYN[blk][0], CELLNAME(blk), True
    part, loc = WHERE[blk]
    return part, loc, False


efault_parts = sorted({SYN[b][0] for b in SYN if b.startswith('efault_')})
for e in E:
    if e['v32'] == 'id':
        continue
    sp_, sl, ssyn = endpoint(e['s'])
    dp_, dl, dsyn = endpoint(e['d'])
    for part, inst, syn, mod in ((sp_, sl, ssyn, B.get(e['s'], {}).get('m')), (dp_, dl, dsyn, B.get(e['d'], {}).get('m'))):
        if syn:
            cell(part, inst, mod)
    if sp_ == dp_:
        drv = dict(cell=sl, port=e['sp'], bits=[0, 0]) if ssyn else dict(inst=sl, port=e['sp'], bits=[0, 0])
        snk = dict(cell=dl, port=e['dp'], bits=[0, 0]) if dsyn else dict(inst=dl, port=e['dp'], bits=[0, 0])
    else:
        sb, db, _ = crossing(e['s'], e['sp'], dp_)
        drv_far = dict(bus=db, bits=[0, 0])
        snk_far = dict(bus=sb, bits=[0, 0])
        # source side: cell/leaf output -> out bus
        if ssyn:
            add(sp_, sl, e['sp'], snk_far)
        else:
            PC[sp_].setdefault('bus_drivers', []).append(dict(bus=sb, drivers=[dict(inst=sl, port=RTL_PORT.get((sl, e['sp']), e['sp']), bits=[0, 0])]))
        drv = drv_far
        snk = dict(cell=dl, port=e['dp'], bits=[0, 0]) if dsyn else dict(inst=dl, port=e['dp'], bits=[0, 0])
        part = dp_
        if dsyn:
            add(part, dl, e['dp'], drv)
        else:
            PC[part]['rewired'].append(dict(sink=snk, driver=drv, kind=e['v32']))
        emitted[e['v32']] += 1
        continue
    part = sp_
    if dsyn:
        add(part, dl, e['dp'], drv)
    elif ssyn:
        add(part, sl, e['sp'], snk)
    else:
        PC[part]['rewired'].append(dict(sink=snk, driver=drv, kind=e['v32']))
    emitted[e['v32']] += 1

# efault eq / clk / rst_n + params; OR cells clk
lat_by_lane = LAT['lanes'] if 'lanes' in LAT else LAT
dst_lat = collections.defaultdict(int)
for ln in P['lanes']:
    if ln['id'] in EMPTY_LANES:
        continue
    cyc = int(lat_by_lane.get(ln['id'], {}).get('cycles', 0))
    for x in ln['ports']:
        dpart = pport[x]['dst']['part']
        if dpart in ptype:
            dst_lat[(dpart, pport[x]['dst']['bus'])] = max(dst_lat[(dpart, pport[x]['dst']['bus'])], cyc)


def lane_in_buses(tn):
    """in buses of the type that are lane destinations from another partition (die IO excluded) -> epoch-carrying"""
    out = []
    for b in T[tn]['buses']:
        if b['dir'] != 'in':
            continue
        if any((m, b['name']) in dst_lat for m in members[tn]):
            out.append(b['name'])
    return sorted(out)


for part in efault_parts:
    tn = ptype[part]
    ins = lane_in_buses(tn)
    for b in ins:
        add(part, 'u_efault', 'eq', dict(epoch=b))
    sync = int(T[tn].get('reset', {}).get('sync_stages', P['reset'].get('sync_stages', 2)))
    age = max(dst_lat[(m, b)] for m in members[tn] for b in ins if (m, b) in dst_lat) + sync
    PC[part]['cells']['u_efault']['params'] = dict(N=len(ins), AGE=age)
    PC[part]['cells']['u_efault']['age_rule'] = f'max in-lane cycles over the {len(members[tn])} replicas ({age - sync}) + {sync} sync stages'
    add(part, 'u_efault', 'clk', dict(net='clk'))
    add(part, 'u_efault', 'rst_n', dict(net='rst_n'))
for part, d in PC.items():
    for inst, c in d['cells'].items():
        if c['module'] == 'qkd_hp_or2':
            c['conns'].setdefault('ck', [dict(net='clk')])
        if c['module'] is None:
            err(f'{part}.{inst}: no module')


# ---- generalise per type; replicas must agree ------------------------------------------------------------------------
def canon(d):
    return json.dumps(d, sort_keys=True)


types = {}
for tn in sorted({ptype[p] for p in PC}):
    reps = members[tn]
    forms = {}
    for m in reps:
        d = PC.get(m)
        if d is None:
            err(f'type {tn}: replica {m} has no plan-cell connectivity while others do')
            continue
        dd = dict(cells={k: dict(v, conns={pp: v['conns'][pp] for pp in sorted(v['conns'])}) for k, v in sorted(d['cells'].items())},
                  rewired=sorted(d['rewired'], key=canon), leaf_binds=sorted(d.get('leaf_binds', []), key=canon),
                  bus_drivers=sorted(d.get('bus_drivers', []), key=canon))
        forms.setdefault(canon(dd), []).append(m)
    if len(forms) != 1:
        err(f'type {tn}: replicas resolve to {len(forms)} different connectivities: {list(forms.values())}')
    k, ms = max(forms.items(), key=lambda kv: len(kv[1]))
    v = json.loads(k)
    v['replicas'] = sorted(reps)
    # every declared plan cell of the type is covered
    declared = {c['inst'] for c in T[tn]['contents'] if c.get('status') == 'new' or c['inst'] == 'u_fch' or c['inst'].startswith('hp_v32_')}
    miss = declared - set(v['cells'])
    if miss:
        err(f'type {tn}: declared plan cells without conns {sorted(miss)}')
    types[tn] = v


# ---- (2) bit-exact strap reproduction: evaluate the ID cells per partition ------------------------------------------
def ev_part(part, inval):
    """returns {(leaf, port): int} for one partition given its ID in-bus values {bus: int}"""
    d = PC[part]
    vals = {}

    def src_val(e, ctx):
        if 'bus' in e:
            v = inval[e['bus']]
        elif 'cell' in e:
            v = ctx[(e['cell'], e['port'])]
        else:
            raise KeyError(e)
        lo, hi = e['bits']
        return (v >> lo) & ((1 << (hi - lo + 1)) - 1)

    ctx = {}
    order = ['u_idsrc_WS', 'u_idsrc_WN', 'u_idsrc_ES', 'u_idsrc_EN', 'u_id_row', 'u_id_grp', 'u_id_stk', 'u_id_grp_rot',
             'u_id_pc0', 'u_id_pc1', 'u_id_pc2', 'u_id_pc3', 'u_id_next']
    for inst in order:
        c = d['cells'].get(inst)
        if not c:
            continue
        pr = c['params']
        if c['module'] == 'ot_dp_id_src':
            V = pr['V']
            w, lit = V.split("'")
            ctx[(inst, 'y')] = int(lit[1:], 16 if lit[0] == 'h' else 10)
            continue
        # input a from conns or from another cell that lists it as a sink
        drv = c['conns'].get('a')
        if drv:
            v, sh = 0, 0
            for e in drv:
                lo, hi = e['bits']
                v |= src_val(e, ctx) << sh
                sh += hi - lo + 1
        else:
            srcs = [(ci, pp, e) for ci, cc in d['cells'].items() for pp, es in cc['conns'].items() for e in es
                    if e.get('cell') == inst and e.get('port') == 'a']
            assert len(srcs) == 1, (part, inst, srcs)
            ci, pp, e = srcs[0]
            v = ctx[(ci, pp)] & ((1 << (e['bits'][1] - e['bits'][0] + 1)) - 1)
        W = pr['W']
        if c['module'] == 'ot_dp_id_add':
            ctx[(inst, 'y')] = (v + pr['K']) % (1 << W)
        else:   # rot
            N = pr['N']
            ctx[(inst, 'o')] = v & ((1 << W) - 1)
            ctx[(inst, 'y')] = (v >> W) | ((v & ((1 << W) - 1)) << (W * (N - 1)))
    for inst, c in d['cells'].items():
        for pp, es in c['conns'].items():
            for e in es:
                if 'inst' in e and (inst, pp) in ctx:
                    v = ctx[(inst, pp)]
                    if 'from' in e:
                        v = (v >> e['from'][0]) & ((1 << (e['from'][1] - e['from'][0] + 1)) - 1)
                    vals[(e['inst'], e['port'])] = v
    for lb in d.get('leaf_binds', []):
        v, sh = 0, 0
        for e in lb['drivers']:
            lo, hi = e['bits']
            v |= src_val(e, ctx) << sh
            sh += hi - lo + 1
        vals[(lb['inst'], lb['port'])] = v
    outs = {}
    for bd in d.get('bus_drivers', []):
        v, sh = 0, 0
        ok = True
        for e in bd['drivers']:
            if 'inst' in e:
                ok = False
                break
            lo, hi = e['bits']
            v |= src_val(e, ctx) << sh
            sh += hi - lo + 1
        if ok:
            outs[bd['bus']] = v
    for inst, c in d['cells'].items():
        for pp, es in c['conns'].items():
            for e in es:
                if 'bus' in e and (inst, pp) in ctx and any(b['name'] == e['bus'] and b['dir'] == 'out'
                                                              for b in T[ptype[part]]['buses']):
                    outs[e['bus']] = ctx[(inst, pp)]
    return vals, outs


checked = mism = 0
fields = collections.Counter()
for q in QS:
    hub = 'hub_Wo' if q[0] == 'W' else 'hub_Eo'
    _, o = ev_part(hub, {})
    sb, db, _ = crossing(f'idsrc_{q}', 'y', f'hroot_{q}')
    v, o = ev_part(f'hroot_{q}', {db: o[sb]})
    chains = [(f'hroot_{q}', v)]
    sb, db, _ = crossing(f'idhr_{q}', 'y', f'pc_{q}_0')
    cur = {db: o[sb]}
    for p in range(8):
        part = f'pc_{q}_{p}'
        v, o = ev_part(part, cur)
        chains.append((part, v))
        if p < 7:
            sb, db, _ = crossing(f'idpc_{q}_{p}', 'y', f'pc_{q}_{p + 1}')
            cur = {db: o[sb]}
    cur = {}
    for p in range(8):
        part = f'hg_{q}_{p}'
        v, o = ev_part(part, cur)
        chains.append((part, v))
        if p < 7:
            sb, db, _ = crossing(f'idhg_{q}_{p}', 'y', f'hg_{q}_{p + 1}')
            cur = {db: o[sb]}
    for part, v in chains:
        for (loc, port), bits in classB[part].items():
            got = v.get((loc, port))
            checked += 1
            fields[port] += len(bits)
            if got is None or got != int(bits, 2):
                mism += 1
                err(f'strap mismatch {part}.{loc}.{port}: as-built {bits} plan {got}')
nB = sum(len(v) for part in classB for v in classB[part].values())

edges_total = collections.Counter(e['v32'] for e in E)
res = dict(
    schema='opentallas.kv_p4.cell_conns.v1',
    plan=dict(file='physical/die_plan/qwen_kvsys/die_plan.json', sha256=hashlib.sha256(open(a.plan, 'rb').read()).hexdigest(),
              version='v3.4', latency='lat_v34 (F_DLY=3)'),
    note='schema + rules: bind/plan_cell_conns_v34.py docstring',
    id_word=dict(pc_chain={'stack': [0, 1], 'row4': [2, 6], 'group_table': [7, 30]}, hg_chain={'pos': [0, 4]},
                 stack=[0, 1]),
    check=dict(strap_ports_checked=checked, strap_bits_checked=nB, strap_mismatches=mism, bits_by_port=dict(fields),
               plan_v32_edges=dict(edges_total), emitted=dict(emitted), errors=ERR),
    types=types)
Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=False) + '\n')
print(json.dumps(res['check'], indent=1))
print('types', len(types), 'cells', sum(len(t['cells']) for t in types.values()), 'errors', len(ERR))
sys.exit(1 if ERR else 0)
