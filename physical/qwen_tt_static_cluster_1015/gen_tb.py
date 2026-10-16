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
# r14: directed real static programme phase before the random phase (the 0818 random-only bench never issued a
# tree command: rom_cmd toggled 0 times in 60,000 cycles, so tree-command mutants could not be observed).  Same
# production PW program load + calendar + GO as rtl/.../tb_qfd_static_head_face.sv (program head_program_rank7.hex),
# explicit idle/ok engine status, then RUNS programme starts with different token/pos.
L.append('  reg [1023:0] prom[0:7]; string ppath; integer pj,pk,prun;')
L.append('  localparam [55:0] COPY={7\'d64,24\'d8192,24\'d8192,1\'b1};')
L.append('  task quiet; begin cp_active=0; native_ret=95\'d3; h_start=0; prog_base=0; pw_v=0; pw_addr=0; pw_data=0;')
L.append('    x_oacc=24\'d3; x_oidle=1; x_oprog=16\'hffff; x_orows=16\'hffff; kv_ok=1; kv_write_drained=1; me_mem_ok=0;')
L.append('    up_fault=0; land_cnt=0; tr_fault=0; p_am=0; p_fault=0; fab_fault=0; end endtask')
L.append('  task pw(input [9:0] a, input [63:0] v); begin @(negedge clk); quiet; pw_v=1; pw_addr=a; pw_data=v; @(negedge clk); pw_v=0; end endtask')
L.append('  task prog_load; begin')
L.append('    for(pj=0;pj<8;pj=pj+1) for(pk=0;pk<16;pk=pk+1) pw(pj*16+pk, prom[pj][64*pk+:64]);')
L.append('    pw(1016,{32\'h43414c31,32\'d600});')
L.append('    pw(976,{17\'d0,1\'b0,2\'d1,12\'d3,32\'d40}); pw(977,{17\'d0,1\'b0,2\'d3,12\'d4,32\'d60});')
L.append('    pw(978,{17\'d0,1\'b0,2\'d1,12\'d4,32\'d180}); pw(979,{17\'d0,1\'b0,2\'d3,12\'d5,32\'d200});')
L.append('    pw(980,{17\'d0,1\'b0,2\'d1,12\'d5,32\'d320}); pw(981,{17\'d0,1\'b0,2\'d3,12\'d6,32\'d340});')
L.append('    pw(982,{17\'d0,1\'b0,2\'d1,12\'d6,32\'d460}); pw(983,{17\'d0,1\'b1,2\'d0,12\'d7,32\'d600});')
L.append('    pw(1019,{8\'d0,COPY}); pw(1020,{8\'d0,COPY}); pw(1021,{8\'d0,COPY});')
L.append('    pw(1017,{32\'h43414c53,4\'d0,10\'d8,6\'d37,6\'d1,6\'d8});')
L.append('  end endtask')
L.append('  task prog_run(input [17:0] tk, input [17:0] ps); begin')
L.append('    repeat(5) begin @(negedge clk); quiet; end')
L.append('    @(negedge clk); quiet; token=tk; pos=ps; h_start=1; @(negedge clk); quiet; h_start=0;')
L.append('    repeat(640) begin @(negedge clk); quiet; cyc=cyc+1; end')
L.append('  end endtask')
L.append('  initial begin')
L.append('    if(!$value$plusargs("PROGRAM=%s",ppath)) $fatal(1,"PROGRAM plusarg required (actual source programme)"); $readmemh(ppath,prom);')
L.append('    rst_n=0; quiet; token=1; pos=7; repeat(20) @(negedge clk); rst_n=1;')
L.append('    prog_load; for(prun=0;prun<`RUNS;prun=prun+1) prog_run(18\'d1+prun, 18\'d7+3*prun);')
L.append('    $display("PROGRAMME_PHASE_DONE runs=%0d cycles=%0d errs=%0d",`RUNS,cyc,errs);')
L.append('    rst_n=0; rnd; repeat(20) @(negedge clk) rnd; rst_n=1;')
L.append('    repeat(`NCYC) begin @(negedge clk); rnd; cyc=cyc+1; if(cyc%20000==10000) begin rst_n=0; @(negedge clk); rnd; rst_n=1; end end')
L.append('    seam_report;')
L.append('    if(errs==0 && (cmd_pair<`MIN_PAIR || ret_pair<`MIN_PAIR)) $display("REGROUP_UNSENSITIZED cmd_pair=%0d ret_pair=%0d min=%0d",cmd_pair,ret_pair,`MIN_PAIR);')
L.append('    else if(errs==0) $display("REGROUP_PASS cycles=%0d outputs=%0d cmd_pair=%0d ret_pair=%0d",cyc,`NOUT,cmd_pair,ret_pair); else $display("REGROUP_FAIL errs=%0d",errs);')
L.append('    if(errs!=0 || cmd_pair<`MIN_PAIR || ret_pair<`MIN_PAIR) $fatal(1,"REGROUP_NOT_PASS"); $finish; end')
# r14: seam sensitization. Count, on the regrouped dut, cycles where each regroup-seam bit toggles and where the
# two bits a mutant swaps differ; the bench FAILS (not passes vacuously) unless both mutant pairs are exercised.
L.append('  integer ct[0:379], rt[0:94]; integer cmd_pair=0, ret_pair=0, k; reg [379:0] pc; reg [94:0] pr;')
L.append('  initial begin for(k=0;k<380;k=k+1) ct[k]=0; for(k=0;k<95;k=k+1) rt[k]=0; pc=0; pr=0; end')
L.append('  always @(posedge clk) if(rst_n) begin')
L.append('    for(k=0;k<380;k=k+1) if(u_dut.rom_cmd[k]!==pc[k]) ct[k]=ct[k]+1;')
L.append('    for(k=0;k<95;k=k+1) if(u_dut.rom_ret[k]!==pr[k]) rt[k]=rt[k]+1;')
L.append('    pc=u_dut.rom_cmd; pr=u_dut.rom_ret;')
L.append('    if(u_dut.rom_cmd[`CMD_A]!==u_dut.rom_cmd[`CMD_B]) cmd_pair=cmd_pair+1;')
L.append('    if(u_dut.rom_ret[`RET_A]!==u_dut.rom_ret[`RET_B]) ret_pair=ret_pair+1;')
L.append('  end')
L.append('  task seam_report; begin')
L.append('    for(k=0;k<380;k=k+1) if(ct[k]!=0) $display("SEAM_CMD_TOG %0d %0d",k,ct[k]);')
L.append('    for(k=0;k<95;k=k+1) if(rt[k]!=0) $display("SEAM_RET_TOG %0d %0d",k,rt[k]);')
L.append('    $display("SEAM_PAIR cmd[%0d]/cmd[%0d] differ=%0d ret[%0d]/ret[%0d] differ=%0d",`CMD_A,`CMD_B,cmd_pair,`RET_A,`RET_B,ret_pair);')
L.append('  end endtask')
L.append('  always @(posedge clk) if(rst_n) begin')
outs=[n for d,w,n in ports if d=='output']
for n in outs:
    L.append(f'    if(r_{n}!==d_{n}) begin errs=errs+1; if(errs<10) $display("MISMATCH cyc=%0d {n}",cyc); end')
L.append('  end\nendmodule')
open(P+'tb_tt_static_regroup.sv','w').write('\n'.join(L).replace('`NOUT',str(len(outs)))+'\n')
print(len(ports),len(outs))
