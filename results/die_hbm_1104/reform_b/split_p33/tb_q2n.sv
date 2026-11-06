`timescale 1ns/1ps
`default_nettype none
// HBM-REFORM-B5 bench: qslots of the q2n2 body, flat against rest logic + tile, both with kit face models. Random slots + payload.
// dst_v, pin_d, link flit at the first flop of the link, capture fault, faults (+2) compared every edge after flush.
module tb_q2n #(parameter integer MUT=0,parameter integer SEED=1,parameter integer BAD=0)();
 localparam integer NS=9,ND=15,PWT=545,SELW=4,NSL=18;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg [ND-1:0] sink;reg [ND*SELW-1:0] sel;reg [NS-1:0] cap;reg [NS*PWT-1:0] src;reg [NS-1:0] svx;wire [NS-1:0] sv=cap3^svx;
 // common d1 -> d2 -> d3
 reg [ND-1:0] sink2,sink3;reg [ND*SELW-1:0] sel2,sel3;reg [NS-1:0] cap2,cap3;
 always @(posedge clk)begin sink2<=sink;sink3<=sink2;sel2<=sel;sel3<=sel2;cap2<=cap;cap3<=cap2;end
 // ---- flat: pin-sourced words come through the flat core's in face
 reg [NS*PWT-1:0] mask;initial begin mask='0;for(integer s=0;s<NS;s=s+1)for(integer i=0;i<((s==8)?PWT:(s<2||(s>=4&&s<8))?512:0);i=i+1)mask[s*PWT+i]=1;end
 reg [NS*PWT-1:0] src_if;always @(posedge clk)src_if<=src;
 wire [NS*PWT-1:0] src_f=(src_if&mask)|(src&~mask);
 wire [NS*PWT-1:0] f_captured;wire [NS-1:0] f_cs,f_cf;
 for(genvar s=0;s<NS;s=s+1)begin:g_fc
  ot_hgi_coll_qslots_capture_pin_v2 u(.clk(clk),.rst_n(rst_n),.src_v(sv[s]),.capture_slot(cap3[s]),.src_d(src_f[s*PWT+:PWT]),.captured(f_captured[s*PWT+:PWT]),.captured_slot(f_cs[s]),.fault(f_cf[s]));
 end
 wire [ND-1:0] f_v;wire [ND*PWT-1:0] f_d;wire f_sf,f_uf;
 ot_hgi_coll_qslots_output #(.NS(NS),.ND(ND),.PWT(PWT),.SELW(SELW)) u_f(.clk(clk),.rst_n(rst_n),.captured(f_captured),.captured_slot(f_cs),.sink_slot(sink3),.sink_select(sel3),.dst_v(f_v),.dst_d(f_d),.select_fault(f_sf),.unavailable_fault(f_uf));
 reg [ND-1:0] f_v_o;reg [ND*PWT-1:0] f_d_o;reg [2*PWT-1:0] f_lk;reg [1:0] f_sf_d,f_uf_d;
 always @(posedge clk)begin f_v_o<=f_v;f_d_o<=f_d;f_lk<=f_d[2*PWT-1:0];f_sf_d<={f_sf_d[0],f_sf};f_uf_d<={f_uf_d[0],f_uf};end
 // ---- split: rest out faces then the tile with its faces (__fs)
 wire [NS-1:0] r_cf;
 for(genvar s=0;s<NS;s=s+1)begin:g_rc
  ot_q2nf_cap u(.clk(clk),.rst_n(rst_n),.src_v(sv[s]),.capture_slot(cap3[s]),.fault(r_cf[s]));
 end
 reg [NS*PWT-1:0] ro_cap;reg [NS-1:0] ro_cs;reg [ND-1:0] ro_ss;reg [ND*SELW-1:0] ro_sl;
 always @(posedge clk)begin ro_cap<=src;ro_cs<=cap2;ro_ss<=sink;ro_sl<=sel;end
 wire [2*PWT-1:0] t_lk;wire [4772:0] t_pd;wire [NSL-1:0] t_sf,t_uf;
 ot_q2nf_qout__fs #(.MUT(MUT)) u_t(.clk(clk),.rst_n(rst_n),.captured((src&mask)|(ro_cap&~mask)),.cap_slot(ro_cs),.sink_slot(ro_ss),.sink_select(ro_sl),.lk_d(t_lk),.pin_d(t_pd),.select_fault(t_sf),.unavailable_fault(t_uf));
 reg [2*PWT-1:0] ri_lk;reg [NSL-1:0] ri_sf,ri_uf;
 always @(posedge clk)begin ri_lk<=t_lk;ri_sf<=t_sf;ri_uf<=t_uf;end
 reg [ND-1:0] sp,dv;always @(posedge clk or negedge rst_n)if(!rst_n)begin sp<=0;dv<=0;end else begin sp<=sink3;dv<=sp;end
 // ---- compare
 integer cyc=0,err=0,nv=0,seed=SEED;
 reg [4772:0] ref_pd;
 always @* begin
  ref_pd='0;
  `include "q2n_refmap.svh"
 end
 always @(negedge clk) if(rst_n&&cyc>8)begin
  if(pin_diff())begin err=err+1;if(err<6)$display("pin_d %0d",cyc);end
  if(lk_diff())begin err=err+1;if(err<6)$display("link %0d",cyc);end
  if(dv!==f_v)begin err=err+1;if(err<6)$display("dest_v %0d %h %h",cyc,dv,f_v);end
  if(r_cf!==f_cf)begin err=err+1;if(err<6)$display("cap_fault %0d",cyc);end
  if((|ri_sf)!==f_sf_d[1]||(|ri_uf)!==f_uf_d[1])begin err=err+1;if(err<6)$display("fault %0d %b %b %b %b",cyc,|ri_sf,f_sf_d[1],|ri_uf,f_uf_d[1]);end
  if(|f_v)nv=nv+1;
 end
 function automatic logic pin_diff();
  return t_pd!==ref_pd;
 endfunction
 function automatic logic lk_diff();
  return ri_lk!==f_lk;
 endfunction
 initial begin
  sink=0;sel=0;cap=0;src=0;svx=0;
  repeat(10)@(negedge clk);rst_n=1;
  repeat(`CYC)begin @(negedge clk);cyc=cyc+1;
   for(integer d=0;d<ND;d=d+1)begin sink[d]=cyc>=50&&($urandom%3)==0;sel[d*SELW+:SELW]=(BAD==2&&($urandom%2000)==0)?4'd12:$urandom%NS;end
   for(integer s=0;s<NS;s=s+1)begin cap[s]=(BAD==1)?(($urandom%5000)!=0):1'b1;svx[s]=(BAD==3&&($urandom%2000)==0);end
   for(integer i=0;i<NS*PWT;i=i+32)src[i+:32]=$urandom;
  end
  $display("Q2N MUT=%0d BAD=%0d cycles %0d valid_edges %0d errors %0d sf %0b uf %0b cf %0b",MUT,BAD,cyc,nv,err,f_sf,f_uf,|f_cf);
  if(err!=0)$fatal(1,"FAIL");
  $display("PASS");$finish;
 end
endmodule
`default_nettype wire
