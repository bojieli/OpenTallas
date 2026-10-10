"""HGI-1 normative record dispatch on the generic HBM die (hgi-takeover, 2026-10-09).

Opt-in generator key ``hgi_dispatch`` (a list of unit keys).  For each listed generic unit it declares the two die buses
from the sequencer (ot_hgi_seq v1.0, hfd_cmdproc) to that unit, at the NORMATIVE dispatch ABI:

  ot_hgi_seq  u_v[k] / u_rdy[k]; d_hdr 128; d_desc = 7 x 256 effective {I,R,O,D,C,B,A}; d_n = 7 x 21; d_pos1 21;
              u_done[k] / u_fault[k]

Each unit receives only the descriptors its operations read (section 6.6 operand table), so the bus carries
valid + header + its descriptors + their effective n; the return is {ready, done, fault}.  No geometry change, no
constant or folded port: a unit's wrapper must bind every field (tools/hgi_die_integration_check.py).
"""
from math import ceil

DESC_BITS, N_BITS, HDR_BITS = 256, 21, 128
# unit key -> (HGI unit code, die hub block, descriptors used, extra sidebands)
UNITS = {
    'quant':  (4, 'quant', 'AO', ()),                 # FUSED.QDQ_* (A in, O out; scale in-band)
    'coll':   (6, 'coll', 'AOI', (('die_id', 8),)),  # COLL.*: A local, O result, I selected row ids; die id strap (seq rank)
    'argmax': (7, 'mtp', 'AO', (('die_id', 8),)),    # ARGMAX.LOCAL (imm_a in the header; global id = local + RANK * imm_a)
                                                      #   -> ot_hgi_argmax_slot (record adapter + ot_hgi_argmax18_m)
    'idx':    (9, 'hgi_idx', 'ABCDOR', (('pos', 20), ('die_id', 8))),   # IDX unit ot_hgi_idx_unit: TOPK + INDEX frames (G18)
    # hgi-takeover 2026-10-09 (hgi-e2e DIE GAP): every record unit has a die record bus (the payload is a die port, not
    # an internal tap); field sets = hgi-adapters' rec_* ports; one credit per unit; placement per hgi-adapters 22:40
    'sm':     (1, 'cmdproc', 'ABO', ()),                  # ot_hgi_sm_record IN the CP block (drives the SM launch tree)
    'su':     (2, 'su_SW', 'ABCDORI', ()),               # ot_hgi_su_unit at the hfd_su SW centre band (one a die)
    'sfu':    (3, 'sfu_SW', 'ABCO', ()),                 # the SU unit in GLU mode (one a die)
    'att':    (5, 'cmdproc', 'ABCO', (('pos1', 21),)),    # Codex ot_hgi_att_record_adapter: IN the CP block until D4
    'dma':    (8, 'loader', 'AO', (('pos1', 21),)),       # ot_hgi_dma_record + ot_hgi_dma_mover beside the loader
    'hc':     (10, 'hc_SW', 'ABO', ()),                  # ot_hgi_hc_unit (one a die)
}
# effective n carried per unit (default: every descriptor's) and the units that take the 256-bit SU template
NSET = {'sm': 'AB', 'su': 'A', 'sfu': 'A', 'att': 'BC', 'dma': 'AO', 'hc': 'AO'}
SUT_UNITS = {'su', 'att'}
# units whose adapter sits inside the CP block: their record bus is a CP-die port bound in the CP view, not a die net
INTERNAL_UNITS = {'sm', 'att'}
RETURN_FIELDS = [('ready', 1), ('done', 1), ('fault', 1)]
# units that decode a static MD field (coll: word 46 coll_group_size) get the 40-bit config station bus
# {cfg_commit, cfg_v, cfg_addr[5:0], cfg_data[31:0]} (ot_hgi_cfg_stn / ot_hgi_cfg_rx)
CFG_UNITS = {'coll'}
CFG_BITS = 40
# units that are VM packet clients of ot_hgi_vm_unit (hfd_vm): {v, req 337} up, {v, rsp 273} down; one outstanding
VM_CLIENTS = ['cp', 'quant', 'idx', 'argmax', 'su', 'sfu', 'hc', 'dma']      # 'cp' = the command processor's VM reads (ot_hgi_cp_die vr_*);
#   argmax: A from VM / O {value, id} to VM (HGI 6.6), ot_hgi_argmax_slot vmq / vmr
# mtp-lead 2026-10-09 / hgi-takeover decision (3): the ARGMAX unit is a VM client and carries the die_id sideband (683
# -> 691) only on the single-CP die ('cp' in hgi_dispatch: the sequencer is the record producer and knows the rank).
# On the interim legacy-CP presets (r25gm / r25g4m: MX1 band relays a 683-bit record, no sequencer) neither applies.
SINGLE_CP_ONLY = {'argmax': ('die_id',)}


def vm_clients(units):
    return [u for u in VM_CLIENTS if u in units and (u != 'argmax' or 'cp' in units)]
VMQ_BITS, VMR_BITS, VMSTAT_BITS = 338, 274, 19
HGI_VM_SLOT = (1399.656, 1080.0)       # 64 macros 174.7 x 70.5 um on a 7 x 10 grid with 2.16 um halos (1,261 x 758 um) + logic
HGI_IDX_SLOT = (640.008, 600.48)        # Codex TOPK K2048 slot (175,534 um2 core) + VM stream engines
LD_MEM_HGI = (346, 293)                # ot_hfd_loader_kport lq / lr per stack
LCP_BITS, CPL_BITS = 419, 222
QID = dict(SW=0, NW=1, SE=2, NE=3)       # hfd_su inject-ownership strap values           # ot_hgi_loader_cp link        # 64 x 174.7 x 70.5 um macros (0.79 mm2) + logic at ~60 %


def fields(unit, units=None):
    code, _, desc, side = UNITS[unit]
    f = [('valid', 1), ('header', HDR_BITS)]
    if unit in SUT_UNITS:
        f += [('sut', 256)]
    f += [(f'desc_{d}', DESC_BITS) for d in desc]
    f += [(f'n_{d}', N_BITS) for d in NSET.get(unit, desc)]
    single = units is not None and 'cp' in units
    f += [x for x in side if single or x[0] not in SINGLE_CP_ONLY.get(unit, ())]
    return f


def layout(fs):
    off, rows = 0, []
    for name, bits in fs:
        rows.append(dict(name=name, lo=off, hi=off + bits - 1))
        off += bits
    return rows, off


def model(hub, units, reach_um=504.0, unit_block=None):
    rows = []
    unit_block = unit_block or {}     # mtp-lead: variant 'hgi_unit_block' (e.g. argmax -> 'mtp_am' in a split slot)
    for u in [x for x in units if x in UNITS]:
        code, blk, desc, _ = UNITS[u]
        blk = unit_block.get(u, blk)
        if blk not in hub:
            raise ValueError(f'hgi_dispatch: hub block {blk} for unit {u} not on this die')
        cmd, cbits = layout(fields(u, units))
        ret, rbits = layout(RETURN_FIELDS)
        s, t = hub['cmdproc'], hub[blk]
        dist = abs(s.x + s.w / 2 - t.x - t.w / 2) + abs(s.y + s.h / 2 - t.y - t.h / 2)
        relays = max(0, ceil(dist / reach_um) - 1)
        rows.append(dict(unit=u, code=code, block=blk, descriptors=desc, command_bits=cbits, return_bits=rbits,
                         command_fields=cmd, return_fields=ret, centre_distance_um=round(dist, 2),
                         relay_edges_each_way=relays, dispatch_to_unit_edges=1 + relays,
                         fp32_macs_per_cycle=0, memory_bytes_per_cycle=0, records_per_cycle=1))
    return dict(schema='opentallas.hgi_die_dispatch.v1', abi='ot_hgi_seq v1.0 (claude/hbm-forks-20261009 bf44b3032)',
                units=rows, total_signal_bits=sum(r['command_bits'] + r['return_bits'] for r in rows),
                scope='die graph declaration; unit wrappers must bind every field (no ties) before adoption')


# ECO pin plan on the closed cmdproc split view (hbm-forks owns hfd_cmdproc; it re-routes the half that takes them):
# (band, face, layer, fraction along the face, pitch in tracks).  coll / quant sit north of the cmdproc (N half, N face);
# the MTP slot (ARGMAX) is south (S half, S face, between the MTP pair at 0.30 / 0.70).
CP_PINS = {'coll': ('hfd_cmdproc_n', 'N', 'M5', 0.25), 'quant': ('hfd_cmdproc_n', 'N', 'M5', 0.70),
           'argmax': ('hfd_cmdproc_s', 'S', 'M5', 0.50), 'idx': ('hfd_cmdproc_n', 'N', 'M7', 0.50)}


def split_extra_ports(units):
    """split_extra_ports entries for hfd_cmdproc (merge into the variant before build)."""
    out = {}
    for u in [x for x in units if x in UNITS and x in CP_PINS]:     # legacy CP split only (the single CP has none)
        band, face, layer, frac = CP_PINS[u]
        cbits = layout(fields(u, units))[1]
        out[f't_hgi_{u}'] = (band, cbits, face, layer, frac, 2)
        out[f'f_hgi_{u}'] = (band, 3, face, layer, round(frac + 0.04, 3), 2)
        if u in CFG_UNITS:
            out[f't_hgi_cfg_{u}'] = (band, CFG_BITS, face, layer, round(frac + 0.08, 3), 2)
    if vm_clients(units):
        out['f_hgi_vmstat'] = ('hfd_cmdproc_n', VMSTAT_BITS, 'N', 'M5', 0.90, 2)
    return out


def variant(base, units):
    """base variant dict + hgi_dispatch + the cmdproc ECO pins."""
    v = dict(base, hgi_dispatch=list(units))
    ex = {k: dict(x) for k, x in (base.get('split_extra_ports') or {}).items()}
    alias = base.get('cp_band_alias') or {}     # mtp-lead: a replaced CP band (e.g. the MX1 south view) keeps the plan
    ex.setdefault('hfd_cmdproc', {}).update({k: (alias.get(t[0], t[0]),) + tuple(t[1:])
                                             for k, t in split_extra_ports(units).items()})
    v['split_extra_ports'] = ex
    if 'cp' in units:
        # hgi-takeover die gap 4: ONE command-processor block (ot_hgi_cp_die) instead of the legacy N / S split; the
        # loader <-> CP link (lcp 419 / cpl 222) replaces the legacy program-store bus; the loader memory lanes carry
        # the native service protocol (lq 346 / lr 293 per stack, ot_hfd_loader_kport)
        v['split_masters'] = {k: x for k, x in (base.get('split_masters') or {}).items() if k != 'hfd_cmdproc'}
        v['split_extra_ports'] = {k: x for k, x in v['split_extra_ports'].items() if k != 'hfd_cmdproc'}
        v['ld_mem'] = LD_MEM_HGI
        v['split_x_new_ports'] = dict(base.get('split_x_new_ports') or {}, lq=LD_MEM_HGI[0], lr=LD_MEM_HGI[1])
    if vm_clients(units):
        # the HGI-1 VM (ot_hgi_vm_unit: 1 MiB, 64 ECC macros 0.79 mm2) gets its own low spine slot under the loader;
        # the legacy hfd_vm tiles keep the x multicast root and the SU / router feeds
        v['spine_slots_low'] = dict(base.get('spine_slots_low') or {}, hgi_vm=HGI_VM_SLOT)
        v['spine_slot_masters'] = dict(base.get('spine_slot_masters') or {}, hgi_vm='hfd_hgi_vm')
        v['spine_slot_domains'] = dict(base.get('spine_slot_domains') or {}, hgi_vm='stream_1p2')
    if 'cp' in units and 'argmax' in units and 'mtp' in (base.get('spine_slot_split') or {}):
        # decision (3): on the single-CP die the slot's ARGMAX instance is the dispatched unit hfd_hgi_am
        # (ot_hgi_argmax_slot: record adapter + engine + VM client, 691-bit record), not the bare closed engine view;
        # it takes the slot's full height beside the controller (180 x 200.88; the engine view alone is 180 x 140)
        parts = tuple((k, 'hfd_hgi_am', (wh[0], 200.88)) if k == 'mtp_am' else (k, mst, wh)
                      for k, mst, wh in base['spine_slot_split']['mtp'])
        v['spine_slot_split'] = dict(base['spine_slot_split'], mtp=parts)
    if 'idx' in units:
        v['spine_slots_low'] = dict(v.get('spine_slots_low') or base.get('spine_slots_low') or {}, hgi_idx=HGI_IDX_SLOT)
        v['spine_slot_masters'] = dict(v.get('spine_slot_masters') or base.get('spine_slot_masters') or {}, hgi_idx='hfd_hgi_idx')
        v['spine_slot_domains'] = dict(v.get('spine_slot_domains') or base.get('spine_slot_domains') or {}, hgi_idx='stream_1p2')
    return v


def install(m, buses, paths, units):
    hub = m['hub']
    rec = model(hub, units, unit_block=(m.get('variant') or {}).get('hgi_unit_block'))
    names = {b[0] for b in buses}
    cp = hub['cmdproc'].name
    for r in rec['units']:
        if r['unit'] in INTERNAL_UNITS:          # the adapter is inside the CP block: a CP-die port, no die net
            continue
        peer = hub[r['block']].name
        for name, bits, eps in ((f"hgi_{r['unit']}_cmd", r['command_bits'], [(cp, f"t_hgi_{r['unit']}"), (peer, 'f_hgi_cmdproc')]),
                                (f"hgi_{r['unit']}_ret", r['return_bits'], [(peer, 't_hgi_cmdproc'), (cp, f"f_hgi_{r['unit']}")])):
            if name in names:
                raise ValueError(f'duplicate hgi dispatch bus {name}')
            buses.append((name, 'hub', bits, eps))
            paths[name] = [name]
            names.add(name)
        if r['unit'] == 'coll':
            # A / O effective bases of a collective record -> the SU quarters' inject / deliver addressing (80 b each)
            for q in ('SW', 'NW', 'SE', 'NE'):
                if f'su_{q}' in hub:
                    name = f'hgi_vmaddr_{q}'
                    buses.append((name, 'hub', 80, [(peer, f't_hgi_vmaddr_{q}'), (hub[f'su_{q}'].name, 'f_hgi_vmaddr')]))
                    paths[name] = [name]
                    # inject-ownership strap (hbm-forks 504aba259): quarter qid drives inject flit i iff i mod 4 == qid;
                    # tied per instance (SW 0, NW 1, SE 2, NE 3), pins su/rtl/strap_pins.tcl
                    name = f'hgi_qid_{q}'
                    buses.append((name, f'strap:{QID[q]}', 2, [(hub[f"su_{q}"].name, 'qid')]))
                    paths[name] = [name]
        if r['unit'] in CFG_UNITS:
            name = f"hgi_cfg_{r['unit']}"
            buses.append((name, 'hub', CFG_BITS, [(cp, f"t_hgi_cfg_{r['unit']}"), (peer, 'f_hgi_cfg')]))
            paths[name] = [name]
            names.add(name)
    vm_cl = vm_clients(units)
    ublk = (m.get('variant') or {}).get('hgi_unit_block') or {}
    if vm_cl and 'hgi_vm' in hub:
        vm = hub['hgi_vm'].name
        for u in vm_cl:
            peer = hub['cmdproc'].name if u == 'cp' else hub[ublk.get(u, UNITS[u][1])].name
            for name, bits, eps in ((f'hgi_vmq_{u}', VMQ_BITS, [(peer, 't_hgi_vmq'), (vm, f'f_hgi_{u}')]),
                                    (f'hgi_vmr_{u}', VMR_BITS, [(vm, f't_hgi_{u}'), (peer, 'f_hgi_vmr')])):
                buses.append((name, 'hub', bits, eps)); paths[name] = [name]
        buses.append(('hgi_vmstat', 'hub', VMSTAT_BITS, [(vm, 't_hgi_vmstat'), (cp, 'f_hgi_vmstat')]))
        paths['hgi_vmstat'] = ['hgi_vmstat']
        rec['vm_clients'] = vm_cl
    if 'cp' in units and 'loader' in hub:
        ld = hub['loader'].name
        buses.append(('hgi_lcp', 'hub', LCP_BITS, [(ld, 't_hgi_cp'), (cp, 'f_hgi_loader')])); paths['hgi_lcp'] = ['hgi_lcp']
        buses.append(('hgi_cpl', 'hub', CPL_BITS, [(cp, 't_hgi_loader'), (ld, 'f_hgi_cp')])); paths['hgi_cpl'] = ['hgi_cpl']
    m['hgi_dispatch'] = rec
    m['notes'].append('HGI normative dispatch buses (hgi_dispatch): declared; per-unit wrappers bind them before adoption.')
    return rec
