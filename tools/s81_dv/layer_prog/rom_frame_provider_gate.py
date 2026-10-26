"""Read every real image through both unchanged emitted frame-provider classes.

The bench overrides only macro address/enable nets to enumerate ROM contents.
It qualifies image selection through emitted class parameters, not sequencer,
arithmetic, reset, physical timing, or whole-token execution.
"""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('prototype','loader','out'):p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
top=(a.prototype/'rtl/s81_bound_top.sv').read_text()
manifest=json.loads((a.loader/'loader_manifest.json').read_text())
body=['`timescale 1ps/1ps','module tb;','reg clk=0; always begin #416 clk=1; #417 clk=0; end','reg [11:0] addr=0; integer i,errors=0,checks=0; integer mut;']
checks=[];forced=[];selected=[];hashes={}
for idx,part in enumerate(('fE2_p1_b0','fE2_p4_b0')):
 # Anchor at the module line, preventing a match spanning preceding instances.
 candidates=list(re.finditer(r'^\s*(\w+)\s*#\(([^\n]*)\)\s+'+part+r'\s*\(',top,re.M))
 assert len(candidates)==1,part
 m=candidates[0];master,params=m.groups();original_params=params;src=a.prototype/'rtl'/f'{master}.sv';text=src.read_text()
 hashes[str(src)]=hashlib.sha256(src.read_bytes()).hexdigest()
 if idx==1:
  # Runtime mutant redirects just one real selector to another valid image.
  old='"u_f_4R01.u_r0.u_c0_0"'
  assert old in params
  params=params.replace(old,'(MUT ? "u_f_6R01.u_r0.u_c0_0" : '+old+')',1)
 body.append('parameter integer MUT=0;') if idx==0 else None
 body.append(f'{master} #({params}) d{idx}(.clk(clk),.arst_n(1\'b0));')
 macros=re.findall(r'ot_rom_4096x72_m8\s*#\(\.INSTANCE\((\w+)\),\s*\.VIAMAP\(""\)\)\s+(\w+)\s*\((.*?)\);',text,re.S)
 assert len(macros)==42,(master,len(macros))
 for pn,cell,ports in macros:
  original=re.search(r'\.'+pn+r'\("([^"]+)"\)',original_params)[1]
  row=next(x for x in manifest['mapping'] if x['original_cell']==original)
  image=(a.loader/row['loader_file']).read_bytes();assert hashlib.sha256(image).hexdigest()==row['image_sha256']
  rows=[int(w,16) for w in image.split()];assert len(rows)==512
  words=[sum(((rows[j//8]>>(b*8+j%8))&1)<<b for b in range(72)) for j in range(4096)]
  n=len(selected);selected.append(row)
  (a.out/f'e{n}.hex').write_text(''.join(f'{w:018x}\n' for w in words))
  body.append(f'reg [71:0] e{n}[0:4095];')
  for port,expr in re.findall(r'\.(addr_in|ce_in)\(([^)]+)\)',ports):
   forced.append(f'force d{idx}.{expr} = '+('addr;' if port=='addr_in' else "1'b1;"))
  q=re.search(r'\.rd_out\(([^)]+)\)',ports)[1]
  checks.append(f'checks=checks+1; if(d{idx}.{q} !== e{n}[i]) errors=errors+1;')
body.append('initial begin')
for n in range(len(selected)):body.append(f'$readmemh("e{n}.hex",e{n});')
body+=list(dict.fromkeys(forced))
body+=['for(i=0;i<4096;i=i+1)begin @(negedge clk);addr=i;@(posedge clk);#2;']+checks+['end','$display("FRAME_ROM checks=%0d errors=%0d",checks,errors);$finish;end endmodule']
(a.out/'tb.sv').write_text('\n'.join(body)+'\n')
files=[]
base=a.prototype.parent
for line in (a.prototype/'bind.f').read_text().splitlines():
 if not line.strip() or line.startswith('+'):continue
 path=Path(line);path=path if path.is_absolute() else base/path
 assert path.exists(),path
 files.append(str(path))
(a.out/'files.f').write_text('\n'.join(files)+'\n')
env=dict(os.environ);env['PATH']=str(Path.home()/'.local/opentallas-tools/bin')+':'+env['PATH']
results=[]
for mut in (0,1):
 cmd=['verilator','--binary','--timing','--top-module','tb','-Wno-fatal','-Wno-lint','-Wno-style',f'-GMUT={mut}','--Mdir',f'obj{mut}','-j','2','-f','files.f','tb.sv']
 with (a.out/f'build{mut}.log').open('w') as log:subprocess.run(cmd,cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str((a.out/f'obj{mut}/Vtb').resolve()),'+OT_ROM_DIR='+str(a.loader)],cwd=a.out,text=True,capture_output=True)
 (a.out/f'run{mut}.log').write_text(r.stdout+r.stderr)
 match=re.search(r'FRAME_ROM checks=(\d+) errors=(\d+)',r.stdout);assert r.returncode==0 and match,r.stdout+r.stderr
 results.append(dict(mutant=mut,checked=int(match[1]),errors=int(match[2])))
assert results[0]==dict(mutant=0,checked=344064,errors=0) and results[1]['errors']>0,results
record=dict(verdict='PASS',scope=__doc__,source_sha256=hashes,selected=selected,results=results,rtl_cycles_added=0)
(a.out/'result.json').write_text(json.dumps(record,indent=1)+'\n');print(json.dumps(dict(verdict='PASS',results=results)))
