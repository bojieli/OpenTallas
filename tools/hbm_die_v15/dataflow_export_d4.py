import json, re, sys, collections
ROLE = [('sm_', 'hfd_sm'), ('pc_', 'hfd_loader'), ('svg', 'hfd_loader'), ('vmks', 'hfd_loader'), ('xc', 'hfd_loader'),
        ('vmh', 'hfd_hgi_vm'), ('vmb', 'hfd_hgi_vm'), ('hb_vms', 'hfd_hgi_vm'), ('lg_', 'hfd_hgi_vm'), ('dbk', 'hfd_hgi_vm'), ('hb_dbk', 'hfd_hgi_vm'), ('wbk', 'hfd_hgi_vm'), ('vmdel', 'hfd_hgi_vm'),
        ('su', 'hfd_su'), ('sfu', 'hfd_sfu'), ('hc', 'hfd_hc'), ('coll', 'hfd_coll'), ('hb_coll', 'hfd_coll'), ('cij', 'hfd_coll'),
        ('ep', 'hfd_serdes_slab'), ('lk', 'ot_pdie_serdes'), ('idx', 'hfd_hgi_idx'), ('hb_idx', 'hfd_hgi_idx'), ('quant', 'hfd_quant'),
        ('xl_', 'hfd_sm'), ('xq_', 'hfd_sm'), ('rly', 'relay'), ('phy', 'PHY')]
def role(n):
    for p, r in ROLE:
        if n.startswith(p): return r
    return 'other'
mode, out = sys.argv[1], sys.argv[2]
if mode == 'plan':
    P = json.load(open(sys.argv[3])); G = json.load(open(sys.argv[4])); M = json.load(open(sys.argv[5])); name = sys.argv[6]
    boxes = {k: dict(x=v['x'], y=v['y'], w=v['w'], h=v['h'], role=role(k)) for k, v in P.items() if isinstance(v, dict) and 'x' in v}
    edges = [dict(name=l['id'], source=[l['src'], l['cls']], sink=[l['dst'], l['cls']], bits=l['bits'], clock=l['cls'], binding=l['cls'])
             for l in G['links'] if l['src'] in boxes and l['dst'] in boxes]
    W, H = M['die_um']
else:   # case: manifest placement + contract edges, relay tiles as blocks (hops visible)
    man = json.load(open(sys.argv[3])); C = json.load(open(sys.argv[4])); name = sys.argv[5]
    boxes = {k: dict(x=v['x'], y=v['y'], w=v['w'], h=v['h'], role=role(k)) for k, v in man['placement'].items()}
    agg = collections.Counter(); clk = {}
    for e in C['edges']:
        s, t = e['source'][0], e['sink'][0]
        if s in boxes and t in boxes:
            k = (s, e['source'][1], t, e['sink'][1]); agg[k] += e['bits']; clk[k] = e.get('clock')
    edges = [dict(name=f'{s}.{sp}>{t}.{tp}', source=[s, sp], sink=[t, tp], bits=b, clock=clk[(s, sp, t, tp)], binding='contract edge')
             for (s, sp, t, tp), b in agg.items()]
    W, H = man['die_um']
json.dump(dict(name=name, adoption_allowed=True, die_outline_um=[W, H], boxes=boxes,
               master_map='role by name prefix (H-DIE dataflow export 10-16)'), open(out + '/boxes.json', 'w'))
json.dump(dict(complete=True, source=name, nodes={}, edges=edges), open(out + '/graph.json', 'w'))
print(len(boxes), 'boxes', len(edges), 'edges')
