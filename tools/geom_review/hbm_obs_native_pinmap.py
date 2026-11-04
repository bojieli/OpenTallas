#!/usr/bin/env python3
"""Read-only OBS native-peer physical pin census. Never substitute contents/core centers."""
import argparse, collections, gzip, json
from pathlib import Path


def load(path):
    p = Path(path)
    with (gzip.open(p, 'rt') if p.suffix == '.gz' else p.open()) as f:
        return json.load(f)


def orient(o, w, h, x, y):
    # The four orientations accepted by the authoritative G0 check._orient_pt.
    return {'R0': (x, y), 'MX': (x, h-y), 'MY': (w-x, y), 'R180': (w-x, h-y)}[o]


class Mapper:
    def __init__(self, plan_path, homes_path, names_path, compose_path):
        self.plan_path = Path(plan_path)
        self.plan = load(plan_path)
        self.homes = load(homes_path)['parts']
        self.names = load(names_path)
        self.composed = {r['inst']: r for r in load(compose_path)['cores']}
        self.parts = {p['name']: p for p in self.plan['partitions']}
        self.cache = {}

    def home(self, canonical):
        if canonical in self.homes:
            return self.homes[canonical], 'map_recovered.parts'
        c = self.composed.get(canonical)
        if not c:
            return None, 'canonical absent from homes/compose'
        members = c.get('members', [])
        hs = [self.homes.get(m) for m in members]
        if members and all(h is not None for h in hs) and len({tuple(h) for h in hs}) == 1:
            return hs[0], 'all composed members agree'
        return None, 'missing or disagreeing composed member homes'

    def pins(self, core):
        rows = [dict(name=p['name'], layer=p['layer'], x=p['xy'][0], y=p['xy'][1]) for p in core.get('pins', [])]
        ref = core.get('pins_file')
        source = None
        if ref:
            path = self.plan_path.parent / ref
            if not path.exists() and Path(str(path)+'.gz').exists():
                path = Path(str(path)+'.gz')
            if not path.exists():
                return None, str(path)
            source = str(path.resolve())
            if source not in self.cache:
                js = load(path)
                js = js.get('pins', js) if isinstance(js, dict) else js
                self.cache[source] = [dict(name=p.get('name') or f"{p['bus']}[{p.get('bit', 0)}]", layer=p['layer'], x=p['x'], y=p['y']) for p in js]
            rows.extend(self.cache[source])
        return rows, source

    def endpoint(self, canonical, port, bit, wrapper_instance=None, partition='NW_hub', allow_scalar=True):
        out = dict(canonical=canonical, port=port, bit=bit, coordinate_space='partition-local')
        if wrapper_instance:
            key = partition+'.'+wrapper_instance
            actual = self.names.get(key)
            out['bind_name_key'] = key
            if actual != canonical:
                return dict(out, status='UNRESOLVED_ALIAS', reason='bind_names mismatch or missing', bind_names_value=actual)
        home, basis = self.home(canonical)
        out['home_basis'] = basis
        if home is None:
            return dict(out, status='UNRESOLVED_HOME', reason=basis)
        part, inst = home
        out.update(partition=part, plan_instance=inst)
        if part not in self.parts:
            return dict(out, status='UNRESOLVED_HOME', reason='home partition absent from plan')
        typ = self.parts[part]['type']
        t = self.plan['partition_types'][typ]
        cs = [c for c in t.get('hard_cores', []) if c['inst'] == inst]
        if len(cs) != 1:
            contents = [c for c in t.get('contents', []) if c.get('inst') == inst]
            return dict(out, status='UNRESOLVED_NO_HARDCORE_PIN_VIEW', reason='home is not one exact hard core; no center inference', contents_match=bool(contents), contents=[{k:v for k,v in c.items() if k in ['inst','module','cells','pins_file','pins','origin_um','outline_um']} for c in contents])
        core = cs[0]
        out.update(partition_type=typ, physical_module=core['module'], origin_um=core['origin_um'], outline_um=core['outline_um'], orientation=core.get('orient', 'R0'), track_offset_um=core.get('track_offset_um', [0, 0]), pins_file=core.get('pins_file'))
        rows, source = self.pins(core)
        out['actual_pins_file'] = source
        if rows is None:
            return dict(out, status='UNRESOLVED_PIN_FILE', reason='referenced physical pin table missing')
        indexed = f'{port}[{bit}]'
        matches = [p for p in rows if p['name'] == indexed]
        if not matches and bit == 0 and allow_scalar:
            # Scalar port fallback only; never substitute a bus center for a nonzero bit.
            matches = [p for p in rows if p['name'] == port]
        unique = {(p['name'], p['layer'], p['x'], p['y']): p for p in matches}
        if len(unique) != 1:
            return dict(out, status='UNRESOLVED_PIN_NAME' if not unique else 'UNRESOLVED_MULTIPLE_PIN_POINTS', reason='no exact bit/scalar physical pin' if not unique else 'multiple actual access points; none selected', matching_points=list(unique.values()))
        pin = next(iter(unique.values()))
        try:
            x, y = orient(core.get('orient', 'R0'), *core['outline_um'], pin['x'], pin['y'])
        except KeyError:
            return dict(out, status='UNRESOLVED_ORIENTATION', reason='not supported by canonical G0 orientation set')
        ox, oy = core['origin_um']
        dx, dy = core.get('track_offset_um', [0, 0])
        out.update(status='MAPPED_ACTUAL_PIN', pin_name=pin['name'], layer=pin['layer'], local_pin_um=[pin['x'], pin['y']], xy_um=[round(ox+dx+x, 6), round(oy+dy+y, 6)])
        c = self.composed.get(canonical)
        if c and port in c.get('ports', {}):
            out['composed_port_direction'] = c['ports'][port].get('dir')
        return out


def main():
    ap = argparse.ArgumentParser()
    for n in ['plan', 'homes', 'names', 'compose', 'peers', 'census', 'out']:
        ap.add_argument('--'+n, required=True)
    a = ap.parse_args()
    mapper = Mapper(a.plan, a.homes, a.names, a.compose)
    peers = load(a.peers)
    rows = []
    observed = collections.defaultdict(set)
    for r in peers['native_bits']:
        for p in r['peers']:
            if p.get('canonical'):
                observed[(p['canonical'],p['port'])].add(p['bit'])
    widths = {p['port']:p['width'] for p in peers['ports']}
    for r in peers['native_bits']:
        for peer in r['peers']:
            if not peer.get('canonical'):
                continue
            source = mapper.endpoint(peer['canonical'], peer['port'], peer['bit'], peer['instance'], allow_scalar=(observed[(peer['canonical'],peer['port'])] == {0}))
            sink = mapper.endpoint('obs_NW', r['obs_port'], r['obs_bit'], 'u_u_obs_Q', allow_scalar=(widths[r['obs_port']] == 1))
            rows.append(dict(obs_port=r['obs_port'], obs_bit=r['obs_bit'], wire=r['wire'], wire_bit=r['wire_bit'], source_port_direction=peer.get('direction'), source_module=peer.get('module'), source=source, capture=sink))
    unplanned = []
    for i in load(a.census)['instances']:
        for p in i['ports']:
            for b in p['bits']:
                if b['wire'].startswith('xi_'):
                    unplanned.append(dict(obs_port=p['port'], obs_bit=b['bit'], wire=b['wire'], wire_bit=b['wire_bit'], status='UNPLANNED_XI', peers=b['peers']))
    status = collections.Counter(r['source']['status'] for r in rows)
    groups = collections.Counter((r['source']['canonical'], r['source']['port'], r['source']['status']) for r in rows)
    result = dict(schema='opentallas.hbm.obs.native_actual_pinmap.v1', scope='physical pin endpoints only; no transport stages, latency, source correctness, CTS or route claim', source_plan=str(Path(a.plan).resolve()), native_logical_bits=len(peers['native_bits']), physical_peer_rows=len(rows), source_status=dict(status), capture_status=dict(collections.Counter(r['capture']['status'] for r in rows)), unplanned_xi=unplanned, groups=[dict(canonical=k[0], port=k[1], status=k[2], bits=n) for k,n in sorted(groups.items())], rows=rows)
    path = Path(a.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=1)+'\n')
    print('OBS native logical bits', len(peers['native_bits']), 'peer rows', len(rows), 'source status', dict(status), 'xi', len(unplanned))
    for g in result['groups']:
        if g['status'] != 'MAPPED_ACTUAL_PIN':
            print('UNRESOLVED', g)


if __name__ == '__main__':
    main()
