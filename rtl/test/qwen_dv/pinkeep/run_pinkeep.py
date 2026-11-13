#!/usr/bin/env python3
"""Extract the real g_pin variants: four-region lockstep, mutant and hierarchy/merge control."""
import json,re,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
root=Path.cwd();blocks=[];widths=[]
for kind,path in [('tail','rtl/qwen_dv/s5/s8/qfd_dv_s8_station_tail1.sv'),('nb0','rtl/qwen_dv/s5/s8/qfd_dv_s8_ce.sv')]:
 s=(root/path).read_text();m=re.search(r'localparam integer PW = ([^;]+);',s[s.index('module qfd_dv_s8_station_tail1'):]);W=eval(m.group(1),{'__builtins__':{}});widths.append(W)
 block=re.search(r'generate if \(PIN_IN\) begin : g_pin.*?end endgenerate',s,re.S).group(0)
 for flag in [0,1]:
  blocks.append(('`define' if flag else '`undef')+' OT_QC_PINKEEP\n'+f'module pin_{kind}_{flag}(input ck,input [{W-1}:0] pin_d,output [{W-1}:0] pin_q);localparam PIN_IN=1,PW={W};\n'+block+'\nendmodule\n')
s=(root/'rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv').read_text();helper=re.search(r'\(\* keep_hierarchy="yes" \*\) module qfd_dv_station_copy.*?endmodule',s,re.S).group(0)
dut=helper+'\n'+''.join(blocks);(out/'dut.sv').write_text(dut)
ports=[];calls=[];checks=[];drive=[]
for kind,W in zip(['tail','nb0'],widths):
 ports.append(f'reg [{W-1}:0] d_{kind};wire [{W*4-1}:0] b_{kind},k_{kind};')
 for j in range(4):
  calls.append(f'pin_{kind}_0 b_{kind}{j}(ck,d_{kind},b_{kind}[{j*W} +: {W}]);pin_{kind}_1 k_{kind}{j}(ck,d_{kind},k_{kind}[{j*W} +: {W}]);')
 checks.append(f'if(b_{kind}!==k_{kind}) begin $display("PINKEEP FAIL {kind} cycle%0d",i);$finish(1);end')
 drive.append(f'for(j=0;j<{W};j=j+1)d_{kind}[j]=$random;')
tb='module tb;reg ck=0;always #5 ck=~ck;integer i,j;'+''.join(ports)+''.join(calls)+'initial begin for(i=0;i<2048;i=i+1)begin @(negedge ck);'+''.join(drive)+'@(posedge ck);#1;'+'\n'.join(checks)+'\nend $display("PINKEEP PASS 2048cycles fourcopies tail+nb0");$finish;end endmodule\n';(out/'tb.sv').write_text(tb)
def run(cmd,log):
 r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(out/log).write_text(r.stdout);return r
for mut in [0,1]:
 if mut:
  old='always @(posedge ck) q<=d;'
  # Accept formatting of the real helper, but fail closed unless one assignment is replaced.
  mm=re.search(r'always\s*@\(posedge ck\)\s*q\s*<=\s*d\s*;',dut);assert mm
  dmut=dut[:mm.start()]+re.sub(r'<=\s*d\s*;','<= (d ^ 1);',mm.group(0))+dut[mm.end():];(out/'mut.sv').write_text(dmut)
 dfile=out/('mut.sv' if mut else 'dut.sv');r=run(['iverilog','-g2012','-s','tb','-o',str(out/f'tb{mut}'),str(dfile),str(out/'tb.sv')],f'build{mut}.log');assert r.returncode==0,r.stdout
 r=run(['vvp',str(out/f'tb{mut}')],f'run{mut}.log');assert ('PINKEEP FAIL' if mut else 'PINKEEP PASS') in r.stdout,r.stdout
 print('MUTANT CAUGHT' if mut else r.stdout.strip())
W=widths[1]
for flag in [0,1]:
 top=f'module top(input ck,input [{W-1}:0] d,output [{4*W-1}:0] q);'+''.join(f'pin_nb0_{flag} p{j}(ck,d,q[{j*W} +: {W}]);' for j in range(4))+'endmodule\n';(out/f'top{flag}.sv').write_text(top)
 cmd=f'read_verilog -sv {out}/dut.sv {out}/top{flag}.sv;hierarchy -top top;proc;opt;flatten;opt;write_json {out}/net{flag}.json'
 r=run(['yosys','-Q','-T','-p',cmd.replace(';','; ')],f'synth{flag}.log');assert r.returncode==0,r.stdout
 net=json.load(open(out/f'net{flag}.json'))['modules']
 def count(mod):
  n=0
  for c in net[mod].get('cells',{}).values():
   if c['type'] in net:n+=count(c['type'])
   elif c['type'] in ['$dff','$adff','$sdff']:n+=int(c['parameters']['WIDTH'],2)
  return n
 bits=count('top');print('SYNTH',flag,'ffbits',bits);assert bits==(4*W if flag else W),(flag,bits,W)
print('PINKEEP SUITE PASS')
