`timescale 1ns/1ps
// redesign-qwen 2026-10-09: ot_qfd_crom_lbuf against the constant ROM's contract.  A behavioural far ROM answers
// (stage, address) FLP edges after its strobe; the reference answers the SU's reads with the same function 5 edges after
// the strobe (ot_qfd_crom's timing).  Tokens of 37 stages (0..35, HEAD) at increasing positions; in every stage the SU
// waits for st_rdy (counted), then reads every region of the stage under the banking contract (lane l reads rb + 64 r + l
// of one region a cycle, random lane subsets, random gaps).  PASS: every answered lane equals the reference, no fault.
module tb_qfd_crom_lbuf #(parameter integer MUT = 0, parameter integer FLP = 11, parameter integer NTOK = 3,
                          parameter integer RPS = 300, parameter integer SEED = 1,
                          parameter integer NOWAIT = 0, parameter integer SRAM = 0);   // 1: the SU does not wait for st_rdy (negative: must FAIL)
    localparam integer SW = 64, AW = 24, LW = 6, NW = 18;
    localparam integer QK0 = 4096, POST0 = 5376, QSCALE = 9472, ROPE0 = 9473, OSC0 = 533761, DSC0 = 537857, END = 541953;
    localparam integer HEAD = 36;
    localparam [63:0] QSW = 64'h3db504f3_00000000;
    reg clk = 0, rst_n = 0;
    always #0.4166665 clk = ~clk;
    function automatic [31:0] h32(input [31:0] x);
        reg [31:0] y; begin y = x * 32'h9e3779b1; y = y ^ (y >> 15); y = y * 32'h85ebca6b; h32 = y ^ (y >> 13); end
    endfunction
    // the constant store's content: the function of (stage, address) the far ROM and the reference share
    function automatic [63:0] V(input [LW-1:0] st, input [AW-1:0] a);
        if (st == HEAD) V = (a < 4096) ? {32'd0, h32({8'd200, a})} : 64'd0;
        else if (a < QK0 || (a >= POST0 && a < QSCALE)) V = 64'd0;
        else if (a < POST0 || (a >= OSC0 && a < END)) V = {32'd0, h32({st, 2'b00, a})};
        else if (a == QSCALE) V = QSW;
        else if (a < OSC0) V = {h32(a ^ 32'h5a5a5a5a), h32(a)};
        else V = 64'd0;
    endfunction
    // DUT
    reg  [SW-1:0] re; reg [SW*AW-1:0] addr; reg [LW-1:0] cst, stage; reg tok_start; reg [NW-1:0] tpos;
    wire [SW*64-1:0] q; wire st_rdy, fault; wire [1:0] fcode;
    wire [SW-1:0] f_re; wire [SW*AW-1:0] f_addr; wire [LW-1:0] f_stage; reg [SW*64-1:0] f_q;
    ot_qfd_crom_lbuf #(.FLP(FLP), .MUT(MUT), .SRAM(SRAM)) dut (.clk(clk), .rst_n(rst_n), .crom_re(re), .crom_addr(addr), .crom_stage(cst),
        .crom_q(q), .stage(stage), .tok_start(tok_start), .tpos(tpos), .st_rdy(st_rdy), .f_re(f_re), .f_addr(f_addr),
        .f_stage(f_stage), .f_q(f_q), .f_fault(1'b0), .fault(fault), .fault_code(fcode));
    // far ROM: answers FLP edges after the strobe (registered pipeline)
    reg [SW*64-1:0] fpipe [0:31];
    integer i, l;
    always @(posedge clk) begin
        for (i = 31; i > 0; i = i - 1) fpipe[i] <= fpipe[i-1];
        for (l = 0; l < SW; l = l + 1) fpipe[0][l*64 +: 64] <= f_re[l] ? V(f_stage, f_addr[l*AW +: AW]) : 64'hx;
    end
    always @(*) f_q = fpipe[FLP-1];
    // reference: the read's expected word, 5 edges after the strobe
    reg [SW*64-1:0] epipe [0:7];
    reg [SW-1:0] vpipe [0:7];
    always @(posedge clk) begin
        for (i = 7; i > 0; i = i - 1) begin epipe[i] <= epipe[i-1]; vpipe[i] <= vpipe[i-1]; end
        vpipe[0] <= rst_n ? re : '0;
        for (l = 0; l < SW; l = l + 1) epipe[0][l*64 +: 64] <= V(cst, addr[l*AW +: AW]);
    end
    integer checks = 0, bad = 0, waits = 0, cyc = 0;
    always @(posedge clk) if (rst_n) begin
        cyc = cyc + 1;
        for (l = 0; l < SW; l = l + 1)
            if (vpipe[4][l]) begin
                checks = checks + 1;
                if (q[l*64 +: 64] !== epipe[4][l*64 +: 64]) begin
                    if (bad < 5) $display("MISMATCH lane %0d got %h want %h at %0d", l, q[l*64 +: 64], epipe[4][l*64 +: 64], cyc);
                    bad = bad + 1;
                end
            end
    end
    // driver
    integer t, s, n, reg_k, r, nrows;
    reg [31:0] rs;
    reg [AW-1:0] rb;
    task automatic rnd; begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5); end endtask
    initial begin
        rs = 32'h1234_5678 ^ SEED;
        re = 0; addr = 0; cst = 0; stage = 0; tok_start = 0; tpos = 100;
        repeat (5) @(posedge clk);
        rst_n = 1;
        for (t = 0; t < NTOK; t = t + 1) begin
            @(posedge clk); tok_start <= 1; tpos <= 100 + t; stage <= 0;
            @(posedge clk); tok_start <= 0;
            for (s = 0; s <= HEAD; s = s + 1) begin
                stage <= s;
                @(posedge clk);
                while (!st_rdy && NOWAIT == 0) begin waits = waits + 1; @(posedge clk); end
                for (n = 0; n < RPS; n = n + 1) begin
                    rnd;
                    reg_k = (s == HEAD) ? 6 : (rs % 6);
                    case (reg_k)
                        0: begin rb = QK0;   nrows = 20; end
                        1: begin rb = OSC0;  nrows = 64; end
                        2: begin rb = DSC0;  nrows = 64; end
                        3: begin rb = 0;     nrows = 64; end            // ZERO (input / post norm folded)
                        4: begin rb = QSCALE; nrows = 0; end
                        5: begin rb = ROPE0 + 64 * (100 + t); nrows = 1; end
                        default: begin rb = 0; nrows = 64; end         // HEAD final norm
                    endcase
                    rnd;
                    r = (nrows > 0) ? (rs % nrows) : 0;
                    rnd;
                    cst <= s;
                    for (l = 0; l < SW; l = l + 1) begin
                        re[l] <= (rs >> (l % 32)) & 1;
                        addr[l*AW +: AW] <= (reg_k == 4) ? QSCALE : rb + 64 * r + l;
                    end
                    @(posedge clk);
                    re <= 0;
                    if (rs[7:6] == 0) @(posedge clk);
                end
            end
        end
        repeat (20) @(posedge clk);
        if (bad == 0 && !fault && checks > 0)
            $display("PASS crom_lbuf checks=%0d waits=%0d tokens=%0d FLP=%0d cycles=%0d", checks, waits, NTOK, FLP, cyc);
        else
            $display("FAIL crom_lbuf checks=%0d bad=%0d fault=%0d code=%0d waits=%0d", checks, bad, fault, fcode, waits);
        $finish;
    end
endmodule
