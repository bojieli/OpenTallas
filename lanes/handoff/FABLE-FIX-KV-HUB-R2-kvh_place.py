# FABLE-FIX-KV-HUB-R2: D28 hard-ring rows for kv3_hub_Wo / kv3_hub_Eo (KV-HUBWO-SPLIT form refreshed on the D27d plan).
# usage: kvh_place.py TREE ROWS_D23.json OUT_DIR   -> OUT_DIR/rows_<type>.json + report
import json,glob,sys,os,re,math,collections,copy
tree,d23,out=sys.argv[1:4]
P=os.path.dirname(glob.glob(tree+'/physical/die_plan/qwen_kvsys/**/plan_c.json',recursive=True)[0])
j=json.load(open(P+'/plan_c.json'))
tmpl={r['module']:r for r in json.load(open(d23))['add_hard_cores'] if r['module'].startswith('kv_cland')}
# w292_ew_abd47 never signed (intel1 run died at place 11-14); w292_ns_abd47 is SIGNED with the same params
_t=copy.deepcopy(tmpl['kv_cland_w292_ew_abd47']); _t.update(module='kv_cland_w292_ns_abd47',physical_master='kv_cland_w292_ns_abd47',outline_um=[51.408,50.976]); tmpl['kv_cland_w292_ns_abd47']=_t
MASTER={1119:'kv_cland_w1119_ew_86ca8',300:'kv_cland_w300_ew_ebc75',292:'kv_cland_w292_ns_abd47',268:'kv_cland_w268_ns_6081a',257:'kv_cland_w257_ew_aee53'}
SKIP=('clock/landing_contract',)
def harvest(o,path,pts,rects):
    if isinstance(o,dict):
        if 'origin_um' in o and o.get('outline_um'):
            x,y=o['origin_um'];w,h=o['outline_um']; rects.append((path,x,y,x+w,y+h))
        for k,v in o.items():
            if k in('origin_um','outline_um'): continue
            if k=='rect_um' and isinstance(v,list) and len(v)==4: rects.append((path+'/rect',)+tuple(v)); continue
            harvest(v,path+'/'+re.sub(r'\d+','N',str(k)),pts,rects)
    elif isinstance(o,list):
        if len(o)==2 and all(isinstance(a,(int,float)) and not isinstance(a,bool) for a in o): pts.append((path,o[0],o[1]))
        else:
            for v in o: harvest(v,path,pts,rects)
GX=float(os.environ.get('GX','1.728')); G=8.64  # x: lcm(M5 0.048, M7 0.064, site 0.054); y: lcm(M4 0.048, M6 0.064, row 0.27)
for tn in os.environ.get('TYPES','kv3_hub_Wo,kv3_hub_Eo').split(','):
    t=j['partition_types'][tn]; W,H=t['outline_um']; lc=t['clock']['landing_contract']; bands=lc['bands']
    part=open(P+'/bind_of_record/rtl/%s_part.sv'%tn).read() if os.path.exists(P+'/bind_of_record/rtl/%s_part.sv'%tn) else open(sys.argv[4]+'/%s_part.sv'%tn).read()
    rings=[]
    for p,inst in re.findall(r'ot_dp_clk_landing_cas\s*#\(([^;]*?)\)\s*(\w+)\s*\(',part,re.S):
        d={k:int(v) for k,v in re.findall(r'\.(\w+)\s*\(\s*(\d+)\s*\)',p)}
        if d.get('W',0)>=250: rings.append((inst[len('u_cland_'):],d))
    pts=[];rects=[]
    for k,v in t.items():
        if k in('outline_um','buses','hard_cores'): continue
        if k=='clock':
            for k2,v2 in v.items():
                if k2=='landing_contract': continue
                harvest(v2,'clock/'+k2,pts,rects)
        else: harvest(v,k,pts,rects)
    for h in t['hard_cores']:
        x,y=h['origin_um'];w,hh=h['outline_um']; rects.append(('hard_core:'+h['inst'],x-4.32,y-4.32,x+w+4.32,y+hh+4.32))
    ringbus={b for b,_ in rings}
    for b,v in bands.items():
        if b not in ringbus: rects.append(('band:'+b,)+tuple(v['rect_um']))
    # bucket points
    B=20.0; buck=collections.defaultdict(list)
    for p in pts: buck[(int(p[1]//B),int(p[2]//B))].append(p)
    def clear(x,y,w,h,m=2.16):
        for q in rects:
            if q[1]<x+w+m and q[3]>x-m and q[2]<y+h+m and q[4]>y-m: return q[0]
        for bx in range(int((x-m)//B),int((x+w+m)//B)+1):
            for by in range(int((y-m)//B),int((y+h+m)//B)+1):
                for p in buck.get((bx,by),()):
                    if x-m<p[1]<x+w+m and y-m<p[2]<y+h+m: return p[0]
        return None
    fs={s['name']+'_i':s for s in t['ft_slots']}
    rows=[];rep=[]
    for bus,d in sorted(rings,key=lambda r:(-r[1]['W'],r[0] if os.environ.get('ORD')!='rev' else [-ord(c) for c in r[0]])):
        mod=MASTER[d['W']]; tm=tmpl[mod]; w,h=tm['outline_um']
        mp=tm['param_wrap']['params']
        assert {k:v for k,v in d.items() if k!='NARROW'}==mp, (bus,d,mp)
        br=bands[bus]['rect_um']; ax,ay=(br[0]+br[2])/2,(br[1]+br[3])/2
        s=fs.get(bus); pin=None
        if s: pin=s['regs_um'][0]
        else:
            pl=lc.get('pins'); pp=pl.get(bus) if isinstance(pl,dict) else next((q for q in (pl or []) if isinstance(q,dict) and q.get('bus')==bus or isinstance(q,dict) and q.get('name')==bus),None)
            if isinstance(pp,dict): pp=pp.get('xy_um') or pp.get('xy') or pp.get('pin_um')
            if isinstance(pp,list) and len(pp)==2 and isinstance(pp[0],(int,float)): pin=pp
        if pin is None: pin=[ax,ay]
        px,py=pin
        def hop(x,y):
            # worst pin-to-core-pin wire: to the facing edge, plus the far end of that edge
            if '_ew_' in mod:
                ex=x+w if px>x+w else (x if px<x else px); return abs(px-ex)+max(abs(py-y),abs(py-(y+h)))
            ey=y+h if py>y+h else (y if py<y else py); return abs(py-ey)+max(abs(px-x),abs(px-(x+w)))
        best=None; blk=collections.Counter()
        for ix in range(5,int((W-w)//GX)-4):
            for iy in range(1,int((H-h)//G)):
                x,y=round(ix*GX,3),iy*G
                dist=hop(x,y)
                if dist>520 or (best and dist>=best[0]): continue
                c=clear(x,y,w,h)
                if c is None: best=(dist,x,y)
                else: blk[re.sub(r':.*','',c)]+=1
        if not best:
            print('  NOFIT',tn,bus,w,h,'anchor',round(ax),round(ay),blk.most_common(8)); continue
        dist,x,y=best
        if '_ew_' in mod: orient='MY' if ax>W/2 else 'R0'
        else: orient='MX' if ay>H/2 else 'R0'
        r=copy.deepcopy(tm); r.update(inst='cl_'+bus,origin_um=[round(x,3),round(y,3)],orient=orient,physical_inst='u_bound.u_cland_'+bus)
        r['note']='KV-D28-HUBRING (FABLE-FIX-KV-HUB-R2, KV-HUBWO-SPLIT form on D27d): landing ring u_cland_%s as a hard child ring core (master %s SIGNED, exact parent params without NARROW, 0 added cycles)'%(bus,mod)
        rows.append(r); rects.append(('new:'+bus,x-4.32,y-4.32,x+w+4.32,y+h+4.32))
        rep.append((bus,d['W'],mod,[round(x,2),round(y,2)],orient,'pin',[round(px,1),round(py,1)],'hop %.0f'%dist,'band_hop_was',bands[bus].get('max_pin_to_band_hop_um'),'cells',tm.get('cells')))
    json.dump(dict(schema='kv_hubc_split_rows.v1',base='D27d plan 07a462a13e91 (epyc8 kv-plan-r3/d27c/tree)',type=tn,add_hard_cores=rows,
                   note='9 ring hard cores, SIGNED CLAND-MACRO-1 masters; 8.64 grid nearest to the soft band centre; clear (2.16 um) of ft bit sites / station regs, internal stations, relay sites, taps, reset sites, START and raw stages, reserved rects, other landing bands, hard-core halos 4.32. Collector tree and raw branches must be re-derived (landing_remap resel, collector_reattach, hard_ring_wreg, kv_start_corridor_event raw).'),
              open(out+'/rows_%s_d28.json'%tn,'w'),indent=1)
    print('==',tn,'rings>=250:',len(rings),'cells removed',sum(r['cells'] for r in rows))
    for x in rep: print('  ',x)
