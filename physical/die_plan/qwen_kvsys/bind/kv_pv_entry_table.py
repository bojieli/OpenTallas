#!/usr/bin/env python3
"""KV-P6-V37 10-23: PV pad table at the PARTITION ENTRY for BINDER3 (KV-P6 decision: first functional proof on the v3.6
lanes, pads shared at the sink partition's input port instead of per sink member).

    kv_pv_entry_table.py BIND_DIR LP.json PLAN.json R8_TABLE RULES.json OUT.json

LP.json = kv_pv_pads_plan.py BIND R8 LP.json --option bound --entry (V-D-H shift 0; member pads + entry groups).
Output sections
  entries   one per (sink partition input port, bit ranges): lane id (port comment of the bound partition RTL), the
            source leaf.port + bits, pad stages (= the group's shared delay), supersedes = r8 member ids it replaces.
  members   residual per-member pads (total LP pad - entry pad of its group, > 0 only), r8 member schema.
  merge     this table is AUTHORITATIVE for every id in 'covered_ids' (pad 0 included): BINDER3 drops the r8 entry of
            those ids and applies entries + members here; every other id keeps its r8 pad (no member padded twice).
  inner     intra-partition ot_dp_dly re-chosen by the LP: part, sink leaf.port, source leaf, ot_dp_dly instance(s)
            u_d<old>_* feeding it, old D, new D (split the instance per sink when one instance gets two new D).
  params    TRUNK_D / FLAG_D / pvfin P0,P1 age shift (LP) and boot ages per vport (see boot_rule).
  type_check  pads per plan TYPE port: every instance of a type must carry the same entry pads (one pad per type port).
"""
import collections, json, re, sys

B, LP, PLAN, R8, RULES, OUT = sys.argv[1:7]
T = json.load(open(LP))
plan = json.load(open(PLAN))
ptype = {x['name']: x['type'] for x in plan['partitions']}
r8ids = {m['id']: m for m in json.load(open(R8))['members']}
rules = {r['param']: r for r in json.load(open(RULES))['rules']}
top = open(B + '/rtl/qwen_kvsys_bound_top.sv').read()
modof = {inst: mod for mod, inst in re.findall(r'^\s*(kv3_\w+)\s+(?:#\(.*?\)\s*)?(\w+)\s*\(\s*$', top, re.M)}

_mcache = {}


def module(part):
    if part in _mcache:
        return _mcache[part]
    t = open(f"{B}/rtl/{modof[part]}.sv").read()
    lanes = {n: l for n, l in re.findall(r'input\s+wire\s*\[[^\]]*\]\s*(\w+),\s*//.*?lane (L\d+)', t)}
    width = {n: int(w) + 1 for w, n in re.findall(r'input\s+wire\s*\[(\d+):0\]\s*(\w+)', t)}
    blocks = {}
    for g, inst, body in re.findall(r'// as-built (\S+)\n\s*\w+\s*(?:#\(.*?\))?\s*(u_\w+)\s*\((.*?)\n\s*\);', t, re.S):
        ports = {p: e.strip() for p, e in re.findall(r'\.(\w+)\((.*?)\)(?=,\s*\n|\s*$)', body, re.S)}
        blocks[g] = (inst, ports)
    _mcache[part] = (lanes, width, blocks)
    return _mcache[part]


def bits_of(expr):
    """concat expression -> list of (signal, bit) LSB first."""
    e = expr.strip()
    if e.startswith('{'):
        e = e[1:-1]
    out = []
    for el in reversed([x.strip() for x in e.split(',')]):
        m = re.match(r'(\w+)(?:\[(\d+)(?::(\d+))?\])?$', el)
        if not m:
            out.append((el, None)); continue
        s, hi, lo = m.group(1), m.group(2), m.group(3)
        if hi is None:
            out.append((s, None)); continue
        hi = int(hi); lo = int(lo) if lo is not None else hi
        out.extend((s, b) for b in range(lo, hi + 1))
    return out


def port_bits(part, sink, sink_port, sink_bits):
    lanes, width, blocks = module(part)
    inst, ports = blocks[sink]
    bl = bits_of(ports[sink_port])
    res = collections.defaultdict(set)
    for lo, hi in sink_bits:
        for b in range(lo, hi + 1):
            s, k = bl[b]
            if s.endswith('_q') and s[:-2] in width:
                res[s[:-2]].add(k)
    return inst, res


def ranges(bs):
    bs = sorted(bs); out = []
    for b in bs:
        if out and b == out[-1][1] + 1:
            out[-1][1] = b
        else:
            out.append([b, b])
    return out


mem = {m['id']: m for m in T['members']}
gof = {}
entries = []
for g in T['entry_groups']:
    for i in g['member_ids']:
        gof[i] = g
    if not g['entry_pad']:
        continue
    pb = collections.defaultdict(set)
    insts = []
    for i in g['member_ids']:
        m = mem[i]
        inst, res = port_bits(m['sink_part'], m['sink'], m['sink_port'], m['sink_bits'])
        insts.append(inst)
        for p, s in res.items():
            pb[p] |= s
    lanes = module(g['sink_part'])[0]
    for p, s in sorted(pb.items()):
        entries.append(dict(sink_part=g['sink_part'], type=ptype[g['sink_part']], port=p, port_bits=ranges(s),
                            lane=lanes.get(p), source=g['source'], source_bits=g['source_bits'], pad=g['entry_pad'],
                            bits=len(s), supersedes=[i for i in g['member_ids'] if i in r8ids],
                            covers=g['member_ids'], sinks=sorted(set(insts))))
# entries keep the LP group pad.  One pad per TYPE port is enforced at MEMBER level (kv_pv_pads_plan.py --tie-types:
# every sink pin of a shared pv type gets the same total pad in all its instances); the entry split may still differ
# per instance because the bound per-instance modules (kv3_pv_v2_part / _part_v1 ...) wire different sources to the
# same port name -> type_conflicts_entry lists those, type_member_check proves the member totals agree.
eff = {}
for e in entries:
    for i in e['covers']:
        eff[i] = e['pad']
resid = []
covered = []
for m in T['members']:
    if m['id'].startswith('INNER:'):
        continue
    covered.append(m['id'])
    e = eff.get(m['id'], 0)
    if m['pad'] - e > 0:
        r = dict(m); r['pad'] = m['pad'] - e; r['entry_pad'] = e; r['landed'] = m['landed']
        resid.append(r)
inner = []
for m in T['members']:
    if not m['id'].startswith('INNER:') or m['landed'] == m['asbuilt']:
        continue
    part = m['sink_part']
    _, _, blocks = module(part)
    inst, ports = blocks.get(m['sink'], (None, {}))
    dl = sorted(set(re.findall(r'\b(d%d_\w+?)(?=[\[\s,}]|$)' % m['asbuilt'], ports.get(m['sink_port'], ''))))
    inner.append(dict(part=part, sink=m['sink'], sink_inst=inst, sink_port=m['sink_port'], source=m['source'],
                      dly_insts=['u_' + d for d in dl], old_D=m['asbuilt'], new_D=m['landed']))
split = collections.defaultdict(set)
for x in inner:
    for d in x['dly_insts']:
        split[(x['part'], d)].add(x['new_D'])
# ---- type consistency: entry pads per (type, port, bits) and residual pads per (type, sink inst, port, bits)
tc = collections.defaultdict(dict)
for e in entries:
    tc[(e['type'], e['port'], json.dumps(e['port_bits']))][e['sink_part']] = e['pad']
conf = []
for k, v in tc.items():
    parts_of_type = [p for p, t in ptype.items() if t == k[0]]
    vals = {p: v.get(p, 0) for p in parts_of_type}
    if len(set(vals.values())) > 1:
        conf.append(dict(type=k[0], port=k[1], port_bits=json.loads(k[2]), pads=vals))
rc = collections.defaultdict(dict)
for r in resid:
    try:
        inst, _ = port_bits(r['sink_part'], r['sink'], r['sink_port'], r['sink_bits'])
    except (KeyError, IndexError):
        inst = re.sub(r'pvw_\d|_[EW][SN]_|_[SN]_', '*', r['sink'])     # non-pv leaf: side-normalised name
    rc[(ptype[r['sink_part']], inst, r['sink_port'], json.dumps(r['sink_bits']))][r['sink_part']] = r['pad']
rconf = []
for k, v in rc.items():
    parts_of_type = [p for p, t in ptype.items() if t == k[0]]
    vals = {p: v.get(p, 0) for p in parts_of_type}
    if len(set(vals.values())) > 1:
        rconf.append(dict(type=k[0], sink_inst=k[1], port=k[2], sink_bits=json.loads(k[3]), pads=vals))
def _nz(x):
    return re.sub(r'pvw_\d', 'pvw_*', re.sub(r'(astk|vport)_([EW])[SN]_', r'\1_\2*_', x))
mt = collections.defaultdict(dict)
for m in T['members']:
    ty = ptype.get(m['sink_part'])
    if ty and sum(1 for x in ptype.values() if x == ty) > 1:
        mt[(ty, _nz(m['sink']), m['sink_port'], json.dumps(m['sink_bits']), _nz(m['source']), m['id'].startswith('INNER:'))][m['sink_part']] = m['landed'] - m['bound'] if not m['id'].startswith('INNER:') else m['landed']
mconf = [dict(type=k[0], sink=k[1], port=k[2], source=k[4], inner=k[5], pads=v) for k, v in mt.items() if len(set(v.values())) > 1]
shared = sorted({t for t in ptype.values() if re.match(r'kv3_pv', t) and sum(1 for x in ptype.values() if x == t) > 1})
# ---- boot ages: request -> ctl arrival equal on all 16 ports (RL = 4 + WP + O + DQ + RT), O = landed header depth
WP = rules['DQ (boot cfg_age)']['W_bound']; RT = rules['RT (boot cfg_age)']['regen_kv35']
O = collections.defaultdict(int)
for m in T['members']:
    mm = re.match(r'(vport_\w+)\.out_(t|valid|epoch)$', m['source'])
    if mm and m['sink_part'] == 'hub_C' and re.match(r'pvw_\d__u_ctl$', m['sink']):
        O[mm.group(1)] = max(O[mm.group(1)], m['landed'])
X = max(WP[k] + O[k] + RT[k] for k in WP)
boot = {}
for k in sorted(WP):
    need = X - (WP[k] + O[k] + RT[k]); dq = min(need, 15)
    boot[k] = dict(WP_bound=WP[k], O_landed=O[k], RT=RT[k], DQ=dq, W_req_pad=need - dq, cfg_age=(dq << 8) | RT[k])
S = T['summary']
params = dict(TRUNK_D=S['TRUNK_D'], FLAG_D=S['FLAG_D'], TRUNK_D_asb=S['TRUNK_D_asb'], FLAG_D_asb=S['FLAG_D_asb'],
              pvfin_P0_P1_cal_age_shift=S['P0_P1_age_shift'], cfg_fia=5 + X, RL=4 + X, boot=boot,
              boot_rule='RL = 4 + WP + O + DQ + RT equal on all 16 ports (qkd_pv16_vport W = WP + O, KV-P6-BOOT 10-23: the '
                        'vport -> ctl return O is part of it); cfg_fia = RL + 1; DQ > 15 -> W request-lane pads (pr_t 14 b + '
                        'pr_valid 1 b); O = landed header depth of this table',
              W_req_pad_flops=sum(15 * b['W_req_pad'] for b in boot.values()))
ent_fl = sum(e['bits'] * e['pad'] for e in entries)
res_fl = sum(sum(hi - lo + 1 for lo, hi in r['sink_bits']) * r['pad'] for r in resid)
summary = dict(entries=len(entries), entry_pad_flops=ent_fl, residual_members=len(resid), residual_pad_flops=res_fl,
               total_pv_pad_flops=ent_fl + res_fl, lp_entry_objective=S['entry_pad_flops'],
               by_kind_lp=S['entry_pad_flops_by_kind'], inner_changed=len(inner),
               inner_delay_flops_new=S['inner_delay_flops_new'], inner_delay_flops_bound_asis=S['inner_delay_flops_bound_asis'],
               dly_insts_needing_split=sorted(f'{p}:{d}' for (p, d), v in split.items() if len(v) > 1),
               covered_ids=len(covered), r8_ids_superseded=sum(1 for i in covered if i in r8ids),
               shared_pv_types=shared, type_conflicts_entry=len(conf), type_conflicts_residual=len(rconf),
               type_member_conflicts=dict(collections.Counter(('inner' if c['inner'] else c['type']) for c in mconf)))
json.dump(dict(schema='opentallas.die_plan.kv_pv_entry_pads.v1', die='qwen_kvsys', note=__doc__.strip(), summary=summary,
               params=params, type_conflicts_entry=conf, type_conflicts_residual=rconf, type_member_conflicts=mconf, entries=entries, members=resid,
               covered_ids=covered, inner=inner), open(OUT, 'w'), indent=1)
print(json.dumps(summary, indent=1)); print(json.dumps({k: v for k, v in params.items() if k != 'boot'}))
print({k: (b['DQ'], b['RT'], b['W_req_pad']) for k, b in boot.items()})
