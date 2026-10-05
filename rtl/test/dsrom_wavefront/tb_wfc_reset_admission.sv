`timescale 1ns/1ps
// Controller-only regression for stage9_w1's first-flit reset boundary.
// Same 41-word receive geometry; payload low64 is the retained first payload.
module tb_wfc_reset_admission;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    integer ip = 0, writes = 0, starts = 0;
    wire in_ready, core_start, vm_we, proto_fault;
    wire [15:0] core_pos;
    wire in_valid = rst_n && ip < 42;
    wire in_last = ip == 41;
    wire [511:0] in_data = ip == 0 ? 512'h29010000 :
                          ip == 1 ? 512'h3f4b00003fd10000 : 512'd1;
    ot_rom_pkg_ctrl_wfc #(.FLIT(512), .NW(16), .AW(24), .VWA(16),
        .MAXU(1), .KVW(32768), .RXWORDS(41), .XWORDS(46),
        .SOURCE(0), .SEND_HIDDEN(1), .WAVE(1), .WIN(6)) dut (
        .clk(clk), .rst_n(rst_n), .cfg_users(8'd1),
        .cfg_prompt_len(16'd3), .cfg_gen_len(16'd3),
        .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
        .out_ready(1'b1), .core_start(core_start), .core_pos(core_pos),
        .core_done(1'b0), .core_next_token(16'd0), .core_next_val(32'd0),
        .vm_we(vm_we), .vm_rq(512'd0), .pr_q(16'd0), .pr_qk(1'b0),
        .proto_fault(proto_fault));
    always @(posedge clk) if (rst_n) begin
        if (!dut.rst_q && in_valid && in_ready)
            $fatal(1, "Input accepted while receiver reset root held");
        if (in_valid && in_ready) ip <= ip + 1;
        if (vm_we) writes <= writes + 1;
        if (core_start) begin
            if (core_pos != 0 || ip != 41 || writes != 40 || starts != 0)
                $fatal(1, "Wrong first job: pos=%0d ip=%0d writes=%0d starts=%0d",
                       core_pos, ip, writes, starts);
            starts <= starts + 1;
        end
    end
    initial begin
        repeat (6) @(negedge clk);
        rst_n = 1;
        repeat (45) @(negedge clk);
        if (ip != 42 || writes != 41 || starts != 1 || proto_fault)
            $fatal(1, "Boundary failed ip=%0d writes=%0d starts=%0d fault=%0d",
                       ip, writes, starts, proto_fault);
        $display("PASS reset admission: header retained, position0, 41 payload writes, one start");
        $finish;
    end
endmodule
