"""Plan real per-PC embedding composites inside existing controller reservations.

This is deliberately a geometry and boundary inventory. It does not turn an
unbound native command provider or a missing protected PHY sector into a wire.
A system builder must bind those providers and use actual routed pin coordinates
before replacing the old controller parent and inserting stations.
"""
import math


def plan_slots(v, model, width_um=247.536, height_um=370.44):
    if not model.get('embedding_columns'):
        raise ValueError('insert actual embedding columns before planning PC slots')
    reserved_w, reserved_h = v.up(width_um, v.GX), v.up(height_um, v.GY)
    slots = []
    parents = {it.name for it in model['ctrls'].values()}
    for stack, ct in model['ctrls'].items():
        cds = model['cdcs'][stack]
        if len(cds) != 32:
            raise ValueError(f'{stack}: expected32 real native KV CDC slots')
        engine = model['embedding_columns']['engines'][stack]
        # The old parent abstract excludes SHAVE, whereas its reserved region
        # spans CTRL_W. Take the reservation, not the undersized parent abstract.
        x0, y0 = ct.x, ct.y
        x1, y1 = ct.x + v.CTRL_W, ct.y + ct.h + v.SHAVE
        if reserved_w > x1 - x0 + 1e-6:
            raise ValueError(f'{stack}: composite exceeds controller reservation')
        pitch = v.dn((y1 - y0) / 32, v.GY)
        if pitch < reserved_h - 1e-6:
            raise ValueError(f'{stack}: 32 full-height composite frames do not fit')
        for pc in range(32):
            y = y0 + pc * pitch + v.dn((pitch - reserved_h) / 2, v.GY)
            if y + height_um > y1 + 1e-6:
                raise ValueError(f'{stack}.{pc}: exceeds reserved stack span')
            for other in model['insts']:
                if other.name in parents:
                    continue
                if min(x0 + width_um, other.x + other.w) > max(x0, other.x) + 1e-6 and min(y + height_um, other.y + other.h) > max(y, other.y) + 1e-6:
                    raise ValueError(f'{stack}.{pc}: overlaps {other.name}')
            # A lower bound on vertical separation, independent of chosen pin
            # packing. Exact endpoints must come from the closed LEF inventory.
            vertical = max(0., y - (engine.y + engine.h), engine.y - (y + height_um))
            slots.append(dict(name=f'emb_pc_{stack}_{pc}', stack=stack, pc=pc,
                rect_um=[x0, y, x0 + width_um, y + height_um],
                native_KV_CDC=cds[pc].name, cmd_bits=288, return_bits=260,
                reserved_frame_um=[reserved_w, reserved_h],
                actual_clock_domains=['core833.333ps', 'HBM1024ps'],
                minimum_vertical_wire_um=round(vertical, 3),
                minimum_350um_segments=math.ceil(vertical / 350.),
                required_providers=['nativecmd32/readcredit3', 'qualified288bprotectedPHYsector',
                                    'actualKVlandingmetadata', 'JEDECcommand/writepayloadPHYbinding'],
                physical_pin_binding=False))
    return dict(schema='opentallas.embedding_PC_slots.v1', slots=slots,
        replica_count=len(slots), old_controller_parents_retained=True,
        native_KV_CDC_retained=True, actual_frames_only=True,
        two_edge_station_estimate_is_not_qualification=True,
        adoption_credit=0, physical_closed=False)
