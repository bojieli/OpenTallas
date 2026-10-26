"""Prepare one isolated rec2 component replay. Do not launch it or claim acceptance."""
from pathlib import Path
import hashlib,json,re,shutil
root=Path('/home/ubuntu/scratch/codex-hbm-token-0936-1023')
src=Path('/home/ubuntu/scratch/tokd-hbm2/r18h5_src/bundle/slice/replay/ds_l0')
out=root/'corrected_rec2';out.mkdir(exist_ok=True)
tb=Path('/home/ubuntu/scratch/tokd-hbm2/r18h5_src/bundle/slice/tb_slice.sv').read_text()
inputs={n:int(i) for i,n in re.findall(r'^\s+(\d+): (\w+) <= v\[',tb,re.M)}
outputs={n:int(i) for i,n in re.findall(r'^\s+(\d+): sample\[.*?\] = (\w+);',tb,re.M)}
model=json.loads((root/'transport_model.json').read_text())
measured=json.loads((root/'phase_result.json').read_text())
shift=model['hcollgi_SW.launch_v']['latency_edges']
assert shift==measured['own_shift_edges'] and measured['own_flits_exact_280bits']==40
paths={src:model[dst]['latency_edges'] for src,dst in {
 'hb_coll_NW__pr_cw_o':'hb_coll_SW.pr_cw_i',
 'hb_coll_SE__pr_ccw_o':'hb_coll_SW.pr_ccw_i',
 'hcollb_NW__cw_o':'hcollb_SW.cw_i',
 'hcollb_SE__ccw_o':'hcollb_SW.ccw_i'}.items()}
shifts={inputs[n]:shift-d for n,d in paths.items()}
a={n:[int(x,16) for x in (src/f'{n}.mem').read_text().split()] for n in ('hdr','val','msk')}
assert len({len(x) for x in a.values()})==1
rows=list(zip(a['hdr'],a['val'],a['msk']));events=[];changes=[];drives=checks=0
for h,v,m in rows:
 k,dom,cyc,pi=h>>62,(h>>60)&3,h&0xffffffff,(h>>44)&0xffff
 rec=((h>>32)&0xfff)-1
 if k==1 and dom==0 and cyc<=450:
  delta=shifts.get(pi,0);drives+=1
 elif k==2 and dom==0 and rec==2:
  delta=0 if pi==outputs['hcollgi_SW__configured'] else shift;checks+=1
 else:continue
 nh=(h&~0xffffffff)|(cyc+delta)
 events.append((nh,v,m))
 if delta:changes.append(dict(kind=k,port=pi,old=cyc,new=cyc+delta))
assert drives==151 and checks==287
assert all(x['new']>=x['old'] for x in changes)
events.sort(key=lambda x:((x[0]>>60)&3,x[0]&0xffffffff,x[0]>>62))
n=len(events);last=max(h&0xffffffff for h,_,_ in events);cap=11843;assert last==366 and n<cap
events.extend([(3<<62,0,0)]*(cap-n))
for j,name in enumerate(('hdr','val','msk')):(out/f'{name}.mem').write_text(''.join(f'{row[j]:x}\n' for row in events))
shutil.copyfile(src/'vm_pre.txt',out/'vm_pre.txt')
assert (src/'vm_pre.txt').read_bytes()==(out/'vm_pre.txt').read_bytes()
index=dict(events=n,drives=drives,checks=checks,vm_preload_words=len((out/'vm_pre.txt').read_text().splitlines()),last_stream_cyc=last,scope='component_probe',qualifies_native_layer=False,qualifies_native_chain=False,state_seed_provenance=['released_checkpoint_fixture'],records=[2])
(out/'index.json').write_text(json.dumps(index,indent=2)+'\n')
meta=dict(scope='PREPARED/NOT RUN; rec2 component candidate only',source=str(src),own_shift_measured_edges=shift,farend_lane_latency_source_model=paths,farend_drive_shifts={n:shift-d for n,d in paths.items()},other_drives='unchanged151-drive prefix except four far-end port schedules',values_and_masks='all identical for retained original events',preload_sha256=hashlib.sha256((out/'vm_pre.txt').read_bytes()).hexdigest(),last_stream_cyc=last,proposed_run_cycles=450,flags=['+verilator+rand+reset+0'],changes=changes,limits=['Source K/N lane model contains NO_E placeholders; this is source-functional timing, not physical clock qualification.','48-edge own shift measured for all40flits;20-edge B-CCW extra latency measured by terminal payload identity;other three ingress lane values are source-model predictions pending candidate validation.','VM checks are retimed by48 but any additional write-side transport failure remains actionable, not waived.'])
(out/'retiming.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({k:v for k,v in meta.items() if k!='changes'},indent=2));print('events',n,'drives',drives,'checks',checks)

# One actual causal negative: omit the selected B-CCW ingress transport term.
neg=root/'negative_omit_bccw';neg.mkdir(exist_ok=True)
negative_port=inputs['hcollb_SE__ccw_o']
negative_extra=paths['hcollb_SE__ccw_o']
negative=[];mutations=0
for h,v,m in events:
 if h>>62==3:continue
 if h>>62==1 and (h>>44)&0xffff==negative_port:
  h=(h&~0xffffffff)|((h&0xffffffff)+negative_extra);mutations+=1
 negative.append((h,v,m))
negative.sort(key=lambda x:((x[0]>>60)&3,x[0]&0xffffffff,x[0]>>62))
assert len(negative)==n and max(h&0xffffffff for h,_,_ in negative)==last
negative.extend([(3<<62,0,0)]*(cap-n))
for j,name in enumerate(('hdr','val','msk')):(neg/f'{name}.mem').write_text(''.join(f'{row[j]:x}\n' for row in negative))
shutil.copyfile(out/'vm_pre.txt',neg/'vm_pre.txt')
shutil.copyfile(out/'index.json',neg/'index.json')
(neg/'mutation.json').write_text(json.dumps(dict(scope='one causal negative; expected FAIL',source=str(out),port='hcollb_SE__ccw_o',omitted_ingress_term=negative_extra,changed_drive_events=mutations,all_expected_values_masks_fault_guards='unchanged',preload_sha256=meta['preload_sha256']),indent=2)+'\n')
print('negative changed drive events',mutations,'by',negative_extra)
