`timescale 1ns/1ps
// Credit-delimited, ordered split of real native QM output: KV goes to static
// host stations, embedding to gateway hb. Real completion owners, not hb_cr,
// advance the shared per-PC retirement ledger. BOOT_END waits for that prefix.
module qkd_host_boot_dispatch #(parameter integer MUT=0)(
 input wire ck,ck_order,rst_n,boot_release,input wire[289:0]ing,output reg ing_cr,
 output reg[289:0]kv,input wire kv_cr,
 output reg[282:0]hb,input wire hb_cr,output reg image_check,
 input wire[127:0]acks,output wire prefix_v,output wire[31:0]landed,
 output reg[31:0]issued,output wire fault);
 reg[289:0]q[0:7];reg[2:0]wp,rp;reg[3:0]count;
 reg[3:0]kc;reg[2:0]hc;reg[8:0]oc;
 reg iv_q,kcr_q,hcr_q,boot_hold,image_dirty;reg[289:0]id_q;reg ff;
 wire[289:0]head=q[rp];wire[31:0]addr=head[33:2];wire marker=addr==32'hffffffff;
 wire embed=addr[31]&&!marker;wire we=head[1];
 wire[24:0]logical_e=addr[24:0];wire[24:0]scale_e=logical_e-25'd19447808;
 wire[1:0]stack=(logical_e<25'd19447808)?logical_e[6:5]:scale_e[6:5];
 wire[6:0]target=embed?{stack,(logical_e<25'd19447808)?logical_e[4:0]:scale_e[4:0]}:addr[6:0];
 wire good=we&&(marker||(embed?(addr[30:25]==0&&logical_e<25'd19457304):(addr[30:24]==0)));
 wire send=count!=0&&!fault&&(!boot_hold||MUT==2)&&good&&(marker?(issued==landed&&kc!=0&&(!image_dirty||hc!=0)):(oc!=0&&(embed?hc!=0:kc!=0)));
 reg issue_v;reg[6:0]issue_pc;wire order_fault;
 qkd_host_commit_order #(.MUT(MUT))u_order(.ck(ck_order),.rst_n(rst_n),.issue_v(issue_v),.issue_pc(issue_pc),.acks(acks),.prefix_v(prefix_v),.prefix_count(landed),.fault(order_fault));
 assign fault=ff|order_fault;
 always @(posedge ck)begin id_q<=ing;if(iv_q&&count<8)q[wp]<=id_q;end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin wp<=0;rp<=0;count<=0;kc<=8;hc<=4;oc<=256;iv_q<=0;kcr_q<=0;hcr_q<=0;ff<=0;boot_hold<=0;image_dirty<=0;image_check<=0;ing_cr<=0;kv<=0;hb<=0;issued<=0;issue_v<=0;issue_pc<=0;end
  else begin
   iv_q<=ing[0];kcr_q<=kv_cr;hcr_q<=hb_cr;ing_cr<=send;kv[0]<=0;hb[0]<=0;issue_v<=0;
   if(iv_q)begin if(count==8&&!send)ff<=1;else wp<=wp+1'b1;end
   if(boot_release)begin if(!boot_hold)ff<=1;else begin boot_hold<=0;image_dirty<=0;end end
   if(send)begin
    rp<=rp+1'b1;
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
