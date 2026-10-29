"""Plan real M6 entry jogs for failed straight R7 columns. Geometry only.
Reads authoritative source metal/OBS, exact islands and physical power access.
No body/tree move, no materialization and no routing/signoff qualification.
"""
import argparse,json,math
from collections import defaultdict
from pathlib import Path
import fixed_tree as F

class Index:
    def __init__(self):self.rows=[];self.src=[];self.bins=defaultdict(list);self.B=.25
    def add(self,r,src='?'):
        net,l,x0,y0,x1,y1=r
        if l not in ('M6','M7'):return
        k=len(self.rows);self.rows.append(r);self.src.append(src);a,b=(y0,y1) if l=='M6' else (x0,x1)
        for v in range(math.floor(a/self.B),math.floor(b/self.B)+1):self.bins[(l,v)].append(k)
    def hits(self,r):
        net,l,x0,y0,x1,y1=r;sp=.032;seen=set();a,b=(y0,y1) if l=='M6' else (x0,x1)
        for v in range(math.floor((a-sp)/self.B),math.floor((b+sp)/self.B)+1):
            for k in self.bins.get((l,v),()):
                if k in seen:continue
                seen.add(k);q=self.rows[k]
                if q[0]==net:continue
                dx=max(0,max(x0,q[2])-min(x1,q[4]));dy=max(0,max(y0,q[3])-min(y1,q[5]))
                if math.hypot(dx,dy)<sp-1e-7:return (self.src[k],q)
        return None

def covered(r,holes):
    """Exact rectangle coverage by the union of real DIE-frame island cuts."""
    _,_,x0,y0,x1,y1=r;xs=sorted({x0,x1}|{max(x0,min(x1,h[0])) for h in holes}|{max(x0,min(x1,h[2])) for h in holes})
    for a,b in zip(xs,xs[1:]):
        if b-a<1e-8:continue
        mid=(a+b)/2;iv=sorted((max(y0,h[1]),min(y1,h[3])) for h in holes if h[0]-1e-7<=mid<=h[2]+1e-7 and h[1]<y1 and h[3]>y0)
        end=y0
        for lo,hi in iv:
            if lo>end+1e-7:return False
            end=max(end,hi)
        if end<y1-1e-7:return False
    return True

def main():
    p=argparse.ArgumentParser()
    for a in ('failures','fixed-wires','cell-windows','geometry','power-access','pg','clock-base','out'):p.add_argument('--'+a,required=True)
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    failures=json.loads(Path(a.failures).read_text())['failures'];holes=json.loads(Path(a.cell_windows).read_text())['cells']
    print('JOG_STAGE load actual lower metal',flush=True);g=json.loads(Path(a.geometry).read_text());dbu=g['dbu'];ix=Index()
    for inst,pin,l,*xy in g['signal_shapes']:
        if l in ('M6','M7'):ix.add([f'SIGNAL:{inst}/{pin}',l,*[v/dbu for v in xy]],'signal')
    for inst,l,*xy in g['obstructions']:
        if l in ('M6','M7'):ix.add([f'OBS:{inst}',l,*[v/dbu for v in xy]],'obs')
    for net,l,*xy in g['existing_supplies']:
        if l in ('M6','M7'):ix.add([net,l,*[v/dbu for v in xy]],'existing_supply')
    phase,count,pitch=g['tracks']['M7']['X'][0];phase/=dbu;pitch/=dbu
    del g
    base=json.loads(Path(a.clock_base).read_text())
    for r in base:ix.add(r,'clock_base')
    # Protect every future straight bar-column path, even before its top track
    # is chosen. New columns must stay clear of these original columns.
    wires=json.loads(Path(a.fixed_wires).read_text())
    for w in wires:
        for s in w['stacks']:
            x,y=s.get('m6_entry_xy',s['xy']);ix.add([w['name'],'M7',x-.016,y-8.667,x+.016,y+8.667],'future_column')
    del wires,base
    print('JOG_STAGE reserve physical power',flush=True);power=json.loads(Path(a.power_access).read_text())
    for r in power:ix.add(r,'power_access')
    nd=dict(width=.08,space=.32,rf=.5,cf=1.15);router=F.C128.TrackRouter(nd,'VSS',F.DCM.DEFAULT_TRACKS,8.64)
    router.reserve(F.C128.pg_shapes(json.loads(Path(a.pg).read_text())))
    router.reserve(F.C128.pg_shapes(power));del power
    records=[];bad=[]
    for n,f in enumerate(failures):
        cell,pin,net=f['cell'],f['pin'],f['net'];x,y=f['base_xy_um'];parts=holes[cell.removeprefix('ck_')]
        if any(q['in_core'] for q in parts):raise ValueError('clock island intersects hardcore')
        hs=[q['rect_die_um'] for q in parts];columns=sorted({round(phase+k*pitch,6) for k in range(math.ceil((x-.7-phase)/pitch),math.floor((x+.7-phase)/pitch)+1)},key=lambda q:abs(q-x))
        ys=sorted({round(.04+k*.08,6) for k in range(math.ceil((min(h[1] for h in hs)+.027-.04)/.08),math.floor((max(h[3] for h in hs)-.027-.04)/.08)+1)},key=lambda q:abs(q-y));found=None
        diag=[]
        for bx in columns:
            if abs(bx-x)<.064:diag.append(dict(bx=bx,stage='too_close'));continue
            local=[[net,'M6',min(x,bx)-.016,y-.016,max(x,bx)+.016,y+.016],
                   [net,'M6',bx-.035,y-.016,bx+.035,y+.016],
                   [net,'M7',bx-.016,y-.036,bx+.016,y+.036]]
            lf=None
            for i,r in enumerate(local):
                if not covered(r,hs):lf=dict(stage='local_uncovered',part=i);break
                h=ix.hits(r)
                if h:lf=dict(stage='local_hit',part=i,src=h[0],layer=r[1],obj=h[1][0]);break
            if lf:lf['bx']=bx;diag.append(lf);continue
            rc=defaultdict(int)
            for ty in ys:
                riser=[net,'M7',bx-.016,min(y,ty)-.027,bx+.016,max(y,ty)+.027]
                if not covered(riser,hs):rc['riser_uncovered']+=1;continue
                h=ix.hits(riser)
                if h:rc['riser_hit:'+h[0]]+=1;continue
                chosen,mode,ext=router.place('M8',ty,bx-.08,bx+.08,net,keep=(ty,ty),dry=True)
                if chosen is None:rc['m8_place_fail']+=1;continue
                found=dict(cell=cell,pin=pin,net=net,entry_xy_um=[x,y],backbone_xy_um=[bx,y],
                           m7_window_um=[min(y,ty),max(y,ty)],m8_witness_y_um=ty,
                           m6_jog_um=round(abs(bx-x),6),geometry=local+[riser],
                           proof='all metal inside exact119 island union; actual M6/M7 SIGNAL+OBS+PG+future clock bases+power clear; M8 shielded tree .08/.32 witness')
                for r in local+[riser]:ix.add(r,'new_jog')
                break
            if found:break
            diag.append(dict(bx=bx,stage='riser_m8',ys=len(ys),counts=dict(rc)))
        f=dict(f,n_columns=len(columns),n_ys=len(ys),diag=diag,island_rects=len(hs))
        if found:records.append(found)
        else:bad.append(f)
        if n%50==0:print(f'JOG_PROGRESS {n+1}/{len(failures)} pass={len(records)} fail={len(bad)}',flush=True)
    result=dict(status='FAIL' if bad else 'PASS_GEOMETRY',physical_route=False,records=records,failures=bad,
                clock_width_um=.08,tree_spacing_um=.32,m6_width_um=.032,max_jog_um=.7,
                note='No physical route; full tree replan and exact access census/render required')
    (out/'backbone_plan_diag.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],len(records),len(bad),flush=True)
if __name__=='__main__':main()
