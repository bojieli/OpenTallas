`timescale 1ns/1ps
// redesign-qwen 2026-10-09: ot_qfd_crom_lbuf against the constant ROM's contract.  A behavioural far ROM answers
// (stage, address) FLP edges after its strobe; the reference answers the SU's reads with the same function 5 edges after
// the strobe (ot_qfd_crom's timing).  Tokens of 37 stages (0..35, HEAD) at increasing positions; in every stage the SU
// waits for st_rdy (counted), then reads every region of the stage under the banking contract (lane l reads rb + 64 r + l
// of one region a cycle, random lane subsets, random gaps).  PASS: every answered lane equals the reference, no fault.
module tb_qfd_cbuf_reqhead_native_l0 #(parameter integer MUT = 0, parameter integer FLP = 11, parameter integer NTOK = 3,
                          parameter integer RPS = 300, parameter integer SEED = 1,
                          parameter integer NOWAIT = 0, parameter integer SRAM = 0,
                          parameter integer GRPS = 0,
                          parameter integer TILE = 0,    // q13: 1 (with GRPS 1) = eight ot_qfd_su_cbuf_g die tiles, f_lat strap = FLP + LATERR
                          parameter integer LATERR = 0,  // negative: the strap disagrees with the far ROM's latency (must FAIL)
                          parameter integer GATE = 0,    // qwen-1010/a: 1 = the stage start through ot_qfd_stage_gate (the seq_su wiring)
                          parameter integer GMUT = 0, PIPE_MUT=0);   // 1 = the gate does not wait (NOWAIT in the master): must FAIL    // 1: eight 8-lane group tiles (ot_qfd_crom_lbuf SW 8, lane_base 8g)   // 1: the SU does not wait for st_rdy (negative: must FAIL)
    localparam integer SW = 64, AW = 24, LW = 6, NW = 18;
    localparam integer QK0 = 4096, POST0 = 4736, QSCALE = 8832, ROPE0 = 8833, OSC0 = 533121, DSC0 = 537217, END = 541313;
    localparam integer HEAD = 36;
    localparam [63:0] QSW = 64'h3db504f3_00000000;
    reg clk = 0, rst_n = 0;
    always #0.4166665 clk = ~clk;
    function automatic [31:0] h32(input [31:0] x);
        reg [31:0] y; begin y = x * 32'h9e3779b1; y = y ^ (y >> 15); y = y * 32'h85ebca6b; h32 = y ^ (y >> 13); end
    endfunction
    // Actual emitted checkpoint cROM is an independent read oracle.
    reg [63:0] image [0:541312];
    reg [4095:0] image_path;
    initial begin
      if (!$value$plusargs("CROM=%s",image_path)) $fatal(1,"Missing actual checkpoint CROM path");
      $readmemh(image_path,image);
    end
    function automatic [63:0] V(input [LW-1:0] st,input [AW-1:0] a);
      if(st==0 && a<541313) V=image[a]; else V=64'd0;
    endfunction
    // DUT (st_rdy is qualified by the stage it reports, as the SU-side controller does)
    wire st_rdy = st_rdy0 && (st_rdy_stage == stage);
    reg  [SW-1:0] re; reg [SW*AW-1:0] addr; reg [LW-1:0] cst, stage_tb; reg tok_start_tb; reg [NW-1:0] tpos;
    // GATE 1: the buffer sees the stage / token start the seq_su gate sends (cb_stage / cb_tok_start)
    reg h_start = 0; reg [LW-1:0] h_stage = 0;
    wire g_go, g_tok; wire [NW-1:0] g_token, g_pos; wire [LW-1:0] g_stage;
    assign g_go=1'b0; assign g_tok=1'b0; assign g_stage=stage_tb;
    wire [LW-1:0] stage = (GATE != 0) ? g_stage : stage_tb;
    wire tok_start = (GATE != 0) ? g_tok : tok_start_tb;
    wire [SW*64-1:0] q; wire st_rdy0, fault; wire [LW-1:0] st_rdy_stage; wire [1:0] fcode;
    wire [SW-1:0] f_re; wire [SW*AW-1:0] f_addr; wire [LW-1:0] f_stage; reg [SW*64-1:0] f_q;
    generate if (GRPS == 0) begin : g_one
    ot_qfd_crom_lbuf #(.FLP(FLP), .MUT(MUT), .SRAM(SRAM)) dut (.clk(clk), .rst_n(rst_n), .crom_re(re), .crom_addr(addr), .crom_stage(cst),
        .crom_q(q), .stage(stage), .tok_start(tok_start), .tpos(tpos), .lane_base(24'd0), .st_rdy(st_rdy0), .st_rdy_stage(st_rdy_stage), .f_re(f_re), .f_addr(f_addr),
        .f_stage(f_stage), .f_q(f_q), .f_fault(1'b0), .f_lat(5'd0), .fault(fault), .fault_code(fcode));
    end else begin : g_grps
        wire [7:0] rdy, flt; wire [15:0] fc; wire [8*LW-1:0] fst, rst_g;
        genvar gg;
        for (gg = 0; gg < 8; gg = gg + 1) begin : g_g
          if (TILE != 0) begin : g_tile
            wire [2:0] grp_s = gg;
            wire [4:0] lat_s = FLP + 1 + LATERR;
            qfd_su_cbuf_native_l0_reqhead #(.MUT(MUT),.PIPE_MUT(PIPE_MUT)) u (.clk(clk), .rst_n(rst_n), .crom_re(re[8*gg +: 8]),
                .crom_addr(addr[8*gg*AW +: 8*AW]), .crom_stage(cst), .crom_q(q[8*gg*64 +: 8*64]), .stage(stage), .tok_start(tok_start),
                .tpos(tpos), .grp(grp_s), .st_rdy(rdy[gg]), .st_rdy_stage(rst_g[gg*LW +: LW]), .f_re(f_re[8*gg +: 8]), .f_addr(f_addr[8*gg*AW +: 8*AW]),
                .f_stage(fst[gg*LW +: LW]), .f_q(f_q[8*gg*64 +: 8*64]), .f_fault(1'b0), .f_lat_total(lat_s), .fault(flt[gg]), .fault_code(fc[2*gg +: 2]));
          end else begin : g_core
            ot_qfd_crom_lbuf #(.SW(8), .FLP(FLP), .MUT(MUT), .SRAM(SRAM)) u (.clk(clk), .rst_n(rst_n), .crom_re(re[8*gg +: 8]),
                .crom_addr(addr[8*gg*AW +: 8*AW]), .crom_stage(cst), .crom_q(q[8*gg*64 +: 8*64]), .stage(stage), .tok_start(tok_start),
                .tpos(tpos), .lane_base(24'(8*gg)), .st_rdy(rdy[gg]), .st_rdy_stage(rst_g[gg*LW +: LW]), .f_re(f_re[8*gg +: 8]), .f_addr(f_addr[8*gg*AW +: 8*AW]),
                .f_stage(fst[gg*LW +: LW]), .f_q(f_q[8*gg*64 +: 8*64]), .f_fault(1'b0), .f_lat(5'd0), .fault(flt[gg]), .fault_code(fc[2*gg +: 2]));
          end
        end
        assign st_rdy0 = &rdy; assign st_rdy_stage = rst_g[LW-1:0]; assign fault = |flt; assign fcode = fc[1:0]; assign f_stage = fst[LW-1:0];
    end endgenerate
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
        re = 0; addr = 0; cst = 0; stage_tb = 0; tok_start_tb = 0; tpos = 100;
        repeat (5) @(posedge clk);
        rst_n = 1;
        if (TILE != 0) repeat (4) @(posedge clk);  // ot_rst_relay: the tile releases 3 edges after the port
        for (t = 0; t < NTOK; t = t + 1) begin
            if (GATE == 0) begin @(posedge clk); tok_start_tb <= 1; tpos <= 100 + t; stage_tb <= 0;
                @(posedge clk); tok_start_tb <= 0; end
            else tpos <= 100 + t;
            for (s = 0; s < 1; s = s + 1) begin
                if (GATE == 0) begin
                    stage_tb <= s;
                    @(posedge clk);
                    while (!st_rdy && NOWAIT == 0) begin waits = waits + 1; @(posedge clk); end
                end else begin
                    h_start <= 1; h_stage <= s; @(posedge clk); h_start <= 0;
                    while (!g_go) begin waits = waits + 1; @(posedge clk); end
                end
                for (n = 0; n < RPS; n = n + 1) begin
                    rnd;
                    reg_k = (s == HEAD) ? 6 : (rs % 6);
                    case (reg_k)
                        0: begin rb = QK0;   nrows = 10; end
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
            $display("PASS cbuf_native_l0 GATE=%0d GMUT=%0d TILE=%0d checks=%0d waits=%0d tokens=%0d FLP=%0d cycles=%0d", GATE, GMUT, TILE, checks, waits, NTOK, FLP, cyc);
        else
            $display("FAIL cbuf_native_l0 checks=%0d bad=%0d fault=%0d code=%0d waits=%0d", checks, bad, fault, fcode, waits);
        $finish;
    end
endmodule
