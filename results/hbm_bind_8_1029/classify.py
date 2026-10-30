"""HBM-BIND-8: group the UNPLANNED pairs of census.json by what crosses (driver/sink families) -> classes (i)/(ii)/(iii)/(b)."""
import sys, json, collections, re
c = json.load(open(sys.argv[1]))
DUP = {'cij', 'cxij_q', 'hb_dbk', 'hcollgi', 'hcollgl', 'pgp', 'sfup', 'sfus', 'smw', 'wbk', 'xl_ctl'}   # HBM-036 families
def fam(p):
    h = p.split('.')[0]
    h = re.sub(r'_(NW|NE|SW|SE|C|S|N)\d*(_[qs])?$', '', h)
    return h
def group(r):
    fs = {fam(d['path']) for d in r['drivers']} | {fam(d['path']) for d in r['sinks']}
    if r['cls'] == 'failed': return 'B-failed SU/hub windows'
    if any(f.startswith('hb_idx') or f == 'col_idx' for f in fs): return 'IDX scorer rows'
    if any(f.startswith('sfu') for f in fs): return 'SFU split3 ctl/lanes'
    if fs & {'ep', 'hb_coll', 'b2_ep1_root', 'epcal'}: return 'EP endpoints (spb0/vsN0)'
    if fs & {'hb_vms', 'hcollb'}: return 'hub<->hub over root'
    if fs & {'sm', 'svg'}: return 'SM front -> svg'
    return 'misc <=9 b'
G = collections.defaultdict(lambda: dict(pairs=0, bits=0, glue_drv_bits=0, leaf_drv_bits=0, dup=set(), gaps=[]))
for r in c['pairs']:
    g = G[group(r)]; g['pairs'] += 1; g['bits'] += r['unplanned']
    for d in r['drivers']:
        g['glue_drv_bits' if d['kind'] == 'glue' else 'leaf_drv_bits'] += d['bits']
    fs = {fam(d['path']) for d in r['drivers'] + r['sinks']}
    g['dup'] |= fs & DUP
    if r['gap_um']: g['gaps'].append(r['gap_um'])
print('| group | pairs | bits | driver bits glue/leaf | gap um | HBM-036 dup families |')
for k, g in sorted(G.items(), key=lambda kv: -kv[1]['bits']):
    gp = f"{min(g['gaps']):.0f}-{max(g['gaps']):.0f}" if g['gaps'] else '-'
    print(f"| {k} | {g['pairs']} | {g['bits']:,} | {g['glue_drv_bits']:,}/{g['leaf_drv_bits']:,} | {gp} | {','.join(sorted(g['dup'])) or '-'} |")
print('total', sum(g['pairs'] for g in G.values()), sum(g['bits'] for g in G.values()))
