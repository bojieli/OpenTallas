#!/usr/bin/env python3
"""Extract fixed station and return-link latency changes from the emitted S81 frame spec.

Every hop is source-pinned to actual child ports. This is compiler input, not a
claim that an emitted production programme meets its schedule.
"""
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools/landed_parent'), str(ROOT/'tools/s81_dv')]
import lp
import frame_return_plan as RP


def extract(specfile):
    spec = lp.load(str(specfile))
    p = lp.Parent(spec)
    plan = p.plan()
    kids = {i['inst']: i for i in p.insts}
    # Frame wrappers spell each internal bit explicitly, including payload/tag bits.
    def bits(ex):
        # TW3-S81/FRAME 10-19: the r1 skew relays (u_y_rt_*_sk) drive sk_n<node>_<bit> nets into every node's b pin;
        # matching only n<id> dropped every r1 leaf (b resolved to 'zero.*'), so the plan predicted r0 words only.
        return re.findall(r'\b(?:sk_n\d+_\d+|n\d+)\b', ex)
    drv = {}
    for i in p.insts:
        for pin, ex in i['conns'].items():
            if p.cports[i['module']][pin] == 'out':
                for k, net in enumerate(bits(ex)):
                    assert net not in drv, ('multiple bit drivers', net)
                    drv[net] = (i['inst'], pin, k)

    def back(net, reader, mode):
        flat, add, crossings, seen = 0, 0, [], set()
        while net in drv:
            assert (net, reader) not in seen, ('loop in traversed data path', net)
            seen.add((net, reader))
            i, pin, k = drv[net]
            it = kids[i]
            if p.region[i] != p.region[reader]:
                add += p.A
                crossings.append(dict(net=net, source=i, reader=reader, added_edges=p.A))
            m = it['module']
            if mode == 'control' and m.startswith('ot_s81_cfg7_seq'):
                upstream = back(bits(it['conns']['lc'])[0], i, 'station')
                return dict(source=upstream['source'], flat_link_edges=flat, added_edges=add+upstream['added_edges'],
                            link_edges=flat+add+upstream['added_edges'], crossings=crossings+upstream['crossings'])
            srcpin = None
            if m.startswith('dsfd_rly') or m == 'dsfd_rstg':
                srcpin = 'i'
            elif m.startswith('dsfd_qbank') and pin.startswith('d_'):
                srcpin = 'e_' + pin[2:]
            elif m.startswith('dsfd_qbank') and pin.startswith('o_'):
                srcpin = 'i_' + pin[2:]
            elif m == 'ot_s81_sstn_payload536':
                srcpin = 'i'
            elif m.startswith('ot_s81_sstn'):
                srcpin = {'xa':'xai', 'xb':'xbi', 'cc':'cci'}.get(pin)
            if srcpin:
                net, reader = bits(it['conns'][srcpin])[k], i
                flat += 1
                continue
            if mode == 'return' and m == 'ot_v41_rom_elem_q_qxpq_w10':
                # pv is MSB first: r1, r0.
                size = len(bits(it['conns'][pin]))
                assert size % 2 == 0, (i, pin, size)
                terminal = i[2:] + '.r' + str(1 - k // (size // 2))
            else:
                terminal = i[2:] if m.startswith('dsfd_node') else i[2:] + '.' + pin
            return dict(source=terminal, flat_link_edges=flat, added_edges=add,
                        link_edges=flat+add, crossings=crossings)
        raise ValueError(('unresolved data bit', net, reader))

    nodes = {}
    for i in p.insts:
        if i['module'].startswith('dsfd_node'):
            n = {}
            for pin in 'ab':
                bb = bits(i['conns'][pin])
                allbits = [back(n, i['inst'], 'return') for n in bb]
                assert len({(v['source'],v['flat_link_edges'],v['added_edges']) for v in allbits}) <= 1, ('split return word',i['inst'],pin)
                b = allbits[-1] if bb else dict(source='zero.'+i['inst']+'.'+pin, flat_link_edges=0, added_edges=0, link_edges=0, crossings=[])
                n[pin], n['link_'+pin] = b['source'], b['link_edges']
                n['evidence_'+pin] = b
            nodes[i['inst'][2:]] = n
    cf = next(i for i in p.insts if i['module'] == 'dsfd_cfifo_crs4')
    root = back(bits(cf['conns']['ri'])[-1], cf['inst'], 'return')
    topo = dict(master=spec['top'].removesuffix('_l4'), r1_skew=True,
                win=RP.WIN, rst=RP.RST, cf=RP.CF, nodes=nodes,
                root=root['source'], root_link=root['link_edges'], root_evidence=root)
    stations = {}
    for i in p.insts:
        if i['module'] == 'ot_v41_rom_elem_q_qxpq_w10':
            paths = {}
            for pin, ex in i['conns'].items():
                if pin.startswith('xs_'):
                    # All bits of one semantic input must keep their relative alignment.
                    bs = [back(n, i['inst'], 'station') for n in bits(ex)]
                    signatures = {(b['source'], b['flat_link_edges'], b['added_edges']) for b in bs}
                    paths[pin] = dict(paths=[dict(source=a, flat_link_edges=b, added_edges=c)
                                                  for a,b,c in sorted(signatures)], aligned=len(signatures)==1)
            added = {b['added_edges'] for pin in paths.values() for b in pin['paths']}
            control = {pin: back(bits(i['conns'][pin])[-1], i['inst'], 'control') for pin in ['go', 'cfg_v']}
            stations[i['inst'][2:]] = dict(inputs=paths, control=control, added_edges=sorted(added),
                                          all_x_inputs_equal_added_edges=len(added)==1)
    sources = {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
               for f in spec['sources']+spec['child_sources']}
    return dict(schema='opentallas.s81.frame_schedule.v1', source_sha256=sources,
                spec=str(Path(specfile).relative_to(ROOT)), added_edges_per_crossing=p.A,
                station_inputs=stations, topology=topo,
                qualification='EXTRACTED ONLY: emission/go/reset alignment, legalised return calendar and actual frame bench required')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('spec',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    d=extract(a.spec.resolve())
    a.out.write_text(json.dumps(d,indent=1)+'\n')
    print('station added edges', {k:v['added_edges'] for k,v in d['station_inputs'].items()})
    print('return nodes',len(d['topology']['nodes']), 'root_link',d['topology']['root_link'])
