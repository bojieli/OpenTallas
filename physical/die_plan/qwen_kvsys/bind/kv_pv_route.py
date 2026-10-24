"""KV-P6-V37 10-23: PV trunk route models for kv_pv_pads_plan.py (V / header / cmd member depths).

Trunk positions: pv_<S|N>_p -> p (0 = die edge ... 7 = next to hub_C), hub_C -> 8.  Every partition crossing of the
bound plan is 2 cycles (checked: --option v36 reproduces the kv35 bind depths of all V / header / cmd members).
  v36    as bound: V(k,p) = 2|p-pk| (own partition INNER), H(k) = 2(8-pk), D(p) = 2(8-p)
  turn7  v3.7 'V turn': the vport's V row goes hub-ward UNTAPPED to pv_*_7 and comes back with the cmd wave,
         tapped at every partition incl. its own: V = 2(7-pk) + 2(7-p); H, D as v36
  turnC  as turn7 but the turn is inside hub_C (V crosses the hub_C face twice): V = 2(8-pk) + 2(8-p)
  mid    KV-P6-PV option (a): vports _0/_1 moved to pv_*_4, _2/_3 to pv_*_3, cmd injected at pv_*_4 (express from
         hub_C, then both ways): V = 2|p-pk'|, H = 2(8-pk'), D = 8 + 2|p-4|
  ctlmid the pair control leaf pvw_<i>__u_ctl moves from hub_C into pv_*_4 (vports, RH, result trunk stay):
         D(p) = 2|p-4|, H(k) = 2|pk-4|, flags R(p) = 2|p-4|, V as v36 (direct)
  --plan PLAN --lat LAT: V / header / cmd depths = summed gen.py cycles of the plan's tap_tree lanes of that source
         (first arrival at the sink partition, >= 1 hop) -- the method for a plan that has no bind yet.
Other members (result trunk, flags, astk pe2, hg read, INNER non-vport edges) keep the kv35 bind depths.
"""
import collections
import json
import re

VSRC = re.compile(r'(vport_\w+)\.out_v_(lo|hi)$')
HSRC = re.compile(r'(vport_\w+)\.out_(t|valid|epoch)$')
CSRC = re.compile(r'pvw_\d__u_ctl\.cmd$')
RSRC = re.compile(r'pvw_\d__u_s\d+_j\.(y_valid|fault)$')


def pos(part):
    m = re.match(r'pv_[SN]_(\d)$', part)
    return int(m.group(1)) if m else (8 if part == 'hub_C' else None)


def kind(m):
    if m.get('inner'):
        return 'Vin' if m['source'].startswith('vport_') else None
    if VSRC.match(m['source']) and pos(m['sink_part']) is not None:
        return 'V'
    if HSRC.match(m['source']) and m['sink_part'] == 'hub_C':
        return 'H'
    if CSRC.match(m['source']) and pos(m['sink_part']) is not None and m['sink_part'] != 'hub_C':
        return 'C'
    if RSRC.match(m['source']) and m['sink_part'] == 'hub_C' and re.match(r'pvw_\d__u_ctl$', m['sink']):
        return 'R'
    return None


def plan_paths(plan, lat):
    P = json.load(open(plan)); L = json.load(open(lat))['lanes']
    ports = {x['id']: x for x in P['ports']}
    g = collections.defaultdict(list)
    for ln in P['lanes']:
        n = ln.get('note', '')
        leaf = n.split(' ', 1)[1].rsplit('.', 1)[0] if ' ' in n else n
        a, b = ports[ln['ports'][0]]['src']['part'], ports[ln['ports'][-1]]['dst']['part']
        g[leaf].append((a, b, L[ln['id']]['cycles'], n))

    def depth(leaf, grp, src, dst):
        edges = [e for e in g[leaf] if e[3].endswith('.' + grp)]
        best = []
        def dfs(cur, d, used):
            if cur == dst and used:
                best.append(d); return
            for i, (a, b, c, _) in enumerate(edges):
                if a == cur and i not in used:
                    dfs(b, d + c, used | {i})
        dfs(src, 0, frozenset())
        assert len(best) == 1, (leaf, grp, src, dst, best)
        return best[0]
    return depth


def reroute(mem, option, plan=None, lat=None):
    home = {}
    for m in mem:
        if kind(m) in ('V', 'H'):
            home[m['source'].rsplit('.', 1)[0]] = pos(m['src_part'])
    if option == 'bound' and not plan:
        return dict(changed=0)
    depth = plan_paths(plan, lat) if plan else None
    newpos = dict(home)
    if option in ('mid', 'ctlv34'):
        for v in home:
            newpos[v] = 4 if v[-1] in '01' else 3
    if option == 'ctlv4':
        for v in home:
            newpos[v] = 4
    stat = collections.Counter(); diff = collections.Counter()
    for m in mem:
        k = kind(m)
        if k is None:
            continue
        side = 'S' if '_S_' in m['sink_part'] or '_S_' in m['src_part'] or re.search(r'_[EW]S_', m['source']) else 'N'
        if k == 'Vin':
            v = m['source']; p = pos(m['sink_part']); pk = home[v]
        elif k in ('V', 'H'):
            v = m['source'].rsplit('.', 1)[0]; pk = home[v]; p = pos(m['sink_part'])
        elif k == 'R':
            p = pos(m['src_part'])
        else:
            p = pos(m['sink_part'])
        if k == 'R' and option not in ('ctlmid', 'ctlv4', 'ctlv34'):
            continue
        if plan:
            if k == 'C':
                nb = depth(m['source'].rsplit('.', 1)[0], 'cmd', 'hub_C', m['sink_part'])
            elif k == 'H':
                nb = depth(v, 'vo', m['src_part'], 'hub_C')
            elif k == 'V':
                nb = depth(v, 'vo', m['src_part'], m['sink_part'])
            else:
                # own-partition V: via the turn if the plan routes it there, else stays INNER
                try:
                    nb = depth(v, 'vo', m['sink_part'], m['sink_part'])
                except AssertionError:
                    continue
        else:
            q = newpos.get(v) if k not in ('C', 'R') else None
            pk = pk if k not in ('C', 'R') else None
            if option == 'v36':
                nb = {'V': 2 * abs(p - (pk if k != 'C' else 0)), 'H': 2 * (8 - pk), 'C': 2 * (8 - p), 'Vin': None}[k]
            elif option in ('turn7', 'turnC'):
                T = 7 if option == 'turn7' else 8
                if k in ('V', 'Vin'):
                    nb = 2 * (T - pk) + 2 * (T - p) if not (pk == T or (k == 'Vin' and pk == 7 and T == 7)) else (2 * abs(p - pk) if k == 'V' else None)
                else:
                    nb = {'H': 2 * (8 - pk), 'C': 2 * (8 - p)}[k]
            elif option == 'ctlmid':
                c_ = 4                      # pvw ctl leaf moved into pv_*_4; vports, RH, result trunk stay
                nb = {'V': 2 * abs(p - pk) if k == 'V' else None, 'Vin': None, 'H': 2 * abs(pk - c_) if k == 'H' else None,
                      'C': 2 * abs(p - c_), 'R': 2 * abs(p - c_)}[k]
            elif option in ('ctlv4', 'ctlv34'):
                # v3.8 (KV-P7-V38): pair ctl AND the vports in pv_*_4 (ctlv34: vports _2/_3 in pv_*_3): V, cmd, flags
                # leave one partition, header is local -> data and command share the lane depth
                c_ = 4
                if k in ('V', 'Vin'):
                    nb = 2 * abs(p - q) if k == 'V' or p != q else None
                else:
                    nb = 2 * abs(q - c_) if k == 'H' else 2 * abs(p - c_)
            elif option == 'mid':
                if k in ('V', 'Vin'):
                    nb = 2 * abs(p - q)
                else:
                    nb = 2 * (8 - q) if k == 'H' else 8 + 2 * abs(p - 4)
            if nb is None:
                continue
        if k == 'Vin':
            m['inner'] = False; m['a'] = 'L:' + v
            m['id'] = m['id'].replace('INNER:', 'LOOP:', 1)
            stat['own_partition_V_routed_via_trunk'] += 1
        if nb != m['bound']:
            diff[(k, nb - m['bound'])] += m['bits']
        m['bound'] = nb
        stat[k] += 1
    return dict(changed=dict(stat), bit_depth_delta={f'{a}{b:+d}': n for (a, b), n in sorted(diff.items())},
                vport_pos=dict(sorted(newpos.items())))
