"""Repair measured pin-to-pin overreach using die-placed registered channel relays.

Freeze the die tool's current master pin assignment before adding relays, so a
shared master's face cannot move in response to the new neighbouring relay.
Never route through a leaf; failed placement remains an explicit plan defect.
"""
import json
import math
import os
import re
from pathlib import Path

# KVR-DERIVE 10-19 (QW-KVATTN2 finding 5): a relay this pass (or kv_bundle_eq / kv_k_rt_eq) adds is clocked by the clock of
# the LAUNCHING pin's register, never by "the first clock trunk touching the source instance" (that put the K / V
# response relays krs / pvrs, slg o_pc and kvpc o_next on n_clk_hbm: unsynchronised core -> HBM -> core resampling).
# Launch domain per tile port = the elaborated-RTL measurement (kvs_port_domains.py, results/arch/qwen_kv_kits_b_1018/
# <kind>_ports.json); a die master without a record launches on the core clock (every non-tile KV die master is a core
# element; the main relay planner clocks every chain on clk_core_*).  ck -> the source's (else the sink's) clk_core_*
# trunk; hck (the kc command / fault chain kck_* / kcf_*: measured hck at both ends) -> its clk_hbm_* trunk; a bundle that
# carries both (slg o_pc / o_ctl, kvpc o_grp) has no single legal relay clock: core (as the main planner) + recorded
# MIXED (the bundle must be split by domain; open item, lanes/KVR-DERIVE.md).
PORT_DOMAINS = 'results/arch/qwen_kv_kits_b_1018'
# KV-DOMSPLIT 10-19 (OT_KV_DOMSPLIT=1): the split tiles' measured records (every group <-> PC / gather word single-domain)
if os.environ.get('OT_KV_DOMSPLIT', '0') == '1':
    PORT_DOMAINS = 'results/arch/qwen_kv_domsplit_1019/ports'
_PD = {}


def _port_record(master):
    kind = re.sub(r'^qkd_kvs_', '', master or '')
    if kind not in _PD:
        f = Path(__file__).resolve().parents[2] / PORT_DOMAINS / f'{kind}_ports.json'
        _PD[kind] = json.loads(f.read_text())['ports'] if master and master.startswith('qkd_kvs_') and f.exists() else None
    return _PD[kind]


def port_domain(master, port):
    """'core' | 'hbm' | 'mixed' | None (unknown / feed-through) for one die pin of a master"""
    rec = _port_record(master)
    if rec is None:
        return None
    v = rec.get(port.lstrip('*'))
    if not v:
        return None
    ds = {d for d in v.get('domains', []) if d not in ('none', '?const')}
    if not ds:
        return None
    if ds == {'ck'}:
        return 'core'
    if ds == {'hck'}:
        return 'hbm'
    return 'mixed'


def launch_domain(by, src, dst):
    """the launching pin's domain of a chain src -> dst (src record, else the sink's, else core)"""
    d = port_domain(getattr(by.get(src[0]), 'master', None), src[1])
    if d is None and dst is not None:
        d = port_domain(getattr(by.get(dst[0]), 'master', None), dst[1])
    return d or 'core'


def relay_trunk(buses, by, src, dst):
    """-> (bus index of the clock trunk for a relay on chain src -> dst, launch domain).  Never an HBM trunk for a core
    word, never a core trunk for an HBM word; mixed bundles take the core trunk (recorded by the callers)."""
    dom = launch_domain(by, src, dst)
    pre = 'clk_hbm_' if dom == 'hbm' else 'clk_core_'
    for inst in (src[0], dst[0] if dst else None):
        j = next((j for j, b in enumerate(buses) if b is not None and b[1] == 'clock_trunk' and b[0].startswith(pre)
                  and any(i == inst for i, _ in b[3])), None)
        if j is not None:
            return j, dom
    if dom == 'hbm':
        raise ValueError(f'kv_pin_repair: HBM-domain chain {src} -> {dst} has no clk_hbm_* trunk at either end')
    return next(j for j, b in enumerate(buses) if b is not None and b[0] == 'clk_core_c'), dom


def trunk_domain(bid):
    return 'hbm' if bid.startswith('clk_hbm') else 'core' if bid.startswith('clk_core') else None


def _cands(K, target, grid, r):
    return [(K.up(target[0]+x*grid, K.GX), K.up(target[1]+y*grid, K.GY)) for x in range(-r, r+1) for y in range(-r, r+1)]


def _choice(K, m, staged, x, y, width, height, ap, bp, cap, distance, detour=0.0):
    if x < 4.32 or y < 4.32 or x+width+4.32 > m['die']['w'] or y+height+4.32 > m['die']['h']:
        return None
    orient = 'MY' if bp[0] < ap[0] else 'R0'
    inp_x, out_x = (x+width-K.SHAVE,x) if orient=='MY' else (x,x+width-K.SHAVE)
    left = abs(ap[0]-inp_x)+abs(ap[1]-(y+height/2))
    remaining = abs(bp[0]-out_x)+abs(bp[1]-(y+height/2))
    if left > cap or remaining >= distance-1+detour:
        return None
    if any(min(x+width+4.32,i.x+i.w)-max(x-4.32,i.x) > .001 and
           min(y+height+4.32,i.y+i.h)-max(y-4.32,i.y) > .001 for i in m['insts']+staged):
        return None
    return (remaining,x,y,left,out_x,orient)


def repair(K, m):
    M = K.masters(m, 1)
    m['assigned_ports'] = {n: {p: list(v) for p, v in mm.ports.items()}
                           for n, mm in M.items() if not n.startswith('qkd_rly')}
    by = {i.name: i for i in m['insts']}
    additions, buses, unresolved, widened = [], [], [], {}
    for bid, cls, bits, eps in m['buses']:
        if len(eps) != 2 or cls in K.ABUT or cls in ('clock_trunk', 'reset', 'constant'):
            buses.append((bid, cls, bits, eps)); continue
        (a, pa), (b, pb) = eps
        ap, bp = K.pin_xy(by[a], M[by[a].master], pa.lstrip('*')), K.pin_xy(by[b], M[by[b].master], pb.lstrip('*'))
        if abs(ap[0]-bp[0]) + abs(ap[1]-bp[1]) <= (K.HOP_REACH if getattr(K, "HOP", False) else K.PIN_REACH):
            buses.append((bid, cls, bits, eps)); continue
        width, height = 52.68, 30.24 if bits <= 512 else K.up(bits * .048 + 4, K.GY)
        if __import__('os').environ.get('OT_KV_RLY_STD', '0') == '1':
            import kv_rly_std as RS          # Q-KVSYS-RLY: the relay-standard row (default off: unchanged)
            width, height, _ = RS.layout(bits, RS.frame_rev(bid))
            width, height = width + K.SHAVE, max(height + K.SHAVE, bits * .048 + 4 if bits > 512 else 0.0)
            height = K.up(height, K.GY) if height > RS.STD[528][1] + K.SHAVE else height
        initial_ap = ap
        ap0 = ap
        for attempt in (0, 1):
          # KV-PLAN3 10-18: attempt 1 (only after attempt 0 left the hop over reach) searches the 40-half-cell ring
          # with a bounded detour at EVERY stage (crowded group / PC control channels: 2-7 residual hops per plan)
          ap = ap0
          chain, staged, previous = [], [], (a,pa)
          # Several registered stages are necessary for a long fault-chain return.
          # Each stage is chosen in free channel space; a trapped chain is rolled back.
          for stage in range(math.ceil((abs(ap[0]-bp[0])+abs(ap[1]-bp[1]))/200)+12):
              cap = 300 if previous[0].startswith('wctl_') and bid.startswith('wencoded_') else (K.HOP_REACH if getattr(K, "HOP", False) else K.PIN_REACH)
              if abs(ap[0]-bp[0])+abs(ap[1]-bp[1]) <= cap:
                  break
              distance = abs(ap[0]-bp[0])+abs(ap[1]-bp[1])
              fraction = min(.5, 350/distance)
              target = (ap[0]+fraction*(bp[0]-ap[0])-width/2,
                        ap[1]+fraction*(bp[1]-ap[1])-height/2)
              grid = K.GRID/2
              choices = []
              for x,y in _cands(K, target, grid, 16):
                  c_ = _choice(K, m, staged, x, y, width, height, ap, bp, cap, distance)
                  if c_:
                      choices.append(c_)
              if not choices and (attempt == 1 or not widened.get(bid)):
                  # Q-KVSYS-HOP 2026-10-16: a pin boxed in by blocks (d2d_kv fwd_* 1-bit pins, ~1,200 um to the first
                  # relay) finds no spot within 16 half-cells; look again up to 40 (only where repair failed before)
                  widened[bid] = True
                  ring = [(x, y) for x, y in _cands(K, target, grid, 40)]
                  for x, y in ring:
                      # a boxed-in pin may step AROUND its blocker first (bounded detour; later stages must progress)
                      c_ = _choice(K, m, staged, x, y, width, height, ap, bp, cap, distance, detour=cap)
                      if c_:
                          choices.append(c_)
              if not choices:
                  break
              remaining,x,y,left,out_x,orient=min(choices)
              name='rly_pinfix_'+bid.replace('__','_')+'_'+str(stage)
              it=K.F.Inst(name,f'qkd_rly_{bits}',x,y,width-K.SHAVE,height-K.SHAVE,orient,kind='relay',region='relay')
              staged.append(it)
              sbid=bid if not chain else bid+'__pinfix'+str(stage)
              chain.append((sbid,cls,bits,[previous,(name,'a')]))
              previous=(name,'b');ap=(out_x,y+height/2)
          if abs(ap[0]-bp[0])+abs(ap[1]-bp[1]) <= (K.HOP_REACH if getattr(K, "HOP", False) else K.PIN_REACH):
            break
        if abs(ap[0]-bp[0])+abs(ap[1]-bp[1]) > (K.HOP_REACH if getattr(K, "HOP", False) else K.PIN_REACH):
            unresolved.append(dict(bus=bid,um=abs(initial_ap[0]-bp[0])+abs(initial_ap[1]-bp[1])));
            buses.append((bid,cls,bits,eps)); continue
        if not staged:
            buses.append((bid,cls,bits,eps));continue
        m['insts'].extend(staged)
        by.update({i.name:i for i in staged})
        buses.extend(chain+[(bid+'__pinfix'+str(len(staged)),cls,bits,[previous,(b,pb)])])
        base=bid.split('__r')[0]
        m['relay_stages'][base]=m['relay_stages'].get(base,0)+len(staged)
        for index,it in enumerate(staged):
            additions.append(dict(bus=bid,relay=it.name,clock_source=a,launch=(a,pa),sink=(b,pb),stages_added=1,
                                  before_um=round(abs(initial_ap[0]-bp[0])+abs(initial_ap[1]-bp[1]),3)))
    mixed = set()
    for row in additions:      # KVR-DERIVE: the launching pin's clock (relay_trunk), not the source's first trunk
        n=row['relay']
        clock, dom = relay_trunk(buses, by, row['launch'], row['sink'])
        row['domain'] = dom
        row['clock'] = buses[clock][0]
        if dom == 'mixed':
            mixed.add(row['bus'])
        bid,cl,bits,eps=buses[clock];buses[clock]=(bid,cl,bits,list(eps)+[(n,'ck')])
    bad = [r_ for r_ in additions if trunk_domain(r_['clock']) != ('core' if r_['domain'] == 'mixed' else r_['domain'])]
    if bad:
        raise ValueError(f'kv_pin_repair: relay clock domain != launching pin domain: {bad[:4]}')
    m['buses']=buses
    m['pin_repair']=dict(added=additions, unresolved=unresolved, mixed_domain_buses=sorted(mixed),
                         method='fixed master pins; registered channel relay; no leaf traversal; relay clock = the '
                                'launching pin domain (kv_pin_repair.relay_trunk)')
    return m
