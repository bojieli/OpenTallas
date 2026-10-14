#!/usr/bin/env python3
"""Actual fullband/fan integration with independent control and bank-order reference."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'rtl/qwen_sys/vm_plane_20261013'

def main():
 cp=ROOT/'results/arch/qwen_tp8_1012/vm_band_composition_codex.json';comp=json.loads(cp.read_text());band=(P/'band/ot_qfd_vm_band.sv').read_text()
 ports=re.findall(r'input wire(?:\s+\[[^\]]+\])?\s+(\w+)',band)
 v=['`timescale 1ns/1ps','module tb_qfd_vm_band_integration;', 'parameter integer SMAX=9,MUT=0,SEED=1,CYCLES=4000;',
 'localparam integer PHW=SMAX-7,NX=1<<SMAX;', 'reg clk=0;always #5 clk=~clk;',
 'reg me_early=0;reg [1:0] me_delay=0;wire me_ref=me_delay[1];reg me_prev=0;',
 'reg [16383:0] d_s=0,d_n=0;', 'reg [9:0] c_a=0,c_nv=1008;reg c_v=0,o_v=0,sel_v=0;',
 'reg [13:0] c_d=0;reg [3:0] c_j=0,c_sp=7,o_sp=7;', 'reg [PHW-1:0] phase=0;reg [15:0] epoch=0;',
 'wire [19:0] pc_in={c_nv,c_a};wire [27:0] lc_in={o_sp,o_v,c_sp,c_j,c_d,c_v};',
 "wire [27:0] tags_in={{(11-PHW){1'b0}},epoch,sel_v,phase};",
 'wire [639:0] fan_pc;wire [895:0] fan_lc,fan_tags;wire [31:0] fan_me;',
 'ot_qfd_vm_band_controls #(.MUT(MUT),.PHW(PHW)) fan(.clk_child({116{clk}}),.me_early(me_early),.pc(pc_in),.lc(lc_in),.tags(tags_in),.pc_columns(fan_pc),.lc_columns(fan_lc),.tags_columns(fan_tags),.me_columns(fan_me));',
 'reg [19:0] rpc[0:2];reg [27:0] rlc[0:2],rtags[0:2];',
 'always @(posedge clk)begin me_delay<={me_delay[0],me_early};me_prev<=me_ref;if(me_prev)begin rpc[0]<=pc_in;rpc[1]<=rpc[0];rpc[2]<=rpc[1];rlc[0]<=lc_in;rlc[1]<=rlc[0];rlc[2]<=rlc[1];rtags[0]<=tags_in;rtags[1]<=rtags[0];rtags[2]<=rtags[1];end end',
 'wire [9:0] ra=rpc[2][9:0],rnv=rpc[2][19:10];wire rv=rlc[2][0],rov=rlc[2][23],rsel=rtags[2][PHW];',
 'wire [13:0] rd=rlc[2][14:1];wire [3:0] rj=rlc[2][18:15],rsp=rlc[2][22:19],rosp=rlc[2][27:24];',
 'wire [PHW-1:0] rphase=rtags[2][0+:PHW];wire [15:0] repoch=rtags[2][PHW+1+:16];',
 'wire [4095:0] q;wire [32*PHW-1:0] q_phase;wire [511:0] q_epoch;wire [31:0] q_v;',
 'wire [32767:0] ref_inputs;', 'ot_qfd_vm_band #(.SMAX(SMAX)) dut(']
 binds=[]
 fields={'c_a':('fan_pc',0,10),'c_nv':('fan_pc',10,10),'c_v':('fan_lc',0,1),'c_d':('fan_lc',1,14),'c_j':('fan_lc',15,4),'c_sp':('fan_lc',19,4),'o_v':('fan_lc',23,1),'o_sp':('fan_lc',24,4),'phase':('fan_tags',0,'PHW'),'epoch':('fan_tags','PHW+1',16),'sel_v':('fan_tags','PHW',1)}
 for port in ports:
  if port.startswith('ck_'):sig='clk'
  elif port.startswith('me_'):sig='fan_me['+str(int(port.split('_')[1][1:])%32)+']'
  elif port in ('d_s','d_n'):sig=port
  else:
   match=re.fullmatch(r'c(\d+)_(.*)',port);assert match,port
   col=int(match[1]);name,off,width=fields[match[2]];base=20*col if name=='fan_pc' else 28*col
   sig=f'{name}[{base}+({off}) +: {width}]'
  binds.append(f'.{port}({sig})')
 binds.extend(f'.{p}({p})' for p in ('q','q_phase','q_epoch','q_v'))
 v+= [',\n'.join(binds),');','integer cyc,w,k,errors=0,checks=0,lane_checks=0,stalls=0,valids=0;',
 'integer root_changes[0:1023];reg [4095:0] lastq=0;reg [(1<<PHW)-1:0] phase_seen=0;',
 'integer idx[0:127];reg [3:0] split=0;', 'reg [PHW-1:0] ph1=0,ph2=0,ph3=0;reg [15:0] ep1=0,ep2=0,ep3=0;reg v1=0,v2=0,v3=0;',
 'reg [31:0] rng;function automatic [31:0] rnd(input integer dummy);begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);rnd=rng;end endfunction',
 'always @(posedge clk)if(me_prev)begin if(rov)split<=rosp;ph1<=rphase;ph2<=ph1;ph3<=ph2;ep1<=repoch;ep2<=ep1;ep3<=ep2;v1<=rsel;v2<=v1;v3<=v2;',
 'for(k=0;k<128;k=k+1)idx[k]<=((32*rphase+k/4)*4+k%4)%(1<<split);end']
 mapping=[];seen=set()
 for i,seg in enumerate(comp['segments']):
  m=re.fullmatch(r'vm_g(\d+)_b(\d+)_xf([01])>p(\d+)',seg['lane']);assert m,seg['lane']
  region,bank,half,col=map(int,m.groups());globalbank=8*region+bank;absolute=16*globalbank+8*half;off=absolute%512;face='lo' if absolute<512 else 'hi'
  assert (col,absolute)not in seen;seen.add((col,absolute));assert 0<=globalbank<64
  target=f'col{col}_d_{face}';depth=seg['stages'];source=f'{seg["input"][0]}[{seg["input"][1]}+:8]'
  v +=[f'reg [{8*depth-1}:0] delay{i}=0;',f'always @(posedge clk)if(me_prev)delay{i}<='+ (f'{{delay{i}[{8*depth-9}:0],{source}}};'if depth>1 else source+';'),
       f'assign ref_inputs[{1024*col+absolute}+:8]=delay{i}[{8*depth-8}+:8];',
       f'always @(posedge clk)begin #1;if(cyc>40)begin lane_checks=lane_checks+1;if(dut.{target}[{off}+:8]!==delay{i}[{8*depth-8}+:8])errors=errors+1;end end']
  mapping.append(dict(lane=seg['lane'],private_input=seg['input'],globalbank=globalbank,xf=half,col=col,reference_absolute_bit=absolute,reference_face=face,reference_offset=off,enabled_depth=depth))
 assert len(seen)==4096
 for col in range(32):
  v +=[f'wire [1007:0] bv{col};wire [NX-1:0] line{col};reg [127:0] expected2_{col}=0,expected3_{col}=0;',
       f'ot_qfd_vm_xplane_t #(.NRB(64)) ref_p{col}(.clk(clk),.me_e(me_ref),.d(ref_inputs[{1024*col}+:1024]),.c_a(ra),.c_nv(rnv),.q(bv{col}));',
       f'ot_qfd_vm_xline_t #(.NRB(64),.SMAX(SMAX),.SELECT_ONLY(1)) ref_l{col}(.clk(clk),.me_e(me_ref),.d(bv{col}),.c_v(rv),.c_d(rd),.c_j(rj),.c_sp(rsp),.o_v(rov),.o_sp(rosp),.q(),.line_data(line{col}));',
       f'integer k{col};always @(posedge clk)if(me_prev)begin for(k{col}=0;k{col}<128;k{col}=k{col}+1)expected2_{col}[k{col}]<=line{col}[idx[k{col}]];expected3_{col}<=expected2_{col};end',
       f'always @(posedge clk)begin #1;if(cyc>40)begin checks=checks+1;if(q_v[{col}]!==v3 || (q[{128*col}+:128]!==expected3_{col} || q_phase[{col}*PHW+:PHW]!==ph3 || q_epoch[{16*col}+:16]!==ep3))errors=errors+1;end end']
 v+= ["initial begin rng=32'h87654321^SEED;for(w=0;w<1024;w=w+1)root_changes[w]=0;",
 'for(cyc=0;cyc<CYCLES;cyc=cyc+1)begin @(negedge clk);me_early=(rnd(0)%4)!=0;if(!me_early)stalls=stalls+1;',
 'for(w=0;w<512;w=w+1)begin d_s[32*w+:32]=rnd(0);d_n[32*w+:32]=rnd(0);end',
 'c_a=rnd(0);c_nv=1008;c_v=(rnd(0)%2)==0;c_d=1<<(rnd(0)%14);c_j=rnd(0)%9;c_sp=7+rnd(0)%(SMAX-6);o_sp=c_sp;o_v=(rnd(0)%8)==0;phase=rnd(0);epoch=rnd(0);sel_v=(rnd(0)%3)!=0;',
 "@(posedge clk);#2;if(q_v==32'hffffffff)begin valids=valids+1;phase_seen[q_phase[PHW-1:0]]=1;for(w=0;w<1024;w=w+1)if(q[4*w+:4]!==lastq[4*w+:4])root_changes[w]=root_changes[w]+1;end lastq=q;end",
 "for(w=0;w<1024;w=w+1)if(root_changes[w]<16)errors=errors+1;if(phase_seen!=={(1<<PHW){1'b1}})errors=errors+1;",
 'if(errors || checks!=(CYCLES-41)*32 || lane_checks!=(CYCLES-41)*4096 || stalls<CYCLES/8 || valids<CYCLES/3)begin $display("FAIL integration SMAX=%0d MUT=%0d errors=%0d checks=%0d lane_checks=%0d",SMAX,MUT,errors,checks,lane_checks);$fatal(1,"FAIL integration");end',
 '$display("PASS integration SMAX=%0d MUT=%0d actual_columns=32 actual_source_roots=32 fan_children=116 actual_padtiles=270 payload=4096 lane_checks=%0d checks=%0d valids=%0d stalls=%0d",SMAX,MUT,lane_checks,checks,valids,stalls);$finish;end endmodule']
 out=P/'band_integration';out.mkdir(exist_ok=True);(out/'tb_qfd_vm_band_integration.sv').write_text('\n'.join(v)+'\n')
 result=ROOT/'results/arch/qwen_tp8_1012/vm_band_integration_mapping_codex.json'
 result.write_text(json.dumps(dict(schema='opentallas.qwen.vm-band-integration-map.v1',composition_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),band_sha256=hashlib.sha256((P/'band/ot_qfd_vm_band.sv').read_bytes()).hexdigest(),source_private_order='Composition private d_s/n ordering preserved; independent globalbank8*r+b and16bankbits+8*xf derives referenceinput halves/offsets, never segmentoutput positions.',mapping=mapping,physical_assignment='UNASSIGNED',production_throughput='UNMEASURED'),indent=1)+'\n')
 print('generated full116fan +32actualroots +270padtiles integration bench,4096 independent bank/half lane references')
if __name__=='__main__':main()
