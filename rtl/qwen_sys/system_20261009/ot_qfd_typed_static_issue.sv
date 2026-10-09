`timescale 1ps/1fs
// One real SROW command stream. Metadata seats are spent before controller
// launch and released only by its registered static column issue. No IDs or
// mirrors: FIFO state is plain flops. Producer must reserve PHY capacity first.
module ot_qfd_typed_static_issue #(parameter integer ENABLE=0,TYPED_ONLY=0,MUT_CLASS=0)(
 input wire clk,rst_n,
 input wire q_v,q_we,q_sidecar,q_emb,q_fence,
 input wire [18:0] q_row,input wire[4:0]q_bank,q_col,
 input wire [15:0]q_tag,input wire[16:0]q_sec,input wire[7:0]q_lrow,
 input wire[255:0]q_data,output wire q_rdy,
 output wire s_v,s_we,output wire[18:0]s_row,output wire[4:0]s_bank,s_col,
 input wire ct_col_v,ct_col_sr,ct_col_we,ct_s_cr,
 input wire[4:0]ct_col_bank,ct_col_col,
 input wire ct_row_v,input wire[2:0]ct_row_op,
 input wire[4:0]ct_row_bank,input wire[18:0]ct_row_row,
 input wire phy_ready,provider_drained,
 output wire issue_v,issue_we,issue_sidecar,issue_emb,issue_fence,
 output wire [18:0]issue_row,output wire[4:0]issue_bank,issue_col,
 output wire[15:0]issue_tag,output wire[16:0]issue_sec,
 output wire[7:0]issue_lrow,output wire[255:0]issue_data,
 output wire logical_data_issue,drained,output reg fault
);
 reg [329:0] fifo[0:3];reg [1:0]rp,wp;
 reg [2:0]count,credits;
 reg [18:0] actual_row[0:31];reg[31:0] actual_open;
 wire hw,hsc,hem,hf;wire[18:0]hr;wire[4:0]hb,hc;
 wire[15:0]ht;wire[16:0]hs;wire[7:0]hl;wire[255:0]hd;
 assign {hw,hsc,hem,hf,hr,hb,hc,ht,hs,hl,hd}=fifo[rp];
 wire push=q_v&&q_rdy;
 wire col=ct_col_v&&ct_col_sr;
 wire bad_col=col&&(count==0 || ct_col_we!=hw || ct_col_bank!=hb || ct_col_col!=hc ||
                 !actual_open[hb] || actual_row[hb]!=hr || !phy_ready);
 wire bad_credit=(ct_s_cr!=col) || (ct_s_cr&&count==0);
 wire bad_native=TYPED_ONLY!=0 && ct_col_v&&!ct_col_sr;
 wire safe=ENABLE!=0&&!fault&&!bad_col&&!bad_credit&&!bad_native;
 wire pop=safe&&col;
 assign q_rdy=ENABLE!=0&&!fault&&credits!=0;
 assign s_v=push;assign {s_we,s_row,s_bank,s_col}={q_we,q_row,q_bank,q_col};
 assign issue_v=pop;
 assign {issue_we,issue_emb,issue_fence,issue_row,issue_bank,issue_col,
         issue_tag,issue_sec,issue_lrow,issue_data}={hw,hem,hf,hr,hb,hc,ht,hs,hl,hd};
 assign issue_sidecar=MUT_CLASS!=0?1'b0:hsc;
 assign logical_data_issue=issue_v&&!issue_we&&!issue_sidecar&&!issue_fence;
 assign drained=count==0&&credits==4&&provider_drained;
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rp<=0;wp<=0;count<=0;credits<=4;fault<=0;actual_open<=0;
   for(i=0;i<32;i=i+1)actual_row[i]<=0;
  end else if(ENABLE!=0)begin
   if(bad_col||bad_credit||bad_native)fault<=1;
   if(ct_row_v)begin
    case(ct_row_op)
     3'd1:begin actual_open[ct_row_bank]<=1;actual_row[ct_row_bank]<=ct_row_row;end
     3'd0,3'd6:actual_open[ct_row_bank]<=0;
     3'd4,3'd5:actual_open<=0;
     default:begin end
    endcase
   end
   if(push)begin
    fifo[wp]<={q_we,q_sidecar,q_emb,q_fence,q_row,q_bank,q_col,q_tag,q_sec,q_lrow,q_data};
    wp<=wp+1'b1;
   end
   if(pop)rp<=rp+1'b1;
   case({push,pop})
    2'b10:begin count<=count+1'b1;credits<=credits-1'b1;end
    2'b01:begin count<=count-1'b1;credits<=credits+1'b1;end
    default:begin end
   endcase
  end
 end
endmodule
