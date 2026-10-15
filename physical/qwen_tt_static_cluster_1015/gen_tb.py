# Generates tb_tt_static_regroup.sv from the original parent port list (lockstep ref vs regrouped dut).
import re
P='physical/qwen_tt_static_cluster_1015/'
src=open(P+'ot_qfd_tt_ctlm_static_parent_ref.sv').read()
hdr=src[src.index('module'):src.index(');\n',src.index('module'))]
ports=[]
for part in re.split(r'(?=\b(?:input|output)\s+wire)',hdr):
    m=re.match(r'\s*(input|output)\s+wire\s*(\[[^\]]*\])?\s*(.*?)\s*$',part,re.S)
    if not m: continue
    for n in m.group(3).replace('\n',' ').split(','):
        n=n.strip()
        if n: ports.append((m.group(1),m.group(2) or '',n))
ev=lambda e: eval(e.replace('/','//'))
clks={'ck_head','ck_tree','ck_me_sched'}
L=['`timescale 1ns/1ps','// Lockstep regrouping bench: original parent body (ref) vs hr+tree regrouping (dut); real SRAM models.',
   'module tb_tt_static_regroup;','  reg clk=0; always #0.5 clk=~clk;','  integer cyc=0, errs=0;']
for d,w,n in ports:
    if n in clks: continue
    L.append(f'  reg {w} {n};' if d=='input' else f'  wire {w} r_{n}, d_{n};')
def conn(pref):
    return ','.join(f'.{n}(clk)' if n in clks else (f'.{n}({n})' if d=='input' else f'.{n}({pref}_{n})') for d,w,n in ports)
L.append(f'  ot_qfd_tt_ctlm_static_parent_ref u_ref({conn("r")});')
L.append(f'  ot_qfd_tt_ctlm_static_parent u_dut({conn("d")});')
L.append('  task rnd; begin')
for d,w,n in ports:
    if d=='input' and n not in clks and n!='rst_n':
        m=re.match(r'\[(.*):(.*)\]',w)
        bits=ev(m.group(1))-ev(m.group(2))+1 if m else 1
        L.append(f'    {n} = {{'+','.join(['$urandom']*((bits+31)//32))+'};')
L.append('  end endtask')
L.append('  initial begin rst_n=0; rnd; repeat(20) @(negedge clk) rnd; rst_n=1;')
L.append('    repeat(`NCYC) begin @(negedge clk); rnd; cyc=cyc+1; if(cyc%20000==10000) begin rst_n=0; @(negedge clk); rnd; rst_n=1; end end')
L.append('    if(errs==0) $display("REGROUP_PASS cycles=%0d outputs=%0d",cyc,`NOUT); else $display("REGROUP_FAIL errs=%0d",errs); $finish; end')
L.append('  always @(posedge clk) if(rst_n) begin')
outs=[n for d,w,n in ports if d=='output']
for n in outs:
    L.append(f'    if(r_{n}!==d_{n}) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d {n}",cyc); end')
L.append('  end\nendmodule')
open(P+'tb_tt_static_regroup.sv','w').write('\n'.join(L).replace('`NOUT',str(len(outs)))+'\n')
print(len(ports),len(outs))
