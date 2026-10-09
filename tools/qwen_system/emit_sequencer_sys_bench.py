#!/usr/bin/env python3
"""Minimum real-controller fixture: full E/L0..35/H programs, stub engines, host-swapped reference.

This proves control/addresses/tags, not arithmetic or engine execution time.
"""
import argparse
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def emit(out):
    old=(ROOT/'rtl/qwen_sys/missing_masters_20261007/gen/ot_qfd_sp_constants_sequencer.sv').read_text()
    ports=re.findall(r'^    (input|output)  ?wire (?:\[([^\]]+)\] )?([a-zA-Z0-9_]+),?$',old,flags=re.M)
    assert len(ports)>110,len(ports)
    removed={'h_start','tp_token','tp_pos','pw_v','pw_addr','pw_data','dw_v','dw_addr','dw_data'}
    s=['`timescale 1ns/1ps','module tb_qfd_sequencer_sys #(parameter integer DIE_RANK=0);',
       'localparam W=16,G=6144,AW=24,NW=18,PAW=12,SW=64,LV=7,D=4;',
       'reg clk=0; always #5 clk=~clk; reg rst_n=0;',
       'reg d_start=0; reg [17:0] d_token=151000,d_pos=0; reg [1:0] d_gen=0;',
       'wire d_done,d_drained,d_fault; wire [1:0] d_done_gen; wire [17:0] d_next_token;',
       'wire [31:0] d_next_val,d_cycles; wire [3:0] d_fault_code;',
       'wire [5:0] stage,st_layer,st_next_layer,st_crom;',
       'wire h_start=dut.h_start; wire [17:0] tp_token=dut.tp_token,tp_pos=dut.tp_pos;']
    for dr,w,n in ports:
        if n in {'clk','rst_n','h_start','tp_token','tp_pos'}: continue
        shape=f'[{w}] ' if w else ''
        s.append(f'{"reg" if dr=="input" else "wire"} {shape}{n}'+('=0;' if dr=='input' else ';'))
        if dr=='output':s.append(f'wire {shape}r_{n};')
    dut=['.clk(clk)', '.rst_n(rst_n)', '.d_start(d_start)', '.d_token(d_token)', '.d_pos(d_pos)', '.d_gen(d_gen)']
    dut += [f'.{n}({n})' for dr,w,n in ports if n not in removed|{'clk','rst_n'}]
    dut += [f'.{n}({n})' for n in ['d_done','d_drained','d_fault','d_done_gen','d_next_token','d_next_val','d_cycles','d_fault_code','stage','st_layer','st_next_layer','st_crom']]
    s.append('ot_qfd_sp_constants_sequencer_sys #(.SYS_ENABLE(1),.DIE_RANK(DIE_RANK),.SYS_BASE_MUT(`SYS_MUT),.WDOG(200000)) dut ('+','.join(dut)+');')
    ref=[f'.{n}({"r_" if dr=="output" else ""}{n})' for dr,w,n in ports]
    s.append('ot_qfd_sp_constants_sequencer #(.FQ_HEAD(1),.MSTN(1)) reference_master ('+','.join(ref)+');')
    s += ['integer errors=0, cycles=0, starts=0, me_ops=0,su_ops=0,coll_ops=0,i,bank,j,rx_left=0,rx_rank=0,case_no=0;',
          'reg check_commands=1,previous_done=0; reg [23:0] expected_code,expected_scale; reg [1:0] expected_prog;',
          'always @(posedge clk) begin expected_code<=(stage==0?0:stage==37?36:stage-1)*512; expected_scale<=(stage==0?0:stage==37?36:stage-1)*1056; end',
          'task bad(input [255:0] what); begin errors=errors+1; if(errors<20)$display("SYS_BAD cycle=%0d stage=%0d what=%0s",cycles,stage,what); end endtask',
          'always @(negedge clk) if(rst_n && check_commands) begin',
          ' cycles=cycles+1;',
          ' if(h_start)begin',
          '  $display("SYS_START stage=%0d cycle=%0d",stage,cycles);',
          '  if(stage!==starts || st_layer!==(starts==0 || starts==37 ? 63 : starts-1)) bad("stage traversal");',
          '  if(st_crom!==(starts==0 ? 63 : starts==37 ? 36 : starts-1))bad("constant stage");',
          '  if(st_next_layer!==(starts<36 ? starts : 63))bad("next layer");',
          '  expected_prog=starts==0?0:starts==37?2:1;',
          '  for(i=0;i<64;i=i+1)reference_master.prog_mem[i]=dut.sys_program(expected_prog,i);',
          '  for(i=0;i<8;i=i+1)reference_master.desc_mem[i]=dut.sys_descriptor(expected_prog,i);',
          '  starts=starts+1;',
          ' end',
          ' if(po_me_go)begin me_ops=me_ops+1;']
    for dr,w,n in ports:
        if dr=='output' and (n=='po_me_go' or n.startswith('po_me_i_')):
            expr='r_'+n
            if n=='po_me_i_wbase':expr='r_po_me_i_wbase+(po_me_i_wsrc?0:expected_code)'
            if n=='po_me_i_wcs':expr='r_po_me_i_wcs+(po_me_i_wsrc?0:expected_scale)'
            s.append(f' if({n} !== ({expr}))bad("{n}");')
    s += [' end',' if(po_su_go)begin su_ops=su_ops+1;']
    for dr,w,n in ports:
        if dr=='output' and (n=='po_su_go' or n.startswith('po_su_i_')):
            s.append(f' if({n} !== r_{n})bad("{n}");')
    s += [' end',
          ' if(s_done!==r_s_done || s_fault!==r_s_fault || core_fault!==r_core_fault)bad("sequencer status");',
          ' if(s_done && !previous_done)$display("SYS_STAGE_DONE stage=%0d cycle=%0d",stage,cycles); previous_done=s_done;',
          ' if(c_valid)begin',
          '  if(c_mode && (c_data[49:32] !== (18\'(DIE_RANK*37984+17))))bad("head rank identity");',
          '  if(c_tag!=={d_gen,stage,d_pos[12:0],d_token[7:0],reference_master.b_c_tag[2:0]})bad("fullshape tag");',
          '  if(c_data!==r_c_data || c_last!==r_c_last || c_mode!==r_c_mode)bad("collective packet");',
          ' end',
          ' r_valid=0;r_last=0;',
          ' if(rx_left>0)begin',
          '  r_valid=1;r_last=(rx_left==1);r_rank=rx_rank;r_data=0;',
          "  if(c_mode)r_data={462'd0,18'd17+rx_rank*18'd37984,32'h3f800000};",
          '  rx_left=rx_left-1;rx_rank=rx_rank+1;',
          ' end else if(c_valid && c_ready && c_last)begin rx_left=c_mode?4:256;rx_rank=0;coll_ops=coll_ops+1;end',
          ' if(cycles>200000)begin $display("SYS_TIMEOUT stage=%0d seq=%0d core=%0d",stage,dut.u_seq.u_base.st,dut.u_ctrl.st);$fatal;end',
          'end',
          'initial begin',
          " kv_write_drained=1;kv_ok=1;me_mem_ok=1;c_ready=1;pi_me_ready=1;pi_me_idle=1;pi_me_am_idx=17;pi_me_am_val=32'h3f800000;pi_me_am_any=1;pi_me_progress=16'hffff;",
          " pi_su_ready=1;pi_su_idle=1;pi_su_progress=16'hffff;pi_su_progress_rows=16'hffff;",
          ' repeat(5)@(negedge clk);rst_n=1;repeat(5)@(negedge clk);',
          ' for(case_no=0;case_no<2;case_no=case_no+1)begin',
          '  d_pos=case_no==0?0:8191;d_gen=case_no;starts=0;',
          '  @(negedge clk);d_start=1;@(negedge clk);d_start=0;',
          '  wait(!d_done);wait(d_done);@(negedge clk);',
          "  if(starts!=38 || !d_drained || d_fault || d_done_gen!=d_gen || d_next_token!=17 || d_next_val!=32'h3f800000)bad(\"final report\");",
          '  $display("SYS_CASE pos=%0d starts=%0d me=%0d su=%0d coll=%0d cycles=%0d bad=%0d",d_pos,starts,me_ops,su_ops,coll_ops,d_cycles,errors);',
          '  repeat(5)@(negedge clk);',
          ' end',
          ' check_commands=0;rst_n=0;repeat(5)@(negedge clk);rst_n=1;repeat(5)@(negedge clk);',
          ' d_start=1;@(negedge clk);d_start=0;',
          " wait(dut.prog_re);force dut.prog_addr=12'd64;repeat(2)@(negedge clk);release dut.prog_addr;",
          ' wait(d_done);@(negedge clk);if(!d_fault || d_fault_code!=2 || d_drained)bad("program bounds fault");',
          ' $display("SYS_BOUNDS_FAULT pass=%0d code=%0d",d_fault && d_fault_code==2 && !d_drained,d_fault_code);',
          ' $display("SEQUENCER_SYS_RESULT pass=%0d cases=2 stages=76 me=%0d su=%0d coll=%0d bad=%0d",errors==0,me_ops,su_ops,coll_ops,errors);',
          ' if(errors)$fatal(1,"control/command mismatch");$finish;',
          'end endmodule']
    out.write_text('\n'.join(s)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);emit(p.parse_args().out)
