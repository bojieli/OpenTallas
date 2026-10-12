// hfd_loader: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  HGI loader (hgi-takeover 2026-10-09): ot_hfd_loader_hgi = 37-bit half-rate loader core (ot_hfd_loader_half37) + the host CP window (ot_hgi_loader_cp) + the memory port to the four stack services (ot_hfd_loader_kport; lane 0 loader, lane 1 CP record-ring fetch); stack index (address bits 36:35) 0..3 = SW, SE, NW, NE. Host link binding as the legacy loader wrapper; the host-memory AXI master m_* stays as in the legacy wrapper (TA-14 host link). + the DMA unit (unit 8): ot_hgi_dma_record + ot_hgi_dma_engines (the DMA front for the svc DMA stream, DMA_FRONT 0 until the svc side binds; the F6 full-rate mover on kport lane 2) + one hfd_hgi_vm client + the 32-lane VM wide write port. R25GQ ([svc] 2026-10-10): host port h sized exactly (HOST_H_HGI tx 406 = loader outputs h[0:406], rx 381 = loader inputs h[406:787], in port order s_/h_/h_dma_/m_/irq/fault); the host-memory AXI master m_*, h_dma_wdata, irq and fault are bound to the host link (no fold/cfg ties). RGX=1 (hardware ROW_GATHER HBM lanes, [svc] 10-10): rgx_q/r/w/a bound to the die nets hgi_rgxq/rgxr/rgxw/rgxa 0..1 (coll). | hbmdie-1011/kvw 2026-10-11: VR2 = 1 (mover VM-source reads on the VM DMA wide read group t_dma_vr2q / f_dma_vr2r) + KVW = 1 (KV write-back engine ot_hgi_dma_kvw, hbm-fq 8df9a0e9f); DMA write lanes re-bound to the 281-b AP lane format (ap = 0). hgi-1010/c2 (AUDIT N5): FMV 1 = the FUSED mover's remote kport read lane (die nets hgi_fmk_q 38 / hgi_fmk_r 257 from hb_quant; ot_hgi_hbm_rdq_server on kport lane 11, after the hgi-1010/c mover lanes 7..10).
module hfd_loader (
    input wire [0:0] ck,
    input wire [8256:0] f_dma_vr2r,
    input wire [703:0] f_hgi_cmdproc,
    input wire [221:0] f_hgi_cp,
    input wire [37:0] f_hgi_fmkq,
    input wire [37:0] f_hgi_rgxq0,
    input wire [37:0] f_hgi_rgxq1,
    input wire [325:0] f_hgi_rgxw0,
    input wire [325:0] f_hgi_rgxw1,
    input wire [273:0] f_hgi_vmr,
    input wire [31:0] f_hgi_vmw,
    input wire [31:0] f_hgi_vmw_done,
    inout wire [788:0] h,
    output wire [350:0] qNE,
    output wire [350:0] qNW,
    output wire [350:0] qSE,
    output wire [350:0] qSW,
    input wire [293:0] rNE,
    input wire [293:0] rNW,
    input wire [293:0] rSE,
    input wire [293:0] rSW,
    input wire [0:0] rst,
    output wire [512:0] t_dma_vr2q,
    output wire [3:0] t_hgi_cmdproc,
    output wire [418:0] t_hgi_cp,
    output wire [256:0] t_hgi_fmkr,
    output wire [0:0] t_hgi_rgxa0,
    output wire [0:0] t_hgi_rgxa1,
    output wire [256:0] t_hgi_rgxr0,
    output wire [256:0] t_hgi_rgxr1,
    output wire [337:0] t_hgi_vmq,
    output wire [8991:0] t_hgi_vmw
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [8256:0] i0_f_dma_vr2r; always @(posedge clk) i0_f_dma_vr2r <= f_dma_vr2r;
    reg [8256:0] i1_f_dma_vr2r; always @(posedge clk) i1_f_dma_vr2r <= i0_f_dma_vr2r;
    reg [8256:0] i2_f_dma_vr2r; always @(posedge clk) i2_f_dma_vr2r <= i1_f_dma_vr2r;
    reg [8256:0] i3_f_dma_vr2r; always @(posedge clk) i3_f_dma_vr2r <= i2_f_dma_vr2r;
    reg [8256:0] i_f_dma_vr2r; always @(posedge clk) i_f_dma_vr2r <= i3_f_dma_vr2r;
    reg [703:0] i0_f_hgi_cmdproc; always @(posedge clk) i0_f_hgi_cmdproc <= f_hgi_cmdproc;
    reg [703:0] i1_f_hgi_cmdproc; always @(posedge clk) i1_f_hgi_cmdproc <= i0_f_hgi_cmdproc;
    reg [703:0] i2_f_hgi_cmdproc; always @(posedge clk) i2_f_hgi_cmdproc <= i1_f_hgi_cmdproc;
    reg [703:0] i3_f_hgi_cmdproc; always @(posedge clk) i3_f_hgi_cmdproc <= i2_f_hgi_cmdproc;
    reg [703:0] i_f_hgi_cmdproc; always @(posedge clk) i_f_hgi_cmdproc <= i3_f_hgi_cmdproc;
    reg [221:0] i0_f_hgi_cp; always @(posedge clk) i0_f_hgi_cp <= f_hgi_cp;
    reg [221:0] i1_f_hgi_cp; always @(posedge clk) i1_f_hgi_cp <= i0_f_hgi_cp;
    reg [221:0] i2_f_hgi_cp; always @(posedge clk) i2_f_hgi_cp <= i1_f_hgi_cp;
    reg [221:0] i3_f_hgi_cp; always @(posedge clk) i3_f_hgi_cp <= i2_f_hgi_cp;
    reg [221:0] i_f_hgi_cp; always @(posedge clk) i_f_hgi_cp <= i3_f_hgi_cp;
    reg [37:0] i0_f_hgi_fmkq; always @(posedge clk) i0_f_hgi_fmkq <= f_hgi_fmkq;
    reg [37:0] i1_f_hgi_fmkq; always @(posedge clk) i1_f_hgi_fmkq <= i0_f_hgi_fmkq;
    reg [37:0] i2_f_hgi_fmkq; always @(posedge clk) i2_f_hgi_fmkq <= i1_f_hgi_fmkq;
    reg [37:0] i3_f_hgi_fmkq; always @(posedge clk) i3_f_hgi_fmkq <= i2_f_hgi_fmkq;
    reg [37:0] i_f_hgi_fmkq; always @(posedge clk) i_f_hgi_fmkq <= i3_f_hgi_fmkq;
    reg [37:0] i0_f_hgi_rgxq0; always @(posedge clk) i0_f_hgi_rgxq0 <= f_hgi_rgxq0;
    reg [37:0] i1_f_hgi_rgxq0; always @(posedge clk) i1_f_hgi_rgxq0 <= i0_f_hgi_rgxq0;
    reg [37:0] i2_f_hgi_rgxq0; always @(posedge clk) i2_f_hgi_rgxq0 <= i1_f_hgi_rgxq0;
    reg [37:0] i3_f_hgi_rgxq0; always @(posedge clk) i3_f_hgi_rgxq0 <= i2_f_hgi_rgxq0;
    reg [37:0] i_f_hgi_rgxq0; always @(posedge clk) i_f_hgi_rgxq0 <= i3_f_hgi_rgxq0;
    reg [37:0] i0_f_hgi_rgxq1; always @(posedge clk) i0_f_hgi_rgxq1 <= f_hgi_rgxq1;
    reg [37:0] i1_f_hgi_rgxq1; always @(posedge clk) i1_f_hgi_rgxq1 <= i0_f_hgi_rgxq1;
    reg [37:0] i2_f_hgi_rgxq1; always @(posedge clk) i2_f_hgi_rgxq1 <= i1_f_hgi_rgxq1;
    reg [37:0] i3_f_hgi_rgxq1; always @(posedge clk) i3_f_hgi_rgxq1 <= i2_f_hgi_rgxq1;
    reg [37:0] i_f_hgi_rgxq1; always @(posedge clk) i_f_hgi_rgxq1 <= i3_f_hgi_rgxq1;
    reg [325:0] i0_f_hgi_rgxw0; always @(posedge clk) i0_f_hgi_rgxw0 <= f_hgi_rgxw0;
    reg [325:0] i1_f_hgi_rgxw0; always @(posedge clk) i1_f_hgi_rgxw0 <= i0_f_hgi_rgxw0;
    reg [325:0] i2_f_hgi_rgxw0; always @(posedge clk) i2_f_hgi_rgxw0 <= i1_f_hgi_rgxw0;
    reg [325:0] i3_f_hgi_rgxw0; always @(posedge clk) i3_f_hgi_rgxw0 <= i2_f_hgi_rgxw0;
    reg [325:0] i_f_hgi_rgxw0; always @(posedge clk) i_f_hgi_rgxw0 <= i3_f_hgi_rgxw0;
    reg [325:0] i0_f_hgi_rgxw1; always @(posedge clk) i0_f_hgi_rgxw1 <= f_hgi_rgxw1;
    reg [325:0] i1_f_hgi_rgxw1; always @(posedge clk) i1_f_hgi_rgxw1 <= i0_f_hgi_rgxw1;
    reg [325:0] i2_f_hgi_rgxw1; always @(posedge clk) i2_f_hgi_rgxw1 <= i1_f_hgi_rgxw1;
    reg [325:0] i3_f_hgi_rgxw1; always @(posedge clk) i3_f_hgi_rgxw1 <= i2_f_hgi_rgxw1;
    reg [325:0] i_f_hgi_rgxw1; always @(posedge clk) i_f_hgi_rgxw1 <= i3_f_hgi_rgxw1;
    reg [273:0] i0_f_hgi_vmr; always @(posedge clk) i0_f_hgi_vmr <= f_hgi_vmr;
    reg [273:0] i1_f_hgi_vmr; always @(posedge clk) i1_f_hgi_vmr <= i0_f_hgi_vmr;
    reg [273:0] i2_f_hgi_vmr; always @(posedge clk) i2_f_hgi_vmr <= i1_f_hgi_vmr;
    reg [273:0] i3_f_hgi_vmr; always @(posedge clk) i3_f_hgi_vmr <= i2_f_hgi_vmr;
    reg [273:0] i_f_hgi_vmr; always @(posedge clk) i_f_hgi_vmr <= i3_f_hgi_vmr;
    reg [31:0] i0_f_hgi_vmw; always @(posedge clk) i0_f_hgi_vmw <= f_hgi_vmw;
    reg [31:0] i1_f_hgi_vmw; always @(posedge clk) i1_f_hgi_vmw <= i0_f_hgi_vmw;
    reg [31:0] i2_f_hgi_vmw; always @(posedge clk) i2_f_hgi_vmw <= i1_f_hgi_vmw;
    reg [31:0] i3_f_hgi_vmw; always @(posedge clk) i3_f_hgi_vmw <= i2_f_hgi_vmw;
    reg [31:0] i_f_hgi_vmw; always @(posedge clk) i_f_hgi_vmw <= i3_f_hgi_vmw;
    reg [31:0] i0_f_hgi_vmw_done; always @(posedge clk) i0_f_hgi_vmw_done <= f_hgi_vmw_done;
    reg [31:0] i1_f_hgi_vmw_done; always @(posedge clk) i1_f_hgi_vmw_done <= i0_f_hgi_vmw_done;
    reg [31:0] i2_f_hgi_vmw_done; always @(posedge clk) i2_f_hgi_vmw_done <= i1_f_hgi_vmw_done;
    reg [31:0] i3_f_hgi_vmw_done; always @(posedge clk) i3_f_hgi_vmw_done <= i2_f_hgi_vmw_done;
    reg [31:0] i_f_hgi_vmw_done; always @(posedge clk) i_f_hgi_vmw_done <= i3_f_hgi_vmw_done;
    reg [788:0] i0_h; always @(posedge clk) i0_h <= h;
    reg [788:0] i1_h; always @(posedge clk) i1_h <= i0_h;
    reg [788:0] i2_h; always @(posedge clk) i2_h <= i1_h;
    reg [788:0] i3_h; always @(posedge clk) i3_h <= i2_h;
    reg [788:0] i_h; always @(posedge clk) i_h <= i3_h;
    reg [293:0] i0_rNE; always @(posedge clk) i0_rNE <= rNE;
    reg [293:0] i1_rNE; always @(posedge clk) i1_rNE <= i0_rNE;
    reg [293:0] i2_rNE; always @(posedge clk) i2_rNE <= i1_rNE;
    reg [293:0] i3_rNE; always @(posedge clk) i3_rNE <= i2_rNE;
    reg [293:0] i_rNE; always @(posedge clk) i_rNE <= i3_rNE;
    reg [293:0] i0_rNW; always @(posedge clk) i0_rNW <= rNW;
    reg [293:0] i1_rNW; always @(posedge clk) i1_rNW <= i0_rNW;
    reg [293:0] i2_rNW; always @(posedge clk) i2_rNW <= i1_rNW;
    reg [293:0] i3_rNW; always @(posedge clk) i3_rNW <= i2_rNW;
    reg [293:0] i_rNW; always @(posedge clk) i_rNW <= i3_rNW;
    reg [293:0] i0_rSE; always @(posedge clk) i0_rSE <= rSE;
    reg [293:0] i1_rSE; always @(posedge clk) i1_rSE <= i0_rSE;
    reg [293:0] i2_rSE; always @(posedge clk) i2_rSE <= i1_rSE;
    reg [293:0] i3_rSE; always @(posedge clk) i3_rSE <= i2_rSE;
    reg [293:0] i_rSE; always @(posedge clk) i_rSE <= i3_rSE;
    reg [293:0] i0_rSW; always @(posedge clk) i0_rSW <= rSW;
    reg [293:0] i1_rSW; always @(posedge clk) i1_rSW <= i0_rSW;
    reg [293:0] i2_rSW; always @(posedge clk) i2_rSW <= i1_rSW;
    reg [293:0] i3_rSW; always @(posedge clk) i3_rSW <= i2_rSW;
    reg [293:0] i_rSW; always @(posedge clk) i_rSW <= i3_rSW;
    wire [0:0] w_ld_clk;
    wire [0:0] w_ld_rst_n;
    wire [0:0] w_ld_s_awvalid;
    wire [0:0] w_ld_s_awready;
    wire [11:0] w_ld_s_awaddr;
    wire [0:0] w_ld_s_wvalid;
    wire [0:0] w_ld_s_wready;
    wire [31:0] w_ld_s_wdata;
    wire [3:0] w_ld_s_wstrb;
    wire [0:0] w_ld_s_bvalid;
    wire [0:0] w_ld_s_bready;
    wire [0:0] w_ld_s_arvalid;
    wire [0:0] w_ld_s_arready;
    wire [11:0] w_ld_s_araddr;
    wire [0:0] w_ld_s_rvalid;
    wire [0:0] w_ld_s_rready;
    wire [31:0] w_ld_s_rdata;
    wire [0:0] w_ld_h_awvalid;
    wire [0:0] w_ld_h_awready;
    wire [11:0] w_ld_h_awaddr;
    wire [0:0] w_ld_h_wvalid;
    wire [0:0] w_ld_h_wready;
    wire [31:0] w_ld_h_wdata;
    wire [3:0] w_ld_h_wstrb;
    wire [0:0] w_ld_h_bvalid;
    wire [0:0] w_ld_h_bready;
    wire [0:0] w_ld_h_arvalid;
    wire [0:0] w_ld_h_arready;
    wire [11:0] w_ld_h_araddr;
    wire [0:0] w_ld_h_rvalid;
    wire [0:0] w_ld_h_rready;
    wire [31:0] w_ld_h_rdata;
    wire [0:0] w_ld_h_dma_arvalid;
    wire [0:0] w_ld_h_dma_arready;
    wire [63:0] w_ld_h_dma_araddr;
    wire [0:0] w_ld_h_dma_rvalid;
    wire [0:0] w_ld_h_dma_rready;
    wire [63:0] w_ld_h_dma_rdata;
    wire [1:0] w_ld_h_dma_rresp;
    wire [0:0] w_ld_h_dma_rlast;
    wire [0:0] w_ld_h_dma_awvalid;
    wire [0:0] w_ld_h_dma_awready;
    wire [63:0] w_ld_h_dma_awaddr;
    wire [0:0] w_ld_h_dma_wvalid;
    wire [0:0] w_ld_h_dma_wready;
    wire [63:0] w_ld_h_dma_wdata;
    wire [7:0] w_ld_h_dma_wstrb;
    wire [0:0] w_ld_h_dma_bvalid;
    wire [0:0] w_ld_h_dma_bready;
    wire [1:0] w_ld_h_dma_bresp;
    wire [0:0] w_ld_m_arvalid;
    wire [0:0] w_ld_m_arready;
    wire [63:0] w_ld_m_araddr;
    wire [7:0] w_ld_m_arlen;
    wire [2:0] w_ld_m_arsize;
    wire [0:0] w_ld_m_rvalid;
    wire [0:0] w_ld_m_rready;
    wire [63:0] w_ld_m_rdata;
    wire [1:0] w_ld_m_rresp;
    wire [0:0] w_ld_m_rlast;
    wire [0:0] w_ld_m_awvalid;
    wire [0:0] w_ld_m_awready;
    wire [63:0] w_ld_m_awaddr;
    wire [7:0] w_ld_m_awlen;
    wire [2:0] w_ld_m_awsize;
    wire [0:0] w_ld_m_wvalid;
    wire [0:0] w_ld_m_wready;
    wire [63:0] w_ld_m_wdata;
    wire [7:0] w_ld_m_wstrb;
    wire [0:0] w_ld_m_wlast;
    wire [0:0] w_ld_m_bvalid;
    wire [0:0] w_ld_m_bready;
    wire [1:0] w_ld_m_bresp;
    wire [418:0] w_ld_lcp;
    wire [221:0] w_ld_cpl;
    wire [1399:0] w_ld_lq;
    wire [1171:0] w_ld_lr;
    wire [703:0] w_ld_dma_rec;
    wire [3:0] w_ld_dma_ret;
    wire [337:0] w_ld_dma_vmq;
    wire [273:0] w_ld_dma_vmr;
    wire [512:0] w_ld_dma_vr2q;
    wire [8256:0] w_ld_dma_vr2r;
    wire [203:0] w_ld_dma_dq;
    wire [3:0] w_ld_dma_dq_rdy;
    wire [8639:0] w_ld_dma_dd;
    wire [31:0] w_ld_dma_dd_cr;
    wire [8959:0] w_ld_dma_vmw;
    wire [31:0] w_ld_dma_vmw_done;
    wire [75:0] w_ld_rgx_q;
    wire [513:0] w_ld_rgx_r;
    wire [651:0] w_ld_rgx_w;
    wire [1:0] w_ld_rgx_a;
    wire [37:0] w_ld_fmk_q;
    wire [256:0] w_ld_fmk_r;
    wire [0:0] w_ld_irq;
    wire [0:0] w_ld_fault;
    assign w_ld_clk = {1{clk}};
    assign w_ld_rst_n = {1{rst_n}};
    assign w_ld_s_awvalid = {i_h[406:406]};
    assign w_ld_s_awaddr = {i_h[418:407]};
    assign w_ld_s_wvalid = {i_h[419:419]};
    assign w_ld_s_wdata = {i_h[451:420]};
    assign w_ld_s_wstrb = {i_h[455:452]};
    assign w_ld_s_bready = {i_h[456:456]};
    assign w_ld_s_arvalid = {i_h[457:457]};
    assign w_ld_s_araddr = {i_h[469:458]};
    assign w_ld_s_rready = {i_h[470:470]};
    assign w_ld_h_awready = {i_h[471:471]};
    assign w_ld_h_wready = {i_h[472:472]};
    assign w_ld_h_bvalid = {i_h[473:473]};
    assign w_ld_h_arready = {i_h[474:474]};
    assign w_ld_h_rvalid = {i_h[475:475]};
    assign w_ld_h_rdata = {i_h[507:476]};
    assign w_ld_h_dma_arvalid = {i_h[508:508]};
    assign w_ld_h_dma_araddr = {i_h[572:509]};
    assign w_ld_h_dma_rready = {i_h[573:573]};
    assign w_ld_h_dma_awvalid = {i_h[574:574]};
    assign w_ld_h_dma_awaddr = {i_h[638:575]};
    assign w_ld_h_dma_wvalid = {i_h[639:639]};
    assign w_ld_h_dma_wdata = {i_h[703:640]};
    assign w_ld_h_dma_wstrb = {i_h[711:704]};
    assign w_ld_h_dma_bready = {i_h[712:712]};
    assign w_ld_m_arready = {i_h[713:713]};
    assign w_ld_m_rvalid = {i_h[714:714]};
    assign w_ld_m_rdata = {i_h[778:715]};
    assign w_ld_m_rresp = {i_h[780:779]};
    assign w_ld_m_rlast = {i_h[781:781]};
    assign w_ld_m_awready = {i_h[782:782]};
    assign w_ld_m_wready = {i_h[783:783]};
    assign w_ld_m_bvalid = {i_h[784:784]};
    assign w_ld_m_bresp = {i_h[786:785]};
    assign w_ld_cpl = {i_f_hgi_cp[221:0]};
    assign w_ld_lr = {i_rNE[292:0], i_rNW[292:0], i_rSE[292:0], i_rSW[292:0]};
    assign w_ld_dma_rec = {i_f_hgi_cmdproc[703:0]};
    assign w_ld_dma_vmr = {i_f_hgi_vmr[273:0]};
    assign w_ld_dma_vr2r = {i_f_dma_vr2r[8256:0]};
    assign w_ld_dma_dq_rdy = 4'd0;
    assign w_ld_dma_dd = 8640'd0;
    assign w_ld_dma_vmw_done = {i_f_hgi_vmw_done[31:0]};
    assign w_ld_rgx_q = {i_f_hgi_rgxq1[37:0], i_f_hgi_rgxq0[37:0]};
    assign w_ld_rgx_w = {i_f_hgi_rgxw1[325:0], i_f_hgi_rgxw0[325:0]};
    assign w_ld_fmk_q = {i_f_hgi_fmkq[37:0]};
    ot_hfd_loader_hgi #(.DMA_FRONT(0), .RGX(1), .VR2(1), .KVW(1), .FMV(1)) u_ld (.clk(w_ld_clk), .rst_n(w_ld_rst_n), .s_awvalid(w_ld_s_awvalid), .s_awready(w_ld_s_awready), .s_awaddr(w_ld_s_awaddr), .s_wvalid(w_ld_s_wvalid), .s_wready(w_ld_s_wready), .s_wdata(w_ld_s_wdata), .s_wstrb(w_ld_s_wstrb), .s_bvalid(w_ld_s_bvalid), .s_bready(w_ld_s_bready), .s_arvalid(w_ld_s_arvalid), .s_arready(w_ld_s_arready), .s_araddr(w_ld_s_araddr), .s_rvalid(w_ld_s_rvalid), .s_rready(w_ld_s_rready), .s_rdata(w_ld_s_rdata), .h_awvalid(w_ld_h_awvalid), .h_awready(w_ld_h_awready), .h_awaddr(w_ld_h_awaddr), .h_wvalid(w_ld_h_wvalid), .h_wready(w_ld_h_wready), .h_wdata(w_ld_h_wdata), .h_wstrb(w_ld_h_wstrb), .h_bvalid(w_ld_h_bvalid), .h_bready(w_ld_h_bready), .h_arvalid(w_ld_h_arvalid), .h_arready(w_ld_h_arready), .h_araddr(w_ld_h_araddr), .h_rvalid(w_ld_h_rvalid), .h_rready(w_ld_h_rready), .h_rdata(w_ld_h_rdata), .h_dma_arvalid(w_ld_h_dma_arvalid), .h_dma_arready(w_ld_h_dma_arready), .h_dma_araddr(w_ld_h_dma_araddr), .h_dma_rvalid(w_ld_h_dma_rvalid), .h_dma_rready(w_ld_h_dma_rready), .h_dma_rdata(w_ld_h_dma_rdata), .h_dma_rresp(w_ld_h_dma_rresp), .h_dma_rlast(w_ld_h_dma_rlast), .h_dma_awvalid(w_ld_h_dma_awvalid), .h_dma_awready(w_ld_h_dma_awready), .h_dma_awaddr(w_ld_h_dma_awaddr), .h_dma_wvalid(w_ld_h_dma_wvalid), .h_dma_wready(w_ld_h_dma_wready), .h_dma_wdata(w_ld_h_dma_wdata), .h_dma_wstrb(w_ld_h_dma_wstrb), .h_dma_bvalid(w_ld_h_dma_bvalid), .h_dma_bready(w_ld_h_dma_bready), .h_dma_bresp(w_ld_h_dma_bresp), .m_arvalid(w_ld_m_arvalid), .m_arready(w_ld_m_arready), .m_araddr(w_ld_m_araddr), .m_arlen(w_ld_m_arlen), .m_arsize(w_ld_m_arsize), .m_rvalid(w_ld_m_rvalid), .m_rready(w_ld_m_rready), .m_rdata(w_ld_m_rdata), .m_rresp(w_ld_m_rresp), .m_rlast(w_ld_m_rlast), .m_awvalid(w_ld_m_awvalid), .m_awready(w_ld_m_awready), .m_awaddr(w_ld_m_awaddr), .m_awlen(w_ld_m_awlen), .m_awsize(w_ld_m_awsize), .m_wvalid(w_ld_m_wvalid), .m_wready(w_ld_m_wready), .m_wdata(w_ld_m_wdata), .m_wstrb(w_ld_m_wstrb), .m_wlast(w_ld_m_wlast), .m_bvalid(w_ld_m_bvalid), .m_bready(w_ld_m_bready), .m_bresp(w_ld_m_bresp), .lcp(w_ld_lcp), .cpl(w_ld_cpl), .lq(w_ld_lq), .lr(w_ld_lr), .dma_rec(w_ld_dma_rec), .dma_ret(w_ld_dma_ret), .dma_vmq(w_ld_dma_vmq), .dma_vmr(w_ld_dma_vmr), .dma_vr2q(w_ld_dma_vr2q), .dma_vr2r(w_ld_dma_vr2r), .dma_dq(w_ld_dma_dq), .dma_dq_rdy(w_ld_dma_dq_rdy), .dma_dd(w_ld_dma_dd), .dma_dd_cr(w_ld_dma_dd_cr), .dma_vmw(w_ld_dma_vmw), .dma_vmw_done(w_ld_dma_vmw_done), .rgx_q(w_ld_rgx_q), .rgx_r(w_ld_rgx_r), .rgx_w(w_ld_rgx_w), .rgx_a(w_ld_rgx_a), .fmk_q(w_ld_fmk_q), .fmk_r(w_ld_fmk_r), .irq(w_ld_irq), .fault(w_ld_fault));
    for (genvar k = 0; k < 204; k = k + 1) begin : g_sink_w_ld_dma_dq
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_dma_dq[k]), .q());
    end
    for (genvar k = 0; k < 32; k = k + 1) begin : g_sink_w_ld_dma_dd_cr
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_dma_dd_cr[k]), .q());
    end
    wire [788:0] od_h = {383'd0, w_ld_fault[0:0], w_ld_irq[0:0], w_ld_m_bready[0:0], w_ld_m_wlast[0:0], w_ld_m_wstrb[7:0], w_ld_m_wdata[63:0], w_ld_m_wvalid[0:0], w_ld_m_awsize[2:0], w_ld_m_awlen[7:0], w_ld_m_awaddr[63:0], w_ld_m_awvalid[0:0], w_ld_m_rready[0:0], w_ld_m_arsize[2:0], w_ld_m_arlen[7:0], w_ld_m_araddr[63:0], w_ld_m_arvalid[0:0], w_ld_h_dma_bresp[1:0], w_ld_h_dma_bvalid[0:0], w_ld_h_dma_wready[0:0], w_ld_h_dma_awready[0:0], w_ld_h_dma_rlast[0:0], w_ld_h_dma_rresp[1:0], w_ld_h_dma_rdata[63:0], w_ld_h_dma_rvalid[0:0], w_ld_h_dma_arready[0:0], w_ld_h_rready[0:0], w_ld_h_araddr[11:0], w_ld_h_arvalid[0:0], w_ld_h_bready[0:0], w_ld_h_wstrb[3:0], w_ld_h_wdata[31:0], w_ld_h_wvalid[0:0], w_ld_h_awaddr[11:0], w_ld_h_awvalid[0:0], w_ld_s_rdata[31:0], w_ld_s_rvalid[0:0], w_ld_s_arready[0:0], w_ld_s_bvalid[0:0], w_ld_s_wready[0:0], w_ld_s_awready[0:0]};
    wire [788:0] o_h;
    for (genvar k = 0; k < 789; k = k + 1) begin : g_o_h
        ot_hfd_oreg5 u (.clk(clk), .d(od_h[k]), .q(o_h[k]));
    end
    assign h[405:0] = o_h[405:0];
    assign h[787:787] = o_h[787:787];
    wire [350:0] od_qNE = {1'd0, w_ld_lq[1399:1050]};
    wire [350:0] o_qNE;
    for (genvar k = 0; k < 351; k = k + 1) begin : g_o_qNE
        ot_hfd_oreg5 u (.clk(clk), .d(od_qNE[k]), .q(o_qNE[k]));
    end
    assign qNE[350:0] = o_qNE[350:0];
    wire [350:0] od_qNW = {1'd0, w_ld_lq[1049:700]};
    wire [350:0] o_qNW;
    for (genvar k = 0; k < 351; k = k + 1) begin : g_o_qNW
        ot_hfd_oreg5 u (.clk(clk), .d(od_qNW[k]), .q(o_qNW[k]));
    end
    assign qNW[350:0] = o_qNW[350:0];
    wire [350:0] od_qSE = {1'd0, w_ld_lq[699:350]};
    wire [350:0] o_qSE;
    for (genvar k = 0; k < 351; k = k + 1) begin : g_o_qSE
        ot_hfd_oreg5 u (.clk(clk), .d(od_qSE[k]), .q(o_qSE[k]));
    end
    assign qSE[350:0] = o_qSE[350:0];
    wire [350:0] od_qSW = {1'd0, w_ld_lq[349:0]};
    wire [350:0] o_qSW;
    for (genvar k = 0; k < 351; k = k + 1) begin : g_o_qSW
        ot_hfd_oreg5 u (.clk(clk), .d(od_qSW[k]), .q(o_qSW[k]));
    end
    assign qSW[350:0] = o_qSW[350:0];
    wire [512:0] od_t_dma_vr2q = {w_ld_dma_vr2q[512:0]};
    wire [512:0] o_t_dma_vr2q;
    for (genvar k = 0; k < 513; k = k + 1) begin : g_o_t_dma_vr2q
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_dma_vr2q[k]), .q(o_t_dma_vr2q[k]));
    end
    assign t_dma_vr2q[512:0] = o_t_dma_vr2q[512:0];
    wire [3:0] od_t_hgi_cmdproc = {w_ld_dma_ret[3:0]};
    wire [3:0] o_t_hgi_cmdproc;
    for (genvar k = 0; k < 4; k = k + 1) begin : g_o_t_hgi_cmdproc
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_cmdproc[k]), .q(o_t_hgi_cmdproc[k]));
    end
    assign t_hgi_cmdproc[3:0] = o_t_hgi_cmdproc[3:0];
    wire [418:0] od_t_hgi_cp = {w_ld_lcp[418:0]};
    wire [418:0] o_t_hgi_cp;
    for (genvar k = 0; k < 419; k = k + 1) begin : g_o_t_hgi_cp
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_cp[k]), .q(o_t_hgi_cp[k]));
    end
    assign t_hgi_cp[418:0] = o_t_hgi_cp[418:0];
    wire [256:0] od_t_hgi_fmkr = {w_ld_fmk_r[256:0]};
    wire [256:0] o_t_hgi_fmkr;
    for (genvar k = 0; k < 257; k = k + 1) begin : g_o_t_hgi_fmkr
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_fmkr[k]), .q(o_t_hgi_fmkr[k]));
    end
    assign t_hgi_fmkr[256:0] = o_t_hgi_fmkr[256:0];
    wire [0:0] od_t_hgi_rgxa0 = {w_ld_rgx_a[0:0]};
    wire [0:0] o_t_hgi_rgxa0;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_t_hgi_rgxa0
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_rgxa0[k]), .q(o_t_hgi_rgxa0[k]));
    end
    assign t_hgi_rgxa0[0:0] = o_t_hgi_rgxa0[0:0];
    wire [0:0] od_t_hgi_rgxa1 = {w_ld_rgx_a[1:1]};
    wire [0:0] o_t_hgi_rgxa1;
    for (genvar k = 0; k < 1; k = k + 1) begin : g_o_t_hgi_rgxa1
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_rgxa1[k]), .q(o_t_hgi_rgxa1[k]));
    end
    assign t_hgi_rgxa1[0:0] = o_t_hgi_rgxa1[0:0];
    wire [256:0] od_t_hgi_rgxr0 = {w_ld_rgx_r[256:0]};
    wire [256:0] o_t_hgi_rgxr0;
    for (genvar k = 0; k < 257; k = k + 1) begin : g_o_t_hgi_rgxr0
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_rgxr0[k]), .q(o_t_hgi_rgxr0[k]));
    end
    assign t_hgi_rgxr0[256:0] = o_t_hgi_rgxr0[256:0];
    wire [256:0] od_t_hgi_rgxr1 = {w_ld_rgx_r[513:257]};
    wire [256:0] o_t_hgi_rgxr1;
    for (genvar k = 0; k < 257; k = k + 1) begin : g_o_t_hgi_rgxr1
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_rgxr1[k]), .q(o_t_hgi_rgxr1[k]));
    end
    assign t_hgi_rgxr1[256:0] = o_t_hgi_rgxr1[256:0];
    wire [337:0] od_t_hgi_vmq = {w_ld_dma_vmq[337:0]};
    wire [337:0] o_t_hgi_vmq;
    for (genvar k = 0; k < 338; k = k + 1) begin : g_o_t_hgi_vmq
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmq[k]), .q(o_t_hgi_vmq[k]));
    end
    assign t_hgi_vmq[337:0] = o_t_hgi_vmq[337:0];
    wire [8991:0] od_t_hgi_vmw = {w_ld_dma_vmw[8959:8959], 1'd0, w_ld_dma_vmw[8958:8680], w_ld_dma_vmw[8679:8679], 1'd0, w_ld_dma_vmw[8678:8400], w_ld_dma_vmw[8399:8399], 1'd0, w_ld_dma_vmw[8398:8120], w_ld_dma_vmw[8119:8119], 1'd0, w_ld_dma_vmw[8118:7840], w_ld_dma_vmw[7839:7839], 1'd0, w_ld_dma_vmw[7838:7560], w_ld_dma_vmw[7559:7559], 1'd0, w_ld_dma_vmw[7558:7280], w_ld_dma_vmw[7279:7279], 1'd0, w_ld_dma_vmw[7278:7000], w_ld_dma_vmw[6999:6999], 1'd0, w_ld_dma_vmw[6998:6720], w_ld_dma_vmw[6719:6719], 1'd0, w_ld_dma_vmw[6718:6440], w_ld_dma_vmw[6439:6439], 1'd0, w_ld_dma_vmw[6438:6160], w_ld_dma_vmw[6159:6159], 1'd0, w_ld_dma_vmw[6158:5880], w_ld_dma_vmw[5879:5879], 1'd0, w_ld_dma_vmw[5878:5600], w_ld_dma_vmw[5599:5599], 1'd0, w_ld_dma_vmw[5598:5320], w_ld_dma_vmw[5319:5319], 1'd0, w_ld_dma_vmw[5318:5040], w_ld_dma_vmw[5039:5039], 1'd0, w_ld_dma_vmw[5038:4760], w_ld_dma_vmw[4759:4759], 1'd0, w_ld_dma_vmw[4758:4480], w_ld_dma_vmw[4479:4479], 1'd0, w_ld_dma_vmw[4478:4200], w_ld_dma_vmw[4199:4199], 1'd0, w_ld_dma_vmw[4198:3920], w_ld_dma_vmw[3919:3919], 1'd0, w_ld_dma_vmw[3918:3640], w_ld_dma_vmw[3639:3639], 1'd0, w_ld_dma_vmw[3638:3360], w_ld_dma_vmw[3359:3359], 1'd0, w_ld_dma_vmw[3358:3080], w_ld_dma_vmw[3079:3079], 1'd0, w_ld_dma_vmw[3078:2800], w_ld_dma_vmw[2799:2799], 1'd0, w_ld_dma_vmw[2798:2520], w_ld_dma_vmw[2519:2519], 1'd0, w_ld_dma_vmw[2518:2240], w_ld_dma_vmw[2239:2239], 1'd0, w_ld_dma_vmw[2238:1960], w_ld_dma_vmw[1959:1959], 1'd0, w_ld_dma_vmw[1958:1680], w_ld_dma_vmw[1679:1679], 1'd0, w_ld_dma_vmw[1678:1400], w_ld_dma_vmw[1399:1399], 1'd0, w_ld_dma_vmw[1398:1120], w_ld_dma_vmw[1119:1119], 1'd0, w_ld_dma_vmw[1118:840], w_ld_dma_vmw[839:839], 1'd0, w_ld_dma_vmw[838:560], w_ld_dma_vmw[559:559], 1'd0, w_ld_dma_vmw[558:280], w_ld_dma_vmw[279:279], 1'd0, w_ld_dma_vmw[278:0]};
    wire [8991:0] o_t_hgi_vmw;
    for (genvar k = 0; k < 8992; k = k + 1) begin : g_o_t_hgi_vmw
        ot_hfd_oreg5 u (.clk(clk), .d(od_t_hgi_vmw[k]), .q(o_t_hgi_vmw[k]));
    end
    assign t_hgi_vmw[8991:0] = o_t_hgi_vmw[8991:0];
endmodule
