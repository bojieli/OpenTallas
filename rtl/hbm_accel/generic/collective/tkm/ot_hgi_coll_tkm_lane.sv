`timescale 1ns/1ps
// One own-flop ingress leaf: decode, three SRAM banks, FIFO head, three staging slots.
// Current selector feedback must gain registered credit/mask seams before physical adoption.
module ot_hgi_coll_tkm_lane #(parameter integer MUT=0)(
 input wire clk, rst_n, input wire del_valid,del_reserve,
 input wire [544:0] del_flit, input wire [7:0] cfg_g,cfg_gbase,
 input wire [15:0] cfg_pf,input wire ins_live,
 input wire [82:0] tau,input wire [7:0] sel_take,input wire sel_pop,
 output wire del_permit,output reg fault,output wire [1:0] early_valid,
 output reg decoded_v,output reg [679:0] decoded_e,
 output wire [679:0] head_e,output wire [7:0] head_m,
 output reg [7:0] taken,output reg [1:0] head_n,
 output reg [7:0] occ,output wire landing_v,output wire fifo_empty
);
 wire [1:0] rr;
 ot_rst_relay #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst
  (.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 wire rn=rr[1];
 reg [7:0] g,gb;reg [15:0] pf;
 always @(posedge clk)begin g<=cfg_g;gb<=cfg_gbase;pf<=cfg_pf;end
 reg [7:0] cr;reg res_q,rfault,fpop_q;
 reg d0_v,d1_v;reg [544:0] d0_f;
 assign early_valid={d1_v,d0_v};
 reg [7:0] d1_q;reg [15:0] d1_gi;reg [511:0] d1_d;reg [23:0] d1_qpf;
 function automatic[31:0] okey(input[31:0]x);
  reg[31:0]c;begin c=(x==32'h80000000)?0:x;okey=c[31]?~c:(c|32'h80000000);end
 endfunction
 // Payload flops have no reset or reset-derived enable.
 always @(posedge clk)begin
  d0_f<=del_flit;
  d1_q<=d0_f[528+:8]-gb;d1_gi<=d0_f[512+:16];d1_d<=d0_f[511:0];
  d1_qpf<=24'(8'(d0_f[528+:8]-gb))*24'(pf);
  for(integer s=0;s<8;s=s+1)begin:decode_payload
   reg[23:0]f,j;reg[31:0]vv,id;reg[84:0]e;
   f=24'(d1_gi)-d1_qpf;vv=d1_d[32*s+:32];id=d1_d[32*(8+s)+:32];j={f[20:0],3'(s)};
   e={1'b1,okey(vv),(MUT==1)?id:~id,~d1_q[6:0],~j[10:0],(vv==32'h80000000)};
   if(vv==32'hffffffff)e='0;
   decoded_e[85*s+:85]<=e;
  end
 end
 wire fo;wire[679:0]fd;wire[6:0]fcnt;
 wire fpop=!fifo_empty&&ins_live&&({1'b0,head_n}+3'(landing_v)<3'd3);
 ot_hcoll_sfifo #(.W(680),.AW(6))u_fifo(.clk(clk),.rst_n(rr[0]),.push(decoded_v),.din(decoded_e),
  .pop(fpop),.empty(fifo_empty),.dout(fd),.ovf(fo),.count(fcnt));
 reg ld_v;reg[679:0]ld_e;reg[82:0]tau_p;
 wire[7:0]ld_m;
 for(genvar s=0;s<8;s=s+1)begin:g_mask
  assign ld_m[s]=ld_e[85*s+83]&&(ld_e[85*s+1+:83]>tau_p);
 end
 reg[679:0]se[0:2];reg[7:0]sm[0:2];
 assign head_e=se[0];assign head_m=sm[0];assign landing_v=ld_v;
 assign del_permit=(cr>8'(res_q))&&ins_live;
 always @(posedge clk)begin
  ld_e<=fd;tau_p<=tau;
  // Masks are computed behind captured fd/tau pins, at the existing staging edge.
  if(sel_pop&&ins_live)begin se[0]<=se[1];sm[0]<=sm[1];se[1]<=se[2];sm[1]<=sm[2];end
  if(ld_v)begin
   case(head_n-2'(sel_pop&&ins_live))
    0:begin se[0]<=ld_e;sm[0]<=ld_m;end
    1:begin se[1]<=ld_e;sm[1]<=ld_m;end
    default:begin se[2]<=ld_e;sm[2]<=ld_m;end
   endcase
  end
 end
 always @(posedge clk or negedge rn)begin
  if(!rn)begin cr<=64;res_q<=0;rfault<=0;fpop_q<=0;d0_v<=0;d1_v<=0;decoded_v<=0;
   occ<=0;ld_v<=0;head_n<=0;taken<=0;fault<=0;end
  else begin
   res_q<=del_reserve;d0_v<=del_valid;d1_v<=d0_v;decoded_v<=d1_v;
   cr<=cr-((MUT==3)?8'd0:8'(res_q))+8'(fpop_q);rfault<=res_q&&(cr==0);fpop_q<=fpop;
   occ<=occ+8'(decoded_v)-8'(fpop);ld_v<=fpop;
   head_n<=head_n-2'(sel_pop&&ins_live)+2'(ld_v);
   if(sel_pop&&ins_live)taken<=0;else if(ins_live)taken<=taken|sel_take;
   if(rfault||fo||(d0_v&&!d0_f[544]))fault<=1;
   if(d1_v&&(d1_q>=g||(24'(d1_gi)-d1_qpf)>=24'(pf)))fault<=1;
   for(integer s=0;s<8;s=s+1)
    if(d1_v&&d1_d[32*s+23+:8]==8'hff&&d1_d[32*s+:23]!=0&&d1_d[32*s+:32]!=32'hffffffff)fault<=1;
  end
 end
endmodule
