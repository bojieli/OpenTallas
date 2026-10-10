// hfd_hgi_su: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 serial-unit slot (hgi-1010/d, 2026-10-10; coordinator-approved own spine slot): the three record units that were declared on the legacy shared quarter masters (hfd_su / hfd_sfu / hfd_hc: only their SW instance carried the record pins) as one block in the free top end of the spine column.  su = ot_hgi_su_unit (N 16, record adapter + stage / drain controller + ot_hdc_v41x_vec + the banked local memory: G0 A 2^17, G1 B+O 2^16, G2 C+R 2^15, G3 D 2^14, GS STREAM 2^16 words, ot_sram_1r1w_{1024,256,128}x256 macros); sfu = the same unit GLU 1 (SFU.GLU) at 2^14 words a group, no STREAM region; hc = HC.HC_MIX / ROWS / POST (below).  Every record bit and VM packet bit is bound; The SU STREAM output drives hfd_hgi_am's logit stream (hgi_am_s_*, gated by its am_rdy: hgi_am_rdy).  OPEN: the SU STREAM input s0 waits for the SM x-load / pub peers in the VM block; hc = ot_hgi_hc_die: the unit + its HBM weight lane client (ot_hgi_hbm_rd_client -> die nets hgi_hcm_q / hgi_hcm_r -> ot_hgi_hbm_rd_server on kport lane 3 of the loader, XLANE 1), weight windows in macros (WMACRO 1).
module hfd_hgi_su (
    input wire [0:0] ck,
    input wire [0:0] f_am_rdy,
    input wire [938:0] f_hgi_cmdproc_hc,
    input wire [1173:0] f_hgi_cmdproc_sfu,
    input wire [2197:0] f_hgi_cmdproc_su,
    input wire [256:0] f_hgi_hcmr,
    input wire [273:0] f_hgi_vmr_hc,
    input wire [273:0] f_hgi_vmr_sfu,
    input wire [273:0] f_hgi_vmr_su,
    input wire [0:0] rst,
    output wire [255:0] t_am_in_bias,
    output wire [0:0] t_am_in_bias_en,
    output wire [0:0] t_am_in_last,
    output wire [7:0] t_am_in_mask,
    output wire [0:0] t_am_in_v,
    output wire [255:0] t_am_in_vals,
    output wire [2:0] t_hgi_cmdproc_hc,
    output wire [2:0] t_hgi_cmdproc_sfu,
    output wire [2:0] t_hgi_cmdproc_su,
    output wire [37:0] t_hgi_hcmq,
    output wire [337:0] t_hgi_vmq_hc,
    output wire [337:0] t_hgi_vmq_sfu,
    output wire [337:0] t_hgi_vmq_su
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [0:0] i0_f_am_rdy; always @(posedge clk) i0_f_am_rdy <= f_am_rdy;
    reg [0:0] i1_f_am_rdy; always @(posedge clk) i1_f_am_rdy <= i0_f_am_rdy;
    reg [0:0] i_f_am_rdy; always @(posedge clk) i_f_am_rdy <= i1_f_am_rdy;
    reg [938:0] i0_f_hgi_cmdproc_hc; always @(posedge clk) i0_f_hgi_cmdproc_hc <= f_hgi_cmdproc_hc;
    reg [938:0] i1_f_hgi_cmdproc_hc; always @(posedge clk) i1_f_hgi_cmdproc_hc <= i0_f_hgi_cmdproc_hc;
    reg [938:0] i_f_hgi_cmdproc_hc; always @(posedge clk) i_f_hgi_cmdproc_hc <= i1_f_hgi_cmdproc_hc;
    reg [1173:0] i0_f_hgi_cmdproc_sfu; always @(posedge clk) i0_f_hgi_cmdproc_sfu <= f_hgi_cmdproc_sfu;
    reg [1173:0] i1_f_hgi_cmdproc_sfu; always @(posedge clk) i1_f_hgi_cmdproc_sfu <= i0_f_hgi_cmdproc_sfu;
    reg [1173:0] i_f_hgi_cmdproc_sfu; always @(posedge clk) i_f_hgi_cmdproc_sfu <= i1_f_hgi_cmdproc_sfu;
    reg [2197:0] i0_f_hgi_cmdproc_su; always @(posedge clk) i0_f_hgi_cmdproc_su <= f_hgi_cmdproc_su;
    reg [2197:0] i1_f_hgi_cmdproc_su; always @(posedge clk) i1_f_hgi_cmdproc_su <= i0_f_hgi_cmdproc_su;
    reg [2197:0] i_f_hgi_cmdproc_su; always @(posedge clk) i_f_hgi_cmdproc_su <= i1_f_hgi_cmdproc_su;
    reg [256:0] i0_f_hgi_hcmr; always @(posedge clk) i0_f_hgi_hcmr <= f_hgi_hcmr;
    reg [256:0] i1_f_hgi_hcmr; always @(posedge clk) i1_f_hgi_hcmr <= i0_f_hgi_hcmr;
    reg [256:0] i_f_hgi_hcmr; always @(posedge clk) i_f_hgi_hcmr <= i1_f_hgi_hcmr;
    reg [273:0] i0_f_hgi_vmr_hc; always @(posedge clk) i0_f_hgi_vmr_hc <= f_hgi_vmr_hc;
    reg [273:0] i1_f_hgi_vmr_hc; always @(posedge clk) i1_f_hgi_vmr_hc <= i0_f_hgi_vmr_hc;
    reg [273:0] i_f_hgi_vmr_hc; always @(posedge clk) i_f_hgi_vmr_hc <= i1_f_hgi_vmr_hc;
    reg [273:0] i0_f_hgi_vmr_sfu; always @(posedge clk) i0_f_hgi_vmr_sfu <= f_hgi_vmr_sfu;
    reg [273:0] i1_f_hgi_vmr_sfu; always @(posedge clk) i1_f_hgi_vmr_sfu <= i0_f_hgi_vmr_sfu;
    reg [273:0] i_f_hgi_vmr_sfu; always @(posedge clk) i_f_hgi_vmr_sfu <= i1_f_hgi_vmr_sfu;
    reg [273:0] i0_f_hgi_vmr_su; always @(posedge clk) i0_f_hgi_vmr_su <= f_hgi_vmr_su;
    reg [273:0] i1_f_hgi_vmr_su; always @(posedge clk) i1_f_hgi_vmr_su <= i0_f_hgi_vmr_su;
    reg [273:0] i_f_hgi_vmr_su; always @(posedge clk) i_f_hgi_vmr_su <= i1_f_hgi_vmr_su;
    wire [0:0] w_su_clk;
    wire [0:0] w_su_rst_n;
    wire [0:0] w_su_rec_v;
    wire [0:0] w_su_rec_rdy;
    wire [127:0] w_su_rec_hdr;
    wire [255:0] w_su_rec_sut;
    wire [255:0] w_su_rec_a;
    wire [255:0] w_su_rec_b;
    wire [255:0] w_su_rec_c;
    wire [255:0] w_su_rec_d;
    wire [255:0] w_su_rec_o;
    wire [255:0] w_su_rec_r;
    wire [255:0] w_su_rec_i;
    wire [20:0] w_su_rec_n_a;
    wire [0:0] w_su_rec_done;
    wire [0:0] w_su_rec_fault;
    wire [0:0] w_su_halted;
    wire [337:0] w_su_vmq;
    wire [273:0] w_su_vmr;
    wire [0:0] w_su_s0_v;
    wire [19:0] w_su_s0_idx;
    wire [31:0] w_su_s0_data;
    wire [522:0] w_su_am_stream;
    wire [0:0] w_su_am_rdy;
    wire [0:0] w_sfu_clk;
    wire [0:0] w_sfu_rst_n;
    wire [0:0] w_sfu_rec_v;
    wire [0:0] w_sfu_rec_rdy;
    wire [127:0] w_sfu_rec_hdr;
    wire [255:0] w_sfu_rec_sut;
    wire [255:0] w_sfu_rec_a;
    wire [255:0] w_sfu_rec_b;
    wire [255:0] w_sfu_rec_c;
    wire [255:0] w_sfu_rec_d;
    wire [255:0] w_sfu_rec_o;
    wire [255:0] w_sfu_rec_r;
    wire [255:0] w_sfu_rec_i;
    wire [20:0] w_sfu_rec_n_a;
    wire [0:0] w_sfu_rec_done;
    wire [0:0] w_sfu_rec_fault;
    wire [0:0] w_sfu_halted;
    wire [337:0] w_sfu_vmq;
    wire [273:0] w_sfu_vmr;
    wire [0:0] w_sfu_s0_v;
    wire [19:0] w_sfu_s0_idx;
    wire [31:0] w_sfu_s0_data;
    wire [522:0] w_sfu_am_stream;
    wire [0:0] w_sfu_am_rdy;
    wire [0:0] w_hc_clk;
    wire [0:0] w_hc_rst_n;
    wire [0:0] w_hc_rec_v;
    wire [0:0] w_hc_rec_rdy;
    wire [127:0] w_hc_rec_hdr;
    wire [255:0] w_hc_rec_a;
    wire [255:0] w_hc_rec_b;
    wire [255:0] w_hc_rec_o;
    wire [20:0] w_hc_rec_n_a;
    wire [20:0] w_hc_rec_n_o;
    wire [0:0] w_hc_rec_done;
    wire [0:0] w_hc_rec_fault;
    wire [0:0] w_hc_halted;
    wire [337:0] w_hc_vmq;
    wire [273:0] w_hc_vmr;
    wire [37:0] w_hc_xq;
    wire [256:0] w_hc_xr;
    assign w_su_clk = {1{clk}};
    assign w_su_rst_n = {1{rst_n}};
    assign w_su_rec_v = {i_f_hgi_cmdproc_su[0:0]};
    assign w_su_rec_hdr = {i_f_hgi_cmdproc_su[128:1]};
    assign w_su_rec_sut = {i_f_hgi_cmdproc_su[384:129]};
    assign w_su_rec_a = {i_f_hgi_cmdproc_su[640:385]};
    assign w_su_rec_b = {i_f_hgi_cmdproc_su[896:641]};
    assign w_su_rec_c = {i_f_hgi_cmdproc_su[1152:897]};
    assign w_su_rec_d = {i_f_hgi_cmdproc_su[1408:1153]};
    assign w_su_rec_o = {i_f_hgi_cmdproc_su[1664:1409]};
    assign w_su_rec_r = {i_f_hgi_cmdproc_su[1920:1665]};
    assign w_su_rec_i = {i_f_hgi_cmdproc_su[2176:1921]};
    assign w_su_rec_n_a = {i_f_hgi_cmdproc_su[2197:2177]};
    assign w_su_vmr = {i_f_hgi_vmr_su[273:0]};
    assign w_su_s0_v = 1'd0;
    assign w_su_s0_idx = 20'd0;
    assign w_su_s0_data = 32'd0;
    assign w_su_am_rdy = {i_f_am_rdy[0:0]};
    ot_hgi_su_unit #(.N(16), .M(8), .LV(6), .LWB(17), .LG1(16), .LG2(15), .LG3(14), .SLB(16), .GLU(0), .MACRO(1)) u_su (.clk(w_su_clk), .rst_n(w_su_rst_n), .rec_v(w_su_rec_v), .rec_rdy(w_su_rec_rdy), .rec_hdr(w_su_rec_hdr), .rec_sut(w_su_rec_sut), .rec_a(w_su_rec_a), .rec_b(w_su_rec_b), .rec_c(w_su_rec_c), .rec_d(w_su_rec_d), .rec_o(w_su_rec_o), .rec_r(w_su_rec_r), .rec_i(w_su_rec_i), .rec_n_a(w_su_rec_n_a), .rec_done(w_su_rec_done), .rec_fault(w_su_rec_fault), .halted(w_su_halted), .vmq(w_su_vmq), .vmr(w_su_vmr), .s0_v(w_su_s0_v), .s0_idx(w_su_s0_idx), .s0_data(w_su_s0_data), .am_stream(w_su_am_stream), .am_rdy(w_su_am_rdy));
    assign w_sfu_clk = {1{clk}};
    assign w_sfu_rst_n = {1{rst_n}};
    assign w_sfu_rec_v = {i_f_hgi_cmdproc_sfu[0:0]};
    assign w_sfu_rec_hdr = {i_f_hgi_cmdproc_sfu[128:1]};
    assign w_sfu_rec_sut = 256'd0;
    assign w_sfu_rec_a = {i_f_hgi_cmdproc_sfu[384:129]};
    assign w_sfu_rec_b = {i_f_hgi_cmdproc_sfu[640:385]};
    assign w_sfu_rec_c = {i_f_hgi_cmdproc_sfu[896:641]};
    assign w_sfu_rec_d = 256'd0;
    assign w_sfu_rec_o = {i_f_hgi_cmdproc_sfu[1152:897]};
    assign w_sfu_rec_r = 256'd0;
    assign w_sfu_rec_i = 256'd0;
    assign w_sfu_rec_n_a = {i_f_hgi_cmdproc_sfu[1173:1153]};
    assign w_sfu_vmr = {i_f_hgi_vmr_sfu[273:0]};
    assign w_sfu_s0_v = 1'd0;
    assign w_sfu_s0_idx = 20'd0;
    assign w_sfu_s0_data = 32'd0;
    assign w_sfu_am_rdy = 1'd0;
    ot_hgi_su_unit #(.N(16), .M(8), .LV(6), .LWB(14), .LG1(14), .LG2(14), .LG3(14), .SLB(4), .GLU(1), .MACRO(1)) u_sfu (.clk(w_sfu_clk), .rst_n(w_sfu_rst_n), .rec_v(w_sfu_rec_v), .rec_rdy(w_sfu_rec_rdy), .rec_hdr(w_sfu_rec_hdr), .rec_sut(w_sfu_rec_sut), .rec_a(w_sfu_rec_a), .rec_b(w_sfu_rec_b), .rec_c(w_sfu_rec_c), .rec_d(w_sfu_rec_d), .rec_o(w_sfu_rec_o), .rec_r(w_sfu_rec_r), .rec_i(w_sfu_rec_i), .rec_n_a(w_sfu_rec_n_a), .rec_done(w_sfu_rec_done), .rec_fault(w_sfu_rec_fault), .halted(w_sfu_halted), .vmq(w_sfu_vmq), .vmr(w_sfu_vmr), .s0_v(w_sfu_s0_v), .s0_idx(w_sfu_s0_idx), .s0_data(w_sfu_s0_data), .am_stream(w_sfu_am_stream), .am_rdy(w_sfu_am_rdy));
    assign w_hc_clk = {1{clk}};
    assign w_hc_rst_n = {1{rst_n}};
    assign w_hc_rec_v = {i_f_hgi_cmdproc_hc[0:0]};
    assign w_hc_rec_hdr = {i_f_hgi_cmdproc_hc[128:1]};
    assign w_hc_rec_a = {i_f_hgi_cmdproc_hc[384:129]};
    assign w_hc_rec_b = {i_f_hgi_cmdproc_hc[640:385]};
    assign w_hc_rec_o = {i_f_hgi_cmdproc_hc[896:641]};
    assign w_hc_rec_n_a = {i_f_hgi_cmdproc_hc[917:897]};
    assign w_hc_rec_n_o = {i_f_hgi_cmdproc_hc[938:918]};
    assign w_hc_vmr = {i_f_hgi_vmr_hc[273:0]};
    assign w_hc_xr = {i_f_hgi_hcmr[256:0]};
    ot_hgi_hc_die #(.W(32), .RMAX(128), .WMACRO(1)) u_hc (.clk(w_hc_clk), .rst_n(w_hc_rst_n), .rec_v(w_hc_rec_v), .rec_rdy(w_hc_rec_rdy), .rec_hdr(w_hc_rec_hdr), .rec_a(w_hc_rec_a), .rec_b(w_hc_rec_b), .rec_o(w_hc_rec_o), .rec_n_a(w_hc_rec_n_a), .rec_n_o(w_hc_rec_n_o), .rec_done(w_hc_rec_done), .rec_fault(w_hc_rec_fault), .halted(w_hc_halted), .vmq(w_hc_vmq), .vmr(w_hc_vmr), .xq(w_hc_xq), .xr(w_hc_xr));
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_su_halted
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_su_halted[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_sfu_halted
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_sfu_halted[k]), .q());
    end
    for (genvar k = 0; k < 523; k = k + 1) begin : g_sink_w_sfu_am_stream
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_sfu_am_stream[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_hc_halted
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_hc_halted[k]), .q());
    end
    wire [255:0] od_t_am_in_bias = {w_su_am_stream[521:266]};
    wire [255:0] o_t_am_in_bias;
    for (genvar k = 0; k < 256; k = k + 1) begin : g_o_t_am_in_bias
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_am_in_bias[k]), .q(o_t_am_in_bias[k]));
    end
    assign t_am_in_bias[255:0] = o_t_am_in_bias[255:0];
    wire [0:0] od_t_am_in_bias_en = {w_su_am_stream[522:522]};
    wire [0:0] o_t_am_in_bias_en;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_t_am_in_bias_en
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_am_in_bias_en[k]), .q(o_t_am_in_bias_en[k]));
    end
    assign t_am_in_bias_en[0:0] = o_t_am_in_bias_en[0:0];
    wire [0:0] od_t_am_in_last = {w_su_am_stream[1:1]};
    wire [0:0] o_t_am_in_last;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_t_am_in_last
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_am_in_last[k]), .q(o_t_am_in_last[k]));
    end
    assign t_am_in_last[0:0] = o_t_am_in_last[0:0];
    wire [7:0] od_t_am_in_mask = {w_su_am_stream[9:2]};
    wire [7:0] o_t_am_in_mask;
    for (genvar k = 0; k < 8; k = k + 1) begin : g_o_t_am_in_mask
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_am_in_mask[k]), .q(o_t_am_in_mask[k]));
    end
    assign t_am_in_mask[7:0] = o_t_am_in_mask[7:0];
    wire [0:0] od_t_am_in_v = {w_su_am_stream[0:0]};
    wire [0:0] o_t_am_in_v;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_t_am_in_v
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_am_in_v[k]), .q(o_t_am_in_v[k]));
    end
    assign t_am_in_v[0:0] = o_t_am_in_v[0:0];
    wire [255:0] od_t_am_in_vals = {w_su_am_stream[265:10]};
    wire [255:0] o_t_am_in_vals;
    for (genvar k = 0; k < 256; k = k + 1) begin : g_o_t_am_in_vals
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_am_in_vals[k]), .q(o_t_am_in_vals[k]));
    end
    assign t_am_in_vals[255:0] = o_t_am_in_vals[255:0];
    wire [2:0] od_t_hgi_cmdproc_hc = {w_hc_rec_fault[0:0], w_hc_rec_done[0:0], w_hc_rec_rdy[0:0]};
    wire [2:0] o_t_hgi_cmdproc_hc;
    for (genvar k = 0; k < 3; k = k + 1) begin : g_o_t_hgi_cmdproc_hc
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_cmdproc_hc[k]), .q(o_t_hgi_cmdproc_hc[k]));
    end
    assign t_hgi_cmdproc_hc[2:0] = o_t_hgi_cmdproc_hc[2:0];
    wire [2:0] od_t_hgi_cmdproc_sfu = {w_sfu_rec_fault[0:0], w_sfu_rec_done[0:0], w_sfu_rec_rdy[0:0]};
    wire [2:0] o_t_hgi_cmdproc_sfu;
    for (genvar k = 0; k < 3; k = k + 1) begin : g_o_t_hgi_cmdproc_sfu
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_cmdproc_sfu[k]), .q(o_t_hgi_cmdproc_sfu[k]));
    end
    assign t_hgi_cmdproc_sfu[2:0] = o_t_hgi_cmdproc_sfu[2:0];
    wire [2:0] od_t_hgi_cmdproc_su = {w_su_rec_fault[0:0], w_su_rec_done[0:0], w_su_rec_rdy[0:0]};
    wire [2:0] o_t_hgi_cmdproc_su;
    for (genvar k = 0; k < 3; k = k + 1) begin : g_o_t_hgi_cmdproc_su
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_cmdproc_su[k]), .q(o_t_hgi_cmdproc_su[k]));
    end
    assign t_hgi_cmdproc_su[2:0] = o_t_hgi_cmdproc_su[2:0];
    wire [37:0] od_t_hgi_hcmq = {w_hc_xq[37:0]};
    wire [37:0] o_t_hgi_hcmq;
    for (genvar k = 0; k < 38; k = k + 1) begin : g_o_t_hgi_hcmq
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_hcmq[k]), .q(o_t_hgi_hcmq[k]));
    end
    assign t_hgi_hcmq[37:0] = o_t_hgi_hcmq[37:0];
    wire [337:0] od_t_hgi_vmq_hc = {w_hc_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq_hc;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq_hc
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_vmq_hc[k]), .q(o_t_hgi_vmq_hc[k]));
    end
    assign t_hgi_vmq_hc[337:0] = o_t_hgi_vmq_hc[337:0];
    wire [337:0] od_t_hgi_vmq_sfu = {w_sfu_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq_sfu;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq_sfu
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_vmq_sfu[k]), .q(o_t_hgi_vmq_sfu[k]));
    end
    assign t_hgi_vmq_sfu[337:0] = o_t_hgi_vmq_sfu[337:0];
    wire [337:0] od_t_hgi_vmq_su = {w_su_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq_su;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq_su
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_hgi_vmq_su[k]), .q(o_t_hgi_vmq_su[k]));
    end
    assign t_hgi_vmq_su[337:0] = o_t_hgi_vmq_su[337:0];
endmodule
