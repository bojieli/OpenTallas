#!/usr/bin/env python3
"""Bounded real producer+START consumer+mapped VM visibility composition.
The c0 read-pin test adapter is explicit; it is not a qualified native engine.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from wfc_guard_gate import instance
from wfc_start_gate import FILES,START_PHASE

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 pkg=json.loads((a.source/'source_manifest.json').read_text());files=[];pins={}
 for entry in pkg['files']:
  f=a.source/Path(entry['path']).name
  if f.suffix not in('.sv','.v')or f.name.startswith('tb_'):continue
  h=hashlib.sha256(f.read_bytes()).hexdigest()
  if h!=entry['sha256']:raise ValueError('source drift '+str(f))
  files.append(f);pins[entry['path']]=h
 local=[a.root/f for f in FILES[:-1]]
 names={f.name for f in files};local=[f for f in local if f.name not in names]
 pins.update({str(f.relative_to(a.root)):hashlib.sha256(f.read_bytes()).hexdigest()for f in local})
 # Same source transaction epoch as the separate producer gate, with no wait.
 s=(a.root/'tools/s81_vm/wfc_start_bench.sv').read_text().replace('if(tc==198+phase)','if(tc==200+phase)')
 s=s.replace('module tb_wfc_start;','module tb_wfc_start;\n localparam integer READ_PIPE=4,HOP1=1;\n wire t_ck=ck,s_ck=sk,rss=rn,rst=rn;')
 core=a.source/'dsfd_vm_a2f_core.sv';wfc=a.source/'dsfd_vm_static_wfc.sv'
 c=instance(core.read_text(),'dsfd_vm_a2f_core','u_core',dict(wf_v='wv',wf_row='wr',wf_d='wd',x_av="{av,3'b0,cmd[84]}",x_ar="{ar,42'd0,14'd1024}",x_rv='xrv',x_rd='xrd',vm_fault='vm_fault',edge_f="{1'b0,wfc_fault,1'b0}"),'#(.READ_PIPE(4),.HOP1(1))')
 f=instance(wfc.read_text(),'dsfd_vm_static_wfc','u_wfc',dict(f_wfc='fwfc',t_wfc='twfc',w_v='wv',w_row='wr',w_d='wd',a_v='av',a_row='ar',e_v='xrv[7:4]',e_d='xrd[4095:2048]',vm_fault='vm_fault',fault='wfc_fault'),'#(.RLAT(15),.RESPONSE_PAD(2))')
 extra='''
 wire[559:0]fwfc={32'd0,swd,swv};wire[1028:0]twfc;
 wire wv;wire[13:0]wr;wire[511:0]wd;wire[3:0]av;wire[55:0]ar;
 wire[7:0]xrv;wire[4095:0]xrd;wire vm_fault,wfc_fault;
 integer vmwrite=-1,vmcommit=-1,firstread=-1,replies=0,sourceinput=-1,outwrite=-1,rawwrite=-1;
 always@(posedge sk)if(rn&&swv&&swd[526:512]==1024)outwrite=sc;
 always@(posedge ck)begin
  if(rn)begin
   if(vw[527]&&cs[52])sourceinput=tc;
   if(wv&&wr==1024)vmwrite=tc;
   if(u_core.u_mem.slice[0].u_slice.bank[0].u_bank.u_sram.w_ce_in&&u_core.u_mem.slice[0].u_slice.bank[0].u_bank.u_sram.w_addr_in==32)rawwrite=tc;
   if(u_core.cm_v[0]&&u_core.cm_a[8:0]==32)vmcommit=tc;
   if(cmd[84])firstread=tc;
   #0.1;
   if(xrv[0])begin replies=replies+1;if(xrd[511:0]!=={16{32'heca86420}})$fatal(1,"actual consumer-command mapped SRAM stale");end
  end
 end
'''
 s=s.replace(' localparam[51:0]META=',extra+c+'\n'+f+'\n localparam[51:0]META=')
 s=s.replace('integer tc=0,','integer badwrite=0; initial if($value$plusargs("BADWRITE=%d",badwrite))begin end\n integer tc=0,')
 s=s.replace("vw={1'b1,15'd1024,{16{32'heca86420}}};","vw={1'b1,15'd1024,({16{32'heca86420}} ^ (badwrite?512'd1:512'd0))};")
 s=s.replace('if(sc==250)begin','''if(sc==250)begin
    $display("START_VM_RESULT phase=%0d write=%0d commit=%0d firstread=%0d replies=%0d vmfault=%0d wfcfault=%0d sourceinput=%0d outgoingwrite=%0d rawwrite=%0d",phase,vmwrite,vmcommit,firstread,replies,vm_fault,wfc_fault,sourceinput,outwrite,rawwrite);
    if(vmwrite<0||vmcommit<0||firstread<=vmcommit||replies!=1||vm_fault||wfc_fault)$fatal(1,"actual mapped write/START/read ordering");''')
 # A same-edge write and START adds one FIFO entry before the doorbell. The
 # immutable phase table below is supplied as input, never normal feedback.
 bench=a.out/'tb_start_vm.sv';bench.write_text(s);pins['generated_bench']=hashlib.sha256(bench.read_bytes()).hexdigest()
 cmd=[str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'),'--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH','-j','8','-MAKEFLAGS','OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0','--top-module','tb_wfc_start','--Mdir',str(a.out/'obj'),'-o','sim',*map(str,files+local),str(bench)]
 with(a.out/'build.log').open('w')as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError('build failed')
 rows=[]
 # Calibration runs diagnose only the immutable input schedule and are not
 # qualification. Then each actual programme is loaded before its START.
 phases=[]
 for phase in range(8):
  r=subprocess.run([str(a.out/'obj/sim'),f'+PHASE={phase}','+CAL=1'],capture_output=True,text=True)
  (a.out/f'cal{phase}.log').write_text(r.stdout+r.stderr)
  m=re.search(r'START_CAL phase=\d+ sp=(\d+)',r.stdout)
  if not m:raise RuntimeError('missing real producer calendar epoch')
  phases.append(int(m.group(1)))
 (a.out/'compiled_phase.json').write_text(json.dumps(phases)+'\n')
 for phase,sp in enumerate(phases):
  r=subprocess.run([str(a.out/'obj/sim'),f'+PHASE={phase}',f'+SP={sp}'],capture_output=True,text=True)
  (a.out/f'phase{phase}.log').write_text(r.stdout+r.stderr)
  m=re.search(r'START_VM_RESULT (.*)',r.stdout);n=re.search(r'START_RESULT (.*)',r.stdout)
  if r.returncode or not m or not n:raise RuntimeError('combined gate failed '+str(phase))
  rows.append(dict(phase=phase,vm=m.group(1),start=n.group(1)))
 negative=[]
 for phase,sp in enumerate(phases):
  r=subprocess.run([str(a.out/'obj/sim'),f'+PHASE={phase}',f'+SP={sp}','+BADWRITE=1'],capture_output=True,text=True)
  (a.out/f'wrongwrite{phase}.log').write_text(r.stdout+r.stderr)
  if not r.returncode or 'actual consumer-command mapped SRAM stale'not in r.stdout:raise RuntimeError('wrongwrite escaped actual SRAM consumer')
  negative.append(dict(phase=phase,rc=r.returncode,failure='actual mapped SRAM read payload mismatch'))
 rec=dict(wrong_write_negative=negative,schema='opentallas.s81.posted-start-mapped-functional.v1' ,qualified=False,source_sha256=pins,compiler_phase=phases,compiler_extra_write_to_start_guard_core_edges=0,scope='actual producer,40generated station semantics,static_c8 PW36,currentWFC+128mappedSRAM; c0-command toVMread is explicit benchadapter, notnativeengine',rows=rows,physical_clocks_qualified=False,early_start_commit_failure_proven=False)
 (a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print('START_VM PASS',len(rows))
if __name__=='__main__':main()
