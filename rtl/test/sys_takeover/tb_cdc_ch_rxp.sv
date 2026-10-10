`timescale 1ps/1ps
// sys-takeover 2026-10-09: ot_qwen_die_cdc_ch receive-buffer bench at the far92 shape (W 523, IBUF 128, OCRED 8, AD 8):
// a credit-honouring sender (IBUF initial credits, one back per i_cr) with random gaps, an unrelated read clock and a
// receiver returning o_cr at a random rate (backpressure fills the async FIFO, the staging FIFO and the buffer).  Every
// word is checked in order (value = f(index)); faults must stay 0; ends when NW words arrived.  -P RXP 0 / 1.
module tb_cdc_ch_rxp #(parameter integer RXP = 1, parameter integer AFW = 0, parameter integer NW = 2000, parameter integer SEND = 70, parameter integer TAKE = 35);
    localparam integer W = 523;
    reg wclk = 0, rclk = 0, rst_n = 0;
    always #417 wclk = ~wclk;
    initial begin #131; forever #397 rclk = ~rclk; end
    function automatic [W-1:0] word(input integer n);
        integer j; reg [W-1:0] x;
        begin x = 0; for (j = 0; j < W; j = j + 32) x[j +: 32] = n * 32'h9e3779b1 + j * 32'h85ebca6b; word = x; end
    endfunction
    reg i_v = 0; reg [W-1:0] i_d = 0; wire i_cr, w_fault, o_v, r_fault; wire [W-1:0] o_d; reg o_cr = 0;
    ot_qwen_die_cdc_ch #(.W(W), .IBUF(128), .OCRED(8), .AD(8), .RXP(RXP), .AFW(AFW)) dut (.wclk(wclk), .wrst_n(rst_n), .i_v(i_v),
        .i_d(i_d), .i_cr(i_cr), .w_fault(w_fault), .rclk(rclk), .rrst_n(rst_n), .o_v(o_v), .o_d(o_d), .o_cr(o_cr), .r_fault(r_fault));
    integer cred = 128, sent = 0, got = 0, bad = 0, held = 0, maxheld = 0, cyc = 0;
    reg [31:0] rs = 32'h1234567, rr = 32'h7654321;
    reg go = 0;                 // senders start after the DUT's reset synchronisers release
    always @(posedge wclk) if (rst_n && go) begin
        rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5);
        cred = cred + (i_cr ? 1 : 0);
        if (cred > 0 && sent < NW && (rs % 100) < SEND) begin i_v <= 1'b1; i_d <= word(sent); sent = sent + 1; cred = cred - 1; end
        else begin i_v <= 1'b0; i_d <= {W{1'bx}}; end
        if (128 - cred > maxheld) maxheld = 128 - cred;
    end
    always @(posedge rclk) if (rst_n) begin
        cyc = cyc + 1;
        rr = rr ^ (rr << 13); rr = rr ^ (rr >> 17); rr = rr ^ (rr << 5);
        if (o_v) begin
            if (o_d !== word(got)) begin bad = bad + 1; if (bad < 5) $display("MISMATCH word %0d", got); end
            got = got + 1; held = held + 1;
        end
        o_cr <= 1'b0;
        if (held > 0 && (rr % 100) < TAKE) begin o_cr <= 1'b1; held = held - 1; end
    end
    initial begin
        repeat (8) @(posedge wclk); rst_n = 1;
        repeat (12) @(posedge wclk); go = 1;
        wait (got == NW || cyc > 400000);
        repeat (20) @(posedge rclk);
        $display("CDC_RXP rxp=%0d words=%0d/%0d mismatches=%0d w_fault=%b r_fault=%b max_outstanding=%0d rclk_cycles=%0d",
                 RXP, got, NW, bad, w_fault, r_fault, maxheld, cyc);
        if (got == NW && bad == 0 && !w_fault && !r_fault) $display("CDC_RXP PASS"); else $display("CDC_RXP FAIL");
        $finish;
    end
endmodule
