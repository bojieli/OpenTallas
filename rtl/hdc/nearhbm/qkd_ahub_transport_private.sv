`timescale 1ns/1ps
// Private opt-in component. No production binding; opaque actual AHUB words.
// Four INDEXED slots, one write/read per bank/edge, READ_OLD semantics.
// Accepted edge n -> ingress n -> store n+1 -> read n+3 -> output n+4.
// Payload is intentionally unreset; slot validity supplies authority.
// Exact REGIONS=1, STAGES=2 ot_rst_pipe equations, with existing s1 exposed.
// This authority prevents an arbitrary old regional q1 from admitting data
// before assertion propagation. No additional arming count or state exists.
module qkd_ahub_reset_face_private(input wire clk,rst_n_in,
    output wire rst_n,qualified);
    (* keep="true",dont_touch="true" *) reg s0,s1,q0,q1;
    always @(posedge clk or negedge rst_n_in)
        if(!rst_n_in) begin s0<=0;s1<=0;end
        else begin s0<=1;s1<=s0;end
    always @(posedge clk) begin q0<=s1;q1<=q0;end
    assign rst_n=q1;
    assign qualified=s1;
endmodule

module qkd_ahub_transport_private #(
    parameter integer W = 268,
    parameter integer BANK_BITS = 8,
    parameter integer MUT = 0
) (
    input wire clk, tx_rst_n, rx_rst_n, in_valid,
    input wire [W-1:0] d,
    output wire [W-1:0] q,
    output wire out_valid, accept
);
    localparam integer BANKS=(W+BANK_BITS-1)/BANK_BITS;
    wire [BANKS-1:0] bank_valid, bank_accepted;
    assign out_valid = &bank_valid;
    assign accept = &bank_accepted;
    genvar b;
    generate for (b=0;b<BANKS;b=b+1) begin:g_bank
        localparam integer BW=((W-b*BANK_BITS)<BANK_BITS)?(W-b*BANK_BITS):BANK_BITS;
        wire tx_ready, rx_ready,tx_qualified,rx_qualified;
        qkd_ahub_reset_face_private u_tx_reset
            (.clk(clk),.rst_n_in(tx_rst_n),.rst_n(tx_ready),.qualified(tx_qualified));
        qkd_ahub_reset_face_private u_rx_reset
            (.clk(clk),.rst_n_in(rx_rst_n),.rst_n(rx_ready),.qualified(rx_qualified));
        (* keep="true", dont_touch="true" *) reg [BW-1:0] ingress, ring_q, landing;
        // Functional-only small indexed storage; no macro qualification inherited.
        (* keep="true", dont_touch="true" *) reg [BW-1:0] payload [0:3];
        (* keep="true", dont_touch="true" *) reg [1:0] phase;
        (* keep="true", dont_touch="true" *) reg [3:0] slot_valid;
        (* keep="true", dont_touch="true" *) reg ingress_valid, ring_valid, landing_valid;
        wire bank_accept=in_valid && tx_ready && rx_ready && ((MUT==5)?1'b1:(tx_qualified && rx_qualified));
        assign bank_accepted[b]=bank_accept;
        wire [1:0] read_slot=phase+2'd2+((MUT==1 && b==0)?2'd1:2'd0);
        always @(posedge clk) begin
            ingress <= d[b*BANK_BITS +: BW];
            ingress_valid <= bank_accept;
            if (!rx_ready || !rx_qualified) begin
                phase <= 2'd0;
                slot_valid <= (MUT==3)?4'b1111:4'b0000;
                ring_valid <= 1'b0;
            end else begin
                payload[phase] <= ingress;
                slot_valid[phase] <= ingress_valid;
                ring_q <= payload[read_slot];
                ring_valid <= slot_valid[read_slot];
                phase <= phase+2'd1;
            end
            landing <= ring_q;
        end
        always @(posedge clk or negedge rx_qualified) begin
            if(!rx_qualified) landing_valid<=1'b0;
            else if(!rx_ready) landing_valid<=1'b0;
            else landing_valid <= (MUT==2 && b==0)?slot_valid[read_slot]:ring_valid;
        end
        assign q[b*BANK_BITS +: BW]=landing;
        assign bank_valid[b]=landing_valid;
    end endgenerate
`ifndef SYNTHESIS
    initial begin
        if (W<1 || BANK_BITS<1 || BANK_BITS>8) $fatal(1,"private transport bank bounds");
    end
`endif
endmodule

// The real ZH return has no epoch/pass field. Ownership is external and must
// remain matched to command identity; this wrapper adds no invented public bits.
module qkd_ahub_zh_transport_private #(
    parameter integer ENABLE=0,
    parameter integer MUT_CMD=0,
    parameter integer MUT_RETURN=0
)(
    input wire clk, core_rst_n, child_rst_n,
    input wire command_valid, return_valid,
    input wire [267:0] command_word,
    input wire [67:0] return_word,
    output wire [267:0] child_command,
    output wire [67:0] core_return,
    output wire command_out_valid, return_out_valid,
    output wire command_accept, return_accept
);
    generate if (ENABLE) begin:g_private
        qkd_ahub_transport_private #(.W(268),.MUT(MUT_CMD)) u_command
            (.clk(clk),.tx_rst_n(core_rst_n),.rx_rst_n(child_rst_n),.in_valid(command_valid),
             .d(command_word),.q(child_command),.out_valid(command_out_valid),.accept(command_accept));
        wire [67:0] r;
        wire [67:0] owned_return;
        if (MUT_RETURN==4) begin:g_wrong_owner
            reg [3:0] previous_fault;
            always @(posedge clk) previous_fault <= return_word[67:64];
            assign owned_return={previous_fault,return_word[63:0]};
        end else begin:g_owned
            assign owned_return=return_word;
        end
        qkd_ahub_transport_private #(.W(68),.MUT(MUT_RETURN)) u_return
            (.clk(clk),.tx_rst_n(child_rst_n),.rx_rst_n(core_rst_n),.in_valid(return_valid),
             .d(owned_return),.q(r),.out_valid(return_out_valid),.accept(return_accept));
        assign core_return=r;
    end else begin:g_default_off
        assign child_command=command_word;
        assign core_return=return_word;
        assign command_out_valid=command_valid;
        assign return_out_valid=return_valid;
        assign command_accept=command_valid;
        assign return_accept=return_valid;
    end endgenerate
endmodule
