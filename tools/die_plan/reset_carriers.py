"""Default-off reset-only carrier registration; reviewed candidate 594c4072d.
Call register(B) just before build_buses' EMPTY_PARTITION loop. Existing emit_type
materializes RT.rtl_lines with the normal delivered clock/reset/START ports.
"""
def register(B):
    names=B.ab.get('reset_carrier_parts',[])
    if not isinstance(names,list) or not all(isinstance(x,str) for x in names) or len(names)!=len(set(names)):
        raise ValueError('reset_carrier_parts must be unique exact partition names')
    if not names:return []
    if B.plan.get('reset',{}).get('release')!='wavefront':
        raise ValueError('reset carriers require existing wavefront reset implementation')
    try:
        from . import reset_tree as RT
    except ImportError:
        import reset_tree as RT
    P=B.wavefront_plan();W=RT.wf_plan(P);rows=[]
    for p in names:
        if p not in B.parts or p not in W['parts']:raise ValueError('reset carrier not in solved wavefront: '+p)
        t=B.types[B.parts[p]['type']]
        if p in B.members:raise ValueError('reset carrier already contains source cells or transport: '+p)
        if t.get('hard') or t.get('hard_cores') or t.get('buses') or t.get('ft_slots') or t.get('internal_stations') or t.get('pads'):
            raise ValueError('reset carrier has payload hardware: '+p)
        if not t.get('contents') or any(c.get('cells')!=0 for c in t['contents']):
            raise ValueError('reset carrier contains nonzero/unknown source logic: '+p)
        tn=B.parts[p]['type'];T=RT.for_type(P,tn);lines=RT.rtl_lines(T)
        if not T.get('relays') or not any('ot_dp_' in line and '(.clk(clk)' in line for line in lines):
            raise ValueError('reset carrier does not emit actual registered reset logic: '+p)
        rows.append(dict(part=p,type=tn,source_cells=0,payload_bits=0,
                         reset_relays=len(T['relays']),entry=T['entry'],depth=T['depth'],
                         wavefront=W['parts'][p],rtl='existing reset_tree.rtl_lines, no alternate implementation'))
    # Validate all requests before mutating any binder state.
    for r in rows:B.members[r['part']]=[]
    B.reset_carriers=rows
    return rows
