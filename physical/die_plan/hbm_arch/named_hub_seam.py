"""Reserve real pin-register bands for the named NW hub/root proof path."""
import json

def apply(plan, band=17.28):
    P={p['name']:p for p in plan['partitions']}
    T=plan['partition_types']
    a,b=P['NW_hub'],P['root']
    src,dst=T[a['type']],T[b['type']]
    sx,sy=a['origin_um'];sw,sh=src['outline_um']
    rx,ry=b['origin_um'];rw,rh=dst['outline_um']
    if abs(sx+sw-rx)>.001:
        raise ValueError('NW hub and root must actually abut')
    moved={}
    # Root's existing right margin accommodates one complete rigid translation.
    end=max(c['origin_um'][0]+c['outline_um'][0] for c in dst['hard_cores'])
    if end+band>rw-8.64+1e-6:
        raise ValueError('root lacks room for a capture band without a re-plan')
    for c in dst['hard_cores']:
        c['origin_um'][0]=round(c['origin_um'][0]+band,4)
        moved[('root',c['inst'])]=band
    for c in dst.get('contents',[]):
        if 'origin_um' in c:
            c['origin_um'][0]=round(c['origin_um'][0]+band,4)
    # Only the hub cores on the shared face move; every moved core must keep
    # a real halo from all neighbours. No macro dimensions are shrunk.
    touching=[c for c in src['hard_cores'] if c['origin_um'][0]+c['outline_um'][0]>sw-band-1e-6]
    for c in touching:
        c['origin_um'][0]=round(c['origin_um'][0]-band,4)
        moved[('q_hub',c['inst'])]=-band
    def separated(c,d,gap=8.64):
        x,y=c['origin_um'];w,h=c['outline_um']
        u,v=d['origin_um'];a,b=d['outline_um']
        return x+w+gap<=u+1e-6 or u+a+gap<=x+1e-6 or y+h+gap<=v+1e-6 or v+b+gap<=y+1e-6
    for c in touching:
        for d in src['hard_cores']:
            if c is not d and not separated(c,d):
                raise ValueError(f"hub seam-band move conflicts: {c['inst']} / {d['inst']}")
    for tn,t in [(a['type'],src),(b['type'],dst)]:
        for tp in t.get('clock',{}).get('taps',[]):
            if tp.get('kind')!='core':continue
            inst=tp['name'].split('.')[0]
            dx=moved.get((tn,inst),0)
            tp['xy'][0]=round(tp['xy'][0]+dx,4)
    return {'band_um':band,'die_area_delta_um2':0,'moves':[
        {'type':tn,'core':inst,'dx_um':dx} for (tn,inst),dx in moved.items()],
        'limits':'new R3 stations/reset/taps and actual endpoint placement remain required before P&R'}
