import re,json,subprocess,hashlib
from pathlib import Path
R=Path('/srv/opentallas-scratch/claude/ref_gate/codex_ctl_safe32_1020');S=Path('/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_ctl_mu6c-20261019-230301/src');G=Path('/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_ctl_mu6c-20261019-230301/routes/gate/work/orfs/results/asap7/opentallas_qkd_kvs_ctl_asap7_ref_gate/base/1_2_yosys.v');C=R/'qkd_kvs_ctl_s32.sv'
# Actual immutable mapped input and final standalone copy graph, all ports preserved.
ports=[]
for m in re.finditer(r'^  (input|output) wire (\[[0-9]+:[0-9]+\] )?(\w+);',C.read_text().split("endmodule",1)[0],re.M):
 d,w,n=m.groups();width=int(w.split(':')[0][1:])+1 if w else 1;ports.append((d,w or '',n,width))
assert len(ports)==45,len(ports)
seq=set(re.findall(r'\b(DFF\w+_ASAP7_75t_R)\s+',G.read_text()));assert seq <= {'DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R'},seq
ys='\n'.join('read_liberty -ignore_miss_func '+str(p) for p in sorted(R.glob('*.lib')))+'\nwrite_verilog '+str(R/'library_imported.v')+'\n'
(R/'pair_models.ys').write_text(ys)
with (R/'pair_models.log').open('w') as f:subprocess.run(['docker','run','--rm','--network','none','-v',str(R)+':'+str(R),(R/'image_id.txt').read_text().strip(),'yosys','-s',str(R/'pair_models.ys')],stdout=f,stderr=subprocess.STDOUT,check=True)
model=(R/'library_imported.v').read_text()
for cell,file in [('DFFASRHQNx1_ASAP7_75t_R','canonical_ASR_normalized.v'),('DFFHQNx1_ASAP7_75t_R','canonical_DFF_normalized.v')]:
 model,n=re.subn(r'(?ms)^module '+cell+r'\b.*?^endmodule\s*', '',model);assert n==1,(cell,n)
 model+='\n'+(R/file).read_text()
(R/'library_verified.v').write_text(model)
macro=list((S/'physical/asap7_memory_macros_v2/ctl_sram_1r1w_64x64_p192').glob('*.v'));macro=[p for p in macro if not p.name.endswith('_bb.v')];assert len(macro)==1,macro
text=['`timescale 1ns/1ps','module tb; parameter integer MUT=0; reg ck=0; always #5 ck=~ck; integer e=0,checks=0,failures=0;']
for d,w,n,bits in ports:
 if n=='ck':continue
 text.append(('reg ' if d=='input' else 'wire ')+w+n+(';' if d=='input' else '_ref, '+n+'_dut;'))
conn=lambda suffix:','.join('.'+n+'('+ (n if d=='input' else n+suffix) +')' for d,w,n,bits in ports)
text+=['qkd_kvs_ctl reference('+conn('_ref')+');','qkd_kvs_ctl_s32 candidate('+conn('_dut')+');','initial begin']
for d,w,n,bits in ports:
 if d=='input' and n!='ck':text.append(n+"='0;")
text+=['for(e=0;e<3000;e=e+1) begin @(negedge ck);']
for d,w,n,bits in ports:
 if d=='input' and n not in ['ck','rst_n','por_n']:
  for lo in range(0,bits,32):
   hi=min(lo+31,bits-1);target=n if bits==1 else n+'[%d:%d]'%(hi,lo);text.append(target+'=$urandom;')
text+=['rst_n=!((e<24)||(e>=900&&e<924)||(e>=1800&&e<1824)); por_n=!(e<24);','@(posedge ck); #1; if(e>=32) begin']
for d,w,n,bits in ports:
 if d=='output':
  expr=n+'_dut'+(" ^ ((MUT==1) ? %d'd1 : %d'd0)"%(bits,bits) if n=='o_hroot_WS' else '')
  text+=['checks++;if('+n+'_ref !== ('+expr+')) begin failures++; if(failures<10)$display("PAIR_MISMATCH e%0d '+n+' ref%h got%h",e,'+n+'_ref,'+n+'_dut);end']
text+=['end end','if(failures)$fatal(1,"CTL_PAIR_FAIL checks%0d failures%0d",checks,failures);','$display("CTL_PAIR_PASS checks%0d edges3000 fulloutputs warmresets2 matchedzeroInit",checks);$finish;end endmodule']
(R/'pair_tb.sv').write_text('\n'.join(text)+'\n')
ver='/root/.local/opentallas-tools/verilator-5.050/bin/verilator'
# Host tool is mounted separately by the launcher.
ver=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
sources=[G,C,R/'library_verified.v',*macro,R/'pair_tb.sv']
res=[]
for mut in [0,1]:
 out=R/('pair_m'+str(mut));out.mkdir(exist_ok=True)
 cmd=[ver,'--binary','--timing','-j','8','-Wno-fatal','-Wno-lint','-Wno-style','--x-initial','0','--x-assign','0','--top-module','tb','-GMUT='+str(mut),'--Mdir',str(out/'obj')]+[str(p) for p in sources]
 with (out/'build.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 if rc:raise SystemExit(rc)
 with (out/'run.log').open('w') as f:rc=subprocess.run([str(out/'obj/Vtb')],stdout=f,stderr=subprocess.STDOUT).returncode
 log=(out/'run.log').read_text();okay=rc==0 and 'CTL_PAIR_PASS' in log if mut==0 else rc!=0 and 'CTL_PAIR_FAIL' in log
 res.append(dict(mut=mut,rc=rc,expected=okay,line=next((l for l in log.splitlines() if 'CTL_PAIR_' in l),'')));print(res[-1],flush=True)
 if not okay:break
(R/'pair_receipt.json').write_text(json.dumps(dict(cases=res,canonical_coupon='3905a5c7d',seq_types=sorted(seq),sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},scope='Mapped vs emitted HDL full-port parser parity under matched zero initialization only; independent initial-state convergence proved separately; not highlevelRTL first-use qualification'),indent=2)+'\n')
raise SystemExit(0 if all(x['expected'] for x in res) and len(res)==2 else 1)
