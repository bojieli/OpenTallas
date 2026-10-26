`timescale 1ns/1ps
// Current KV R8 PC token/epoch repair. Selection is a pure function of the
// declared physical position IDs, never an arbitrary phase or delay strap.
// All 52 data flops survive in every template; no reset on datapath flops.
(* keep_hierarchy = 1 *)
// EPOCH_D (KV-BIND-R3 10-26, ABI kv_pc_r8_position_bank_v2_cland): epoch delay depth of the ES_1 position;
// default 1 = the v1 bank. The landed plan (+3/crossing) needs 4: replica EN_1/ES_1 x__tep land +9/+6.
module kv_pc_r8_position_bank #(parameter integer MUT = 0, parameter integer EPOCH_D = 1) (
    input wire clk,
    input wire [1:0] stack_id, // WS=0 WN=1 ES=2 EN=3 (plan ID lane)
    input wire [2:0] group_id, // existing slg cfg_group position ID
    input wire [17:0] tok_i,
    input wire [15:0] epoch_i,
    output wire [17:0] tok_o,
    output wire [15:0] epoch_o
);
    (* keep = 1 *) reg [17:0] tok1, tok2;
    (* keep = 1 *) reg [16*EPOCH_D-1:0] epoch_sr;
    always @(posedge clk) begin
        tok1 <= tok_i;
        tok2 <= tok1;
    end
    generate
        if (EPOCH_D == 1) begin : g_ep1
            always @(posedge clk) epoch_sr <= epoch_i;
        end else begin : g_epn
            always @(posedge clk) epoch_sr <= {epoch_sr[16*(EPOCH_D-1)-1:0], epoch_i};
        end
    endgenerate
    wire [15:0] epoch1 = epoch_sr[16*EPOCH_D-1 -: 16];
    wire tok_delayed = (stack_id == ((MUT == 1) ? 2'd2 : 2'd3)) &&
                       ((group_id == 3'd2) || (group_id == 3'd3) ||
                        (group_id == 3'd4) || (group_id == 3'd6));
    wire epoch_delayed = (stack_id == 2'd2) && (group_id == 3'd1);
    assign tok_o = tok_delayed ? tok2 : tok_i;
    assign epoch_o = epoch_delayed ? epoch1 : epoch_i;
endmodule
