import json,sys
d=json.load(open('hk4.json'))
T=d['partition_types']; P={p['name']:p for p in d['partitions']}
def pinpos(part,bus):
    p=P[part]; t=T[p['type']]; W,H=t['outline_um']; ox,oy=p['origin_um']
    b=None
    for x in t.get('buses',[]):
        if x['name']==bus: b=x;f=x['face'];w=x['window_um']
    if b is None:
        for s in t.get('ft_slots',[]):
            if bus in (s['name']+'_i',s['name']+'_o',s['name']):
                pass
        return None
    m=(w[0]+w[1])/2
    if p.get('orient','R0')!='R0': return ('orient',p['orient'])
    return {'W':(ox,oy+m),'E':(ox+W,oy+m),'S':(ox+m,oy),'N':(ox+m,oy+H)}[f]
print('ctl origin',P['ctl']['origin_um'],T['hd_ctl']['outline_um'])
for pt in d['ports']:
    for end in ('src','dst'):
        if pt[end]['part']=='ctl':
            o=pt['dst' if end=='src' else 'src']
            a=pinpos('ctl',pt[end]['bus']); b=pinpos(o['part'],o['bus']) if o['part'] in P else None
            dist = abs(a[0]-b[0])+abs(a[1]-b[1]) if a and b and isinstance(a[0],float) and isinstance(b[0],float) else None
            print(pt['id'],pt['kind'],pt['width'],end,'ctl.'+pt[end]['bus'],a,'<->',o['part'],P.get(o['part'],{}).get('type'),o.get('bus'),b, 'L1=%.0f'%dist if dist is not None else '')
