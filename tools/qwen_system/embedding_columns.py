"""Real shoreline reservation for four embedding engines, before relay creation.

The caller supplies measured physical engine width; this does not shrink any
existing tile corridor or insert an unimplemented controller crossing. Engine
interfaces must subsequently be bound by the system builder before routing.
"""


def insert_columns(v, model, width_um, height_um=2000., master='qfd_emb_strip_narrow92'):
    if model.get('relay_plan') or any(i.kind == 'relay' or i.name.startswith('dr_') for i in model['insts']):
        raise ValueError('embedding columns must precede relay placement')
    if 'embedding_columns' in model:
        raise ValueError('embedding columns already inserted')
    width = v.up(width_um, v.GX)
    height = v.up(height_um, v.GY)
    die, g = model['die'], model['geo']
    new_w = die['w'] + 2 * width
    area = new_w * die['h'] / 1e6
    # 26 x 33 mm field; orientation may swap, but both linear limits apply.
    if sorted((new_w, die['h']))[0] > 26000. + 1e-6 or sorted((new_w, die['h']))[1] > 33000. + 1e-6:
        raise ValueError(f'embedding outline {new_w:.3f} x {die["h"]:.3f} um exceeds 26 x 33 mm')
    if area > die['budget_mm2'] + 1e-9:
        raise ValueError(f'embedding outline area {area:.6f} exceeds {die["budget_mm2"]} mm2')
    west, east, eps = g['x_arr_w'], g['x_eband'], 1e-6
    left_shift = lambda x: 2 * width if x >= east - eps else width if x >= west - eps else 0.
    right_shift = lambda x: 2 * width if x > east + eps else width if x > west + eps else 0.
    planned = []
    for stack, landing in model['lfifos'].items():
        side = 'W' if landing.x < west else 'E'
        x = west if side == 'W' else east + width
        y = v.dn(landing.y + (landing.h - height) / 2, v.GY)
        if y < landing.y - eps or y + height > landing.y + landing.h + eps:
            raise ValueError(f'embedding engine {stack} exceeds actual stack vertical span')
        # Check against every actual shifted abstract, including controller and CDC.
        for other in model['insts']:
            ox = other.x + left_shift(other.x)
            if min(x + width - v.SHAVE, ox + other.w) > max(x, ox) + eps and min(y + height - v.SHAVE, other.y + other.h) > max(y, other.y) + eps:
                raise ValueError(f'embedding engine {stack} overlaps {other.name}')
        planned.append((stack, side, x, y))
    if len(planned) != 4:
        raise ValueError(f'expected four real HBM stack spans, got {len(planned)}')
    # Mutate only after all outline and occupancy checks succeed.
    for it in model['insts']:
        it.x = round(it.x + left_shift(it.x), 3)
    for region in model['regions']:
        a, b, c, d = region['rect']
        region['rect'] = [round(a + left_shift(a), 3), b, round(c + right_shift(c), 3), d]
    for key in ('x_arr_w', 'x_spine', 'x_vch', 'x_arr_e', 'x_eband'):
        g[key] = round(g[key] + left_shift(g[key]), 3)
    old_col_x = model['col_x']
    model['col_x'] = lambda col: old_col_x(col) + (width if col < 32 else 2 * width)
    engines = {}
    for stack, side, x, y in planned:
        engine = v.Inst(f'emb_engine_{stack}', master, x, y, width-v.SHAVE, height-v.SHAVE,
                        kind='embedding_engine', region='strip', domain='stream')
        model['insts'].append(engine)
        engines[stack] = engine
        model['regions'].append(dict(name=engine.name, kind='strip', rect=[x,y,x+width,y+height]))
    die.update(w=round(new_w, 3), mm2=round(area, 6), margin_mm2=round(die['budget_mm2']-area, 6))
    model['embedding_columns'] = dict(width_um=width, height_um=height,
        engines=engines, added_outline_mm2=round(2*width*die['h']/1e6, 6),
        linear_reticle_limits_um=[26000,33000], physical_closed=False,
        interfaces_bound=False, added_pc_core_stations_forward=1,
        added_pc_core_stations_return=1, proposed_parallel_batch_added_edges=2,
        latency_adopted=False, pcport_slot='inside measured controller frame; not yet bound',
        obligations=['bind actual strip master ports and hub class link',
                     'implement and measure command/response CDC to actual PC ports',
                     'measure code/scale arbitration phase before headline latency',
                     'include added stations in model and RTL before routing'])
    return engines
