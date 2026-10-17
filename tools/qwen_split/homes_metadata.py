"""Rebase array search and routing regions with source-pinned block homes.

Only rigid horizontal translations of each complete field are supported.
Regions are routing/clock planning envelopes, never physical obstructions.
"""
import copy
import re


def prepare(model, proposed, reserve):
    tiles = {}
    for i in model['insts']:
        match = re.fullmatch(r't_(\d+)_(\d+)', i.name)
        if match:
            tiles.setdefault(int(match[1]), []).append(i)
    if not tiles or 'col_x' not in model or 'regions' not in model:
        return {}, dict(scope='No array search metadata in this model')
    cols = sorted(tiles)
    if cols != list(range(len(cols))) or len(cols) % 2:
        raise ValueError('OT_SPLIT_HOMES: incomplete array column metadata')
    delta = {}
    for c, members in tiles.items():
        ds = {(round(proposed[i.name]['x']-i.x, 6),
               round(proposed[i.name]['y']-i.y, 6)) for i in members}
        if len(ds) != 1 or next(iter(ds))[1] != 0:
            raise ValueError('OT_SPLIT_HOMES: array requires rigid horizontal field translations')
        delta[c] = next(iter(ds))[0]
    half = len(cols)//2
    shifts = [set(delta[c] for c in cols[:half]), set(delta[c] for c in cols[half:])]
    if any(len(s) != 1 for s in shifts):
        raise ValueError('OT_SPLIT_HOMES: nonrigid array field metadata')
    # The column's station and head must follow its actual tiles, including
    # stationary columns. A partial move would leave the planner's lane false.
    for i in model['insts']:
        match = re.fullmatch(r'(?:t|s)_(\d+)_\d+|h_(\d+)', i.name)
        if not match:
            continue
        c = int(match[1] if match[1] is not None else match[2])
        p = proposed[i.name]
        if (abs(p['x']-i.x-delta[c]) > 1e-3 or abs(p['y']-i.y) > 1e-3
                or p['o'] != i.orient):
            raise ValueError('OT_SPLIT_HOMES: tile/station/head field transform mismatch')
    regions = copy.deepcopy(model['regions'])
    removed = []
    new_regions = []
    for r in regions:
        n = r['name']
        if n == 'spine_vchan':
            # A nonrigid core placement does not retain the historical clear
            # full-height channel. Only checked body-empty reserves replace it.
            removed.append(n)
            continue
        if n in ('tile_field_w','tile_field_e') or n.startswith('hchan_') and n.endswith(('_w','_e')):
            dx = delta[0 if n.endswith('_w') else half]
            r['rect'] = [x+dx if k in (0,2) else x for k,x in enumerate(r['rect'])]
        elif re.fullmatch(r'corr_\d+', n):
            dx = delta[int(n[5:])]
            r['rect'] = [x+dx if k in (0,2) else x for k,x in enumerate(r['rect'])]
        elif n.startswith('slab_'):
            name = 'sp_' + n[5:]
            if name not in proposed:
                raise ValueError('OT_SPLIT_HOMES: slab region lacks its actual source instance')
            p = proposed[name]
            r['rect'] = [p['x'],p['y'],p['x']+p['w'],p['y']+p['h']]
        new_regions.append(r)
    fields = {r['name']:r for r in new_regions if r['kind']=='tile_field'}
    if set(fields) != {'tile_field_w','tile_field_e'}:
        raise ValueError('OT_SPLIT_HOMES: missing source field routing regions')
    w,e = fields['tile_field_w']['rect'],fields['tile_field_e']['rect']
    if w[2] >= e[0]:
        raise ValueError('OT_SPLIT_HOMES: inverted field routing envelopes')
    for r in new_regions:
        if r['name']=='spine' and r['kind']=='hub':
            r['rect'] = [w[2],w[1],e[0],w[3]]
    for n,p in reserve.items():
        new_regions.append(dict(name='gfp_reserve_'+n,kind='channel',
            rect=[p['x'],p['y'],p['x']+p['w'],p['y']+p['h']]))
    old_col_x = model['col_x']
    updates = dict(col_x=lambda c:old_col_x(c)+delta[c],regions=new_regions)
    if model.get('corridor_lanes'):
        if len(model['corridor_lanes']) != len(cols):
            raise ValueError('OT_SPLIT_HOMES: incomplete source corridor lanes')
        updates['corridor_lanes'] = [(x+delta[c],width)
            for c,(x,width) in enumerate(model['corridor_lanes'])]
    if 'geo' in model:
        geo = dict(model['geo'])
        geo.update(x_arr_w=w[0],x_spine=w[2],x_arr_e=e[0],x_eband=e[2],spine_w=e[0]-w[2])
        updates['geo'] = geo
    return updates, dict(scope='Array relay search and planning regions only; no routed qualification',
        field_dx_um=[delta[0],delta[half]],columns=len(cols),
        removed_stale_regions=removed,reserve_channel_regions=len(reserve),
        hub_rect=[w[2],w[1],e[0],w[3]],
        actual_obstructions_and_PG_shapes_required=True)
