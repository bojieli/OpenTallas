"""Disabled source-ownership repair of existing programme FFs and ABI windows.

No RTL, state count or cycle changes. The exact adjacency audit must still run
after this candidate: this emitter never claims a physical or timing PASS.
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_trial'))
from legal_sites import RowAllocator


def plain(name):return name.replace('\\[','[').replace('\\]',']')


def family(name):return re.sub(r'\[\d+\]$','',name.split('$_')[0])


def main():
    p=argparse.ArgumentParser();p.add_argument('--rows',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--ingress',type=Path,required=True)
    p.add_argument('--edges',type=Path,required=True);p.add_argument('--bounds',type=Path,required=True)
    p.add_argument('--pins',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    old={r['cell']:r for r in csv.DictReader(a.rows.open())};model=json.loads(a.model.read_text())
    ing=json.loads(a.ingress.read_text());absent=set(ing['reserved_row_FF_absent_from_post_SYNTH_ODB']['names'])
    current={k:dict(v)for k,v in old.items()if k not in absent};assert len(current)==20842
    W,H=model['outline_um'];macro=model['macros'];leaf={}
    for i in range(11):
        boxes=[m['rect_um']for m in macro if m['leaf']==i]
        leaf[i]=[(min(q[0]for q in boxes)+max(q[2]for q in boxes))/2,
                 (min(q[1]for q in boxes)+max(q[3]for q in boxes))/2]
    fixed={r['FF']:r for r in json.loads(a.bounds.read_text())}
    output={k for k,r in current.items()if r['planned_output_pin_x_um']}
    payload={k for k in output if k.startswith(('compiler_control[','io_word['))}
    moving={k for k,r in current.items()if r['ownership']=='top_other'}|output
    shared={k for k in current if '.u_leaf.start_v_q' in k and k in fixed}
    moving|=shared
    blocked=[[x-4.32,y-4.32,X+4.32,Y+4.32]for x,y,X,Y in [m['rect_um']for m in macro]]
    allocator=RowAllocator([4.32,4.32,W-4.32,H-4.32],blocked,cell_size=(1.404,.27),column_pitch=2.16,row_pitch=.27)
    def reserve(r):
        x,y=float(r['x_um']),float(r['y_um'])
        ix=round((x-allocator.cw/2)/allocator.cp);iy=round((y-allocator.ch/2)/allocator.rp)
        assert abs(allocator.cp*ix+allocator.cw/2-x)<1e-6 and abs(allocator.rp*iy+allocator.ch/2-y)<1e-6
        key=(iy-allocator.iy0)*allocator.nx+ix-allocator.ix0
        assert key not in allocator.used
        allocator.used.add(key)
    for k,r in current.items():
        if k not in moving:reserve(r)
    # Extra pre-opt rows remain reserved space, never emitted as actual cells.
    for k in absent:reserve(old[k])
    depths={0:1,1:3,2:5,3:1,4:3,5:5,6:0,7:2,8:0,9:2,10:4}
    program_rows={0:[230,160],1:[230,450],2:[230,530],3:[230,350]}
    collect_rows={0:[130,130],1:[130,450],2:[130,530],3:[130,350]}
    def target(k):
        base=k.split('$_')[0];f=family(k)
        if k in shared:return fixed[k]['candidate_centre_um']
        if base.startswith(('g_leaf[6].a_in','g_leaf[6].d_in')):return [150,300]
        if base.startswith(('g_leaf[8].a_in','g_leaf[8].d_in')):return [150,600]
        if f in ('cr_data0','cr_addr0'):return [250,80]
        if f in ('cr_data3','cr_addr3'):return [300,270]
        if f.startswith('p_io_cfg'):return [150,600]
        if f.startswith('p_cfg'):return [150,300]
        if f.startswith('p_io_start'):return [200,650]
        if f.startswith('p_start'):return [230,350]
        if f in ('rs1','rs2','ra_top'):return [150,400]
        mm=re.match(r'ra_leaf\[(\d+)\]',base)
        if mm:return [(150+leaf[int(mm[1])][0])/2,(400+leaf[int(mm[1])][1])/2]
        mm=re.match(r'we_d(\d+)\[(\d+)\]',base)
        if mm:
            stage,i=map(int,mm.groups());start=np.array([150,300 if i<8 else 600]);end=np.array(leaf[i]);ratio=min(1.,stage/(depths[i]+1));return (start+(end-start)*ratio).tolist()
        mm=re.match(r'pr_\w+\[(\d+)\]',base)
        if mm:return program_rows[int(mm[1])]
        mm=re.match(r'sp_\w+\[(\d+)\]',base)
        if mm:return collect_rows[int(mm[1])]
        mm=re.match(r'si_\w+\[(\d+)\]',base)
        if mm:return [130,660 if int(mm[1])==0 else 760]
        if f in ('p_sv','p_sv_q'):return [230,500]
        if f=='si_mm':return [200,700]
        if f=='nb7_s':return [150,450]
        if f=='p_fault':return [130,330]
        if f in ('io_fault','nbio_s'):return [130,710]
        if base=='rb_d[0]':return [8.64,400]
        if base=='rb_d[1]':return [130,550]
        if base=='rb_d[2]':return [130,330]
        if base=='rb[1]':return [150,550]
        if f=='rbd1':return [200,470]
        if f in ('rb','rb_d','rbd1'):return [230,400]
        return [150,400]
    groups=defaultdict(list)
    for k in moving-output:groups[family(k)].append(k)
    allocation=[]
    # Existing shared fanout cells first; other groups retain their exact names.
    for name,ks in sorted(groups.items(),key=lambda q:(not any(k in shared for k in q[1]),q[0])):
        ks=sorted(ks);targets=[target(k)for k in ks]
        # Vector families with different regional roles allocate by exact role.
        buckets=defaultdict(list)
        for k,t in zip(ks,targets):buckets[tuple(t)].append(k)
        for t,keys in buckets.items():
            points,stats=allocator.allocate(t,len(keys),120.)
            for k,point in zip(keys,points):current[k]['x_um'],current[k]['y_um']=map(float,point)
            allocation.append(dict(family=name,target_um=t,**stats))
    incoming=defaultdict(set)
    for e in csv.DictReader(a.edges.open()):
        if e['launch_kind']=='ff'and e['capture_kind']=='ff':
            src,dst=plain(e['launch_owner']),plain(e['capture_owner'])
            if dst in output and src!=dst:incoming[dst].add(src)
    for k in sorted(output):
        base=k.split('$_')[0]
        if k in payload:
            cal=[s for s in incoming[k]if'.u_leaf.out_cal[' in s]
            assert len(cal)==1,(k,cal)
            t=[W-8.64,float(current[cal[0]]['y_um'])]
        elif base.startswith('programme_ordinal'):t=[8.64,130]
        elif base.startswith('io_ordinal'):t=[8.64,660]
        elif base.startswith(('programme_active','programme_done')):t=[8.64,330]
        elif base.startswith(('io_active','io_done')):t=[8.64,710]
        else:assert base=='fault',base;t=[8.64,520]
        points,stats=allocator.allocate(t,1,120.);current[k]['x_um'],current[k]['y_um']=map(float,points[0])
        allocation.append(dict(family=base,target_um=t,**stats))
    # All actual mapped FFs are native DFFHQNx1 (1.08 x .27). Preserve each
    # conservative 1.404-wide reserved envelope's left edge, so the native
    # lower-left remains on the 2.16 column grid. Do not use the envelope
    # centre as a native-cell centre (which would offset its origin by .162).
    for r in current.values():
        assert r['master']=='DFFHQNx1_ASAP7_75t_R'
        r['x_um']=float(r['x_um'])-(1.404-1.08)/2
        assert abs((r['x_um']-.54)/2.16-round((r['x_um']-.54)/2.16))<1e-7
        assert abs((float(r['y_um'])-.135)/.27-round((float(r['y_um'])-.135)/.27))<1e-7
    # Native ABI names remain unchanged. New positions follow actual source
    # ownership; status returns west to the collar, bulk control/IO go east.
    pins=json.loads(a.pins.read_text());pinmap={p['name']:p for p in pins};used=set();tracks=[round(.024+i*.048,6)for i in range(17000)if 4.32<=.024+i*.048<=H-4.32]
    def choose(name,face,y):
        p=pinmap[name];x=.024 if face=='W'else W-.024
        for yy in sorted(tracks,key=lambda z:(abs(z-y),z)):
            key=('M4',x,yy)
            if key not in used:used.add(key);p.update(layer='M4',face=face,x=round(x,6),y=yy);return p
        raise ValueError('ABI face capacity')
    for k in sorted(output):
        port=k.split('$_')[0];face='E'if k in payload else'W';p=choose(port,face,float(current[k]['y_um']))
        current[k]['planned_output_pin_x_um']=p['x'];current[k]['planned_output_pin_y_um']=p['y']
    for q in ing['rows']:
        p=pinmap[q['port']]
        if p['layer']=='M5':continue
        ff=[x['mapped_row_cell_name']for x in q['first_sequential_sinks']if x['kind']=='ff'];assert ff
        choose(q['port'],'W',float(np.median([float(current[n]['y_um'])for n in ff])))
    for p in pins:
        if p['layer']=='M5':used.add((p['layer'],p['x'],p['y']))
    assert len(used)==len(pins)==2904
    header=['cell','master','ownership','x_um','y_um','planned_output_pin_x_um','planned_output_pin_y_um']
    with(a.out/'actual_FF_rows.csv').open('w')as file:
        w=csv.DictWriter(file,header);w.writeheader();w.writerows(current[k]for k in sorted(current))
    (a.out/'native_pins.json').write_text(json.dumps(pins,separators=(',',':'))+'\n')
    (a.out/'model.json').write_text(json.dumps(dict(status='DISABLED_REPAIRED_CANDIDATE_REQUIRES_ADJACENCY_AUDIT',
        actual_FF=20842,extra_conservative_reserved_rows=1088,moved_existing_FF=len(moving),added_FF=0,added_cycles=0,
        outline_um=[W,H],macros=macro,allocation=allocation,
        native_FF_footprint_um=[1.08,.27],reserved_envelope_um=[1.404,.27],native_lower_left_grid_um=[2.16,.27],
        source_role='Same actual0525post-SYNTH netlist and all2904ABI names; no RTL/body/default activation',
        holds=['No PLACE/CTS/route/STA','Exact adjacency, first-input and macro-pingrid checks required','Actual clock/reset/START/collar/parent joins unqualified']),indent=2)+'\n')
    print('DISABLED_REPAIRED_CANDIDATE',len(current),'actualFF; moved',len(moving),'no new state/cycles',flush=True)


if __name__=='__main__':main()
