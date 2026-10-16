`timescale 1ns/1ps
// H-DIE 2026-10-15: ONE pseudo-channel of ot_hbm_svc_native_sector_pipeline_stack as a hardenable die leaf (the stack's
// g_pc[P] body verbatim, per-PC slices renamed to scalar ports; the stack's ca_fault channel-pair check and fault OR stay
// in the parent ot_hbm_svc_native_sector_pipeline_leaves).  Real controller: actual ot_hbm_r14_stream_pc sequencer +
// same-row FIFO32 + 32 reserved responses in an actual 128x256 SRAM.  K side faces the SM service group; row/column/data
// side faces the PHY-only abstract (the only modelled boundary).  clk = this PC's pc_clk root.
// OREG=1 (H-DIE 2026-10-15, die default): every PHY-side command output (row_*, col_*, write data/strobe) leaves from a
// flop -- one uniform extra cycle on the command path to the PHY (relative DRAM command timing unchanged); the read
// return path is unchanged.  OREG=0 is the stack body exactly.
// KREG=1 (die default): the K request enters a 2-entry pin-registered skid; k_rdy = skid not full (a register), so no
// K input reaches k_rdy or the queue combinationally; one extra hbm cycle on the request, full rate.  KREG=0: as the stack.
// KRREG=1 (die default): the K response leaves through a 2-entry skid whose registers drive kr_v/kr_tag/kr_beat/kr_data;
// kr_rdy only pops the skid.  One extra hbm cycle on the response, full rate.  KRREG=0: as the stack.
module ot_hbm_svc_pc_ctrl_leaf #(
    parameter integer PHASE=0,
    parameter integer P=0,
    parameter integer OREG=1,
    parameter integer KREG=1,
    parameter integer KRREG=1,
    parameter integer RREG=1,
    parameter integer WPAY=1
)(
    input wire clk,rst_n,
    input wire k_v,output wire k_rdy,input wire k_we,
    input wire[29:0]k_addr,input wire[3:0]k_len,input wire[16:0]k_tag,
    input wire[255:0]k_wdata,input wire[31:0]k_wstrb,
    output wire kr_v,input wire kr_rdy,
    output wire[16:0]kr_tag,output wire[3:0]kr_beat,output wire[255:0]kr_data,
    output reg k_wr_done,
    output wire row_v,output wire[2:0]row_op,output wire[4:0]row_bank,output wire[18:0]row_row,
    output wire col_v,col_we,output wire[4:0]col_bank,col_col,
    output wire[255:0]col_data,output wire[31:0]col_strb,
    input wire dram_rvalid,input wire[255:0]dram_rdata,
    output wire pc_fault,owner_fault
);
    // One actual physical master for every PC. These are declared die constants,
    // captured by the child's pin registers during the three-edge reset relay.
    localparam integer RP=(PHASE+P*118/32)%118;
    localparam integer RELOAD=118+RP+((RP+118+P)%2);
`ifdef OT_PC_CFG_MUT_PC
    localparam integer PC_STRAP=P^1;
`else
    localparam integer PC_STRAP=P;
`endif
`ifdef OT_PC_CFG_MUT_PHASE
    localparam integer REF_STRAP=RELOAD^1;
`else
    localparam integer REF_STRAP=RELOAD;
`endif
    ot_hbm_svc_pc_ctrl_leaf_cfg #(.OREG(OREG),.KREG(KREG),.KRREG(KRREG),.RREG(RREG),.WPAY(WPAY)) u_cfg(
        .pc_id(5'(PC_STRAP)),.refresh_reload(8'(REF_STRAP)),
        .k_v(k_v),
        .k_rdy(k_rdy),
        .k_we(k_we),
        .k_addr(k_addr),
        .k_len(k_len),
        .k_tag(k_tag),
        .k_wdata(k_wdata),
        .k_wstrb(k_wstrb),
        .kr_v(kr_v),
        .kr_rdy(kr_rdy),
        .kr_tag(kr_tag),
        .kr_beat(kr_beat),
        .kr_data(kr_data),
        .k_wr_done(k_wr_done),
        .row_v(row_v),
        .row_op(row_op),
        .row_bank(row_bank),
        .row_row(row_row),
        .col_v(col_v),
        .col_we(col_we),
        .col_bank(col_bank),
        .col_col(col_col),
        .col_data(col_data),
        .col_strb(col_strb),
        .dram_rvalid(dram_rvalid),
        .dram_rdata(dram_rdata),
        .clk(clk),
        .rst_n(rst_n),
        .pc_fault(pc_fault),
        .owner_fault(owner_fault));
endmodule
// Two-entry elastic pin skid at the external HBM-service boundary. A head
// register directly drives the output pins; selection happens before its flop.
// This removes the old pointer-selected output mux without adding an edge or
// changing count<2 admission. On-die execution starts from block-ready.
module ot_hbm_svc_pin_skid2 #(parameter integer WIDTH=1,MUT=0)(
    input wire clk,rst_n,input wire in_v,output wire in_r,
    input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
    output wire [WIDTH-1:0]out_data
);
    reg head_valid,tail_valid;
    reg [WIDTH-1:0]head_data,tail_data;
    wire push=in_v&&in_r,pop=out_v&&out_r;
    assign in_r=!tail_valid;assign out_v=head_valid;assign out_data=head_data;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin head_valid<=0;tail_valid<=0;end
        else begin
            case({push,pop})
                2'b10:begin
                    if(!head_valid)begin head_data<=in_data;head_valid<=1;end
                    else begin tail_data<=in_data;tail_valid<=1;end
                end
                2'b01:begin
                    if(tail_valid)head_data<=tail_data;
                    head_valid<=tail_valid;tail_valid<=0;
                end
                2'b11:begin head_data<=in_data;head_valid<=1;tail_valid<=0;end
                default:;
            endcase
            // Checked negative control: illegally overwrite a stalled head.
            if(MUT!=0 && push && head_valid && !out_r)head_data<=in_data;
        end
    end
endmodule
`default_nettype wire
