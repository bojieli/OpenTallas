`timescale 1ns/1ps
// The actual290-bit hostsector ABI has8sharedcredits. Eachword enters exactly
// one branch; returned branchcredits accumulate before onecredit/cycle returns
// upstream. Markerregion0 preserves oldRoPE,2RoPE,3Engram,1reservedinvalid.
module ot_s81_host_dispatch #(parameter integer ENABLE=0)(
 input wire ck,rst_n,input wire i_v,i_we,input wire[31:0] i_addr,input wire[255:0] i_d,
 output reg i_cr,output reg[2:0] branch_v,output reg branch_we,
 output reg[31:0] branch_addr,output reg[255:0] branch_d,
 input wire[2:0] branch_cr,output reg fault
);
 generate if(!ENABLE)begin:g_off
  always @(*)begin i_cr=0;branch_v=0;branch_we=0;branch_addr=0;branch_d=0;fault=0;end
 end else begin:g_on
  reg[3:0] outstanding,debt;reg[3:0] owned[0:2];reg state_p;
  integer k;reg[3:0] no[0:2];reg owned_bad;
  wire state_bad=state_p!=(^{outstanding,debt,owned[0],owned[1],owned[2]});
  wire marker=i_addr==32'hffffffff;
  wire invalid=!i_we||(marker&&i_d[65:64]==1);
  wire[2:0] cls=marker ? ((i_d[65:64]==3)?3'b100:3'b010) :
                 (!i_addr[31]?3'b001:(!i_addr[30]?3'b010:3'b100));
  wire send_credit=debt!=0;
  wire[3:0] returned={3'b0,branch_cr[0]}+{3'b0,branch_cr[1]}+{3'b0,branch_cr[2]}+
                      ((i_v&&invalid)?4'd1:4'd0);
  wire[4:0] debt_next={1'b0,debt}+returned-(send_credit?5'd1:5'd0);
  wire[4:0] outstanding_next={1'b0,outstanding}+(i_v?5'd1:5'd0)-(send_credit?5'd1:5'd0);
  always @(*)begin
   owned_bad=0;
   for(integer j=0;j<3;j=j+1)begin
    no[j]=owned[j]+((i_v&&!invalid&&cls[j])?1:0)-(branch_cr[j]?1:0);
    if(branch_cr[j]&&owned[j]==0)owned_bad=1;
   end
  end
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin outstanding<=0;debt<=0;owned[0]<=0;owned[1]<=0;owned[2]<=0;state_p<=0;i_cr<=0;branch_v<=0;branch_we<=0;branch_addr<=0;branch_d<=0;fault<=0;end
   else begin
    i_cr<=0;branch_v<=0;
    if(state_bad||owned_bad||debt_next>8||outstanding_next>8||returned>outstanding+(i_v?1:0))fault<=1;
    else if(!fault)begin
     outstanding<=outstanding_next[3:0];debt<=debt_next[3:0];state_p<=^{outstanding_next[3:0],debt_next[3:0],no[0],no[1],no[2]};
     for(k=0;k<3;k=k+1)owned[k]<=no[k];
     i_cr<=send_credit;
     if(i_v)begin
      if(invalid)fault<=1;
      else begin branch_v<=cls;branch_we<=i_we;branch_addr<=i_addr;branch_d<=i_d;end
     end
    end
   end
  end
 end endgenerate
endmodule
