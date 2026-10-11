// hfd_hc: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 HC die master (hgi-1010/c2, AUDIT N2): ot_hgi_hc_unit (W 32, RMAX 128, weight windows / x memory in macros, PMAX 8) bound to hgi_hc_cmd 939 / ret 3 and the VM packet client hgi_vmq_hc / vmr. Weight source = VM aperture (N3, open: d's window port); lgW taps open until HC is a wide client.
module hfd_hc (
    input wire [0:0] ck0,
    input wire [0:0] ck1,
    input wire [0:0] ck2,
    input wire [0:0] ck3,
    input wire [0:0] ck4,
    input wire [0:0] ck5,
    input wire [0:0] ck6,
    input wire [0:0] ck7,
    input wire [938:0] f_hgi_cmdproc,
    input wire [273:0] f_hgi_vmr,
    input wire [8256:0] f_lgW_rdn,
    input wire [64:0] f_lgW_wdn,
    input wire [1023:0] f_sfu,
    input wire [0:0] rst,
    output wire [2:0] t_hgi_cmdproc,
    output wire [337:0] t_hgi_vmq,
    output wire [512:0] t_lgW_rup,
    output wire [8960:0] t_lgW_wup,
    output wire [1023:0] t_sfu
);
    wire clk = ck0[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [0:0] i0_ck1; always @(posedge clk) i0_ck1 <= ck1;
    reg [0:0] i_ck1; always @(posedge clk) i_ck1 <= i0_ck1;
    reg [0:0] i0_ck2; always @(posedge clk) i0_ck2 <= ck2;
    reg [0:0] i_ck2; always @(posedge clk) i_ck2 <= i0_ck2;
    reg [0:0] i0_ck3; always @(posedge clk) i0_ck3 <= ck3;
    reg [0:0] i_ck3; always @(posedge clk) i_ck3 <= i0_ck3;
    reg [0:0] i0_ck4; always @(posedge clk) i0_ck4 <= ck4;
    reg [0:0] i_ck4; always @(posedge clk) i_ck4 <= i0_ck4;
    reg [0:0] i0_ck5; always @(posedge clk) i0_ck5 <= ck5;
    reg [0:0] i_ck5; always @(posedge clk) i_ck5 <= i0_ck5;
    reg [0:0] i0_ck6; always @(posedge clk) i0_ck6 <= ck6;
    reg [0:0] i_ck6; always @(posedge clk) i_ck6 <= i0_ck6;
    reg [0:0] i0_ck7; always @(posedge clk) i0_ck7 <= ck7;
    reg [0:0] i_ck7; always @(posedge clk) i_ck7 <= i0_ck7;
    reg [938:0] i0_f_hgi_cmdproc; always @(posedge clk) i0_f_hgi_cmdproc <= f_hgi_cmdproc;
    reg [938:0] i_f_hgi_cmdproc; always @(posedge clk) i_f_hgi_cmdproc <= i0_f_hgi_cmdproc;
    reg [273:0] i0_f_hgi_vmr; always @(posedge clk) i0_f_hgi_vmr <= f_hgi_vmr;
    reg [273:0] i_f_hgi_vmr; always @(posedge clk) i_f_hgi_vmr <= i0_f_hgi_vmr;
    reg [8256:0] i0_f_lgW_rdn; always @(posedge clk) i0_f_lgW_rdn <= f_lgW_rdn;
    reg [8256:0] i_f_lgW_rdn; always @(posedge clk) i_f_lgW_rdn <= i0_f_lgW_rdn;
    reg [64:0] i0_f_lgW_wdn; always @(posedge clk) i0_f_lgW_wdn <= f_lgW_wdn;
    reg [64:0] i_f_lgW_wdn; always @(posedge clk) i_f_lgW_wdn <= i0_f_lgW_wdn;
    reg [1023:0] i0_f_sfu; always @(posedge clk) i0_f_sfu <= f_sfu;
    reg [1023:0] i_f_sfu; always @(posedge clk) i_f_sfu <= i0_f_sfu;
    wire [0:0] w_u_clk;
    wire [0:0] w_u_rst_n;
    wire [31:0] w_u_cfg_norm_eps;
    wire [0:0] w_u_rec_v;
    wire [0:0] w_u_rec_rdy;
    wire [127:0] w_u_rec_hdr;
    wire [255:0] w_u_rec_a;
    wire [255:0] w_u_rec_b;
    wire [255:0] w_u_rec_o;
    wire [20:0] w_u_rec_n_a;
    wire [20:0] w_u_rec_n_o;
    wire [0:0] w_u_rec_done;
    wire [0:0] w_u_rec_fault;
    wire [0:0] w_u_halted;
    wire [337:0] w_u_vmq;
    wire [273:0] w_u_vmr;
    wire [0:0] w_u_hq_v;
    wire [0:0] w_u_hq_rdy;
    wire [34:0] w_u_hq_addr;
    wire [2:0] w_u_hq_len;
    wire [10:0] w_u_hq_tag;
    wire [0:0] w_u_hr_v;
    wire [10:0] w_u_hr_tag;
    wire [1:0] w_u_hr_beat;
    wire [255:0] w_u_hr_data;
    assign w_u_clk = {1{clk}};
    assign w_u_rst_n = {1{rst_n}};
    assign w_u_cfg_norm_eps = 32'd897988541;
    assign w_u_rec_v = {i_f_hgi_cmdproc[0:0]};
    assign w_u_rec_hdr = {i_f_hgi_cmdproc[128:1]};
    assign w_u_rec_a = {i_f_hgi_cmdproc[384:129]};
    assign w_u_rec_b = {i_f_hgi_cmdproc[640:385]};
    assign w_u_rec_o = {i_f_hgi_cmdproc[896:641]};
    assign w_u_rec_n_a = {i_f_hgi_cmdproc[917:897]};
    assign w_u_rec_n_o = {i_f_hgi_cmdproc[938:918]};
    assign w_u_vmr = {i_f_hgi_vmr[273:0]};
    assign w_u_hq_rdy = 1'd0;
    assign w_u_hr_v = 1'd0;
    assign w_u_hr_tag = 11'd0;
    assign w_u_hr_beat = 2'd0;
    assign w_u_hr_data = 256'd0;
    ot_hgi_hc_unit #(.W(32), .RMAX(128), .WMACRO(1), .XMACRO(1), .PMAX(8)) u_u (.clk(w_u_clk), .rst_n(w_u_rst_n), .cfg_norm_eps(w_u_cfg_norm_eps), .rec_v(w_u_rec_v), .rec_rdy(w_u_rec_rdy), .rec_hdr(w_u_rec_hdr), .rec_a(w_u_rec_a), .rec_b(w_u_rec_b), .rec_o(w_u_rec_o), .rec_n_a(w_u_rec_n_a), .rec_n_o(w_u_rec_n_o), .rec_done(w_u_rec_done), .rec_fault(w_u_rec_fault), .halted(w_u_halted), .vmq(w_u_vmq), .vmr(w_u_vmr), .hq_v(w_u_hq_v), .hq_rdy(w_u_hq_rdy), .hq_addr(w_u_hq_addr), .hq_len(w_u_hq_len), .hq_tag(w_u_hq_tag), .hr_v(w_u_hr_v), .hr_tag(w_u_hr_tag), .hr_beat(w_u_hr_beat), .hr_data(w_u_hr_data));
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_u_halted
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_u_halted[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_u_hq_v
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_u_hq_v[k]), .q());
    end
    for (genvar k = 0; k < 35; k = k + 1) begin : g_sink_w_u_hq_addr
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_u_hq_addr[k]), .q());
    end
    for (genvar k = 0; k < 3; k = k + 1) begin : g_sink_w_u_hq_len
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_u_hq_len[k]), .q());
    end
    for (genvar k = 0; k < 11; k = k + 1) begin : g_sink_w_u_hq_tag
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_u_hq_tag[k]), .q());
    end
    wire [2:0] od_t_hgi_cmdproc = {w_u_rec_fault[0:0], w_u_rec_done[0:0], w_u_rec_rdy[0:0]};
    wire [2:0] o_t_hgi_cmdproc;
    for (genvar k = 0; k < 3; k = k + 1) begin : g_o_t_hgi_cmdproc
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_hgi_cmdproc[k]), .q(o_t_hgi_cmdproc[k]));
    end
    assign t_hgi_cmdproc[2:0] = o_t_hgi_cmdproc[2:0];
    wire [337:0] od_t_hgi_vmq = {w_u_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_hgi_vmq[k]), .q(o_t_hgi_vmq[k]));
    end
    assign t_hgi_vmq[337:0] = o_t_hgi_vmq[337:0];
    wire [512:0] od_t_lgW_rup = {513'd0};
    wire [512:0] o_t_lgW_rup;
    for (genvar k = 0; k < 513; k = k + 1) begin : g_o_t_lgW_rup
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_lgW_rup[k]), .q(o_t_lgW_rup[k]));
    end
    assign t_lgW_rup[512:0] = o_t_lgW_rup[512:0];
    wire [8960:0] od_t_lgW_wup = {8961'd0};
    wire [8960:0] o_t_lgW_wup;
    for (genvar k = 0; k < 8961; k = k + 1) begin : g_o_t_lgW_wup
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_lgW_wup[k]), .q(o_t_lgW_wup[k]));
    end
    assign t_lgW_wup[8960:0] = o_t_lgW_wup[8960:0];
    wire [1023:0] od_t_sfu = {1024'd0};
    wire [1023:0] o_t_sfu;
    for (genvar k = 0; k < 1024; k = k + 1) begin : g_o_t_sfu
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_sfu[k]), .q(o_t_sfu[k]));
    end
    assign t_sfu[1023:0] = o_t_sfu[1023:0];
endmodule
