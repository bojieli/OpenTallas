`timescale 1ns/1ps
`ifndef OT_HOST_BOOT_FIFO_DEFAULT
`define OT_HOST_BOOT_FIFO_DEFAULT 0
`endif
`ifndef OT_HOST_BOOT_FIFO_MUT
`define OT_HOST_BOOT_FIFO_MUT 0
`endif
// Credit-delimited, ordered split of real native QM output: KV goes to static
// host stations, embedding to gateway hb. Real completion owners, not hb_cr,
// advance the shared per-PC retirement ledger. BOOT_END waits for that prefix.
module qkd_host_boot_dispatch_debt #(parameter integer MUT=0,SRAM_FIFO=`OT_HOST_BOOT_FIFO_DEFAULT,SRAM_MUT=`OT_HOST_BOOT_FIFO_MUT)(
 input wire ck,ck_order,rst_n,boot_release,input wire[289:0]ing,output reg ing_cr,
 output reg[289:0]kv,input wire kv_cr,
 output reg[282:0]hb,input wire hb_cr,output reg image_check,
 input wire[127:0]acks,output wire prefix_v,output wire[31:0]landed,
 output reg[31:0]issued,output wire fault,output reg dispatch_quiet,output wire order_quiet);
 always @(posedge ck or negedge rst_n)
  if(!rst_n)dispatch_quiet<=0;
  else dispatch_quiet<=count==0&&kc==8&&hc==4&&oc==256&&!ing[0]&&!iv_q&&!kv[0]&&!hb[0]&&
   !boot_hold&&!issue_v&&!ing_cr&&!kv_cr&&!hb_cr&&!kcr_q&&!hcr_q&&!fault;
 reg[2:0]wp,rp;reg[3:0]count;
 reg[3:0]kc;reg[2:0]hc;reg[8:0]oc;
 reg iv_q,kcr_q,hcr_q,boot_hold,image_dirty;reg[289:0]id_q;reg ff;
 // HRORDER 10-18 (route qkd_hr_core_order-r2-c420f015e TT -17 ps: rp -> q[rp] -> address decode -> send -> issued):
 // the decode {target7,good,embed,marker} is done once at enqueue from the registered id_q and kept beside the word;
 // a 10-bit head register hd = those fields of q[rp] (write-bypassed) feeds send. Cycle-exact with the previous form
 // (bench tools/qwen_kv_die/host_cluster/bench/hrorder_equiv); no added latency.
 wire[31:0]i_addr=id_q[33:2];wire i_marker=i_addr==32'hffffffff;
 wire i_embed=i_addr[31]&&!i_marker;wire i_we=id_q[1];
 wire[24:0]i_le=i_addr[24:0];wire[24:0]i_se=i_le-25'd19447808;
 wire[1:0]i_stack=(i_le<25'd19447808)?i_le[6:5]:i_se[6:5];
 wire[6:0]i_target=i_embed?{i_stack,(i_le<25'd19447808)?i_le[4:0]:i_se[4:0]}:i_addr[6:0];
 wire i_good=i_we&&(i_marker||(i_embed?(i_addr[30:25]==0&&i_le<25'd19457304):(i_addr[30:24]==0)));
 wire[9:0]id_dec={i_target,i_good,i_embed,i_marker};
 reg[9:0]qd[0:7];reg[9:0]hd;
 wire[289:0]head;
 generate if(SRAM_FIFO)begin:g_sram_fifo
  qkd_host_boot_fifo8_sram #(.W(290),.MUT(SRAM_MUT))u_payload(.ck(ck),.wr(iv_q&&count<8),.wp(wp),
   .wd(id_q),.rp(rp),.next_rp(send?rp+3'd1:rp),.head(head));
 end else begin:g_flop_fifo
  reg[289:0]q[0:7];
  always @(posedge ck)if(iv_q&&count<8)q[wp]<=id_q;
  assign head=q[rp];
 end endgenerate
 wire[24:0]logical_e=head[26:2];
 wire marker=hd[0],embed=hd[1],good=hd[2];wire[6:0]target=hd[9:3];
 wire send=count!=0&&!fault&&(!boot_hold||MUT==2)&&good&&(marker?(issued==landed&&kc!=0&&(!image_dirty||hc!=0)):(oc!=0&&(embed?hc!=0:kc!=0)));
 reg issue_v;reg[6:0]issue_pc;wire order_fault;
 qkd_host_commit_order_debt #(.MUT(MUT))u_order(.ck(ck_order),.rst_n(rst_n),.issue_v(issue_v),.issue_pc(issue_pc),.acks(acks),.prefix_v(prefix_v),.prefix_count(landed),.fault(order_fault),.order_quiet(order_quiet));
 assign fault=ff|order_fault;
 wire wr=iv_q&&count<8;wire[2:0]rp1=rp+3'd1;
 always @(posedge ck)begin
  id_q<=ing;if(wr)begin qd[wp]<=id_dec;end
  if(send)hd<=(wr&&wp==rp1)?id_dec:qd[rp1];
  else hd<=(wr&&wp==rp)?id_dec:qd[rp];
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin wp<=0;rp<=0;count<=0;kc<=8;hc<=4;oc<=256;iv_q<=0;kcr_q<=0;hcr_q<=0;ff<=0;boot_hold<=0;image_dirty<=0;image_check<=0;ing_cr<=0;kv<=0;hb<=0;issued<=0;issue_v<=0;issue_pc<=0;end
  else begin
   iv_q<=ing[0];kcr_q<=kv_cr;hcr_q<=hb_cr;ing_cr<=send;kv[0]<=0;hb[0]<=0;issue_v<=0;
   if(iv_q)begin if(count==8&&!send)ff<=1;else wp<=wp+1'b1;end
   if(boot_release)begin if(!boot_hold)ff<=1;else begin boot_hold<=0;image_dirty<=0;end end
   if(send)begin
    rp<=rp1;
    if(marker||!embed)kv<=head;
    if(embed)image_dirty<=1;
    if(embed)hb<={head[289:34],logical_e,1'b0,1'b1};
    if(marker)begin boot_hold<=1;image_check<=image_dirty;end
    if(marker&&image_dirty)hb<={192'b0,head[97:34],25'b0,1'b1,1'b1};
    if(!marker)begin issued<=issued+1'b1;issue_v<=1;issue_pc<=target;if(issued==32'hffffffff)ff<=1;end
   end
   if(count!=0&&!good)ff<=1;
   case({iv_q&&!(count==8&&!send),send})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
   case({kcr_q,send&&(marker||!embed)})2'b10:begin if(kc==8)ff<=1;else kc<=kc+1'b1;end 2'b01:kc<=kc-1'b1;default:;endcase
   case({hcr_q,send&&((marker&&image_dirty)||embed)})2'b10:begin if(hc==4)ff<=1;else hc<=hc+1'b1;end 2'b01:hc<=hc-1'b1;default:;endcase
   case({prefix_v,send&&!marker})2'b10:begin if(oc==256)ff<=1;else oc<=oc+1'b1;end 2'b01:oc<=oc-1'b1;default:;endcase
  end
 end
endmodule
