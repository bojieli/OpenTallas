from pathlib import Path
import re,json,subprocess
r=Path('/srv/opentallas-scratch2/claude/codex-s81types-1030');src=r/'ln_plain_phase4';dst=r/'ln_plain_control_free'
if not dst.exists():subprocess.run(['cp','--reflink=auto','-a',str(src),str(dst)],check=True)
p=dst/'ln_pregpl.tcl';s=p.read_text();before=s
for gid in [16,33]:
 pat=r'set lp_region \[odb::dbRegion_create \$lp_b ln_native_chunk_'+str(gid)+r'\]\n.*?puts "LN_NATIVE_CHUNK '+str(gid)+r' inventory \d+"\n'
 s,n=re.subn(pat,'# CONTROL chunks64..69 remain globally placeable; their real captured/output fields have mixed faces.\n',s,flags=re.S);assert n==1,(gid,n)
 s,nmap=re.subn(r'^dict set ::ln_plain_phase4_port_groups .* ln_native_chunk_'+str(gid)+r'\n','',s,flags=re.M)
 print('removedcontrolregion',gid,'portbufferhomesreleased',nmap)
assert s.count('set lp_region [odb::dbRegion_create')==32
p.write_text(s)
p=dst/'face_flops_release.tcl';s=p.read_text();lines=s.splitlines();out=[];i=0;skipped=0
while i<len(lines):
 if lines[i].startswith('set ln_o [$ff_blk findInst') and i+4<len(lines) and re.search(r'ln_native_chunk_(16|33)\]',lines[i+2]):
  assert lines[i+4]=='$ln_g addInst $ln_o';i+=5
  if i<len(lines) and lines[i].startswith('$ln_o setLocation '):i+=1
  skipped+=1;continue
 out.append(lines[i]);i+=1
assert not any(re.search(r'findGroup ln_native_chunk_(16|33)\]',x) for x in out)
p.write_text('\n'.join(out)+'\n')
# Keep cached native floorplan/GPL inputs; preserve inherited failed verdict separately.
archive=dst/'inherited_phase4_failure';archive.mkdir(exist_ok=True)
for p in (dst/'run/results').glob('asap7/*/base/3_3*'):
 p.rename(archive/p.name)
if (dst/'place.log').exists():(dst/'place.log').rename(archive/'place.log')
# Native initial-region report prices actual cell/fixed area, before routability inflation.
log=(src/'place.log').read_text();regions={}
for m in re.finditer(r'\[INFO GPL-0014\] Region name:\s+([^\n]+)\.\n(.*?)(?=\[INFO GPL-0032\]|\Z)',log,re.S):
 b=m[2];fields={}
 for key in ['Region area','Fixed instances area','Movable instances area']:
  q=re.search(re.escape(key)+r':\s+([0-9.]+)',b)
  if q:fields[key]=float(q[1])
 if len(fields)==3:regions[m[1]]=fields
base=regions['top-level'];available=base['Region area']-base['Fixed instances area'];area=base['Movable instances area']
for gid in [16,33]:
 z=regions['ln_native_chunk_'+str(gid)];available+=z['Region area']-z['Fixed instances area'];area+=z['Movable instances area']
receipt=dict(schema='opentallas.ln.control_free.prep.v1',source='native plain16466 same RTL/ports/clocks/reset/cycles',boundary_ff_inventory=5580,payload_fences_retained=32,control_fences_removed=[16,33],control_logical_chunks=[64,65,66,67,68,69],output_FF_group_constraints_released=skipped,actual_init_free_area_after_fixed_um2=available,actual_init_free_movable_area_um2=area,estimated_free_utilization=area/available,prior_failure='GPL-0305; routability artificial inflation+50.22%; control-cone homes opposite their actual mixed-face/bottom boundary FFs',physical_adoption=False,ready_for='render+LOOK before ONE fresh PLACE/GRT; no CTS/DRT')
(dst/'PREP.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt,indent=1))
