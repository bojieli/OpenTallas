"""HBM-ARCH: as-built r18h5 census -> (served quadrant, role) using the d4g label propagation (gen_plan_v2)."""
import collections, gzip, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
D4G = os.path.join(HERE, '..', 'hbm')
sys.path.insert(0, D4G)
import gen_plan_v2 as g2          # noqa: E402  (logical_labels / role_of; read-only reuse)
FT = os.path.join(D4G, 'inputs')


def load():
    cen = json.load(gzip.open(f'{FT}/census/hbm_census.json.gz'))
    blocks = {}
    for line in open(f'{FT}/dumps/dump-hbm/blocks.tsv'):
        f = line.rstrip('\n').split('\t')
        blocks[f[0]] = dict(master=f[1], w=float(f[4]), h=float(f[5]))
    names = sorted({x for gr in cen['groups'] for x in (gr['src'], gr['dst'])})
    lab = g2.logical_labels(names, cen['groups'])
    role = {n: g2.role_of(n, lab) for n in names}
    bw = json.load(gzip.open(f'{D4G}/census/bus_widths.json.gz'))
    return cen, blocks, role, bw


if __name__ == '__main__':
    cen, blocks, role, bw = load()
    rs = collections.defaultdict(set)
    for n, (q, r) in role.items():
        rs[r].add(q)
    for r in sorted(rs):
        print(r, sorted(rs[r]))
