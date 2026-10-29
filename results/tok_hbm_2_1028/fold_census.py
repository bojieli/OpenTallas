"""TOK-HBM-2 read-only estimate: for every open S-role (SW/SE) client net of the composed top, the N-role (NW/NE)
mirror net and its driving instance/master/params = the template the q0-half fold copy must instantiate."""
import re, sys, json, collections, hashlib
p = sys.argv[1]; src = open(p).read()
ins = {m.group(2): int(m.group(1)) + 1 for m in re.finditer(r'input wire \[(\d+):0\] (\w+);', src)}
drv = {}; inst_info = {}; conns = {}; readers = {}
for m in re.finditer(r'\n  (\w+)(?: #\((.*?)\))? (\w+) \(\n(.*?)\n  \);', src, re.S):
    master, params, inst, body = m.group(1), m.group(2) or '', m.group(3), m.group(4)
    inst_info[inst] = (master, params)
    for pm in re.finditer(r'\.(\w+)\((\w+)(?:\[\d+:\d+\])?\)', body):
        if pm.group(2) == f'{inst}__{pm.group(1)}': drv[pm.group(2)] = (inst, pm.group(1))
        conns.setdefault(inst, {})[pm.group(1)] = pm.group(2)
        readers.setdefault(pm.group(2), []).append((inst, pm.group(1)))
S = [n for n in ins if not n.startswith('native_required') and re.search(r'_(SW|SE)', n)]
rows = []; fam = collections.defaultdict(lambda: dict(nets=0, bits=0, templates=set(), masters=set(), missing_mirror=0))
for n in sorted(S):
    # mirror by READER PORT: the open net's reader (S-role inst, port) -> same port on the N-role mirror instance
    mir = None
    for ri, rp in readers.get(n, []):
        mi = ri.replace('_SW', '_NW').replace('_SE', '_NE')
        if mi != ri and conns.get(mi, {}).get(rp): mir = conns[mi][rp]; break
    d = drv.get(mir) if mir else None; f = fam[re.sub(r'_(SW|SE)\w*', '_S*', n.split('__')[0])]
    f['nets'] += 1; f['bits'] += ins[n]
    if d: f['templates'].add(d[0]); f['masters'].add(inst_info[d[0]][0])
    else: f['missing_mirror'] += 1
    rows.append(dict(net=n, width=ins[n], mirror=mir, mirror_driver=d and dict(instance=d[0], port=d[1], master=inst_info[d[0]][0], params=inst_info[d[0]][1])))
out = dict(schema='opentallas.tok_hbm_2.s_role_fold_census.v1', source=p, sha256=hashlib.sha256(src.encode()).hexdigest(),
           note='read-only; S role = q0 half of the folded hub (DIE-HBM-7/8 fold contract). Template = the N-role mirror driver in the same composed top. Copy params (QID, READ/WRITE_RETURN, ...) must come from the plan legs, not from the template.',
           families={k: dict(nets=v['nets'], bits=v['bits'], template_instances=len(v['templates']), template_masters=sorted(v['masters']), nets_without_mirror_driver=v['missing_mirror']) for k, v in sorted(fam.items())},
           nets=rows)
json.dump(out, open(sys.argv[2], 'w'), indent=1)
for k, v in out['families'].items(): print(k, v)
