"""Opt-in composition of measured CDC hard elements, before die relays.

Ports i/o are physical bus groups, not additional RTL ports: they contain
payload, valid and the credit travelling in the opposite direction.
"""
SLOT_W = 626.832
CDC_WH = (302.4, 388.8)
COLL_WH = (324.0, 540.0)
GAP = 21.6
CDC_RECORD = 'results/closure_loop/qfd_cdc1024_a-1a9caff1a-tc/verdict.json'
COLL_RECORD = 'results/closure_loop/qfd_coll_xfifo_b-66fd85cda-tc/verdict.json'
CHANNELS = {'ucie_tx': 'ut', 'ucie_rx': 'ur', 'serdes_tx': 'st', 'serdes_rx': 'sr'}


def sizing():
    return dict(schema='opentallas.qwen.split_io_cdc.v1',
                target='Qwen3-8B ROM', macs_per_cycle=0,
                payload_bytes_per_cycle_per_tile=128,
                boundary_bits_per_tile_face=1026,
                fifo_bits_per_tile=1024 * 8,
                replicas=4, shared_data_muxes=0, clock_pairs_per_tile=1,
                cdc_tile_um=list(CDC_WH), collective_um=list(COLL_WH),
                slot_um=[SLOT_W, 1563.816],
                prior_slot_um=[400.008, 1563.816],
                added_reserved_area_mm2=(SLOT_W - 400.032) * 1563.816 / 1e6,
                hard_area_mm2=(4 * CDC_WH[0] * CDC_WH[1] + COLL_WH[0] * COLL_WH[1]) / 1e6,
                pin_layers=['M4', 'M6'], pin_pitch_um=0.048,
                face_tracks_available=int(2 * (CDC_WH[1] - 8) / 0.048),
                face_tracks_required=1026,
                pipeline=2, cycles_added_vs_pipe2_predecessor=0,
                cycles_added_vs_pipe0_predecessor=2,
                credit_initial=4,
                cdc_parameters=dict(W=1024, IBUF=4, OCRED=4, AD=8, PIPE=2),
                collective_parameters=dict(WSQ=546, WCQ=516, N=4, MB=513, CQ_AD=64, PIPE=0),
                collective_initial_forward_credits=4, collective_engine_ib_required=4,
                qualification='child TT/FF/DRC and exactness qualified; die routing, reset/fault integration and relay cost remain separate gates')


def integrate(v, m):
    old = m['io']['xfifo']
    if old.w < SLOT_W - v.SHAVE - 0.01:
        raise ValueError('split CDC slot must be sized before the floorplan is built')
    by = {i.name: i for i in m['insts']}
    layout = {'ut': (0, 0), 'ur': (1, 0), 'st': (0, 1), 'sr': (1, 1)}
    tiles = {}
    for ch, (col, row) in layout.items():
        tiles[ch] = v.Inst('io_cdc_' + ch, 'qfd_cdc1024',
                           old.x + col * (CDC_WH[0] + GAP),
                           old.y + row * (CDC_WH[1] + GAP), *CDC_WH,
                           kind='io_cdc_tile', region='io', domain='cdc')
    coll = v.Inst('io_coll_cdc', 'qfd_coll_xfifo_b', old.x,
                  old.y + 2 * (CDC_WH[1] + GAP), *COLL_WH,
                  kind='io_cdc_tile', region='io', domain='cdc')
    fresh = list(tiles.values()) + [coll]
    for a in fresh:
        if a.x + a.w > old.x + old.w + .01 or a.y + a.h > old.y + old.h + .01:
            raise ValueError('split CDC tile exceeds reserved slot: ' + a.name)
        for b in m['insts']:
            if b is old:
                continue
            if min(a.x + a.w, b.x + b.w) > max(a.x, b.x) + .01 and min(a.y + a.h, b.y + b.h) > max(a.y, b.y) + .01:
                raise ValueError('split CDC overlap: ' + a.name + ' / ' + b.name)
    m['insts'] = [i for i in m['insts'] if i is not old] + fresh
    # Clock identities come from the net's physical role, not the monolith's
    # historical cks/ckd names (which disagreed with its RTL).
    ckmap = {'ck': [(tiles['ut'].name, 'wclk'), (tiles['ur'].name, 'rclk'),
                    (tiles['st'].name, 'wclk'), (tiles['sr'].name, 'rclk'), (coll.name, 'ck')],
             'cku': [(tiles['ut'].name, 'rclk'), (tiles['ur'].name, 'wclk')],
             'ckd': [(tiles['st'].name, 'rclk'), (tiles['sr'].name, 'wclk')],
             'cks': [(coll.name, 'ckd')]}
    portmap = {}
    for name, short in CHANNELS.items():
        portmap['i_' + name] = (tiles[short].name, 'i')
        portmap['o_' + name] = (tiles[short].name, 'o')
    for p in ('i_seq_coll', 'o_seq_coll', 'i_coll_seq', 'o_coll_seq'):
        portmap[p] = (coll.name, p)
    buses, peer_widths = [], {}
    for bid, cls, bits, eps in m['buses']:
        ne = []
        hit = False
        for inst, port in eps:
            if inst != old.name:
                ne.append((inst, port))
            elif cls == 'clock_trunk':
                ne.extend(ckmap[port])
            else:
                ne.append(portmap[port])
                hit = True
        if hit and any(p in portmap and 'seq' not in p for inst, p in eps if inst == old.name):
            if bits != 1024:
                raise ValueError('unexpected IO payload width for ' + bid)
            bits += 2   # payload + valid + returning credit, on both faces
            for inst, port in ne:
                if inst in by and inst != old.name:
                    peer_widths[(by[inst].master, port)] = bits
        if hit and (old.name, 'i_coll_seq') in eps:
            bits = 517  # engine pushes data516 + valid; no ready/credit pin
            for inst, port in ne:
                if inst in by and inst != old.name:
                    peer_widths[(by[inst].master, port)] = bits
        buses.append((bid, cls, bits, ne))
    m['buses'] = buses
    for crossing in m['r18']['crossings']:
        if crossing['fifo'] == old.name:
            bus = crossing['bus']
            crossing['fifo'] = tiles[CHANNELS[bus]].name if bus in CHANNELS else coll.name
            crossing['bits'] = next(bits for bid, cls, bits, eps in buses if bid == bus)
    m['r18']['io_cdc_tiles'] = [i.name for i in fresh]
    model = sizing()
    model.update(instances={i.name: i.d() for i in fresh},
                 predecessor=old.d(), port_map=portmap,
                 clock_map=ckmap, records=[CDC_RECORD, COLL_RECORD],
                 physical_ports={'i': {'i_d': 1024, 'i_v': 1, 'i_cr': 1},
                                 'o': {'o_d': 1024, 'o_v': 1, 'o_cr': 1}},
                 physical_group_maps={
                     'qfd_cdc1024': {
                         'i': [(0, 1024, 'i_d', 'input'), (1024, 1, 'i_v', 'input'), (1025, 1, 'i_cr', 'output')],
                         'o': [(0, 1024, 'o_d', 'output'), (1024, 1, 'o_v', 'output'), (1025, 1, 'o_cr', 'input')]},
                     'qfd_coll_xfifo_b': {
                         'i_seq_coll': [(0, 546, 'i_seq_coll', 'input'), (546, 1, 'i_seq_coll_v', 'input'), (547, 1, 'i_seq_coll_cr', 'output')],
                         'o_seq_coll': [(0, 546, 'o_seq_coll', 'output'), (546, 1, 'o_seq_coll_v', 'output'), (547, 1, 'o_seq_coll_cr', 'input')],
                         'i_coll_seq': [(0, 516, 'i_coll_seq', 'input'), (516, 1, 'i_coll_seq_v', 'input')],
                         'o_coll_seq': [(0, 516, 'o_coll_seq', 'output'), (516, 1, 'o_coll_seq_v', 'output'), (517, 1, 'o_coll_seq_cr', 'input')]}},
                 reset_fault_gate='unconnected on predecessor floorplan as well; bind all wrst_n/rrst_n and sticky faults in the production netlist before adoption')
    m['split_io_cdc'] = model
    base = v.masters

    def masters(model, k=1, port_bits=None):
        out = base(model, k, port_bits)
        out.pop(old.master, None)
        for (master, p), bits in peer_widths.items():
            spec = out[master].ports[p]
            out[master].ports[p] = spec[:1] + (bits,) + spec[2:]
        mm = v.Master('qfd_cdc1024', *CDC_WH, 7,
                      'ot_qwen_die_cdc_ch W1024 PIPE2; qfd_cdc1024_a-1a9caff1a-tc')
        mm.face('i', 1026, 'W', 'M4', 194.4, 1)
        mm.face('o', 1026, 'E', 'M4', 194.4, 1)
        for j, p in enumerate(('wclk', 'rclk', 'wrst_n', 'rrst_n', 'w_fault', 'r_fault')):
            mm.face(p, 1, 'N', 'M5', 100 + j * 10, 1)
        out[mm.name] = mm
        cm = v.Master(coll.master, *COLL_WH, 7,
                      'ot_qwen_die_coll_xfifo; qfd_coll_xfifo_b-66fd85cda-tc')
        for p, bits, face, centre in (
                ('i_seq_coll', 548, 'W', 135), ('o_coll_seq', 518, 'W', 405),
                ('o_seq_coll', 548, 'E', 135), ('i_coll_seq', 517, 'E', 405)):
            cm.face(p, bits, face, 'M4', centre, 1)
        for j, p in enumerate(('ck', 'ckd', 'rst_n', 'fault_ck', 'fault_ckd')):
            cm.face(p, 1, 'N', 'M5', 100 + j * 10, 1)
        out[cm.name] = cm
        return out
    v.masters = masters
