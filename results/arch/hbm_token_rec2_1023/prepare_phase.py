from pathlib import Path
import hashlib,json,re,shutil
src=Path('/home/ubuntu/scratch/tokd-hbm2/r18h5_src/bundle/slice/replay/ds_l0')
root=Path('/home/ubuntu/scratch/codex-hbm-token-0936-1023');out=root/'replay';out.mkdir(exist_ok=True)
a={n:[int(x,16) for x in (src/f'{n}.mem').read_text().split()] for n in ('hdr','val','msk')}
assert len({len(v) for v in a.values()})==1
old=list(zip(a['hdr'],a['val'],a['msk']));cap=11843
# Preserve every original drive that can occur before the finite diagnostic horizon.
# Other-domain first original drive is serial3757, outside this early430-stream-edge observation.
drives=[(h,v,m) for h,v,m in old if h>>62==1 and ((h>>60)&3)==0 and (h&0xffffffff)<=450]
assert not [(h,v,m) for h,v,m in old if h>>62==1 and ((h>>60)&3) in (1,2) and (h&0xffffffff)<450]
tb=Path('/home/ubuntu/scratch/tokd-hbm2/r18h5_src/bundle/slice/tb_slice.sv').read_text()
ports={n:(int(i),int(hi)+1) for i,hi,n in re.findall(r'^\s+(\d+): sample\[(\d+):0\] = (\w+);',tb,re.M)}
rings=['hb_coll_SW__pr_cw_o','hb_coll_SW__pr_ccw_o','hcollb_SW__cw_o','hcollb_SW__ccw_o']
clocks=['rf0024_s042_l0__ck_o','rf0024_s042_l1__ck_o','rf0024_s042_l0__eb','rf0024_s042_l1__eb']
faults=['hcollgi_SW__fault','hcollgi_SW__tgt_fault','hcollb_SW__fault','hcollrs_SW__fault']
events=list(drives)
for dom,cycles,names in [(0,range(200,441),rings+clocks+faults),(1,range(150,331),clocks)]:
 for cyc in cycles:
  for name in names:
   pi,width=ports[name];events.append(((2<<62)|(dom<<60)|(pi<<44)|cyc,0,(1<<width)-1))
events.sort(key=lambda x:((x[0]>>60)&3,x[0]&0xffffffff,x[0]>>62))
n=len(events);assert n<cap
events.extend([(3<<62,0,0)]*(cap-n))
for j,name in enumerate(('hdr','val','msk')):(out/f'{name}.mem').write_text(''.join(f'{row[j]:x}\n' for row in events))
shutil.copyfile(src/'vm_pre.txt',out/'vm_pre.txt')
assert (src/'vm_pre.txt').read_bytes()==(out/'vm_pre.txt').read_bytes()
assert [(h,v,m) for h,v,m in events if h>>62==1]==drives
manifest=dict(scope='DIAGNOSTIC/TRUNCATED; expected acceptance failures; never functional PASS',source=str(src),stream_horizon=450,monitor_stream=[200,440],monitor_serial=[150,330],events=n,capacity=cap,unchanged_prefix_drives=len(drives),source_drive_sha256=hashlib.sha256(repr(drives).encode()).hexdigest(),preload_sha256=hashlib.sha256((out/'vm_pre.txt').read_bytes()).hexdigest(),ports={x:ports[x] for x in rings+clocks+faults},flags=['+SHOWVAL','+CYCLES=450','+verilator+rand+reset+0'],limits='forwarded clock samples are available rf0024 boundary clocks, not direct hcollgi internal clocks; phase at domain sampling edges only')
(out/'diagnostic.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
