`timescale 1ns/1ps
`ifndef OT_HOST_BOOT_FIFO_DEFAULT
`define OT_HOST_BOOT_FIFO_DEFAULT 0
`endif
`ifndef OT_HOST_BOOT_FIFO_MUT
`define OT_HOST_BOOT_FIFO_MUT 0
`endif
// Production KV and embedding sector map. See original qkd_ctrl_pc wj/wrow
// and ot_qfd_emb_pkg.emb_loc; logical PC is preserved for local lpc strap.
// Eight input word credits initially; returns after registered decode is emitted.
// Output per stack is {data256,row19,col5,bank5,lpc5,v}291, four initial
// downstream credits per logical PC. End marker66 is held until real commit count reaches
// all previously emitted sectors. Host QPIPE is write-only; RMW faults.
module qkd_host_ingest_map #(parameter integer MUT=0,SRAM_FIFO=`OT_HOST_BOOT_FIFO_DEFAULT,SRAM_MUT=`OT_HOST_BOOT_FIFO_MUT,ORDERED=0,BOOT_SCRATCH_ROW=0)(
 input wire ck,rst_n,
 input wire[289:0]ing,output reg ing_cr,
 output reg[1163:0]out,input wire[127:0]out_cr,
 input wire[7:0]ack_n,
 output reg marker_v,output reg[65:0]marker,input wire marker_cr,
 output reg fault,output reg[31:0]issued,landed,
 input wire ord_cr,output reg issue_v,output reg[6:0]issue_pc
);
 reg[289:0]iq;reg[127:0]crq;reg[7:0]aq;reg mcq,ocq;reg[8:0]ord_credit;
 // HRORDER 10-18 (route qkd_hr_core_order-r2-c420f015e TT -112 ps: rp -> q[rp] -> address decode -> credit mux -> emit
 // fanout, 1,634 endpoints): the sector decode is done ONCE at enqueue from the registered iq and stored with the
 // word; a 9-bit head register hd = control fields of q[rp] (write-bypassed) feeds emit. Cycle-exact with the
 // previous form (bench tools/qwen_kv_die/host_cluster/bench/hrorder_equiv); no added latency.
 reg[3:0]count;reg[2:0]wp,rp;
 wire pending=count!=0;
 reg[8:0]q_ctl[0:7];       // {data256,row19,col5,bank5,pc5,stack2,good,mark}
 reg[8:0]hd;             // {pc5,stack2,good,mark} of q[rp]
 wire[293:0]word;
 generate if(SRAM_FIFO)begin:g_sram_fifo
  wire[284:0]payload;
  qkd_host_boot_fifo8_sram #(.W(285),.MUT(SRAM_MUT))u_payload(.ck(ck),.wr(wr),.wp(wp),
   .wd(iq_dec[293:9]),.next_rp(adv?rp1:rp),.head(payload));
  assign word={payload,hd};
 end else begin:g_flop_fifo
  reg[293:0]q[0:7];
  always @(posedge ck)if(wr)q[wp]<=iq_dec;
  assign word=q[rp];
 end endgenerate
 wire[255:0]data=word[293:38];wire[18:0]row=word[37:19];wire[4:0]col=word[18:14],bank=word[13:9];
 wire[4:0]pc=hd[8:4];wire[1:0]stack=hd[3:2];wire good=hd[1],hmark=hd[0];
 reg[2:0]credits[0:127];reg marker_credit;
 // Enqueue-side decode of the registered input word (the previous head-side decode, unchanged).
 wire[31:0]addr=iq[33:2];wire we=iq[1];
 reg[1:0]d_stack;reg[4:0]d_pc,d_bank,d_col;reg[18:0]d_row;reg d_good;
 reg[24:0]e,s;reg[17:0]t;reg[9:0]p,j;reg[16:0]sec;
 always @*begin
  e=addr[24:0];s=e-25'd19447808;t=18'(e>>7);p=0;j=0;sec=addr[23:7];
  d_stack=addr[6:5];d_pc=addr[4:0];d_bank=0;d_col=0;d_row=0;d_good=we&&addr!=32'hffffffff;
  if(!addr[31])begin
   // address31=0, local sector17=a23:7; high address bits and dummy t13
   // must be zero at CTX8192. j excludes the map's dummy bit7.
   sec=addr[23:7];j={sec[10:8],sec[6:0]};d_bank={j[9:7],j[1:0]};d_col=j[6:2];d_row=19'd64+{13'd0,sec[16:11]};
   d_good=d_good&&addr[30:24]==0&&!sec[7]&&sec[16:11]<36;
  end else begin
   d_good=d_good&&addr[30:25]==0&&e<25'd19457304;
   if(e<25'd19447808)begin d_stack=e[6:5];d_pc=e[4:0];p=t[9:0];d_row=19'd24427+{11'd0,t[17:10]};end
   else begin d_stack=s[6:5];d_pc=s[4:0];p=10'd384+10'(s[13:7]);d_row=19'd24575;end
   d_bank={p[9:7],p[1:0]};d_col=p[6:2];
  end
  // Cold boot checker owns this scratch row on all PCs. Even a future address
  // map revision must fail closed if a payload aliases its reserved storage.
  d_good=d_good&&(d_row!=BOOT_SCRATCH_ROW);
  if(MUT==1)d_bank=d_bank^5'd1;
 end
 wire[293:0]iq_dec={iq[289:34],d_row,d_col,d_bank,d_pc,d_stack,d_good,we&&addr==32'hffffffff};
 wire mark=pending&&hmark;
 wire emit=pending&&good&&!fault&&credits[{stack,pc}]!=0&&(!ORDERED||ord_credit!=0);
 wire emit_marker=mark&&!fault&&issued==landed&&marker_credit;
 wire[32:0]sum={1'b0,landed}+33'(aq);
 // Credit-overflow fault, restructured (HRORDER 10-18 gate: hd -> 128:1 credit mux -> emit -> per-k spend -> 128-input OR
 // -> fault was 15 levels, -32 ps est): OR_k(crq[k]&&credits[k]==4&&!(emit&&sel==k)) ==
 // OR_{k!=sel}(cfull[k]) | (cfull[sel]&&!emit). The 128-wide OR now runs in parallel with emit; same cycle, exact.
 wire[6:0]sel={stack,pc};
 wire[127:0]cfull;
 wire ovf_other=|(cfull&~(128'd1<<sel));
 wire ovf_sel=cfull[sel]&&!emit;
 for(genvar k=0;k<128;k++)begin:g_credit
  wire spend=emit&&sel==7'(k);
  assign cfull[k]=crq[k]&&credits[k]==4;
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)credits[k]<=4;
   else case({crq[k],spend})
    2'b10:if(credits[k]<4)credits[k]<=credits[k]+1'b1;
    2'b01:credits[k]<=credits[k]-1'b1;default:;
   endcase
  end
 end
 wire wr=iq[0]&&count<8;
 wire adv=emit||emit_marker;
 wire[2:0]rp1=rp+3'd1;
 always @(posedge ck)begin
  if(wr)q_ctl[wp]<=iq_dec[8:0];
  if(adv)hd<=(wr&&wp==rp1)?iq_dec[8:0]:q_ctl[rp1];
  else hd<=(wr&&wp==rp)?iq_dec[8:0]:q_ctl[rp];
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin
   iq<=0;crq<=0;aq<=0;mcq<=0;wp<=0;rp<=0;count<=0;out<=0;ing_cr<=0;marker_v<=0;marker<=0;
   fault<=0;issued<=0;landed<=0;marker_credit<=1;ocq<=0;ord_credit<=256;issue_v<=0;issue_pc<=0;

  end else begin
   iq<=ing;ocq<=ord_cr;issue_v<=emit;issue_pc<={stack,pc};
   if(ORDERED)case({ocq,emit})2'b10:begin if(ord_credit==256)fault<=1;else ord_credit<=ord_credit+1'b1;end 2'b01:ord_credit<=ord_credit-1'b1;default:;endcase
   crq<=out_cr;aq<=ack_n;mcq<=marker_cr;ing_cr<=0;marker_v<=0;
   for(integer k=0;k<4;k++)out[k*291]<=0;
   if(ovf_other||ovf_sel)fault<=1;
   if(sum[32]||sum[31:0]>issued)fault<=1;else landed<=sum[31:0];
   if(iq[0]&&!fault)begin if(count==8)fault<=1;else wp<=wp+1'b1;end
   if(adv)rp<=rp1;
   case({iq[0]&&!fault&&count<8,adv})
    2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
   if(pending&&!good&&!mark)fault<=1;
   if(emit)begin
    for(integer k=0;k<4;k++)if(stack==2'(k))out[k*291+:291]<={data,row,col,bank,pc,1'b1};   // constant slices (no wide $shift)
    issued<=issued+1'b1;if(issued==32'hffffffff)fault<=1;ing_cr<=1;
   end
   if(mcq)begin if(marker_credit)fault<=1;else marker_credit<=1;end
   if(emit_marker)begin marker_v<=1;marker<=word[103:38];ing_cr<=1;marker_credit<=0;end
  end
 end
endmodule
