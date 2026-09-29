`timescale 1ns/1ps
module tb_chip_v41x_rope_su_word;
    reg [1:0] src;
    reg [29:0] addr;
    reg valid, hold, kind;
    reg [20:0] pos;
    reg [2047:0] pairs;
    wire is_rope, bad;
    wire [31:0] data;
    reg [63:0] fixture [0:31];
    string dir, name;
    integer checks;

    ot_chip_v41x_rope_su_word #(.AW(30), .PW(21)) dut (
        .src(src), .addr(addr), .cache_valid(valid), .cache_hold(hold),
        .cache_kind(kind), .cache_pos(pos), .cache_pairs(pairs),
        .is_rope(is_rope), .bad(bad), .data(data));

    task automatic load_case(input string file, input bit k, input [20:0] p);
        $readmemh({dir, "/", file, ".hex"}, fixture);
        kind=k; pos=p; valid=1; hold=1;
        for (integer i=0;i<32;i=i+1) pairs[64*i +: 64]=fixture[i];
        for (integer i=0;i<32;i=i+1) begin
            addr = {2'b10 | {1'b0,k}, 28'(p*32+i)};
            src=2'd1; #1;
            if (!is_rope || bad || data !== fixture[i][31:0])
                $fatal(1,"cos case=%s i=%0d got=%h want=%h",file,i,data,fixture[i][31:0]);
            checks++;
            src=2'd2; #1;
            if (!is_rope || bad || data !== fixture[i][63:32])
                $fatal(1,"sin case=%s i=%0d got=%h want=%h",file,i,data,fixture[i][63:32]);
            checks++;
        end
    endtask

    initial begin
        if (!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR fixture missing");
        src=0; addr=0; valid=0; hold=0; kind=0; pos=0; pairs=0; checks=0;
        load_case("plain200k",0,21'd199999);
        load_case("yarn200k",1,21'd199999);
        load_case("plain1m",0,21'd1048575);
        src=2'd1; addr={2'b10,28'(21'd1048574*32)}; #1;
        if (!is_rope || !bad || data != 0) $fatal(1,"wrong position must fail closed"); checks++;
        addr={2'b11,28'(21'd1048575*32)}; #1;
        if (!is_rope || !bad || data != 0) $fatal(1,"wrong kind must fail closed"); checks++;
        addr={2'b10,28'(21'd1048575*32)}; hold=0; #1;
        if (!is_rope || !bad || data != 0) $fatal(1,"released entry must fail closed"); checks++;
        hold=1; valid=0; #1;
        if (!is_rope || !bad || data != 0) $fatal(1,"invalid entry must fail closed"); checks++;
        valid=1; addr=30'd1234; #1;
        if (is_rope || bad) $fatal(1,"ordinary CROM must not be captured"); checks++;
        $display("ROPE_SU_WORD_PASS checks=%0d",checks);
        $finish;
    end
endmodule
