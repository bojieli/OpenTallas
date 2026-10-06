`timescale 1ns/1ps
// Bench of ot_dsrom_su_softmax (tools/dsrom_su_softmax.py writes the case files into the run directory):
//   s.mem (nv score vectors), pv.mem (512/LPH PV vectors), e_exp.mem, o_exp.mem (BF16), par.mem (nv, lt, scale),
//   vec.mem (sink, max, row sum, den per head), rope.mem (cos, sin of the 32 tail pairs).
// Cycle 0 is the first score vector at the unit's input; the PV stream starts the cycle after den reaches the
// lanes.  Prints one SMX line: event cycles and per-check element mismatches.
module tb_dsrom_su_softmax;
    parameter integer H = 16;
    parameter integer LPH = 16;
    parameter integer NVMAX = 40;
    parameter integer LTMAX = 6;
    parameter integer LM = 5;
    parameter integer LA = 4;
    parameter integer ELM = 5;
    parameter integer ELA = 4;
    parameter integer ADD6 = 0;
    parameter integer EXP6 = 0;
    parameter integer EXPNS = 0;
    parameter integer DENK = 0;
    parameter integer MARGIN = 0;
    localparam integer NL = H * LPH;
    localparam integer NPV = 512 / LPH;
    localparam integer TAIL = 64;

    reg clk = 1'b0, rst_n = 1'b0;
    always #1 clk = ~clk;

    reg [NL*32-1:0] s_mem [0:NVMAX-1];
    reg [NL*32-1:0] pv_mem [0:NPV-1];
    reg [NL*32-1:0] e_exp [0:NVMAX-1];
    reg [NL*16-1:0] o_exp [0:NPV-1];
    reg [31:0]      par [0:2];
    reg [H*32-1:0]  vec [0:3];
    reg [16*TAIL-1:0] rope [0:1];

    reg              s_v, pv_v;
    reg [NL*32-1:0]  s_d, pv_d;
    wire             e_v, mx_v, es_v, den_v, o_v, fault;
    wire [NL*32-1:0] e_d;
    wire [H*32-1:0]  mx_d, es_d, den_d;
    wire [NL*16-1:0] o_d;
    wire [6:0] nv = par[0][6:0];
    wire [2:0] lt = par[1][2:0];

    ot_dsrom_su_softmax #(.H(H), .LPH(LPH), .NVMAX(NVMAX), .LTMAX(LTMAX), .LM(LM), .LA(LA), .ELM(ELM), .ELA(ELA), .ADD6(ADD6), .EXP6(EXP6), .EXPNS(EXPNS), .DENK(DENK), .MARGIN(MARGIN)) dut (
        .clk(clk), .rst_n(rst_n), .nv(nv), .lt(lt), .scale(par[2]), .sink(vec[0]), .cosv(rope[0]), .sinv(rope[1]),
        .s_v(s_v), .s_d(s_d), .e_v(e_v), .e_d(e_d), .mx_v(mx_v), .mx_d(mx_d), .es_v(es_v), .es_d(es_d),
        .den_v(den_v), .den_d(den_d), .pv_v(pv_v), .pv_d(pv_d), .o_v(o_v), .o_d(o_d), .fault(fault));

    integer cyc, t_mx, t_elast, t_es, t_den, t_pv0, t_olast, ecnt, ocnt, pcnt, i;
    integer err_max, err_es, err_den, err_e, err_o, n_e, n_o;
    initial begin
        $readmemh("s.mem", s_mem);
        $readmemh("pv.mem", pv_mem);
        $readmemh("e_exp.mem", e_exp);
        $readmemh("o_exp.mem", o_exp);
        $readmemh("par.mem", par);
        $readmemh("vec.mem", vec);
        $readmemh("rope.mem", rope);
        cyc = -1; t_mx = -1; t_elast = -1; t_es = -1; t_den = -1; t_pv0 = -1; t_olast = -1;
        ecnt = 0; ocnt = 0; pcnt = 0; err_max = 0; err_es = 0; err_den = 0; err_e = 0; err_o = 0; n_e = 0; n_o = 0;
        s_v = 1'b0; pv_v = 1'b0; s_d = 0; pv_d = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        cyc = 0;
    end
    // one block per edge k (cycle k follows edge k): first the monitor (outputs seen now were visible in cycle
    // k-1), then the drive of cycle k.  Cycle 0 is the first score vector at the unit's input.
    always @(posedge clk) if (cyc >= 0) begin
        if (cyc >= 1) begin
            if (mx_v) begin
                t_mx = cyc - 1;
                for (i = 0; i < H; i = i + 1) if (mx_d[32*i +: 32] !== vec[1][32*i +: 32]) err_max = err_max + 1;
            end
            if (e_v) begin
                for (i = 0; i < NL; i = i + 1) begin
                    n_e = n_e + 1;
                    if (e_d[32*i +: 32] !== e_exp[ecnt][32*i +: 32]) err_e = err_e + 1;
                end
                ecnt = ecnt + 1;
                t_elast = cyc - 1;
            end
            if (es_v) begin
                t_es = cyc - 1;
                for (i = 0; i < H; i = i + 1) if (es_d[32*i +: 32] !== vec[2][32*i +: 32]) err_es = err_es + 1;
            end
            if (den_v) begin
                t_den = cyc - 1;
                for (i = 0; i < H; i = i + 1) if (den_d[32*i +: 32] !== vec[3][32*i +: 32]) err_den = err_den + 1;
            end
            if (o_v) begin
                for (i = 0; i < NL; i = i + 1) begin
                    n_o = n_o + 1;
                    if (o_d[16*i +: 16] !== o_exp[ocnt][16*i +: 16]) err_o = err_o + 1;
                end
                ocnt = ocnt + 1;
                t_olast = cyc - 1;
            end
        end
        if (ocnt == NPV) begin
            $display("SMX t_mx=%0d t_elast=%0d t_es=%0d t_den=%0d t_pv0=%0d t_olast=%0d err_max=%0d err_es=%0d err_den=%0d err_e=%0d err_o=%0d n_e=%0d n_o=%0d fault=%0d",
                     t_mx, t_elast, t_es, t_den, t_pv0, t_olast, err_max, err_es, err_den, err_e, err_o, n_e, n_o,
                     fault);
            $finish;
        end
        if (cyc > 20000) begin
            $display("SMX_TIMEOUT");
            $finish;
        end
        s_v <= (cyc < nv);
        if (cyc < nv) s_d <= s_mem[cyc];
        pv_v <= 1'b0;
        if (t_den >= 0 && pcnt < NPV) begin
            pv_v <= 1'b1;
            pv_d <= pv_mem[pcnt];
            if (pcnt == 0) t_pv0 = cyc;
            pcnt = pcnt + 1;
        end
        cyc = cyc + 1;
    end
endmodule
