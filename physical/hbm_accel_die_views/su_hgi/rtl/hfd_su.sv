// hfd_su: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI-1 SU die master (hgi-1010/c2, AUDIT N1): ot_hgi_su_unit WIDE (production engine: 32-lane VM stage / drain on the lgW lane group, slot 0) bound to the record bus hgi_su_cmd 2198 / ret 3 (cmdproc t_hgi_su), the VM packet client hgi_vmq_su 338 / vmr 274 and the full-width lgW station tap (hb_stn_lgW_su, E face). lgW tap packing (LSB first) = ot_hgi_vm_lanestation local side: rup {wrq 32x16, rg_req} | rdn {wrr 32x257, wrq_cr 32, rg_gnt} | wup {wwq 32x280, wg_req} | wdn {wwq_done 32, wwq_cr 32, wg_gnt}; the station view must use the same order. WIDE = 1 today; b's ctlx (WIDE = 2, on d's lane-local lmem) is port-identical and replaces it by the param when merged. LQ 32 = the lgW chain contract.
module hfd_su (
    input wire [1057:0] a,
    input wire [0:0] ck0,
    input wire [0:0] ck1,
    input wire [0:0] ck2,
    input wire [0:0] ck3,
    input wire [0:0] ck4,
    input wire [0:0] ck5,
    input wire [0:0] ck6,
    input wire [0:0] ck7,
    input wire [619:0] f_coll,
    input wire [2197:0] f_hgi_cmdproc,
    input wire [79:0] f_hgi_vmaddr,
    input wire [273:0] f_hgi_vmr,
    input wire [8256:0] f_lgW_rdn,
    input wire [64:0] f_lgW_wdn,
    input wire [1023:0] f_sfu,
    input wire [1023:0] f_su_ew,
    input wire [1023:0] f_su_ns,
    input wire [2047:0] f_vm,
    input wire [2164:0] r,
    input wire [0:0] rst,
    output wire [1023:0] t_coll,
    output wire [2:0] t_hgi_cmdproc,
    output wire [337:0] t_hgi_vmq,
    output wire [512:0] t_lgW_rup,
    output wire [8960:0] t_lgW_wup,
    output wire [1023:0] t_sfu,
    output wire [1023:0] t_su_ew,
    output wire [1023:0] t_su_ns,
    output wire [2047:0] t_vm
);
    wire clk = ck0[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [1057:0] i0_a; always @(posedge clk) i0_a <= a;
    reg [1057:0] i_a; always @(posedge clk) i_a <= i0_a;
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
    reg [619:0] i0_f_coll; always @(posedge clk) i0_f_coll <= f_coll;
    reg [619:0] i_f_coll; always @(posedge clk) i_f_coll <= i0_f_coll;
    reg [2197:0] i0_f_hgi_cmdproc; always @(posedge clk) i0_f_hgi_cmdproc <= f_hgi_cmdproc;
    reg [2197:0] i_f_hgi_cmdproc; always @(posedge clk) i_f_hgi_cmdproc <= i0_f_hgi_cmdproc;
    reg [79:0] i0_f_hgi_vmaddr; always @(posedge clk) i0_f_hgi_vmaddr <= f_hgi_vmaddr;
    reg [79:0] i_f_hgi_vmaddr; always @(posedge clk) i_f_hgi_vmaddr <= i0_f_hgi_vmaddr;
    reg [273:0] i0_f_hgi_vmr; always @(posedge clk) i0_f_hgi_vmr <= f_hgi_vmr;
    reg [273:0] i_f_hgi_vmr; always @(posedge clk) i_f_hgi_vmr <= i0_f_hgi_vmr;
    reg [8256:0] i0_f_lgW_rdn; always @(posedge clk) i0_f_lgW_rdn <= f_lgW_rdn;
    reg [8256:0] i_f_lgW_rdn; always @(posedge clk) i_f_lgW_rdn <= i0_f_lgW_rdn;
    reg [64:0] i0_f_lgW_wdn; always @(posedge clk) i0_f_lgW_wdn <= f_lgW_wdn;
    reg [64:0] i_f_lgW_wdn; always @(posedge clk) i_f_lgW_wdn <= i0_f_lgW_wdn;
    reg [1023:0] i0_f_sfu; always @(posedge clk) i0_f_sfu <= f_sfu;
    reg [1023:0] i_f_sfu; always @(posedge clk) i_f_sfu <= i0_f_sfu;
    reg [1023:0] i0_f_su_ew; always @(posedge clk) i0_f_su_ew <= f_su_ew;
    reg [1023:0] i_f_su_ew; always @(posedge clk) i_f_su_ew <= i0_f_su_ew;
    reg [1023:0] i0_f_su_ns; always @(posedge clk) i0_f_su_ns <= f_su_ns;
    reg [1023:0] i_f_su_ns; always @(posedge clk) i_f_su_ns <= i0_f_su_ns;
    reg [2047:0] i0_f_vm; always @(posedge clk) i0_f_vm <= f_vm;
    reg [2047:0] i_f_vm; always @(posedge clk) i_f_vm <= i0_f_vm;
    reg [2164:0] i0_r; always @(posedge clk) i0_r <= r;
    reg [2164:0] i_r; always @(posedge clk) i_r <= i0_r;
    wire [0:0] w_u_clk;
    wire [0:0] w_u_rst_n;
    wire [0:0] w_u_rec_v;
    wire [0:0] w_u_rec_rdy;
    wire [127:0] w_u_rec_hdr;
    wire [255:0] w_u_rec_sut;
    wire [255:0] w_u_rec_a;
    wire [255:0] w_u_rec_b;
    wire [255:0] w_u_rec_c;
    wire [255:0] w_u_rec_d;
    wire [255:0] w_u_rec_o;
    wire [255:0] w_u_rec_r;
    wire [255:0] w_u_rec_i;
    wire [20:0] w_u_rec_n_a;
    wire [0:0] w_u_rec_done;
    wire [0:0] w_u_rec_fault;
    wire [0:0] w_u_halted;
    wire [337:0] w_u_vmq;
    wire [273:0] w_u_vmr;
    wire [0:0] w_u_s0_v;
    wire [19:0] w_u_s0_idx;
    wire [31:0] w_u_s0_data;
    wire [522:0] w_u_am_stream;
    wire [0:0] w_u_am_rdy;
    wire [511:0] w_u_wrq;
    wire [31:0] w_u_wrq_cr;
    wire [8223:0] w_u_wrr;
    wire [8959:0] w_u_wwq;
    wire [31:0] w_u_wwq_cr;
    wire [31:0] w_u_wwq_done;
    wire [0:0] w_u_rg_req;
    wire [0:0] w_u_rg_gnt;
    wire [0:0] w_u_wg_req;
    wire [0:0] w_u_wg_gnt;
    assign w_u_clk = {1{clk}};
    assign w_u_rst_n = {1{rst_n}};
    assign w_u_rec_v = {i_f_hgi_cmdproc[0:0]};
    assign w_u_rec_hdr = {i_f_hgi_cmdproc[128:1]};
    assign w_u_rec_sut = {i_f_hgi_cmdproc[384:129]};
    assign w_u_rec_a = {i_f_hgi_cmdproc[640:385]};
    assign w_u_rec_b = {i_f_hgi_cmdproc[896:641]};
    assign w_u_rec_c = {i_f_hgi_cmdproc[1152:897]};
    assign w_u_rec_d = {i_f_hgi_cmdproc[1408:1153]};
    assign w_u_rec_o = {i_f_hgi_cmdproc[1664:1409]};
    assign w_u_rec_r = {i_f_hgi_cmdproc[1920:1665]};
    assign w_u_rec_i = {i_f_hgi_cmdproc[2176:1921]};
    assign w_u_rec_n_a = {i_f_hgi_cmdproc[2197:2177]};
    assign w_u_vmr = {i_f_hgi_vmr[273:0]};
    assign w_u_s0_v = 1'd0;
    assign w_u_s0_idx = 20'd0;
    assign w_u_s0_data = 32'd0;
    assign w_u_am_rdy = 1'd0;
    assign w_u_wrq_cr = {i_f_lgW_rdn[32:1]};
    assign w_u_wrr = {i_f_lgW_rdn[8256:33]};
    assign w_u_wwq_cr = {i_f_lgW_wdn[32:1]};
    assign w_u_wwq_done = {i_f_lgW_wdn[64:33]};
    assign w_u_rg_gnt = {i_f_lgW_rdn[0:0]};
    assign w_u_wg_gnt = {i_f_lgW_wdn[0:0]};
    ot_hgi_su_unit #(.N(512), .M(128), .LV(7), .LWB(18), .GLU(0), .WIDE(1), .LQ(32)) u_u (.clk(w_u_clk), .rst_n(w_u_rst_n), .rec_v(w_u_rec_v), .rec_rdy(w_u_rec_rdy), .rec_hdr(w_u_rec_hdr), .rec_sut(w_u_rec_sut), .rec_a(w_u_rec_a), .rec_b(w_u_rec_b), .rec_c(w_u_rec_c), .rec_d(w_u_rec_d), .rec_o(w_u_rec_o), .rec_r(w_u_rec_r), .rec_i(w_u_rec_i), .rec_n_a(w_u_rec_n_a), .rec_done(w_u_rec_done), .rec_fault(w_u_rec_fault), .halted(w_u_halted), .vmq(w_u_vmq), .vmr(w_u_vmr), .s0_v(w_u_s0_v), .s0_idx(w_u_s0_idx), .s0_data(w_u_s0_data), .am_stream(w_u_am_stream), .am_rdy(w_u_am_rdy), .wrq(w_u_wrq), .wrq_cr(w_u_wrq_cr), .wrr(w_u_wrr), .wwq(w_u_wwq), .wwq_cr(w_u_wwq_cr), .wwq_done(w_u_wwq_done), .rg_req(w_u_rg_req), .rg_gnt(w_u_rg_gnt), .wg_req(w_u_wg_req), .wg_gnt(w_u_wg_gnt));
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_u_halted
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_u_halted[k]), .q());
    end
    for (genvar k = 0; k < 523; k = k + 1) begin : g_sink_w_u_am_stream
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_u_am_stream[k]), .q());
    end
    wire [1023:0] od_t_coll = {1024'd0};
    wire [1023:0] o_t_coll;
    for (genvar k = 0; k < 1024; k = k + 1) begin : g_o_t_coll
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_coll[k]), .q(o_t_coll[k]));
    end
    assign t_coll[1023:0] = o_t_coll[1023:0];
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
    wire [512:0] od_t_lgW_rup = {w_u_wrq[511:0], w_u_rg_req[0:0]};
    wire [512:0] o_t_lgW_rup;
    for (genvar k = 0; k < 513; k = k + 1) begin : g_o_t_lgW_rup
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_lgW_rup[k]), .q(o_t_lgW_rup[k]));
    end
    assign t_lgW_rup[512:0] = o_t_lgW_rup[512:0];
    wire [8960:0] od_t_lgW_wup = {w_u_wwq[8959:0], w_u_wg_req[0:0]};
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
    wire [1023:0] od_t_su_ew = {1024'd0};
    wire [1023:0] o_t_su_ew;
    for (genvar k = 0; k < 1024; k = k + 1) begin : g_o_t_su_ew
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_su_ew[k]), .q(o_t_su_ew[k]));
    end
    assign t_su_ew[1023:0] = o_t_su_ew[1023:0];
    wire [1023:0] od_t_su_ns = {1024'd0};
    wire [1023:0] o_t_su_ns;
    for (genvar k = 0; k < 1024; k = k + 1) begin : g_o_t_su_ns
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_su_ns[k]), .q(o_t_su_ns[k]));
    end
    assign t_su_ns[1023:0] = o_t_su_ns[1023:0];
    wire [2047:0] od_t_vm = {2048'd0};
    wire [2047:0] o_t_vm;
    for (genvar k = 0; k < 2048; k = k + 1) begin : g_o_t_vm
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_vm[k]), .q(o_t_vm[k]));
    end
    assign t_vm[2047:0] = o_t_vm[2047:0];
endmodule
