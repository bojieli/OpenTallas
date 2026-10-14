`timescale 1ns/1ps
module dsfd_sp_capture (input wire [0:0] ck, input wire [0:0] rst, input wire [0:0] ckv, input wire [0:0] rsv,
    input wire [6946:0] f_gather, output wire [13375:0] t_vm);
    wire [13375:0] rv; wire [11:0] rc, dc;
    capc_ref u_ref (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_gather(f_gather), .t_vm(rv), .t_cd(rc));
    dsfd_sp_capture_c u_dut (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_gather(f_gather), .t_vm(t_vm), .t_cd(dc));
    integer mm = 0, tg = 0, nw = 0; reg tq = 1'b0; reg live = 1'b0;
    always @(posedge ckv[0]) if (rsv[0]) begin
        live <= 1'b1;
        if (live) begin
            if (rv !== t_vm || rc !== dc) begin mm = mm + 1; if (mm < 5) $display("CAPC_EQ MISMATCH t=%0t cd %h/%h", $time, rc, dc); end
            if (dc[11] !== tq) begin tg = tg + 1; tq <= dc[11]; end
            if (|t_vm[13311:0]) nw = nw + 1;
        end
    end
    final $display("CAPC_EQ mismatches=%0d tcd_toggles=%0d vm_active_cycles=%0d %s", mm, tg, nw, (mm == 0 && nw > 0) ? "EQ_PASS" : "EQ_FAIL");
endmodule
