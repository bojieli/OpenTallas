#!/usr/bin/env python3
"""Literal control-only binary/init gate; ownership and electrical timing remain open.
No engine datapath, mapping, P&R, or numerical token is elaborated.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
R3=Path('rtl/hdc/ot_qwen_rom_tile_context_candidate_r3_retained.sv')
ME=Path('rtl/hdc/ot_qwen_w12_matvec.sv')
DIST=Path('rtl/physical/ot_qwen_rom_bank5_control_distribution.sv')
PROVIDER=Path('rtl/physical/ot_qwen_rom_reset_parent_provider.sv')
ARITH=Path('rtl/hdc/ot_qwen_w12_arith.sv')
FIELDS=[('nout',18),('tiles',18),('k',18),('wsrc',1),('wbase',24),('ts',24),('ks',24),('js',24),('xbase',24),('xks',24),('xjs',24),('xcs',24),('jsh',3),('split',4),('wcs',24),('round',1),('obase',24),('ots',24),('ojs',24),('mmode',1),('oen',1),('amax',1),('rmax',1),('mbase',24)]

def packet(**updates):
 d=dict(nout=128,tiles=1,k=1,split=6,js=1,ks=32,ts=64);d.update(updates);v=0
 for n,w in FIELDS:v=(v<<w)|d.get(n,0)
 return v

def fixture(mutant=None):
 r=(ROOT/R3).read_text();s=(ROOT/ME).read_text()
 metadata=r[r.index('    wire [CODE_BANKS-1:0] code_rd_bank;'):r.index('    // -- KV slice ----')]
 if mutant=='missing_mask_reset':metadata=metadata.replace('.RESETN(mask_reset_n)',".RESETN(1'b1)")
 decl=s[s.index('    reg              active;'):s.index('    assign ready = !active && !pend;')]
 fast=s.split('end else begin : g_issue_fast',1)[1].split('end endgenerate',1)[0]
 fields='\n'.join(f'wire [{w-1}:0] i_{n};' for n,w in FIELDS)
 text='''`timescale 1ns/1ps
module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output reg QN);
 always @(posedge CLK or negedge RESETN or negedge SETN)
 if(!RESETN) QN<=1'b1;else if(!SETN) QN<=1'b0;else QN<=!D;endmodule
 module INVx1_ASAP7_75t_R(input A,output Y);assign Y=~A;endmodule
 module BUFx4_ASAP7_75t_R(input A,output Y);assign Y=A;endmodule
 module AND3x1_ASAP7_75t_R(input A,B,C,output Y);assign Y=A&B&C;endmodule
 module metadata #(parameter ROM_REPLICA_CELL_RETENTION=0)(input clk,rst_n,wrom_re,input[23:0]wrom_addr,input[2659:0]rom_rd,output[511:0]wrom_q);
 localparam CODE_BANKS=5,TG=4,W=16,MEM_EXTRA=1,AW=24,ROM_CONTROL_DISTRIBUTION=1,ROM_BANK5_CONTROL=1,ROM_HOLD_DIRECT_CAPTURE=1;
 wire[4:0]rom_ce;wire[11:0]rom_addr;wire[119:0]rom_distributed_addr;
 '''+metadata+'''endmodule
 module tb;
 localparam W=16,IL=8,AW=24,NW=18,GT=6144,PRUNE=1,SMIN=6,KV_PREP=3,INT8_WEIGHT=1,INT8_SCALE_WCS_BASE=1;
 reg clk=0,external_reset_n=1,parent_domains_ready=0,ib_go=0;reg[378:0]ib=0,ib_q;reg go_q;
 wire rst_n,launch;wire go=go_q;reg wrom_re,kv_re;reg[23:0]wrom_addr;
 ot_qwen_rom_reset_parent_provider #(.RESET_CONTEXT(1)) provider(.clk_stream(clk),.external_reset_n(external_reset_n),.parent_domains_ready(parent_domains_ready),.ib_go(ib_go),.released_reset_n(rst_n),.launch_enable(launch));
 always @(posedge clk or negedge rst_n) if(!rst_n)go_q<=0;else go_q<=launch;
 always @(posedge clk)ib_q<=ib;
 '''+fields+'\nassign {'+','.join('i_'+n for n,w in FIELDS)+'}=ib_q;\n'+decl+'\ngenerate begin:g_issue_fast\n'+fast+'''end endgenerate
 reg[2659:0]rom_rd;
 wire[511:0]a,b;
 metadata #(.ROM_REPLICA_CELL_RETENTION(0)) inferred(clk,rst_n,wrom_re,wrom_addr,rom_rd,a);
 metadata #(.ROM_REPLICA_CELL_RETENTION(1)) retained(clk,rst_n,wrom_re,wrom_addr,rom_rd,b);
 genvar pair,bank,chunk;
 generate for(pair=0;pair<2;pair=pair+1)begin:rp for(bank=0;bank<5;bank=bank+1)begin:rb
 localparam[31:0]PAYLOAD=32'h12340000+pair*5+bank;
 always @(posedge clk)if(retained.rom_ce[bank])rom_rd[(pair*5+bank)*266+:266]<={10'd0,{8{PAYLOAD}}};
 for(chunk=0;chunk<8;chunk=chunk+1)begin:rc
 always @(negedge clk)if(rst_n)begin
 if(retained.g_pair[pair].g_bank[bank].g_cap.g_direct.g_mask[chunk].local_sel !== inferred.g_pair[pair].g_bank[bank].g_cap.g_direct.g_mask[chunk].local_sel)$fatal(1,"mask equivalence");
 if(retained.g_pair[pair].g_bank[bank].g_cap.g_direct.g_mask[chunk].local_sel !== 0 && retained.g_pair[pair].g_bank[bank].g_cap.g_direct.g_mask[chunk].local_sel !== 1)$fatal(1,"mask not initialized binary");
 end end end end endgenerate
 integer ticks=0;
 task tick;begin #1;clk=1;#1;
 if(launch && (!parent_domains_ready || !rst_n))$fatal(1,"launch before owned readiness");
 if(launch && $isunknown(ib))$fatal(1,"accepted instruction not binary");
 if(rst_n)begin
 if($isunknown(retained.code_sel_q) || $isunknown(retained.code_rd_bank) || $isunknown(retained.code_sel_q2))$fatal(1,"metadata not initialized binary");
 if(retained.code_sel_q !== inferred.code_sel_q || retained.code_rd_bank !== inferred.code_rd_bank || retained.code_sel_q2 !== inferred.code_sel_q2)$fatal(1,"metadata equivalence");
 if(a !== b || $isunknown(b))$fatal(1,"unqualified payload observation");
 end clk=0;#1;ticks=ticks+1;end endtask
 initial begin
 external_reset_n=0;tick;tick;external_reset_n=1;
 '''
 for case in range(7):
  text+=f"ib=379'h{packet(wbase=case*4096 if case<5 else 0,wsrc=int(case==6),k=64 if case==6 else 1):x};\n"
  # Hold readiness low during the early requested launch, then release with
  # the same known instruction stable. This is a boundary stimulus, not an
  # actual service-domain readiness producer receipt.
  text+='parent_domains_ready=0;ib_go=1;tick;tick;ib_go=0;tick;parent_domains_ready=1;tick;ib_go=1;tick;ib_go=0;\n'
  if mutant=='accepted_Z' and case==0:text+="ib[300]=1'bz;ib_go=1;tick;ib_go=0;\n"
  text+='repeat(28)tick;\n'
  if case==3:text+='external_reset_n=0;#1;if(retained.code_sel_q!==0 || retained.code_rd_bank!==0)$fatal(1,"async reset");tick;tick;external_reset_n=1;tick;tick;\n'
 text+='$display("PASS_LITERAL_BINARY_INIT_METADATA_CONTROL ticks=%0d",ticks);$finish;end endmodule\n'
 return text

def run(out,mutant=None):
 if out.exists():raise ValueError('refuse overwrite')
 out.mkdir(parents=True);(out/'fixture.sv').write_text(fixture(mutant))
 command=['iverilog','-g2012','-s','tb','-o',str(out/'sim'),str(out/'fixture.sv'),str(ROOT/DIST),str(ROOT/PROVIDER),str(ROOT/ARITH),str(ROOT/ME)]
 c=subprocess.run(command,capture_output=True,text=True);(out/'compile.log').write_text(c.stdout+c.stderr)
 if c.returncode:
  (out/'terminal.json').write_text(json.dumps(dict(status='FAIL_LITERAL_CONTROL_FIXTURE_COMPILE',returncode=c.returncode,new_engine=False),indent=2)+'\n')
  raise ValueError('literal control fixture compile failed')
 r=subprocess.run(['vvp',str(out/'sim')],capture_output=True,text=True);(out/'run.log').write_text(r.stdout+r.stderr)
 result=dict(status='PASS_LITERAL_BINARY_METADATA_CONDITIONAL_ONLY' if r.returncode==0 else 'FAIL_LITERAL_BINARY_METADATA',returncode=r.returncode,mutant=mutant,
 source_sha256={str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (R3,ME,DIST,PROVIDER,ARITH)},
 retained_cell_instances=85,source_metadata_bits_including_pruned_q2=95,physical_metadata_inventory=90,
 owned_ready_provider='explicit known boundary stimulus only; actual service/serial/KV readiness producer unqualified',
 actual_parent_driven_initialization_contract=False,transition_induction=False,physical_control_survival=False,contextual_SSFF=False,stored_Z='FAIL_RETAINED',new_engine=False,new_map=False,new_token=False)
 (out/'terminal.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--mutant',choices=['missing_mask_reset','accepted_Z']);a=p.parse_args()
 result=run(a.out,a.mutant);print(result['status']);raise SystemExit(result['returncode'])
