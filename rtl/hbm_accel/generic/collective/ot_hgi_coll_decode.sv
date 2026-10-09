`timescale 1ns/1ps
// HGI-1 engine-side header decode. One queued command; downstream completes
// against the existing collective/gather datapath, never against this decoder.
// ENABLE=0 leaves the legacy backend unchanged. Header layout: normative
// tools/hbm_generic_iface.py D_UOP_FIELDS, COLL unit6/op0..5. Error commands
// retire as faults without asserting backend_v. Config is quasi-static per model.
module ot_hgi_coll_decode #(
 parameter integer ENABLE=0, MUT_GROUP=0, MUT_ROW_BLOCK=0
)(
 input wire clk,rst_n,
 input wire [7:0] coll_group_size, die_id,
 input wire cmd_v, output wire cmd_r,
 input wire [127:0] hdr,
 input wire [19:0] selected_count,
 output reg backend_v, input wire backend_r,
 output reg [5:0] backend_op,
 output reg [3:0] backend_gsz,
 output reg [7:0] backend_group_size,backend_rank,backend_group,
 output reg [7:0] backend_subgroup,backend_owner_block,backend_destinations,
 output reg [19:0] backend_row_count,
 output reg error_v, input wire error_r
);
 reg pending;reg [127:0] hdr_q;reg [7:0] group_q,die_q;reg [19:0] count_q;
 wire [5:0] op=hdr_q[123:118];
 wire [7:0] param_lo=hdr_q[71:64];
 wire [31:0] imm_a=hdr_q[63:32],imm_b=hdr_q[31:0];
 wire [6:0] operands=hdr_q[99:93];
 wire legal_group=(group_q==1 || group_q==2 ||
                   group_q==4 || group_q==8 || group_q==96);
 reg [3:0] gsz;
 reg [7:0] rank,group_id;
 always @* begin
   gsz=4'hf;rank=die_q;group_id=0;
   case(group_q)
    1: begin gsz=0;rank=0;group_id=die_q;end
    2: begin gsz=1;rank={7'd0,die_q[0]};group_id=die_q>>1;end
    4: begin gsz=2;rank={6'd0,die_q[1:0]};group_id=die_q>>2;end
    8: begin gsz=3;rank={5'd0,die_q[2:0]};group_id=die_q>>3;end
    96: begin rank=(die_q>=192)?die_q-192:((die_q>=96)?die_q-96:die_q);
              group_id=(die_q>=192)?2:((die_q>=96)?1:0);end
    default: begin rank=0;group_id=0;end
   endcase
 end
 wire subgroup_ok=(param_lo==2 || param_lo==4 || param_lo==8) &&
                   group_q>=param_lo;
 wire header_bad=(hdr_q[127:124]!=6 || op>5 || hdr_q[92] ||
                  !operands[0] || !operands[4]);
 wire reduce_bad=(op==4 && (!subgroup_ok || hdr_q[88:72]!=0));
 wire gather_bad=(op==5 && (!operands[6] || param_lo==0 || hdr_q[88:72]!=0 ||
                   imm_b==0 || imm_b>group_q ||
                   (count_q==0 && (imm_a==0 || imm_a>32'hfffff))));
 assign cmd_r=(ENABLE!=0) && !pending && !backend_v && !error_v;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   backend_v<=0;error_v<=0;pending<=0;hdr_q<=0;group_q<=96;die_q<=0;count_q<=0;backend_op<=0;backend_gsz<=4'hf;
   backend_group_size<=96;backend_rank<=0;backend_group<=0;
   backend_subgroup<=0;backend_owner_block<=0;backend_destinations<=0;
   backend_row_count<=0;
  end else if(ENABLE!=0) begin
   if(backend_v && backend_r) backend_v<=0;
   if(error_v && error_r) error_v<=0;
   if(cmd_v && cmd_r) begin
    pending<=1;hdr_q<=hdr;group_q<=coll_group_size;die_q<=die_id;count_q<=selected_count;
   end
   if(pending)begin
    pending<=0;
    if(!legal_group || header_bad || reduce_bad || gather_bad) error_v<=1;
    else begin
     backend_v<=1;backend_op<=op;backend_gsz<=gsz;
     backend_group_size<=group_q;
     backend_rank<=MUT_GROUP ? 0:rank;backend_group<=group_id;
     backend_subgroup<=(op==4)?param_lo:0;
     backend_owner_block<=(op==5)?(MUT_ROW_BLOCK?1:param_lo):0;
     backend_destinations<=(op==5)?imm_b[7:0]:group_q;
     backend_row_count<=(op==5)?((count_q!=0)?count_q:imm_a[19:0]):0;
    end
   end
  end
 end
endmodule
