import sys, json, re, collections
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools'); sys.path.insert(0,str(Path(__file__).parent))
out={}
def pack(name, W, H, items, meta):
    # items: (kind, name, x, y, w, h, extra)
    kinds=sorted(set(i[0] for i in items))
    ki={k:j for j,k in enumerate(kinds)}
    rects=[[ki[i[0]], round(i[2],1), round(i[3],1), round(i[4],1), round(i[5],1), i[1]] for i in items]
    out[name]=dict(w=round(W,3),h=round(H,3),kinds=kinds,rects=rects,meta=meta,
                   counts=dict(collections.Counter(i[0] for i in items)))
# HBM DS
import hbm_accel_die_fp as H
m=H.build()
items=[(it.kind,it.name,it.x,it.y,it.w,it.h) for it in m['insts']]
fp=json.load(open('/home/ubuntu/OpenTallas/results/rtl/hbm_accel_die_floorplan_20261005/floorplan.json'))
regs=[dict(name=r['name'],clock=r['clock'],rect=r['rect']) for r in fp['clock_region_list']]
masters={it.name:it.master for it in m['insts']}
pack('hbm_ds', m['geo']['W'], m['geo']['H'], items, dict(clock_regions=regs, masters={k:v for k,v in masters.items() if not k.startswith(('at_','stn','wp','cd','ga','mc'))}))
# HBM Qwen (branch tool)
import hbm_accel_die_fp_q as HQ
HQ.ROOT=Path('/home/ubuntu/OpenTallas')
mq=HQ.build_qwen({})
items=[(it.kind,it.name,it.x,it.y,it.w,it.h) for it in mq['insts']]
pack('hbm_qwen', mq['geo']['W'], mq['geo']['H'], items, dict(masters={it.name:it.master for it in mq['insts'] if it.kind not in('tile','head','waypoint')}))
# S81 layer die
import dsrom_s81_fulldie as S
S.configure('layer'); ms=S.build()
items=[(it.kind,it.name,it.x,it.y,it.w,it.h) for it in ms['insts'] if it.kind!='cfg']
cfgn=sum(1 for it in ms['insts'] if it.kind=='cfg')
W,Hh=S.DIE
pack('ds_s81_layer', W, Hh, items, dict(cfg_roms=cfgn, masters={it.name:it.master for it in ms['insts'] if it.kind in('hub','phy','ctrl','svc','band_blk','link')}))
# Qwen ROM r17b
lef={}
for f in ['/tmp/qdie17/r17b_pdn/elements.lef','/tmp/qdie17/r17b_pdn/phy_ew.lef']:
    cur=None
    for ln in open(f):
        mm=re.match(r'MACRO (\S+)',ln)
        if mm: cur=mm.group(1)
        mm=re.match(r'\s+SIZE ([\d.]+) BY ([\d.]+)',ln)
        if mm and cur and cur not in lef: lef[cur]=(float(mm.group(1)),float(mm.group(2)))
mast={}
for ln in open('/tmp/qdie17/r17b_pdn/die.v'):
    mm=re.match(r'\s*((?:qfd_|ot_hbm3e)\w*)\s+(\w+)\s*\(',ln)
    if mm: mast[mm.group(2)]=mm.group(1)
def qkind(ms):
    if ms=='qfd_tile': return 'tile'
    if ms=='qfd_cst': return 'station'
    if ms=='qfd_chead': return 'col_head'
    if ms=='qfd_reng': return 'row_engine'
    if ms=='qfd_lfifo': return 'link_fifo'
    if ms=='qfd_ctrl': return 'hbm_ctrl'
    if ms=='qfd_cdc': return 'cdc'
    if ms=='qfd_hub': return 'hub'
    if ms.startswith('qfd_lst'): return 'link_station'
    if ms.startswith('qfd_sp_'): return 'spine'
    if ms.startswith('qfd_port_tiles'): return 'band_slab'
    if ms.startswith('qfd_io_'): return 'io'
    if ms.startswith('ot_hbm3e'): return 'phy'
    return 'other'
items=[]
for ln in open('/tmp/qdie17/r17b_pdn/place.tcl'):
    mm=re.match(r'ot_mts::place \[\$_blk findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)',ln)
    if not mm: continue
    n=mm.group(1); ms=mast[n]; w,h=lef[ms]
    if mm.group(4) in ('R90','R270','MXR90','MYR90'): w,h=h,w
    items.append((qkind(ms),n,float(mm.group(2)),float(mm.group(3)),w,h))
plan=json.load(open('/tmp/qdie17/plan17c/plan.json'))
pack('qwen_rom', 25113.888, 32801.76, items, dict(masters={n:mast[n] for n in mast if qkind(mast[n]) not in ('tile','station','cdc','link_station','col_head')}, clock_regions_summary=plan.get('clock_regions_summary')))
for k,v in out.items(): print(k, v['w'], v['h'], v['counts'], len(json.dumps(v)))
json.dump(out, open(Path(__file__).parent/'geo.json','w'), separators=(',',':'))
