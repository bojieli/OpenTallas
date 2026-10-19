#!/usr/bin/env python3
"""KV-ATTN 10-19: every public INPUT pin of the safe ATTN native source (6326ff81a, qkd_kvs_attn_safe_control) lands
first in a flop D pin, with ZERO added edges (exact cycle function).

Two structural cases exist in the source (all others are already pin -> flop D):
  RETIME  a plain unreset DFFHQN F whose D is a combinational cone over input pins only (the RX zero-test partial ORs,
          d2d__rx_payload -> OR5/OR4 -> status_nonzero).  Every leaf pin p already has a plain unreset landing flop L_p
          (DFFHQN, D = p).  F(t) = cone(p(t-1)) = cone(L_p.Q(t)), so F is removed and its QN net is driven by
          INV(cone'(INV(L_p.QN))) -- a copy of the cone fed from the landed copies.  No edge is added or removed.
  SPLIT   an async set/reset DFFASRHQN F whose D is ONE OR2/AND2 of two input pins (the fault-root ufk pairs).
          Each pin gets its own flop with F's CLK/RESETN/SETN; F.QN = AND2(QN_a, QN_b) for OR2 (OR2(QN_a,QN_b) for AND2).
          OR/AND are idempotent, so the reset/set value is preserved; no edge is added.
Usage: pinreg.py <in.v> <out.v> <report.json> [MUT]   MUT 1 = one retimed leaf fed from the raw pin (bench mutant),
       MUT 2 = split recombination with the wrong gate (bench mutant).
"""
import json, re, sys, collections

src_path, out_path, rep_path = sys.argv[1:4]
MUT = int(sys.argv[4]) if len(sys.argv) > 4 else 0
lines = open(src_path).read().split('\n')
CELL = re.compile(r'^(\s*\(\*[^*]*\*\)\s*)(\w+)\s+(c\d+)\s*\((.*)\);\s*$')
ASG = re.compile(r'^\s*assign\s+(\S+)\s*=\s*(\S+?)\s*;\s*$')
OUTS = {'Y', 'QN', 'Q', 'H', 'L', 'CON', 'SN'}
cells, cell_line = {}, {}
port_of_net, net_of_port, out_assign = {}, {}, {}
for i, ln in enumerate(lines):
    m = CELL.match(ln)
    if m:
        pre, ms, name, conns = m.groups()
        pins = {k: v.strip() for k, v in re.findall(r'\.(\w+)\(([^()]*)\)', conns)}
        cells[name] = (ms, pins)
        cell_line[name] = i
        continue
    m = ASG.match(ln)
    if m:
        lhs, rhs = m.groups()
        if re.fullmatch(r'n\d+', lhs):
            port_of_net[lhs] = rhs
            net_of_port[rhs] = lhs
        else:
            out_assign[lhs] = rhs
drv, loads = {}, collections.defaultdict(list)
for n, (ms, p) in cells.items():
    for pin, net in p.items():
        (drv.__setitem__(net, (n, pin)) if pin in OUTS else loads[net].append((n, pin)))
for lhs, rhs in out_assign.items():
    loads[rhs].append(('PORT', lhs))
isff = lambda ms: ms.startswith('DFF')
CLK = cells[next(c for c, (ms, p) in cells.items() if isff(ms))][1]['CLK']


def first_contacts(net):
    return [(c, pin) for c, pin in loads.get(net, [])]


def cone(net):
    """backward comb cone of net -> (cells list topo, leaf nets) ; None if it hits a flop/tie"""
    order, leaves, seen = [], set(), set()

    def walk(n):
        if n in port_of_net:
            leaves.add(n); return True
        if n not in drv:
            return False
        c, _ = drv[n]
        ms, p = cells[c]
        if isff(ms) or ms.startswith('TIE'):
            return False
        if c in seen:
            return True
        seen.add(c)
        ok = all(walk(v) for k, v in p.items() if k not in OUTS)
        order.append(c)
        return ok
    return (order, leaves) if walk(net) else None


# 1. affected flops: any FF reached through comb from an input pin
affected = set()
for net, port in port_of_net.items():
    stack, seen = [net], set()
    while stack:
        n = stack.pop()
        for c, pin in loads.get(n, []):
            if c == 'PORT':
                continue
            ms, p = cells[c]
            if isff(ms):
                if n != net:
                    affected.add(c)
                continue
            if c in seen:
                continue
            seen.add(c)
            stack += [v for k, v in p.items() if k in OUTS]
landing = {}
for net in port_of_net:
    for c, pin in loads.get(net, []):
        if c != 'PORT' and cells[c][0] == 'DFFHQNx1_ASAP7_75t_R' and pin == 'D' and cells[c][1]['CLK'] == CLK:
            landing.setdefault(net, c)

new_lines, removed, added, inv_of = [], set(), [], {}
rep = {'source': src_path, 'retime': [], 'split': [], 'mut': MUT}
uid = [0]


def fresh(prefix):
    uid[0] += 1
    return f'{prefix}{uid[0]}'


def cell_text(ms, name, pins):
    return '  (* keep = 1, dont_touch = 1 *) %s %s (%s);' % (ms, name, ', '.join(f'.{k}({v})' for k, v in pins.items()))


mut_done = False
for F in sorted(affected, key=lambda c: int(c[1:])):
    ms, p = cells[F]
    cn = cone(p['D'])
    assert cn, f'{F}: D cone reaches a flop/tie; no exact zero-edge transform'
    order, leaves = cn
    if ms == 'DFFHQNx1_ASAP7_75t_R' and set(p) == {'CLK', 'D', 'QN'}:
        miss = [port_of_net[l] for l in leaves if l not in landing]
        assert not miss, f'{F}: leaf pins without a plain landing flop {miss}'
        ren = {}
        for l in sorted(leaves):
            if l not in inv_of:   # landed Q = INV(landing QN), shared by every retimed cone
                q = fresh('npr_lq')
                added.append(cell_text('INVx1_ASAP7_75t_R', fresh('cprl'), {'A': cells[landing[l]][1]['QN'], 'Y': q}))
                inv_of[l] = q
            ren[l] = inv_of[l]
            if MUT == 1 and not mut_done:
                ren[l] = l; mut_done = True      # MUTANT: raw pin, one edge early
        for c in order:
            cms, cp = cells[c]
            np_ = {}
            for k, v in cp.items():
                if k in OUTS:
                    ren[v] = fresh('npr_c'); np_[k] = ren[v]
                else:
                    np_[k] = ren[v]
            added.append(cell_text(cms, fresh('cprc'), np_))
        added.append(cell_text('INVx1_ASAP7_75t_R', fresh('cpro'), {'A': ren[p['D']], 'Y': p['QN']}))
        removed.add(F)
        rep['retime'].append(dict(ff=F, qn=p['QN'], cone_cells=order, leaves=sorted(port_of_net[l] for l in leaves),
                                  landing=sorted(landing[l] for l in leaves)))
    elif ms == 'DFFASRHQNx1_ASAP7_75t_R' and len(order) == 1 and cells[order[0]][0] in ('OR2x2_ASAP7_75t_R', 'AND2x2_ASAP7_75t_R'):
        g = order[0]
        gms, gp = cells[g]
        ins = [gp['A'], gp['B']]
        assert all(i in port_of_net for i in ins), F
        qns = []
        sr = {}
        for k in ('RESETN', 'SETN'):   # a constant set/reset gets its own tie cell (keeps every tie net <= 24 loads)
            d = drv.get(p[k])
            if d and cells[d[0]][0].startswith('TIE'):
                tn = fresh('npr_t')
                added.append(cell_text(cells[d[0]][0], fresh('cprt'), {d[1]: tn}))
                sr[k] = tn
            else:
                sr[k] = p[k]
        for i in ins:
            q = fresh('npr_sq')
            added.append(cell_text(ms, fresh('cprs'), {'CLK': p['CLK'], 'D': i, 'QN': q, 'RESETN': sr['RESETN'], 'SETN': sr['SETN']}))
            qns.append(q)
        comb = 'AND2x2_ASAP7_75t_R' if gms.startswith('OR2') else 'OR2x2_ASAP7_75t_R'
        if MUT == 2 and not mut_done:
            comb = 'OR2x2_ASAP7_75t_R' if comb.startswith('AND') else 'AND2x2_ASAP7_75t_R'; mut_done = True
        added.append(cell_text(comb, fresh('cprj'), {'A': qns[0], 'B': qns[1], 'Y': p['QN']}))
        removed.add(F)
        rep['split'].append(dict(ff=F, master=ms, gate=g, gate_master=gms, pins=[port_of_net[i] for i in ins]))
    else:
        raise SystemExit(f'{F} {ms}: unsupported pin->comb->flop structure')
assert MUT == 0 or mut_done
# dead original cone cells: drop comb cells whose outputs no longer have any load
live_loads = collections.defaultdict(int)
for n, (ms, p) in cells.items():
    if n in removed:
        continue
    for k, v in p.items():
        if k not in OUTS:
            live_loads[v] += 1
for lhs, rhs in out_assign.items():
    live_loads[rhs] += 1
dead = set()
changed = True
while changed:
    changed = False
    for n, (ms, p) in cells.items():
        if n in removed or n in dead or isff(ms) or ms.startswith('TIE'):
            continue
        if all(live_loads[v] == 0 for k, v in p.items() if k in OUTS):
            dead.add(n); changed = True
            for k, v in p.items():
                if k not in OUTS:
                    live_loads[v] -= 1
for k in dead:
    removed.add(k)
rep['dead_cone_cells'] = len(dead)
newnets = sorted({v for t in added for v in re.findall(r'\((npr_\w+)\)', t)})
out = []
for i, ln in enumerate(lines):
    m = CELL.match(ln)
    if m and m.group(3) in removed:
        continue
    if ln.startswith('module qkd_kvs_attn_safe_control '):
        ln = ln.replace('module qkd_kvs_attn_safe_control ', 'module qkd_kvs_attn_safe_pr ', 1)
    if ln.strip() == 'endmodule':
        out += [f'  wire {n};' for n in newnets] + added
    out.append(ln)
out[0:0] = ['// GENERATED by tools/qwen_kv_die/attn_pinreg_1019/pinreg.py from %s (MUT %d) -- do not edit; re-run.' % (src_path.split('/')[-1], MUT),
            '// Every public input pin lands first in a flop D pin; zero added edges (see pinreg.py docstring).']
open(out_path, 'w').write('\n'.join(out))
rep.update(removed_ff=len([c for c in removed if isff(cells[c][0])]), added_cells=len(added), retimed=len(rep['retime']), nsplit=len(rep['split']))
json.dump(rep, open(rep_path, 'w'), indent=1)
print('PINREG retime=%d split=%d dead=%d added=%d' % (rep['retimed'], rep['nsplit'], len(dead), len(added)))
