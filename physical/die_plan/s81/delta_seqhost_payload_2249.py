#!/usr/bin/env python3
"""Drop two proven-constant seqhost CW payload bits on the complete physical lane."""
import argparse
import copy
import json
from pathlib import Path

LANE = 'unit__seqhost__gunit'
OLD, NEW = 267, 265


def band_width(band):
    if band.get('width') != OLD:
        raise ValueError('unexpected seqhost landing-band width')
    band['width'] = NEW
    if 'live_data_storage_flops' in band:
        if band['live_data_storage_flops'] % (OLD+1):
            raise ValueError('unexpected landing storage depth')
        band['live_data_storage_flops'] = band['live_data_storage_flops']//(OLD+1)*(NEW+1)
    # Padded ring storage/clock roles and geometry remain identical: both
    # 268-bit and 266-bit words occupy five 64-bit chunks.


def apply(raw, sidecar):
    plan, sc = copy.deepcopy(raw), copy.deepcopy(sidecar)
    part_types = {p['name']: p['type'] for p in plan['partitions']}
    lane = next(x for x in plan['lanes'] if x['id'] == LANE)
    ports = {x['id']: x for x in plan['ports']}
    if len(lane['ports']) != 14:
        raise ValueError('seqhost lane must retain all fourteen cuts')
    touched = {}
    manifest = []
    for pid in lane['ports']:
        port = ports[pid]
        if port['width'] != OLD or port.get('segments'):
            raise ValueError(f'{pid}: unexpected source width/segmentation')
        port['width'] = NEW
        manifest.append(dict(id=pid, src=port['src'], dst=port['dst'], old_width=OLD,
                             new_width=NEW, old_epoch_bit=OLD, new_epoch_bit=NEW, added_cycles=0))
        for endpoint in (port['src'], port['dst']):
            tn, bus = part_types[endpoint['part']], endpoint['bus']
            touched.setdefault(tn, set()).add(bus)
    for tn, buses in touched.items():
        typ = plan['partition_types'][tn]
        affected_parts = {e['part'] for row in manifest for e in (row['src'], row['dst'])
                          if part_types[e['part']] == tn}
        if {p for p, t in part_types.items() if t == tn} != affected_parts:
            raise ValueError(f'{tn}: shared type would require an explicit split')
        for bus in typ.get('buses', []):
            if bus['name'] in buses:
                if bus['width'] != OLD:
                    raise ValueError(f'{tn}.{bus["name"]}: unexpected bus width')
                bus['width'] = NEW
        for slot in typ.get('ft_slots', []):
            if slot['name']+'_i' not in buses and slot['name']+'_o' not in buses:
                continue
            if slot['width'] != OLD:
                raise ValueError(f'{tn}.{slot["name"]}: unexpected FT width')
            slot['width'] = NEW
            for key in ('bit_sites_um',):
                for sites in slot.get(key, []):
                    if len(sites) != OLD+1:
                        raise ValueError('unexpected FT bit-site count')
                    # Preserve every live data site and the original epoch site.
                    sites[:] = sites[:NEW]+[sites[OLD]]
        lc = typ.get('clock', {}).get('landing_contract', {})
        for bus, band in lc.get('bands', {}).items():
            if bus in buses:
                band_width(band)
        for source in lc.get('collector_local_sources', []):
            if source.get('name') in buses and source.get('band'):
                band_width(source['band'])
        collector = sc.get('collector', {}).get('types', {}).get(tn, {})
        for source in collector.get('local_sources', []):
            if source.get('name') in buses and source.get('band'):
                band_width(source['band'])
    crossing_count = 0
    for port in sc['ports']:
        if port['lane'] == LANE:
            if port['width'] != OLD:
                raise ValueError('unexpected sidecar width')
            port['width'] = NEW
            crossing_count += 1
    sc['bits'] = sum(port['width'] for port in sc['ports'])
    if set(sc['by_class_pair']) != {'std->std'}:
        raise ValueError('review crossing class aggregation before applying')
    sc['by_class_pair']['std->std']['bits'] = sc['bits']
    report = dict(lane=LANE, cuts=manifest, affected_types=sorted(touched),
                  crossing_count=crossing_count, added_cycles=0,
                  fields=dict(address_native_bits=[0,1,2,3,4,5,8,9], address_payload_bits=list(range(8)),
                              data_payload_bits=[8,263], valid_payload_bit=264, epoch_bit=265),
                  removed_constant_payload_bits=[265,266],
                  proof_basis='current native bind fields, seqhost_unit_o4_fail.json; no constant-output waiver')
    return plan, sc, report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan'); ap.add_argument('sidecar'); ap.add_argument('out'); ap.add_argument('sidecar_out')
    a = ap.parse_args()
    p, s, report = apply(json.loads(Path(a.plan).read_text()), json.loads(Path(a.sidecar).read_text()))
    Path(a.out).write_text(json.dumps(p, separators=(',', ':'))+'\n')
    Path(a.sidecar_out).write_text(json.dumps(s, separators=(',', ':'))+'\n')
    Path(a.out+'.mapping.json').write_text(json.dumps(report, indent=1)+'\n')
    print(f'SEQHOST_PAYLOAD PASS {len(report["cuts"])} cuts, {len(report["affected_types"])} types, 0 added cycles')
