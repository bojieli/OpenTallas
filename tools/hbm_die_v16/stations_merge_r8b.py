#!/usr/bin/env python3
"""H-DIE-R8b 2026-10-17: relay station list for the run8b netlist (input of relay_layer_d4f.py).

Two sources, both placed station lists of tools/hbm_die_v15/die_relay_stations.py (reach 405):
  BASE  the run6 list the current relay layer was built from (relay-free case: rows are end-to-end buses);
  NEW   a list planned on the run8 case (its netlist carries the run6 relay tiles, so only rows whose driver and every
        sink are NOT relay tiles are end-to-end; these are the buses run8 bound without relays: the SU programme root
        su_pgr <-> slices pgp_<q>, col_su -> su_pgr, the fault tree, ...).
Both are re-expressed in run8b names through the r8b layer (v16_layers/r8b_d4f.json): an LG tap becomes its fold
consumer (port names per 'hoist'), cij_SW.inj_d becomes inj_d_r0+inj_d_r1 ('port_split').  A row whose driver is
the fold of one of its sinks is the old tap seam (now inside the tile): that sink is dropped (the row too when no sink
is left).  Rows are keyed by (driver, sink set); BASE wins, NEW only adds buses BASE does not know.  Rows whose driver
or a sink no longer exists in the run8b LAYER=none contract are dropped and counted (e.g. the monolithic su_prog).

    stations_merge_r8b.py --base B.json --new N.json --layer r8b_d4f.json --contract C.json[.gz] --out OUT.json
"""
import argparse
import gzip
import json


def ld(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


def main():
    ap = argparse.ArgumentParser()
    for k in ('--base', '--new', '--layer', '--contract', '--out'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    L = ld(a.layer); C = ld(a.contract); I = C['instances']
    tap = {t: next(v[0][0] for v in pm.values() if v) for t, pm in L['hoist'].items()}
    pmap = {(t, p): sorted({x[1] for x in v}) for t, pm in L['hoist'].items() for p, v in pm.items() if v}
    for n, r in L['remaster'].items():
        for p, v in (r.get('port_split') or {}).items():
            pmap[(n, p)] = sorted({x[1] for x in v}) if v else []
    stats = dict(base=0, new=0, kept_base=0, added_new=0, dropped_seam=0, dropped_gone=0, dropped_relay=0, sinks_dropped=0)

    def remap(row):
        di, dp = row['driver'].split('.', 1)
        ports = []
        for p in dp.split('+'):
            ports += pmap.get((di, p), [p])
        nd = tap.get(di, di)
        keep = []
        for k, s in enumerate(row['sinks']):
            ns = tap.get(s, s)
            if ns == nd:
                stats['sinks_dropped'] += 1; continue
            keep.append((k, ns))
        if not keep:
            stats['dropped_seam'] += 1; return None
        if nd not in I or any(ns not in I for _, ns in keep) or any(p not in I[nd]['ports'] for p in ports):
            stats['dropped_gone'] += 1; return None
        r = dict(row, driver=f"{nd}.{'+'.join(dict.fromkeys(ports))}", sinks=[ns for _, ns in keep],
                 sink_depths=[row['sink_depths'][k] for k, _ in keep] if 'sink_depths' in row else None)
        if r['sink_depths'] is None:
            r.pop('sink_depths')
        else:
            r['depth'] = max(r['sink_depths'])
        r['stations'] = [dict(s, toward=tap.get(s.get('toward'), s.get('toward'))) for s in row.get('stations', [])]
        r['pads'] = [dict(p, sink=tap.get(p['sink'], p['sink'])) for p in row.get('pads', []) if tap.get(p['sink'], p['sink']) != nd]
        return r
    B = ld(a.base); N = ld(a.new)
    out, seen = [], {}

    def merge_into(r):
        """one row per (driver instance, sink set): the two banks of a folded tap pair (their own rows before the fold)
        become one bus; their driver ports are unioned into the kept row (else two layer buses drive the same bits)."""
        key = (r['driver'].split('.')[0], frozenset(r['sinks']))
        k = seen.get(key)
        if k is None:
            seen[key] = len(out); return False
        o = out[k]
        di, dp = o['driver'].split('.', 1)
        o['driver'] = di + '.' + '+'.join(dict.fromkeys(dp.split('+') + r['driver'].split('.', 1)[1].split('+')))
        stats['merged'] = stats.get('merged', 0) + 1
        return True
    for row in B['rows']:
        stats['base'] += 1
        r = remap(row)
        if r is None:
            continue
        if merge_into(r):
            continue
        out.append(r); stats['kept_base'] += 1
    base_keys = set(seen)
    for row in N['rows']:
        stats['new'] += 1
        ms = [row.get('driver_master', '')]
        if row['driver'].split('.')[0].startswith(('rf', 'rfr_', 'sfr_')) or any(s.startswith(('rf', 'rfr_', 'sfr_')) for s in row['sinks']) \
                or ms[0].startswith('hbfd_rly'):
            stats['dropped_relay'] += 1; continue
        r = remap(row)
        if r is None:
            continue
        if (r['driver'].split('.')[0], frozenset(r['sinks'])) in base_keys:
            continue
        if merge_into(r):
            continue
        out.append(dict(r, source_list='run8')); stats['added_new'] += 1
    res = dict(B, rows=out, buses=len(out), merged_by='tools/hbm_die_v16/stations_merge_r8b.py', merge_stats=stats,
               sources=dict(base=a.base, new=a.new))
    json.dump(res, open(a.out, 'w'))
    print('STATIONS_MERGE', json.dumps(stats))


if __name__ == '__main__':
    main()
