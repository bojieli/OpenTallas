#!/usr/bin/env python3
"""S81 die-level data-flow graph for the GLOBAL-FP-S floorplan study (screen only, never a closure).

Nodes: every die-level block of a canonical construction plan (128 field frames, the 11 hub parents, PHY/ctrl/svc,
selector/collector bands, links, svc join) plus the contract-v21 / S-DIE reservations that the plan does not bind yet
(Engram MIX4, six HCX projection homes + controller/gatherpack, embed expand, Engram dispatch).
Edges: every die-level link of the plan.  Transport instances (stations, hub stations, hub ends, x-stages, link clock
stations) are contracted: a connected transport component between real blocks is ONE die link (p2p, or a tree when
frames hang on it).  Width = widest bus segment of the component (the RTL port width of the link); a frame's leaf
width = bits of its own incident segments.  Clock/reset distribution (fclk/clock/reset/col_clock/col_reset) is NOT a
data edge.  Pads (TOP) are off-chip and excluded.  Edges that exist only in RTL ABI contracts (VM <-> MIX4) are added
from the VM die ABI with provenance; interfaces with no RTL port list yet are recorded under `unknowns` and carry no
weight.

Traffic: bits/cycle averaged over the token = width x duty(class), duty = class share of the measured token path
(results/arch/token_path_20261009/ds_rom.json totals.by_class).  A statically scheduled link streams at full width
while its class is active (owner rule: static cycle schedule).  This is an ACTIVITY PROXY, not a per-link calendar;
the per-link S81 compiler calendar does not exist yet (NATIVE_CALENDAR_INCOMPLETE).
"""
import argparse, collections, gzip, hashlib, json
from pathlib import Path

TRANSPORT = {'stn', 'hstn', 'hend', 'xstg', 'lkck'}
NONDATA = {'fclk', 'clock', 'reset', 'col_clock', 'col_reset'}
FIELD_KINDS = {'bfcol', 'bf', 'cfg', 'seq', 'q', 'sstn', 'qbank', 'node', 'cfifo', 'rstg', 'rly'}

# class duty = share of the measured AR token path (ds_rom.json totals.by_class, 828,878 cycles/token)
DUTY_SRC = 'results/arch/token_path_20261009/ds_rom.json totals.by_class (AR, 828,878.4 cycles/token)'
DUTY = dict(field=0.504757, hop=0.148624, su=0.140131, coll=0.136819, hbm=0.03147, select=0.026314,
            head=0.010575, embed=0.001296)
# Engram MIX4: 772 measured cycles per Engram layer (exact MIX4 bench L01, S-ELEM-C 06:25) over the mean stage group
# (13,814 cycles, ds_rom.json groups) -> ASSUMED one MIX4 job per stage group
DUTY['engram'] = round(772 / 13814.44, 6)

# class of a link by its (sorted) real end blocks; first match wins
def link_class(ends, has_frames):
    s = set(ends)
    if has_frames:
        return 'field'
    if any(e.startswith('lk_') for e in s):
        return 'coll+hop'
    if 'sp_collective' in s:
        return 'coll'
    if s & {'phy_SW', 'ctrl_SW', 'svc_SW', 'svcj'}:
        return 'select' if s & {'bk_selector', 'bk_collector'} else 'hbm'
    if s & {'bk_selector', 'bk_collector'}:
        return 'select'
    if s & {'mix4'}:
        return 'engram'
    if s & {'sp_su_s', 'sp_hc_s', 'sp_hc_t'}:
        return 'su'
    return 'field'          # VM <-> capture/gather/PQ/WFC/sseq: field-phase datapath


def duty_of(cls):
    return sum(DUTY[c] for c in cls.split('+'))


def load(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)


def block_of(inst):
    g = inst[8]
    if g.startswith('frame_'):
        return 'F' + g[6:]
    return inst[0]


def build(plan_path, vm_abi_path=None, reservations=None):
    plan = load(plan_path)
    ins = {i[0]: i for i in plan['insts']}
    # ---- nodes
    nodes = {}
    for r in plan['regions']:
        if r['kind'] == 'field':
            k = r['name'][6:]
            fr = plan['frames'][k]
            x0, y0, x1, y1 = r['rect']
            st = fr['street']
            nodes['F' + k] = dict(name='F' + k, kind='frame', rect=[x0, y0, x1 - x0, y1 - y0],
                                  port=[(st[0] + st[2]) / 2, (st[1] + st[3]) / 2],
                                  half=fr['half'], tier=fr['tier'], col=fr['col'], movable='field_array',
                                  prov='plan.regions[field] + plan.frames[].street (cfifo street = frame die port)')
    for i in plan['insts']:
        if i[8].startswith('frame_') or i[7] in TRANSPORT:
            continue
        nodes[i[0]] = dict(name=i[0], kind=i[7], master=i[1], rect=[i[2], i[3], i[4], i[5]],
                           movable=('fixed_io' if i[7] in ('phy', 'link', 'ctrl', 'svc') else 'hub'),
                           prov='plan.insts')
    for r in (reservations or []):
        nodes[r['name']] = dict(r, movable='reservation')
    # pqrom live inside the sp_pq stack: fold into sp_pq
    fold = {n: 'sp_pq' for n in nodes if n.startswith('pqrom')}
    for n in fold:
        nodes.pop(n)
    # ---- contract transport components
    par = {}
    def f(x):
        while par.setdefault(x, x) != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for b in plan['buses']:
        if b[1] in NONDATA:
            continue
        tr = [n for n, _ in b[3] if n in ins and ins[n][7] in TRANSPORT]
        for t in tr[1:]:
            par[f(tr[0])] = f(t)
    comp = collections.defaultdict(lambda: dict(blocks=collections.Counter(), kinds=collections.Counter(), w=0,
                                                segs=0, names=set()))
    direct = collections.defaultdict(lambda: dict(w=0, kinds=collections.Counter(), names=set()))
    excluded = collections.Counter()
    for b in plan['buses']:
        if b[1] in NONDATA:
            excluded['nondata:' + b[1]] += 1
            continue
        ends = [n for n, _ in b[3]]
        if 'TOP' in ends:
            excluded['pad:' + b[1]] += b[2]
            continue
        tr = [n for n in ends if ins[n][7] in TRANSPORT]
        real = [fold.get(block_of(ins[n]), block_of(ins[n])) for n in ends if ins[n][7] not in TRANSPORT]
        if tr:
            c = comp[f(tr[0])]
            for r in real:
                c['blocks'][r] += b[2]
            c['kinds'][b[1]] += 1; c['segs'] += 1; c['w'] = max(c['w'], b[2]); c['names'].add(b[0].split('[')[0])
        else:
            rs = tuple(sorted(set(real)))
            if len(rs) < 2:
                continue                    # frame- or block-internal
            if all(x.startswith('F') for x in rs):
                excluded['frame_to_frame_direct'] += b[2]
                continue
            d = direct[rs]; d['w'] += b[2]; d['kinds'][b[1]] += 1; d['names'].add(b[0])
    edges = []
    for cid, c in comp.items():
        bl = c['blocks']
        frames = sorted(k for k in bl if k.startswith('F'))
        hubs = sorted(k for k in bl if not k.startswith('F'))
        if not hubs and not frames:
            continue
        cls = link_class(hubs, bool(frames))
        e = dict(kind='tree' if frames else 'p2p', ends=hubs + frames, width=c['w'], cls=cls,
                 duty=duty_of(cls), segments=c['segs'], bus_kinds=dict(c['kinds']),
                 sample_names=sorted(c['names'])[:4],
                 prov='plan.buses transport component (stations/hub ends contracted)')
        if frames:
            e['root'] = hubs[0] if len(hubs) == 1 else hubs
            e['leaf_bits'] = {k: bl[k] for k in frames}
            e['tree_mode'] = 'broadcast' if c['kinds'].get('lane', 0) and min(bl[k] for k in frames) >= c['w'] - 2 else 'collect'
        edges.append(e)
    for rs, d in direct.items():
        cls = link_class(rs, False)
        edges.append(dict(kind='p2p', ends=list(rs), width=d['w'], cls=cls, duty=duty_of(cls), segments=len(d['names']),
                          bus_kinds=dict(d['kinds']), sample_names=sorted(d['names'])[:4], prov='plan.buses direct (abutted/pin-to-pin)'))
    # merge parallel p2p edges between the same pair (several components = several RTL ports of one link)
    merged = collections.OrderedDict()
    for e in edges:
        if e['kind'] == 'p2p':
            k = ('p2p', tuple(sorted(e['ends'])))
            if k in merged:
                m = merged[k]; m['width'] += e['width']; m['segments'] += e['segments']; m['ports'] += 1
                for a, v in e['bus_kinds'].items():
                    m['bus_kinds'][a] = m['bus_kinds'].get(a, 0) + v
                continue
            e = dict(e, ports=1)
            merged[k] = e
        else:
            merged[('tree', len(merged))] = e
    edges = list(merged.values())
    unknowns = []
    if vm_abi_path:
        abi = load(vm_abi_path)
        fp = abi['functional_ports']
        mx = {k: v['bits'] for k, v in fp.items() if '_mx_' in k}
        if 'mix4' in nodes:
            edges.append(dict(kind='p2p', ends=['mix4', 'sp_vm'], width=sum(mx.values()), cls='engram', duty=DUTY['engram'],
                              segments=0, ports=len(mx), bus_kinds={'abi': len(mx)},
                              sample_names=sorted(mx), prov='VM die ABI results/arch/s81_vm_die_abi_1015/contract.json f_mx_*/t_mx_* (not in the plan: no MIX4 slot bound)'))
    for n, v in nodes.items():
        if v.get('movable') == 'reservation' and v.get('interface') == 'UNKNOWN':
            unknowns.append(dict(node=n, why=v.get('why', 'no RTL port list bound to a die slot')))
    for i, e in enumerate(edges):
        e['id'] = 'e%03d' % i
        e['traffic'] = e['width'] * e['duty']
        e['critical'] = e['cls'] in ('field', 'su', 'coll', 'coll+hop')
    return plan, nodes, edges, unknowns, excluded


def reservations_default():
    """Unbound S81 blocks with known area; positions = the CURRENT proposed homes (S-DIE / contract v21)."""
    R = []
    # Engram MIX4: S-DIE GEN18m2 proposal (rotated 1x4, 771.12 x 3229.2 at 15714.0,9061.2), footprint S-ELEM-C plan.json
    R.append(dict(name='mix4', kind='res', master='dsfd_engram_mix4_c', rect=[15714.0, 9061.2, 771.12, 3229.2],
                  prov='S-DIE r11 06:30 --mix4-slot (GEN18m2); 2.49 mm2 measured footprint S-ELEM-C plan.json',
                  interface='VM_ABI'))
    for nm, x in (('south0', 9417.6), ('south1', 11232.0), ('north0', 13046.4), ('north1', 14860.8), ('west0', 16675.2), ('west1', 18489.6)):
        R.append(dict(name='hcx_' + nm, kind='res', master='ot_s81_hcx_projection_leaf', rect=[x, 24624.0, 1728.0, 1296.0],
                      prov='plan.unbound_supplemental_reservations (GEN18c)', interface='UNKNOWN',
                      why='HCX projection: no die port list (S-FUNC r10: port 9 command face proposed, H-row transport unpriced)'))
    R.append(dict(name='hcx_ctl', kind='res', master='ot_s81_hcx_controller', rect=[15362.4, 22770.0, 216.0, 216.0],
                  prov='contract v21 slot', interface='UNKNOWN'))
    R.append(dict(name='hcx_gatherpack', kind='res', master='ot_s81_hcx_gatherpack', rect=[15600.0, 22770.0, 216.0, 216.0],
                  prov='contract v21 slot', interface='UNKNOWN'))
    R.append(dict(name='embed_expand', kind='res', master='ot_s81_embed_expand', rect=[15120.0, 22770.0, 216.0, 216.0],
                  prov='contract v21 slot', interface='UNKNOWN'))
    R.append(dict(name='engram_dispatch', kind='res', master='ot_s81_engram_dispatch', rect=[15120.0, 23007.6, 129.6, 86.4],
                  prov='contract v21 slot', interface='UNKNOWN'))
    return R


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--vm-abi', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    plan, nodes, edges, unknowns, excluded = build(a.plan, a.vm_abi, reservations_default())
    out = dict(schema='opentallas.s81.globalfp.graph.v1',
               scope='SCREEN_ONLY_BLOCK_LEVEL_DATAFLOW_GRAPH_NOT_NATIVE',
               source_sha256={str(Path(p).name): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (a.plan, a.vm_abi)},
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               plan_scope=plan.get('scope'), die_um=plan['die'], duty=DUTY, duty_source=DUTY_SRC,
               nodes=nodes, edges=edges, unknowns=unknowns, excluded=dict(excluded),
               counts=dict(nodes=len(nodes), frames=sum(1 for n in nodes if n.startswith('F')), edges=len(edges),
                           trees=sum(e['kind'] == 'tree' for e in edges)))
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out['counts']))
    for e in sorted(edges, key=lambda e: -e['traffic'])[:40]:
        print(e['id'], e['kind'], e['cls'], e['width'], round(e['traffic']), e['ends'][:3], len(e['ends']), e.get('tree_mode', ''))


if __name__ == '__main__':
    main()
