`timescale 1ns/1ps
// One real reduced six-position HCP projection, same command and operands in
// the ROM and HBM arms. hcp_w.mem is the checkpoint-derived FP32 weight-bank
// image and also the source of the HBM sectors, byte for byte.
module tb_hdc_v41x_hcp_hbm_exact(input wire clk);
    localparam integer W=8, AW=16, HAW=20, WORDS=256, CW=9, TW=8;
    reg [31:0] meta [0:3];
    reg [31:0] cmdm [0:7];
    reg [31:0] wmem [0:8*WORDS*W-1];
    reg [15:0] xmem [0:8*128*W-1];
    reg [47:0] expm [0:255];
    integer wd, xd, nexp, cyc=0, ei=0, errors=0, faults=0;
    integer cstart=0, start_wait=0, sent=0;
    reg rst_n=0, cmd_valid=0, win_start=0;
    reg hbm=0;
    wire cmd_ready, o_valid, o_last, fault, idle;
    wire [7:0] w_re, x_re;
    wire [8*AW-1:0] w_addr, x_addr;
    wire [2:0] o_pos;
    wire [4:0] o_idx;
    wire [31:0] o_data;
    reg [8*W*32-1:0] w0, w1, hbm1;
    reg [8*W*16-1:0] x0, x1;
    wire [8*W*32-1:0] win_q;
    wire win_ready, win_fault;
    wire [31:0] received;
    wire [7:0] hq_v, hr_rdy;
    wire [8*HAW-1:0] hq_addr;
    wire [7:0] hq_len;
    reg [7:0] hr_beat=0;
    wire [8*TW-1:0] hq_tag;
    reg [7:0] hr_v=0;
    reg [8*TW-1:0] hr_tag=0;
    reg [8*256-1:0] hr_data=0;
    integer b,l,a;
    reg [47:0] ex;
    initial begin
        $readmemh("hcp_meta.mem", meta);
        wd=meta[1]; xd=meta[2]; nexp=meta[3];
        $readmemh("hcp_cmd.mem", cmdm);
        $readmemh("hcp_w.mem", wmem, 0, 8*wd*W-1);
        $readmemh("hcp_x.mem", xmem, 0, 8*xd*W-1);
        $readmemh("hcp_exp.mem", expm, 0, nexp-1);
        hbm=$test$plusargs("HBM");
        if (meta[0] != 1 || wd < 1 || wd > WORDS || nexp != cmdm[0]*cmdm[1])
            $fatal(1, "invalid HCP fixture");
    end

    ot_hdc_v41x_hcp_hbm_window #(.HW(W), .WORDS(WORDS), .AW(AW), .HAW(HAW)) u_win (
        .clk(clk), .rst_n(rst_n), .start(win_start), .release_window(1'b0),
        .rom_base(AW'(cmdm[6])), .hbm_base(HAW'(0)), .nwords(CW'(wd)),
        .ready(win_ready), .hq_v(hq_v), .hq_rdy(8'hff),
        .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag),
        .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag), .hr_beat(hr_beat),
        .hr_data(hr_data), .rom_re(hbm ? w_re : 8'd0), .rom_addr(w_addr),
        .rom_q(win_q), .fault(win_fault), .received_sectors(received)
    );
    ot_hdc_v41x_hcp #(.W(W), .TL(9), .PMAX(8), .OMAX(32), .AW(AW),
                       .CW(16), .ML(2), .DF(32)) u_hcp (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready),
        .cmd_npos(cmdm[0][3:0]), .cmd_nout(cmdm[1][5:0]),
        .cmd_nchunk(cmdm[2][15:0]), .cmd_scale(cmdm[3][0]),
        .cmd_nf(cmdm[4]), .cmd_eps(cmdm[5]),
        .cmd_wbase(cmdm[6][AW-1:0]), .cmd_xbase(cmdm[7][AW-1:0]),
        .w_re(w_re), .w_addr(w_addr), .w_data(hbm ? hbm1 : w1),
        .x_re(x_re), .x_addr(x_addr), .x_data(x1),
        .o_valid(o_valid), .o_ready(1'b1), .o_pos(o_pos),
        .o_idx(o_idx), .o_data(o_data), .o_last(o_last),
        .fault(fault), .idle(idle)
    );
    always @(posedge clk) begin
        cyc <= cyc+1;
        if (cyc == 4) rst_n <= 1;
        win_start <= 0;
        if (rst_n && cyc == 8 && hbm) begin
            win_start <= 1;
            start_wait <= cyc;
        end
        if (rst_n && !cmd_valid && sent == 0 && cmd_ready &&
            ((!hbm && cyc > 10) || (hbm && win_ready))) begin
            cmd_valid <= 1;
            sent <= 1;
        end
        if (cmd_valid && cmd_ready) begin
            cmd_valid <= 0;
            cstart <= cyc;
        end
        if (fault || (hbm && win_fault)) faults <= faults+1;
        if (o_valid) begin
            ex=expm[ei];
            if (o_data !== ex[31:0] || o_pos !== ex[42:40] || o_idx !== ex[36:32] ||
                o_last !== (ei+1 == nexp)) begin
                errors <= errors+1;
                if (errors < 6) $display("MISMATCH %0d got %08x/%0d/%0d exp %012x", ei,o_data,o_pos,o_idx,ex);
            end
            ei <= ei+1;
            if (ei+1 == nexp) begin
                $display("HCP_AB_PASS mode=%0d outputs=%0d errors=%0d faults=%0d sectors=%0d wait=%0d run=%0d", 
                         hbm, nexp, errors, faults, received, hbm ? cstart-start_wait : 0, cyc-cstart);
                $finish;
            end
        end
        if (cyc > 100000) $fatal(1,"HCP timeout output=%0d/%0d",ei,nexp);
    end
    always @(posedge clk) begin
        // ROM and HBM images read exactly the same bank/lane words.
        for (b=0;b<8;b=b+1) begin
            for (l=0;l<W;l=l+1) begin
                w0[(b*W+l)*32 +: 32] <= wmem[(b*wd+w_addr[b*AW +: AW])*W+l];
                x0[(b*W+l)*16 +: 16] <= xmem[(b*xd+x_addr[b*AW +: AW])*W+l];
            end
            hr_v[b] <= hq_v[b];
            hr_tag[b*TW +: TW] <= hq_tag[b*TW +: TW];
            hr_beat[b] <= 0;
            a = hq_addr[b*HAW +: HAW] - b*WORDS;
            for (l=0;l<W;l=l+1)
                hr_data[(b*W+l)*32 +: 32] <= (hq_v[b] && a < wd) ? wmem[(b*wd+a)*W+l] : 0;
        end
        w1 <= w0;
        x1 <= x0;
        hbm1 <= win_q;
    end
endmodule
