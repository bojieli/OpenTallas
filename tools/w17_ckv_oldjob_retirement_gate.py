#!/usr/bin/env python3
"""Bounded source-pinned old P/C/W jobs; injected return/completion delays are fixtures, not service bounds."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];PIN='d2c28c279c4b8df731f9c4937e790831529a954b'
P=r'''
`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;reg rst_n=0,pv=0;wire pr,done,valid,hold,fault;
wire[3:0]qv,rr;wire[63:0]qt;reg[3:0]rv=0;reg[63:0]rt=0;reg[1023:0]data=0;
wire[31:0]ni,nr;wire[2047:0]pairs;
ot_chip_v41x_rope_hbm_cache dut(.clk(clk),.rst_n(rst_n),.pf_v(pv),.pf_rdy(pr),.pf_kind(1'b0),.pf_pos(21'd0),.pf_release(1'b0),.pf_done(done),.cache_valid(valid),.cache_hold(hold),.cache_kind(),.cache_pos(),.cache_pairs(pairs),.table_present(2'b11),.plain_base(120'd0),.yarn_base(120'd0),.req_v(qv),.req_rdy(4'hf),.req_addr(),.req_len(),.req_tag(qt),.req_we(),.req_wdata(),.req_wstrb(),.rsp_v(rv),.rsp_rdy(rr),.rsp_tag(rt),.rsp_beat(16'd0),.rsp_data(data),.fault(fault),.issued_sectors(ni),.received_sectors(nr),.stalled_cycles(),.cache_hits());
integer cyc=0,issued=0,received=0,mode=0;integer count[0:3],sent[0:3];reg[15:0]tags[0:3][0:1];
initial begin if($value$plusargs("MODE=%d",mode))begin end for(integer a=0;a<4;a=a+1)begin count[a]=0;sent[a]=0;tags[a][0]=0;tags[a][1]=0;end end
always @(posedge clk)if(rst_n===1'b1)begin
 for(integer a=0;a<4;a=a+1)begin
  if(qv[a]===1'b1)begin if(count[a]>=2)$fatal(1,"P request overflow");tags[a][count[a]]=qt[a*16+:16];count[a]=count[a]+1;issued=issued+1;end
  if(rv[a]===1'b1)begin if(rr[a]!==1'b1)$fatal(1,"P reserved return refused");sent[a]=sent[a]+1;received=received+1;end
 end
 #1;
 if(fault!==1'b0)$fatal(1,"P fault");
 if(done!==1'b0 && done!==1'b1)$fatal(1,"P unknown done");
 if(done===1'b1)begin
  if(issued!==8||received!==8||ni!==32'd8||nr!==32'd8||valid!==1'b1||hold!==1'b1||qv!==0||rr!==0)$fatal(1,"P early retirement");
  $display("PASS_P_OLD_RETIRED issued=8 received=8");$finish;
 end
end
always @(negedge clk)begin
 cyc=cyc+1;if(cyc==5)rst_n=1;pv=(cyc==7);rv=0;rt=0;data=0;
 if(cyc>40)for(integer a=0;a<4;a=a+1)if(sent[a]<count[a] && !(mode==1 && a==3 && sent[a]==1))begin rv[a]=1;rt[a*16+:16]=tags[a][sent[a]];data[a*256+:256]={8{32'h3f800000}};end
 if(cyc==300)$fatal(1,"finite P drain failed issued=%0d received=%0d",issued,received);
end
endmodule
'''
C=r'''
`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;reg rst_n=0,jv=0,ready=0;wire jr,ov,done,fault;wire[1:0]fc;
wire[3:0]mv;wire[39:0]mt;reg[3:0]sv=0;reg[39:0]st=0;wire[2303:0]row;
ot_chip_v41x_ckv_sel_fetch #(.DIE_ID(0),.NSLOT(64),.K(512)) dut(.clk(clk),.rst_n(rst_n),.job_v(jv),.job_ready(jr),.window_count(8'd0),.published_source_count(21'd1),.region_base_sector({4{30'd64}}),.region_sector_count({4{30'd9}}),.id_count(10'd1),.id_done(1'b1),.id_idx(),.id_rank_in(10'd0),.id_gid(21'd0),.id_die(2'd0),.o_v(ov),.o_ready(ready),.o_rank(),.o_gid(),.o_row(row),.done(done),.fault(fault),.fault_code(fc),.st_owned_rows(),.m_v(mv),.m_rdy(4'hf),.m_addr(),.m_tag(mt),.s_v(sv),.s_tag(st),.s_beat(16'd0),.s_data(1024'd0));
integer cyc=0,issued=0,received=0,emitted=0,mode=0;reg[9:0]tags[0:8];
initial begin if($value$plusargs("MODE=%d",mode))begin end for(integer a=0;a<9;a=a+1)tags[a]=0;end
always @(posedge clk)if(rst_n===1'b1)begin
 if(mv[0]===1'b1)begin if(issued>=9)$fatal(1,"C request overflow");tags[issued]=mt[0+:10];issued=issued+1;end
 if(sv[0]===1'b1)received=received+1;
 if(ov===1'b1 && ready===1'b1)emitted=emitted+1;
 #1;
 if(fault!==1'b0)$fatal(1,"C fault");
 if(done!==1'b0 && done!==1'b1)$fatal(1,"C unknown done");
 if(done===1'b1)begin
  if(issued!==9||received!==9||emitted!==1||ov!==1'b0||jr!==1'b1||dut.busy!==64'd0)$fatal(1,"C early retirement");
  $display("PASS_C_OLD_RETIRED issued=9 received=9 emitted=1");$finish;
 end
end
always @(negedge clk)begin
 cyc=cyc+1;if(cyc==5)rst_n=1;jv=(cyc==7);ready=(cyc>60 && mode!=1);sv=0;st=0;
 if(cyc>30 && received<issued)begin sv[0]=1;st[0+:10]=tags[received];end
 if(cyc==300)$fatal(1,"finite C drain failed issued=%0d received=%0d emitted=%0d",issued,received,emitted);
end
endmodule
'''
W=r'''
`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;reg rst_n=0,bv=0;wire br,pr,fault;wire[3:0]mv,we;reg[3:0]wd=0;
ot_chip_v41x_window_kv_prefetch #(.WIN_STACK(0)) dut(.clk(clk),.rst_n(rst_n),.region_base_sector(30'd64),.region_sector_count(30'd2176),.prime_v(1'b0),.prime_ready(),.prime_user(10'd0),.prime_row(21'd0),.blk_v(bv),.blk_ready(br),.blk_user(10'd0),.blk_row(21'd0),.blk_idx(4'd0),.blk_codes(256'd0),.blk_scale(8'd127),.prefetch_v(1'b0),.prefetch_ready(pr),.prefetch_user(10'd0),.prefetch_row(21'd0),.kv_ok(),.re(1'b0),.ruser(10'd0),.rrow(21'd0),.relem(9'd0),.q(),.packed_re(1'b0),.packed_ruser(10'd0),.packed_rrow(21'd0),.packed_ridx(4'd0),.packed_valid(),.packed_row(),.packed_codes(),.packed_scale(),.fault(fault),.fault_code(),.st_rows_fetched(),.st_blocks_written(),.st_sectors_read(),.st_sectors_written(),.m_v(mv),.m_rdy(4'hf),.m_addr(),.m_len(),.m_tag(),.m_we(we),.m_wdata(),.m_wstrb(),.m_wr_done(wd),.s_v(4'd0),.s_rdy(),.s_tag(64'd0),.s_beat(16'd0),.s_data(1024'd0));
integer cyc=0,writes=0,acks=0,due=0,mode=0;
initial begin if($value$plusargs("MODE=%d",mode))begin end end
always @(posedge clk)if(rst_n===1'b1)begin
 if(mv[0]===1'b1)begin if(we[0]!==1'b1||due!=0)$fatal(1,"W ownership violation");writes=writes+1;due=cyc+7;end
 if(wd[0]===1'b1)acks=acks+1;
 #1;
 if(fault!==1'b0)$fatal(1,"W fault");
 if(cyc>7 && br===1'b1)begin
  if(writes!==2||acks!==2||pr!==1'b1)$fatal(1,"W early retirement");
  $display("PASS_W_OLD_RETIRED writes=2 completions=2");$finish;
 end
 if(cyc>7 && br!==1'b0 && br!==1'b1)$fatal(1,"W unknown retirement");
end
always @(negedge clk)begin
 cyc=cyc+1;if(cyc==5)rst_n=1;bv=(cyc==7);wd=0;
 if(due!=0 && cyc==due && !(mode==1 && writes==2))begin wd[0]=1;due=0;end
 if(cyc==300)$fatal(1,"finite W drain failed writes=%0d completions=%0d",writes,acks);
end
endmodule
'''
SPECS={
 'P':(P,['rtl/chip/ot_chip_v41x_rope_hbm_cache.sv'],'issued=8 received=7'),
 'C':(C,['rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv','rtl/chip/ot_chip_v41x_ckv_selected_dma.sv','rtl/chip/ot_chip_v41x_ckv_fp4_decode.sv'],'issued=9 received=9 emitted=0'),
 'W':(W,['rtl/chip/ot_chip_v41x_window_kv_prefetch.sv','rtl/chip/ot_chip_v41x_window_row_codec.sv'],'writes=2 completions=1')}
SPECS['W_banked']=(W.replace('.WIN_STACK(0)', '.WIN_STACK(0),.BANKED_STAGE(1)'),SPECS['W'][1]+['rtl/chip/ot_chip_v41x_window_stage4.sv'],SPECS['W'][2])
def main(out):
 cases={};pins={}
 with tempfile.TemporaryDirectory(prefix='w17-oldjob-',dir='/home/ubuntu') as tmp:
  d=pathlib.Path(tmp)
  for name,(bench,paths,negative) in SPECS.items():
   sources=[]
   for i,path in enumerate(paths):
    raw=subprocess.check_output(['git','show',PIN+':'+path],cwd=ROOT);pins[path]=dict(commit=PIN,path=path,sha256=hashlib.sha256(raw).hexdigest());f=d/f'{name}{i}.sv';f.write_bytes(raw);sources.append(str(f))
   b=d/f'{name}tb.sv';b.write_text(bench);exe=d/name
   c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(b),*sources],capture_output=True,text=True,timeout=30)
   if c.returncode:cases[name+'_compile']=dict(log=c.stderr,matched_expectation=False);continue
   for mode in [0,1]:
    run=subprocess.run(['vvp',str(exe),f'+MODE={mode}'],capture_output=True,text=True,timeout=30);log=run.stdout+run.stderr
    good=(run.returncode==0 and f'PASS_{name.split("_")[0]}_OLD_RETIRED' in log) if mode==0 else (run.returncode==1 and log.count('FATAL:')==1 and f'finite {name.split("_")[0]} drain failed {negative}' in log and 'Time: 3000000 Scope: tb' in log)
    cases[f'{name}_{mode}']=dict(returncode=run.returncode,log=log,matched_expectation=good,bench_sha256=hashlib.sha256(bench.encode()).hexdigest())
 result=dict(status='PASS_UNCHANGED_OLDJOB_ENDPOINTS' if all(x['matched_expectation'] for x in cases.values()) else 'FAIL_UNCHANGED_OLDJOB_ENDPOINTS',source_pins=pins,cases=cases,scope='production NSLOT64/K512 Cfetch one old row; Pcache8sectors; Wtwo writes with delayed fixture completions at BANKED_STAGE0 and1, REFILL_CREDITS1; no bank read-pipeline retirement exercised. No actual HBM burst-visible provider, peer credit, wholeprelease latency, fulltoken or numerical claim',hardware_admission=False)
 assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(cases,indent=2));return result['status'].startswith('PASS')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();raise SystemExit(0 if main(a.out) else 1)
