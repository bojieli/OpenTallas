#!/usr/bin/env python3
"""Minimum WFC serial write/read guard against one immutable real A2F array.

This consumes a VM-owner flat package; no VM source is rewritten. XIO and
capture producers are uninstantiated. A START doorbell is not a capture START.
"""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_ftok'))
from die_port_bind import header


def width(range_text):
 hi,lo=range_text.rsplit(':',1)
 return f'(({hi})-({lo})+1)'


def instance(text,module,name,special,params=''):
 _,ports=header(text,module)
 if not ports:raise ValueError('missing actual module header '+module)
 pins=[]
 for pin,(direction,ran)in ports.items():
  if pin in special:value=special[pin]
  elif direction=='output':value=''
  elif pin.startswith('ck')or pin=='cks':value='{'+width(ran)+'{'+('s_ck'if pin.endswith('_s')else 't_ck')+'}}'
  elif pin.startswith(('rst','rss')):value='{'+width(ran)+'{'+('rst'if pin.endswith('_s')else 'rss')+'}}'
  else:value="'0"
  pins.append(f'.{pin}({value})')
 return f'{module} {params} {name} ('+',\n  '.join(pins)+');'


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
 p.add_argument('--wfc-sha256',required=True);p.add_argument('--out',type=Path,required=True)
 p.add_argument('--jobs',type=int,default=8);p.add_argument('--max-gap',type=int,default=10)
 a=p.parse_args();a.source=a.source.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
 package=json.loads(a.manifest.read_text());manifest={i['path']:i['sha256']for i in package['files']}if 'files'in package else package;files=[];pins={}
 for rel,expected in manifest.items():
  file=a.source/Path(rel).name
  if file.name.startswith('tb_'):continue
  if file.suffix not in('.sv','.v'):continue
  actual=hashlib.sha256(file.read_bytes()).hexdigest()
  if actual!=expected:raise ValueError('stale package source '+rel)
  files.append(file);pins[rel]=actual
 wfc=a.source/'dsfd_vm_static_wfc.sv';core=a.source/'dsfd_vm_a2f_core.sv'
 if hashlib.sha256(wfc.read_bytes()).hexdigest()!=a.wfc_sha256:raise ValueError('WFC revision not the explicitly selected immutable source')
 _,cports=header(core.read_text(),'dsfd_vm_a2f_core')
 if cports['ck_write_payload'][1]!='15:0':raise ValueError('requires current payload16 parent; historical payload4 package refused')
 c=instance(core.read_text(),'dsfd_vm_a2f_core','u_core',dict(wf_v='wv',wf_row='wr',wf_d='wd',x_av="{av,4'b0}",x_ar="{ar,56'd0}",x_rv='xrv',x_rd='xrd',vm_fault='vm_fault',edge_f="{1'b0,wfc_fault,1'b0}"),'#(.READ_PIPE(4),.HOP1(1))')
 f=instance(wfc.read_text(),'dsfd_vm_static_wfc','u_wfc',dict(f_wfc='fwfc',t_wfc='twfc',w_v='wv',w_row='wr',w_d='wd',a_v='av',a_row='ar',e_v='xrv[7:4]',e_d='xrd[4095:2048]',vm_fault='vm_fault',fault='wfc_fault'),'#(.RLAT(15),.RESPONSE_PAD(2))')
 template=ROOT/'tools/s81_vm/wfc_guard_bench.sv.in';bench=a.out/'tb_wfc_guard.sv'
 bench.write_text(template.read_text().replace('@CORE@',c).replace('@WFC@',f))
 tool=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 cmd=[str(tool),'--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH','-j',str(a.jobs),'-MAKEFLAGS','OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0','--top-module','tb_wfc_guard','--Mdir',str(a.out/'obj'),'-o','sim',*map(str,files),str(bench)]
 (a.out/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
 with(a.out/'build.log').open('w')as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError('build failed; inspect '+str(a.out/'build.log'))
 rows=[];minima={}
 for phase in range(8):
  for gap in range(a.max_gap+1):
   r=subprocess.run([str(a.out/'obj/sim'),f'+PHASE={phase}',f'+GAP={gap}'],capture_output=True,text=True)
   (a.out/f'phase{phase}_gap{gap}.log').write_text(r.stdout+r.stderr)
   m=re.search(r'^WFC_GUARD_RESULT (.*)$',r.stdout,re.M)
   if not m:raise RuntimeError('missing actual guard result')
   row={k:int(v)for k,v in re.findall(r'(\w+)=(-?\d+)',m.group(1))};row['rc']=r.returncode
   if row['errors']:raise RuntimeError('invalid source/phase or fault: '+str(row))
   row['legal']=r.returncode==0 and 'WFC_GUARD PASS'in r.stdout
   rows.append(row)
  legal=[r['gap']for r in rows if r['phase']==phase and r['legal']]
  if not legal:raise RuntimeError('no legal guard found for phase'+str(phase))
  minimum=min(legal);minima[str(phase)]=minimum
  if minimum==0:raise RuntimeError('no earlier client edge available to prove minimum')
  early=next(r for r in rows if r['phase']==phase and r['gap']==minimum-1)
  if early['legal']or not early['old']:raise RuntimeError('earlier guard did not expose actual stale SRAM data')
 if pins!={rel:hashlib.sha256((a.source/Path(rel).name).read_bytes()).hexdigest()for rel in pins}:raise RuntimeError('source drift during build/run')
 rec=dict(schema='opentallas.s81.wfc.minimum-read-guard.v1',scope='one real A2F core and128 mapped SRAM plus WFC; no XIO/capture/kit START qualification',qualified=False,source_sha256=pins,wfc_sha256=a.wfc_sha256,parameters=dict(READ_PIPE=4,HOP1=1,RLAT=15,RESPONSE_PAD=2),minimum_guard_serial_edges=minima,rows=rows,start_path_instantiated=False,start_guard_qualified=False,physical_clocks_qualified=False,source_bench_sha256=hashlib.sha256(bench.read_bytes()).hexdigest())
 (a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(dict(minimum_guard_serial_edges=minima,cases=len(rows),status='PASS')))
if __name__=='__main__':main()
