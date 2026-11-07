from pathlib import Path
b=Path(__file__).parent;s=(b/'svgr_top_cachecut_original.sv').read_text();a=s.index('module ot_svgr_prod_s_cachecut');z=s.index('endmodule',a)+len('endmodule');g=s[a:z];(b/'producer_gold.sv').write_text(g.replace('module ot_svgr_prod_s_cachecut','module producer_gold',1))
n=g.replace('module ot_svgr_prod_s_cachecut','module producer_local',1).replace('parameter integer OREG=0','parameter integer OREG=0,parameter integer LOCAL_FAULT=0,parameter integer FMUT=0')
old='''    else begin
     allocated[reserve_bank]<=1;bank_epoch[reserve_bank]<=reserve_epoch;bank_total[reserve_bank]<=reserve_total;
     for(si=0;si<8;si=si+1)completed_q[reserve_bank][si]<=reserve_total<=si;
     ready_q[reserve_bank]<=0;announced[reserve_bank]<=0;
    end'''
new='''    if(LOCAL_FAULT==0)begin
     if(reserve_ready&&descriptor_ok)begin
      allocated[reserve_bank]<=1;bank_epoch[reserve_bank]<=reserve_epoch;bank_total[reserve_bank]<=reserve_total;
      for(si=0;si<8;si=si+1)completed_q[reserve_bank][si]<=reserve_total<=si;
      ready_q[reserve_bank]<=0;announced[reserve_bank]<=0;
     end
    end else begin
     for(integer bl=0;bl<LBANKS;bl=bl+1)if(bank_reserve_go[bl])begin
      allocated[bl]<=1;bank_epoch[bl]<=reserve_epoch;bank_total[bl]<=reserve_total;
      for(si=0;si<8;si=si+1)completed_q[bl][si]<=reserve_total<=si;
      ready_q[bl]<=0;announced[bl]<=0;
     end
    end'''
assert n.count(old)==1;n=n.replace(old,new)
anchor=' reg draining;reg [LB-1:0] drain_bank;reg [10:0] drain_ordinal;reg [10:0] read_ordinal_q;reg [2:0] drain_phase;'
insert='''
 // Opt-in mirror of registered stream_fault ONLY; seam_h_fault/bfault remain combinational.
 wire next_stream_fault=stream_fault || (reserve_v&&(!reserve_ready||!descriptor_ok)) ||
   (start_v&&(draining||!ready_q[start_bank]||start_epoch!=bank_epoch[start_bank]||fault));
 wire [LBANKS-1:0] sf_bank,bank_reserve_go;
 generate for(genvar fb=0;fb<LBANKS;fb=fb+1)begin:g_local_fault
  if(LOCAL_FAULT!=0)begin:g_on
   ot_svgr_fault_mirror #(.MUT((FMUT==1)?1:((FMUT==2&&fb==1)?2:0))) u_mirror(.clk(stream_clk),.rst_n(srst),.d(next_stream_fault),.q(sf_bank[fb]));
  end else begin:g_off
   assign sf_bank[fb]=stream_fault;
  end
  wire region_fault=sf_bank[fb]||seam_h_fault||(|seam_bfault);
  assign bank_reserve_go[fb]=srst&&!allocated[fb]&&!region_fault&&descriptor_ok&&(reserve_bank==LB'(fb));
 end endgenerate
'''
assert n.count(anchor)==1;n=n.replace(anchor,anchor+insert)
n+='''\n(* keep_hierarchy,keep *) module ot_svgr_fault_mirror #(parameter integer MUT=0)(input wire clk,rst_n,d,output wire q);
 (* keep *)reg state;
 always @(posedge clk or negedge rst_n)if(!rst_n)state<=0;else state<=d;
 generate if(MUT==1)begin:g_lag
  reg lag;always @(posedge clk or negedge rst_n)if(!rst_n)lag<=0;else lag<=state;
  assign q=lag;
 end else begin:g_normal
  assign q=(MUT==2)?1'b0:state;
 end endgenerate
endmodule\n'''
(b/'producer_local.sv').write_text(n)
