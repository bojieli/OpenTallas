"""Kit-only actual-connectivity CA packing trial, no RTL/latency/pin change."""
import sys,re,json,hashlib,argparse
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--private-write-comb',action='store_true',help='explicit typed per-bit writer feedback/hold logic placement')
ap.add_argument('--kit',type=Path,required=True);ap.add_argument('--dump',type=Path,required=True)
ap.add_argument('--geom-tools',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args();p=a.out;p.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.geom_tools));import geom_rules as G
D=G.Design(a.dump);land=json.load(open(a.kit/'land_slots.json'));guard=json.load(open(a.kit/'face_guard.json'))
cap=G.land_ring_captures(D,land,guard);assert not cap['errors'],cap['errors']
pin={v['name']:v for v in D.pins};ca=(a.kit/'rtl/ot_dp_clk_landing_ca.sv').read_text()
# Match the actual implementation's equal-width subdivision. Chunk0 remains valid for NCH1.
mt=re.search(r'localparam int NCH\s*=\s*\(W\s*%\s*(\d+)\s*==\s*0\)\s*\?\s*W\s*/\s*\1\s*:\s*1',ca);assert mt,'unknown actual native chunk definition';CHUNK=int(mt[1])
ring={i:c for i,c in D.cells.items() if c[0]=='S' and c[6].startswith('u_cland_i/')};writes={};reads={};where={};used=set();groups=[]
for pn,ids in cap['caps'].items():
 if pn.startswith('i[') or pn in ['cland_dn_ready_i','cland_dn_fault_i']:
  for i in ids:
   if i not in ring:raise ValueError('non-ring data capture '+D.cells[i][6])
   clean=D.cells[i][6].replace('\\','');m=re.search(r'\.s_d\[(\d+)\]\[(\d+)\]',clean);assert m,clean
   slot,b=map(int,m.groups());writes.setdefault(b,[]).append((slot,i));where.setdefault(b,pn);assert where[b]==pn
for i,c in ring.items():
 n=c[6].replace('\\','');m=re.search(r'\.dch\[(\d+)\]\.u_dsel/y\[(\d+)\]',n)
 if m:
  chunk,local=map(int,m.groups());b=CHUNK*chunk+local;assert b not in reads;reads[b]=i
assert land['buses']['i']['D']==4, 'native8 profile requires production ring depth4'
assert len(writes)==568 and all(len(x)==4 and {slot for slot,i in x}=={0,1,2,3} for x in writes.values()), 'native8 profile requires 568 live bits x 4 writer slots'
assert set(reads)==set(writes),('write/read global bit inventory mismatch',set(reads)^set(writes))
def group(names,rect,label):
 ids=sorted((i for i in names if i not in used),key=lambda i:D.cells[i][6]);used.update(ids)
 if ids:groups.append({'label':label,'rect_um':rect,'cells':[D.cells[i][6] for i in ids]})
fstart='cland_fstart_in_i';assert fstart in cap['caps'],cap['rejected'];fp=pin[fstart]
data_ids={i for rows in writes.values() for slot,i in rows}
assert len(set(cap['caps'][fstart])-data_ids)==26, 'unexpected START controls'
group(set(cap['caps'][fstart])-data_ids,[17.28,fp['y']-4.32,26.46,fp['y']+4.32],'proved_fstart_control_captures')
# FSTART directly enables every writer: keep ALL writer cells within150um of it.
# Preserve each data pin's Y except the few edge groups that need finite packing room.
assert all(0<=pin[where[b]]['x']<=3 and 708<=pin[where[b]]['y']<=1010 for b in writes), 'requires actual west native input pins, not unplaced DB'
order=sorted(writes,key=lambda b:(pin[where[b]]['y'],b));target={};prev=742-.27
for b in order:
 target[b]=max(742,pin[where[b]]['y'],prev+.27);prev=target[b]
nxt=990+.27
for b in reversed(order):
 target[b]=min(990,target[b],nxt-.27);nxt=target[b]
assert min(target.values())>=742-1e-8
assert all(target[b]-target[a]>=.27-1e-8 for a,b in zip(order,order[1:]))
# Writer slots follow each actual bit/control pin; read FF for that same GLOBAL bit sits beside the slots.
for b in sorted(writes,reverse=True):
 pn=where[b];y=target[b];ys=[max(742,y-1.08),min(990,y+1.08)]
 group([i for slot,i in sorted(writes[b])],[12.96,ys[0],22.14,ys[1]],f'write_globalbit_{b}')
 group([reads[b]],[32.4,ys[0],47.52,ys[1]],f'read_globalbit_{b}')
# Chunk one-hot selector registers stay by the middle of their OWN data interval.
for chunk in range(max(reads)//CHUNK+1):
 bits=[b for b in reads if b//CHUNK==chunk];y=sum(pin[where[b]]['y'] for b in bits)/len(bits)
 ids=[i for i,c in ring.items() if re.search(r'\.dch\['+str(chunk)+r'\]\.u_dsel/di\[',c[6].replace('\\',''))]
 group(ids,[32.4,max(708.48,y-4.32),47.52,min(1008.512,y+4.32)],f'chunk_{chunk}_selector')
group(ring,[32.4,845.28,47.52,879.84],'remaining_ring_control')
assert len(ring)==2941, 'unexpected native ring inventory'
assert used==set(ring),(len(used),len(ring),set(ring)-used)
origin=[i for i,c in D.cells.items() if c[0]=='S' and c[6].startswith('u_cland_origin/')]
assert len(origin)==6, 'unexpected origin capture inventory'
group(origin,[509.76,854.304,527.04,871.584],'origin_at_declared_start_capture')
# Place only combinational cells exclusive to one writer bit. Stop at every sequential/input boundary.
private_comb={}
if a.private_write_comb:
 owners={}
 for b,slots in writes.items():
  todo=[];seen=set()
  for slot,i in slots:
   for n,is_clock in D.cell_in.get(i,[]):
    if not is_clock:todo.append(n)
  while todo:
   n=todo.pop()
   dr=D.nets[n][1]
   if not dr or dr[0]!='i' or D.kind(dr[1]) not in ('B','L'):continue
   cid=dr[1]
   if cid in seen:continue
   seen.add(cid);owners.setdefault(cid,set()).add(b)
   for pn,is_clock in D.cell_in.get(cid,[]):
    if not is_clock:todo.append(pn)
 for cid,bs in owners.items():
  if len(bs)==1:private_comb.setdefault(next(iter(bs)),[]).append(cid)
 for b,ids in sorted(private_comb.items()):
  y=target[b];group(ids,[20.52,max(742,y-1.08),47.52,min(990,y+1.08)],f'private_write_comb_globalbit_{b}')

lines=['# Actual native CA ring, typed write/read slot inventory; default source untouched.']
for g in groups:
 rect=' '.join(map(str,g['rect_um']));lines.append('set cland_cursor {}')
 for name in g['cells']:
  lines.extend([f'set nri [$ff_blk findInst {{{name}}}]','if {$nri eq "NULL"} {error "NATIVE_RING missing actual proved capture"}'])
  put=f'cland_put $nri {{{rect}}} native:{g["label"]} 0.6 1'
  if g['label']=='origin_at_declared_start_capture':
   ax,ay,bx,by=g['rect_um']
   lines.extend(['if {[dict exists $cland_done [$nri getName]]} {',' set nob [$nri getBBox]',f' if {{[$nob xMin] < ({ax}-0.001)*$ff_dbu || [$nob yMin] < ({ay}-0.001)*$ff_dbu || [$nob xMax] > ({bx}+0.001)*$ff_dbu || [$nob yMax] > ({by}+0.001)*$ff_dbu}} {{error "NATIVE_RING existing origin outside declared capture rectangle"}}','} else {',put,'}'])
  else:lines.append(put)
lines.append(f'puts "NATIVE_RING typed packing {len(ring)} ring FF + {len(origin)} origin FF; {len(writes)} global bits; chunk={CHUNK}"')
(p/'native_ring_layout.tcl').write_text('\n'.join(lines)+'\n')
(p/'native_ring_layout.json').write_text(json.dumps({'kind':'HD_TILE_NATIVE8_REUSABLE_TYPED_PROFILE','source_dump_sha256':hashlib.sha256(a.dump.read_bytes()).hexdigest(),'requires_band_i_rect_um':[12.96,708.48,47.52,1008.512],'live_read_ff':568,'logical_padded_read_width':576,'forwarded_writer_ff':2298,'data_cycles_added':0,'private_write_comb_opt_in':a.private_write_comb,'private_write_comb_count':sum(map(len,private_comb.values())),'actual_rtl_sha256':hashlib.sha256(ca.encode()).hexdigest(),'chunk_width_derived':CHUNK,'write_bits':len(writes),'write_ff':sum(map(len,writes.values())),'read_ff':len(reads),'ring_ff':len(ring),'origin_ff':len(origin),'all_ring_ff_covered':True,'groups':groups},indent=1)+'\n')
print('private_write_comb',sum(map(len,private_comb.values())),'max_per_bit',max(map(len,private_comb.values()),default=0))
print('ring',len(ring),'write',sum(map(len,writes.values())),'read',len(reads),'chunk',CHUNK,'origin',len(origin))
