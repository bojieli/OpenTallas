#!/usr/bin/env python3
"""Full-width deterministic edge oracle for the four previously unviewed A2F leaves.
No parent RTL or receipt is modified. Mutants corrupt a DUT output (W0/FJ)
or select the wrong release tap (rsched), and must be observed by the oracle.
The REL8-to-REL10 delayed comparison excludes reset flush transients (20 edges);
request outputs are checked across resets. The full source-pinned parent proof
provides reset/calendar integration coverage.
"""
import argparse, pathlib, subprocess, tempfile, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as D
VM='rtl/dsrom_sys/s81_ph/vm/'
P={'header':('s81_a2_w0_header','tools/s81_vm/area_a2_controlled.sv'),
'payload':('s81_a2_w0_payload','tools/s81_vm/area_a2_controlled.sv'),
'fault':('s81_a2f_fault_join4','tools/s81_vm/area_a2f.sv'),
'rsched':('dsfd_vm_a2f_rsched_p',VM+'dsfd_vm_a2f_rsched.sv')}
def main():
 a=argparse.ArgumentParser();a.add_argument('leaf',choices=P);a.add_argument('--mutant',action='store_true');a=a.parse_args()
 top,src=P[a.leaf];m=next(x for x in D.parse_modules((ROOT/src).read_text(),src) if x.name==top);env=m.env({});ws={n:m.width(n,env) for n in m.ports}
 ins=[n for n in ws if m.ports[n][0]=='input'];outs=[n for n in ws if n not in ins]
 t=['module tb; reg ck=0; always #5 ck=~ck; integer c,j,seed=817,since_reset=0; reg ep_rst=0; reg [1:0] rr=0; reg [2:0] epoch=0;']
 for n,w in ws.items():
  if n=='ck':continue
  t.append(f'{"reg" if n in ins else "wire"} [{w-1}:0] {n};')
 t.append(top+(' #(.REL(10))' if a.mutant and a.leaf=='rsched' else '')+' dut('+','.join('.'+n+'('+n+')' for n in ws)+');')
 if a.leaf=='rsched':
  for n in outs:t.append(f'wire [{ws[n]-1}:0] ref_{n}; reg [{ws[n]-1}:0] d1_{n},d2_{n};')
  t.append('dsfd_vm_static_rsched_p refdut('+','.join('.'+n+'('+(n if n in ins else 'ref_'+n)+')' for n in ws)+');')
  delayed={'release_v','release_group','release_mask','prepare_v','prepare_group','prepare_mask','expected_v','release_slot','aux_expected','mx_expected','mx_rslot'}
 if a.leaf=='fault':t.append('reg [39:0] pf=0; reg [3:0] expfault=0;')
 t.append('initial begin rst_n=0;')
 if a.mutant and a.leaf!='rsched':
  n={'header':'o_row','payload':'o_data','fault':'fault'}[a.leaf];t.append(f'force dut.{n}[0]=0;')
 t.append('for(c=0;c<900;c=c+1) begin @(negedge ck); rst_n=!(c<7 || (c>=211 && c<212) || (c>=503 && c<510));')
 for n in ins:
  if n in ('ck','rst_n'):continue
  t.append(f'for(j=0;j<{ws[n]};j=j+1) {n}[j]=$random(seed);')
 t.append('@(posedge ck);')
 if a.leaf in ('header','payload'):
  t.append("epoch=rr[1] ? epoch+1 : 0; rr=ep_rst ? {rr[0],1'b1}:0; ep_rst=rst_n; #1;")
  for n in outs:
   e='epoch' if n=='o_epoch' else 'i_'+n[2:]
   t.append(f'if(c>9 && {n} !== {e}) begin $display("LEAF FAIL {a.leaf} %0d {n}",c); $finish; end')
 elif a.leaf=='fault':
  t.append("for(j=0;j<4;j=j+1) expfault[j]=rr[1] ? |pf[10*j+:10]:0; pf=i_fault; rr=ep_rst ? {rr[0],1'b1}:0; ep_rst=rst_n; #1; if(c>9 && fault!==expfault) begin $display(\"LEAF FAIL fault %0d\",c);$finish;end")
 else:
  t.append('#1; if(!rst_n) since_reset=0; else since_reset=since_reset+1;')
  for n in outs:
   lhs='d2_'+n if n in delayed else n
   cond='c>25 && since_reset>20' if n in delayed else 'c>25'
   t.append(f'if({cond} && {lhs} !== ref_{n}) begin $display("LEAF FAIL rsched %0d {n}",c);$finish;end')
  for n in outs:t.append(f'd2_{n}=d1_{n};d1_{n}={n};')
 t.append('end $display("LEAF PASS '+a.leaf+'");$finish;end endmodule')
 with tempfile.TemporaryDirectory() as d:
  tb=pathlib.Path(d)/'tb.sv';tb.write_text('\n'.join(t));bin=pathlib.Path(d)/'tb'
  files=[ROOT/src]+([ROOT/(VM+'dsfd_vm_static_rsched.sv')] if a.leaf=='rsched' else [])
  subprocess.run(['iverilog','-g2012','-s','tb','-o',str(bin),str(tb),*map(str,files)],check=True)
  out=subprocess.check_output(['vvp',str(bin)],text=True);print(out,end='')
  return 0 if 'LEAF PASS '+a.leaf in out else 1
if __name__=='__main__':sys.exit(main())
