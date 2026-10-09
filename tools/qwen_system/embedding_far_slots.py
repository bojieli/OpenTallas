"""Reserve real class endpoint frames in the added embedding columns.

The endpoint is separate from the existing KV landing. No native KV FIFO space
is reclaimed and no hub/PHY provider is synthesized from an abstract bus name.
Actual master views and the qualified native providers still gate binding.
"""


def insert_far_slots(v, model, width_um=92.016, height_um=1401.84, master='qfd_emb_far92'):
    columns = model.get('embedding_columns')
    if not columns:
        raise ValueError('embedding columns must be installed first')
    if model.get('relay_plan') or any(i.kind == 'relay' for i in model['insts']):
        raise ValueError('class endpoints must precede relays')
    if 'embedding_far_slots' in model:
        raise ValueError('class endpoint slots already installed')
    if abs(v.up(width_um,v.GX)-width_um)>1e-6 or abs(v.up(height_um,v.GY)-height_um)>1e-6:
        raise ValueError('class endpoint frame must use actual lattice dimensions')
    if width_um > columns['width_um'] + 1e-6:
        raise ValueError('class endpoint does not fit added column width')
    planned=[]
    for stack, engine in columns['engines'].items():
        x,y=engine.x,v.dn(engine.y-height_um,v.GY)
        ct=model['ctrls'][stack]
        if y < ct.y -1e-6 or y+height_um > ct.y+ct.h+v.SHAVE+1e-6:
            raise ValueError(f'{stack}: class endpoint exceeds actual stack span')
        for other in model['insts']:
            if min(x+width_um,other.x+other.w)>max(x,other.x)+1e-6 and min(y+height_um,other.y+other.h)>max(y,other.y)+1e-6:
                raise ValueError(f'{stack}: class endpoint overlaps {other.name}')
        planned.append((stack,x,y))
    slots={}
    for stack,x,y in planned:
        it=v.Inst(f'emb_far_{stack}',master,x,y,width_um,height_um,
                  kind='embedding_far_endpoint',region='strip',domain='stream')
        model['insts'].append(it);slots[stack]=it
        model['regions'].append(dict(name=it.name,kind='strip',rect=[x,y,x+width_um,y+height_um]))
    model['embedding_far_slots']=dict(slots=slots,added_macro_area_mm2=4*width_um*height_um/1e6,
        added_outline_area_mm2=0,physical_closed=False,interfaces_bound=False,
        existing_native_KV_landing_retained=True,
        master_source='rtl/qwen_sys/emb_hbm_20261008/ot_qfd_link_far_bus.sv',
        provider_obligations=['hub actuallink528 bidirectional+forwardedclock',
            'engine actualclass525 bidirectional', 'nativeKV actualclass525 bidirectional',
            'qualifiednativecommand/sector/ordinal/writeledger providers'])
    return slots
