"""S81 Q element per-mac re-partition: seam pin plan (mac0 | ctl | mac1), M4 at the 0.048 track grid.
Each seam bit gets the SAME y on both facing faces (straight abutted wires across the seam channel); the 566-b
ctl -> {mac0, mac1} broadcast leaves the ctl container on BOTH faces (duplicated output port per face, one driver)."""
import json,collections,hashlib
mods=json.load(open('mapped.json'))['modules']; top=mods['ot_v41_rom_elem_q_qxpq_w10']
cells={n:c for n,c in top['cells'].items() if n in ('u_ctl','u_mac0','u_mac1')}
drv={}; loads=collections.defaultdict(list)
for n,c in cells.items():
    for p,bits in c['connections'].items():
        for i,b in enumerate(bits):
            if not isinstance(b,int): continue
            (drv.__setitem__(b,(n,p,i)) if c['port_directions'][p]=='output' else loads[b].append((n,p,i)))
for p,v in top['ports'].items():
    for i,b in enumerate(v['bits']):
        if isinstance(b,int):
            (drv.__setitem__(b,('TOP',p,i)) if v['direction']=='input' else loads[b].append(('TOP',p,i)))
H=216.0; MARGIN=10.8; PITCH=0.048
seams={'W':'u_mac0','E':'u_mac1'}   # ctl face -> mac
plan={}; dens={}
for face,mac in seams.items():
    bits=[]
    for b,(dn,dp,di) in sorted(drv.items()):
        ls={l[0] for l in loads.get(b,[])}
        if dn=='TOP': continue
        if dn==mac and 'u_ctl' in ls: bits.append(('m2c',b,(dn,dp,di),[l for l in loads[b] if l[0]=='u_ctl']))
        elif dn=='u_ctl' and mac in ls: bits.append(('c2m' if ls=={mac} else 'bcast',b,(dn,dp,di),[l for l in loads[b] if l[0]==mac]))
    n=len(bits); tracks=int((H-2*MARGIN)/PITCH); step=tracks/n
    rows=[]
    for k,(cls,b,d,L) in enumerate(bits):
        y=round(MARGIN+round(k*step)*PITCH+PITCH/2,4)
        rows.append(dict(cls=cls,y=y,driver=list(d),loads=[list(l) for l in L]))
    plan[face]=rows; dens[face]=dict(bits=n,tracks=tracks,ratio=round(n/tracks,4),by_class=dict(collections.Counter(r['cls'] for r in rows)))
out=dict(schema='opentallas.s81.q_permac_seam_pins.v1',layer='M4',pitch_um=PITCH,face_h_um=H,margin_um=MARGIN,
         order='mac0 | ctl | mac1; ctl W face = mac0 E face, ctl E face = mac1 W face, same y both sides',
         broadcast='ctl drives the 566-b broadcast out of BOTH faces: one driver net, a duplicated output port per face (wires only, no cycle)',
         density=dens,mapped_sha256=hashlib.sha256(open('mapped.json','rb').read()).hexdigest(),seams=plan)
json.dump(out,open('seam_pins.json','w'))
print(json.dumps(dens))
