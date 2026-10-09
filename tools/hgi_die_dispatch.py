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
    'coll':   (6, 'coll', 'AOI', ()),                 # COLL.*: A local, O result, I selected row ids (ROW_GATHER)
    'argmax': (7, 'mtp', 'AO', ()),                   # ARGMAX.LOCAL (imm_a in the header); ot_hgi_argmax18_m in hfd_mtp
    'idx':    (9, 'index_SW', 'ABOR', ()),            # IDX.TOPK A/O/R, EHASH B/O, SELECT O/R (one dispatch point)
}
RETURN_FIELDS = [('ready', 1), ('done', 1), ('fault', 1)]


def fields(unit):
    code, _, desc, side = UNITS[unit]
    f = [('valid', 1), ('header', HDR_BITS)]
    f += [(f'desc_{d}', DESC_BITS) for d in desc]
    f += [(f'n_{d}', N_BITS) for d in desc]
    f += list(side)
    return f


def layout(fs):
    off, rows = 0, []
    for name, bits in fs:
        rows.append(dict(name=name, lo=off, hi=off + bits - 1))
        off += bits
    return rows, off


def model(hub, units, reach_um=504.0):
    rows = []
    for u in units:
        code, blk, desc, _ = UNITS[u]
        if blk not in hub:
            raise ValueError(f'hgi_dispatch: hub block {blk} for unit {u} not on this die')
        cmd, cbits = layout(fields(u))
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
    for u in units:
        band, face, layer, frac = CP_PINS[u]
        cbits = layout(fields(u))[1]
        out[f't_hgi_{u}'] = (band, cbits, face, layer, frac, 2)
        out[f'f_hgi_{u}'] = (band, 3, face, layer, round(frac + 0.04, 3), 2)
    return out


def variant(base, units):
    """base variant dict + hgi_dispatch + the cmdproc ECO pins."""
    v = dict(base, hgi_dispatch=list(units))
    ex = {k: dict(x) for k, x in (base.get('split_extra_ports') or {}).items()}
    ex.setdefault('hfd_cmdproc', {}).update(split_extra_ports(units))
    v['split_extra_ports'] = ex
    return v


def install(m, buses, paths, units):
    hub = m['hub']
    rec = model(hub, units)
    names = {b[0] for b in buses}
    cp = hub['cmdproc'].name
    for r in rec['units']:
        peer = hub[r['block']].name
        for name, bits, eps in ((f"hgi_{r['unit']}_cmd", r['command_bits'], [(cp, f"t_hgi_{r['unit']}"), (peer, 'f_hgi_cmdproc')]),
                                (f"hgi_{r['unit']}_ret", r['return_bits'], [(peer, 't_hgi_cmdproc'), (cp, f"f_hgi_{r['unit']}")])):
            if name in names:
                raise ValueError(f'duplicate hgi dispatch bus {name}')
            buses.append((name, 'hub', bits, eps))
            paths[name] = [name]
            names.add(name)
    m['hgi_dispatch'] = rec
    m['notes'].append('HGI normative dispatch buses (hgi_dispatch): declared; per-unit wrappers bind them before adoption.')
    return rec
