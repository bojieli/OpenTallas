#!/usr/bin/env python3
"""TOK-HBM-3 (opt-in, read-only on its input): generate the S-role (SW/SE) instance copies that close the open S-role
client nets of the composed HBM native top (tools/hbm_b2/current_native_top.py output), from the N-role (NW/NE) mirror
drivers found by reader-port mirroring (results/tok_hbm_2_1028/s_role_fold_census.json method).

Copy rule: instance <i> with _NW/_NE in its name -> <i> with _SW/_SE; every connected net that names an N role is renamed
to the S role; nets naming no role (die clock / POR / shared programme buses) are kept. Each renamed net must ALREADY exist
in the top (wire or open input port) -> otherwise UNRESOLVED (needs the plan/bind, never invented). A renamed output that
is already driven by another instance is a MULTI_DRIVER error. Families without an N mirror (svg_S*: SM key-line service
of stack 1, 8 x 1099 b) FAIL CLOSED until the plan names their provider.

Params: the plan legs (C25b) own the S-role params (QID, READ/WRITE_RETURN, pads). Until --params JSON gives them, the
template params are copied and every copy is marked PARAMS_FROM_TEMPLATE (status != BOUND); nothing is wired by this tool.
Usage: fold_s_roles.py <top.sv> <census.json> <out_prefix> [--params plan_params.json]
"""
import re, sys, json, hashlib, collections

def role_swap(s):
    return s.replace('_NW', '_SW').replace('_NE', '_SE')

def main(argv):
    top, census, out = argv[1], argv[2], argv[3]
    params_plan = {}
    if '--params' in argv: params_plan = json.load(open(argv[argv.index('--params') + 1]))
    src = open(top).read(); cen = json.load(open(census))
    declared = {m.group(2): m.group(1) for m in re.finditer(r'\n  (input|output|wire) wire \[\d+:0\] (\w+);|\n  (?:input|output) wire \[\d+:0\] (\w+);', src) if m.group(2)}
    for m in re.finditer(r'\n  (input|output) wire \[\d+:0\] (\w+);', src): declared[m.group(2)] = m.group(1)
    for m in re.finditer(r'\n  wire \[\d+:0\] (\w+);', src): declared.setdefault(m.group(1), 'wire')
    insts = {}; drivers = collections.defaultdict(list)
    for m in re.finditer(r'\n  (\w+)(?: #\((.*?)\))? (\w+) \(\n(.*?)\n  \);', src, re.S):
        master, params, inst, body = m.group(1), m.group(2) or '', m.group(3), m.group(4)
        insts[inst] = dict(master=master, params=params, body=body)
        for pm in re.finditer(r'\.(\w+)\((\w+)\[', body):
            if pm.group(2) == f'{inst}__{pm.group(1)}': drivers[pm.group(2)].append(inst)
    templates = sorted({r['mirror_driver']['instance'] for r in cen['nets'] if r.get('mirror_driver')})
    no_mirror = sorted(r['net'] for r in cen['nets'] if not r.get('mirror_driver'))
    copies, frag = [], []
    new_outputs = set()                                       # outputs of every copy (pass 1): sibling copies may read them
    for t in templates:
        ni = role_swap(t)
        for pm in re.finditer(r'\.(\w+)\((\w+)\[', insts[t]['body']):
            if pm.group(2) == f'{t}__{pm.group(1)}': new_outputs.add(f'{ni}__{pm.group(1)}')
    for t in templates:
        ti = insts[t]; ni = role_swap(t)
        status = 'PARAMS_FROM_PLAN' if ni in params_plan else 'PARAMS_FROM_TEMPLATE'
        prm = params_plan.get(ni, ti['params'])
        if ni in insts: copies.append(dict(instance=ni, template=t, status='EXISTS')); continue
        unresolved, multi, renamed, kept, new_wires = [], [], 0, 0, []
        body = ti['body']
        def sub(m):
            nonlocal renamed, kept
            net = m.group(1); new = role_swap(net)
            if new == net: kept += 1; return m.group(0)
            renamed += 1
            if new.startswith(t + '__'): new = ni + new[len(ni):]
            if new.startswith(ni + '__'):            # output of the copy: a new wire unless it closes an open net
                if drivers.get(new): multi.append(new)
                if new not in declared: new_wires.append(new)
            elif new not in declared and new not in new_outputs: unresolved.append(new)
            return m.group(0).replace(net, new)
        nbody = re.sub(r'(?<=[({,\s])(\w+)(?=\[)', sub, body)
        st = 'MULTI_DRIVER' if multi else ('UNRESOLVED' if unresolved else status)
        copies.append(dict(instance=ni, template=t, master=ti['master'], params=prm, status=st, renamed_nets=renamed,
                           kept_nets=kept, new_wires=len(set(new_wires)), unresolved=sorted(set(unresolved)), multi_driver=sorted(set(multi))))
        frag.append(f"  // TOK-HBM-3 fold copy of {t} ({st})\n  {ti['master']}{' #(' + prm + ')' if prm else ''} {ni} (\n{nbody}\n  );")
    closes = {r['net'] for r in cen['nets'] if r.get('mirror_driver')}
    produced = set()
    for c in copies:
        if c.get('status') in ('PARAMS_FROM_TEMPLATE', 'PARAMS_FROM_PLAN'):
            produced |= {n for n in closes if n.startswith(c['instance'] + '__')}
    upstream = collections.Counter()
    for c in copies:
        for u in c.get('unresolved', []): upstream[re.sub(r'__\w+$', '', u)] += 1
    open_after = sorted((closes - produced) | set(no_mirror))
    verdict = 'FAIL_CLOSED' if (no_mirror or any(c['status'] in ('UNRESOLVED', 'MULTI_DRIVER') for c in copies)) else \
              ('TEMPLATE_PARAMS_PENDING_PLAN' if any(c['status'] == 'PARAMS_FROM_TEMPLATE' for c in copies) else 'BOUND')
    rep = dict(schema='opentallas.tok_hbm_3.s_role_fold.v1', top=top, top_sha256=hashlib.sha256(src.encode()).hexdigest(),
               census=census, verdict=verdict, copies=len(copies),
               status_counts=dict(collections.Counter(c['status'] for c in copies)),
               s_nets=len(cen['nets']), s_nets_closed_by_copies=len(produced), open_after=open_after,
               fail_closed_no_mirror=no_mirror, missing_upstream_s_instances=dict(sorted(upstream.items())), instances=copies,
               note='a copy output closes an open S net only if the net name is <copy>__<port>; nets read under other names stay open (listed)')
    json.dump(rep, open(out + '.json', 'w'), indent=1)
    open(out + '.svh', 'w').write('// GENERATED by tools/hbm_b2/fold_s_roles.py -- NOT BOUND (verdict %s)\n' % verdict + '\n'.join(frag) + '\n')
    print(verdict, rep['status_counts'], 'closed', len(produced), 'of', len(cen['nets']), 'open_after', len(open_after))
    return 0 if verdict != 'FAIL_CLOSED' else 2

if __name__ == '__main__':
    sys.exit(main(sys.argv))
