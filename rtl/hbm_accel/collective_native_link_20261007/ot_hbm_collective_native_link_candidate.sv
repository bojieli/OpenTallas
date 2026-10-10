// Source-derived default-off native link successor. Model: hbm_collective_native_link_model.py.
// Baseline e9cbc1c4e remains immutable; this source requires independent full-shape qualification.
// ADDITIVE storage candidate. core clk and PHY pclk are independent real inputs;
// no generated PLL outputs. Single-endpoint qualification and token composition
// remain open. Original truecredit and production parents are byte-identical.
`timescale 1ns/1ps
// Additive real TU parent successor. OWNER_REDUCER=0 uses byte-pinned original.
// Cold POR only; arm changes transaction state after real quiet, never FIFO pointers/credits.
// Publication and matched remote-debt release remain shared8/Dewey authorities.
module ot_hbm_collective_native_link_candidate #(
    parameter integer LINK_PROTECTION = 0,
    parameter integer PACKET_SRAM = 0, // opt-in; queue II3, token composition pending
    parameter integer ENABLE = 0,
    parameter integer OWNER_REDUCER = 0, // default original parent
    parameter integer SLOTREG = 1,
    parameter integer OWNER_BANKED_HALF = 0, // default off; sender/receiver credits
    parameter integer OWNER_TRUE_CREDIT = 0, TC_FWD = 7, TC_RET = 7, // internal candidate; actual physical hops unqualified
    // credit-ready (2026-10-08, default 0 = same-cycle receiver_ready): OWNER_RX_CREDIT=1 (needs OWNER_TRUE_CREDIT and
    // OWNER_BANKED_HALF) uses ot_ha2_truecredit_receiver_p CREDIT=1 and the half owner's H_CREDIT pulses (OWNER_RX_CRD
    // credits = the half owner's injector FIFO depth FD=8).
    parameter integer OWNER_RX_CREDIT = 0, OWNER_RX_CRD = 8,
    parameter integer OWNER_HUB_QAW = 6,
    parameter integer NC     = 8,
    parameter integer NOG    = 8,
    parameter integer PFMAX  = 64,
    parameter integer LANES  = 16,
    parameter integer BF16   = 1,
    parameter integer NPT    = 8,
    parameter integer INJ    = 2,
    parameter integer DEL    = 4,
    parameter integer HUBW   = 35,
    parameter integer WSTG   = 14,
    parameter integer BITS_X100 = 72000,
    parameter integer PWB    = 545,
    parameter integer RXAW   = 8,
    parameter integer QAW    = 6,
    parameter integer TXAW   = 6,
    parameter integer SWCRED = 256,
    parameter integer LAT    = 7,
    parameter integer FW     = 32 * LANES,
    parameter integer PWT    = FW + 33
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 pclk,            // this die's PHY (serializer) clock
    input  wire                 prst_n,
    input wire cold_link_start,session_admit,
    output wire [NPT-1:0] source_debt_zero,source_initial_ack_seen,
    output wire data_queues_quiet,
    input wire [23:0] link_epoch,
    // Atomic protected control transport in clk domain; actual CDC/PHY wrapper required.
    input wire [NPT-1:0] tx_grant_valid,tx_ack_ready,
    output wire [NPT-1:0] tx_grant_ready,tx_ack_valid,
    input wire [NPT*72-1:0] tx_grant_word,
    output wire [NPT*72-1:0] tx_ack_word,
    output wire [NPT-1:0] rx_grant_valid,rx_ack_ready,
    input wire [NPT-1:0] rx_grant_ready,rx_ack_valid,
    output wire [NPT*72-1:0] rx_grant_word,
    input wire [NPT*72-1:0] rx_ack_word,
    input  wire [7:0]           rank,
    input wire [63:0] context_operation, input wire [31:0] context_phase,
    output wire endpoint_rearm_ready, endpoint_quiet_core, endpoint_quiet_phy,
    input  wire [15:0]          pf,              // flits per contributor this collective (runtime)
    input  wire                 go,
    output wire [INJ*16-1:0]    inj_idx,
    output wire [INJ-1:0]       inj_rd,
    input  wire [INJ*FW-1:0]    inj_data,
    // switch side, PHY clock: one flit a pclk at most per port, after the serializer
    output wire [NPT-1:0]       ph_tx_v,
    output wire [NPT*PWT-1:0]   ph_tx_flit,
    input  wire [NPT-1:0]       sw_cr_ret,       // switch ingress credit return (core clock)
    input  wire [NPT-1:0]       ph_rx_v,         // from the switch egress (PHY clock)
    input  wire [NPT*PWT-1:0]   ph_rx_flit,
    output wire [NPT-1:0]       rx_credit,       // receive-buffer pop (core clock) -> switch egress credit
    output wire [DEL-1:0]       del_valid,
    output wire [DEL*PWT-1:0]   del_flit,
    output wire                 fault,
    output wire [31:0]          stat_credit_stall
);
    initial if(LINK_PROTECTION && (!OWNER_REDUCER || !PACKET_SRAM || NPT!=8 || WSTG!=14 || PWT!=545 || TXAW!=6 || RXAW!=8 || BITS_X100<PWB*100))
      $fatal(1,"protected native link requires full sized owner/SRAM/flight contract");
    generate if(!LINK_PROTECTION || !ENABLE || !OWNER_REDUCER)begin:g_control_off
      assign tx_grant_ready=0;assign tx_ack_valid=0;assign tx_ack_word=0;
      assign rx_grant_valid=0;assign rx_grant_word=0;assign rx_ack_ready=0;
      assign source_debt_zero=0;assign source_initial_ack_seen=0;assign data_queues_quiet=0;
    end endgenerate
    initial if(PACKET_SRAM && (!OWNER_REDUCER || PWT!=545 || RXAW!=8 || QAW!=6 || TXAW!=6))
      $fatal(1,"full collective SRAM requires native owner and full queue geometry");
    localparam integer LV   = $clog2(NC);
    localparam integer OFMX = PFMAX / NC;

    generate if (OWNER_REDUCER == 0) begin : g_original
      ot_hbm_accel_tu_endpoint #(.ENABLE(ENABLE),.NC(NC),.NOG(NOG),.PFMAX(PFMAX),.LANES(LANES),.BF16(BF16),.NPT(NPT),.INJ(INJ),.DEL(DEL),.HUBW(HUBW),.WSTG(WSTG),.BITS_X100(BITS_X100),.PWB(PWB),.RXAW(RXAW),.QAW(QAW),.TXAW(TXAW),.SWCRED(SWCRED),.LAT(LAT),.FW(FW),.PWT(PWT)) u_original
      (.clk(clk),.rst_n(rst_n),.pclk(pclk),.prst_n(prst_n),.rank(rank),.pf(pf),.go(go),.inj_idx(inj_idx),.inj_rd(inj_rd),.inj_data(inj_data),.ph_tx_v(ph_tx_v),.ph_tx_flit(ph_tx_flit),.sw_cr_ret(sw_cr_ret),.ph_rx_v(ph_rx_v),.ph_rx_flit(ph_rx_flit),.rx_credit(rx_credit),.del_valid(del_valid),.del_flit(del_flit),.fault(fault),.stat_credit_stall(stat_credit_stall));
      // Original parent has no positive quiet/rearm API; do not fabricate it.
      assign endpoint_rearm_ready=0; assign endpoint_quiet_core=0;assign endpoint_quiet_phy=0;
    end else begin : g_candidate
    if (ENABLE == 0) begin : g_off
        assign inj_idx = '0; assign inj_rd = '0; assign ph_tx_v = '0; assign ph_tx_flit = '0;
        assign rx_credit = '0; assign del_valid = '0; assign del_flit = '0; assign fault = 1'b0;
        assign stat_credit_stall = 0;
        assign endpoint_rearm_ready=0;assign endpoint_quiet_core=0;assign endpoint_quiet_phy=0;
    end else begin : g_on
        wire [31:0] RANK = {24'b0, context_bound ? bound_rank : rank};
        wire [31:0] OG = RANK / NC, J = RANK % NC;
        wire CONTRIB = RANK < NOG * NC;
        wire [31:0] PF = {16'b0, context_bound ? bound_pf : pf};
        wire [31:0] OF = PF / NC;
        wire [31:0] ROF = BF16 ? OF / 2 : OF;

        reg context_bound,context_fault;
        reg [7:0] bound_rank; reg [15:0] bound_pf;
        reg [63:0] bound_operation;reg [31:0] bound_phase;
        wire config_ok=pf>0 && pf<=PFMAX && pf%NC==0 && (!BF16 || !((pf/NC)&1)) && rank<96; // actual shared8 TP96 admission, AR has only 64 contributors
        wire arm=go && endpoint_rearm_ready && config_ok;
        always @(posedge clk or negedge rst_n) if(!rst_n) begin
          context_bound<=0;context_fault<=0;bound_rank<=0;bound_pf<=0;bound_operation<=0;bound_phase<=0;
        end else begin
          if((go&&!arm) || invalid_partial)context_fault<=1;
          if(arm)begin context_bound<=1;bound_rank<=rank;bound_pf<=pf;
            bound_operation<=context_operation;bound_phase<=context_phase;end
          else if(context_bound && !endpoint_rearm_ready && (rank!=bound_rank || pf!=bound_pf || context_operation!=bound_operation || context_phase!=bound_phase))context_fault<=1;
        end
        // ================= hub issue -> HUBW wire stages ==========================================
        integer k;
        reg started;
        reg [INJ*16-1:0] r_idx;
        reg [INJ-1:0] r_rd;
        always @* begin
            r_idx = '0; r_rd = '0;
            for (integer i = 0; i < INJ; i = i + 1)
                if (CONTRIB && started && !context_fault && (&hub_issue_ready) && k + i < PF) begin
                    r_rd[i] = 1'b1;           // rotated slice order: own slice last in each round
                    r_idx[16*i +: 16] = (NC == 1) ? 16'(k + i) :
                        16'(((J + 1 + 32'((k + i) % NC)) % NC) * OF + 32'((k + i) / NC));
                end
        end
        assign inj_idx = r_idx;
        assign inj_rd  = r_rd;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin k <= 0; started <= 1'b0; end
            else begin
                if(arm)begin started<=1'b1;k<=0;end
                else if (|r_rd) k <= k + INJ;
            end
        wire [INJ-1:0] h_v,hub_idle,hub_raw_v,hub_issue_ready,owner_h_r;
        wire [NPT-1:0] owner_p_r;
        wire hub_sender_quiet,hub_sender_fault;
        wire [INJ*(32+FW)-1:0] hub_raw_d;
        wire [INJ*(16+16+FW)-1:0] h_d;   // {injection ordinal, flit index, data}
        for (genvar i = 0; i < INJ; i = i + 1) begin : g_hub
            ot_ha2_delay_quiet #(.W(32 + FW), .D(HUBW)) u_h (.clk(clk), .rst_n(rst_n), .v_in(r_rd[i]),
                .d_in({16'(k + i), r_idx[16*i +: 16], inj_data[FW*i +: FW]}), .quiet(hub_idle[i]), .v_out(hub_raw_v[i]),
                .d_out(hub_raw_d[(32+FW)*i +: 32+FW]));
        end

        if(OWNER_TRUE_CREDIT && OWNER_BANKED_HALF && NC>1)begin:g_truecredit
          localparam integer TW=16,HW=32+FW;
          wire[INJ-1:0] txv,rxv,rv,backv;
          wire[INJ*HW-1:0] txdata,rxdata;
          wire[INJ*TW-1:0] txtag,rxtag,rtag,backtag;
          wire tq,rq,tf,rf;
          ot_ha2_truecredit_sender #(.W(HW),.INJ(INJ),.AW(OWNER_HUB_QAW),.TAGW(TW)) u_tx
           (.clk(clk),.rst_n(rst_n),.issue_v(r_rd),.arrival_v(hub_raw_v),.arrival_data(hub_raw_d),
            .return_v(backv),.return_tag(backtag),.issue_ready(hub_issue_ready),
            .send_v(txv),.send_data(txdata),.send_tag(txtag),.quiet(tq),.fault(tf));
          for(genvar i=0;i<INJ;i=i+1)begin:g_link
            wire[HW+TW-1:0] frame;
            if(TC_FWD==0)begin
              assign rxv[i]=txv[i];assign frame={txtag[i*TW+:TW],txdata[i*HW+:HW]};
            end else begin:g_forward
              ot_ha2_delay_quiet #(.W(HW+TW),.D(TC_FWD)) u_delay
               (.clk(clk),.rst_n(rst_n),.v_in(txv[i]),.d_in({txtag[i*TW+:TW],txdata[i*HW+:HW]}),
                .v_out(rxv[i]),.d_out(frame),.quiet());
            end
            assign rxdata[i*HW+:HW]=frame[HW-1:0];assign rxtag[i*TW+:TW]=frame[HW+:TW];
            if(TC_RET==0)begin assign backv[i]=rv[i];assign backtag[i*TW+:TW]=rtag[i*TW+:TW];end
            else begin:g_return
              ot_ha2_delay_quiet #(.W(TW),.D(TC_RET)) u_delay
               (.clk(clk),.rst_n(rst_n),.v_in(rv[i]),.d_in(rtag[i*TW+:TW]),
                .v_out(backv[i]),.d_out(backtag[i*TW+:TW]),.quiet());
            end
          end
          if(OWNER_RX_CREDIT!=0)begin:g_rx_credit
            // credit-ready: pipelined receiver, owner_h_r = registered credit-return pulses from the half owner
            ot_ha2_truecredit_receiver_p #(.W(HW),.INJ(INJ),.AW(OWNER_HUB_QAW),.TAGW(TW),.CREDIT(1),.CRD(OWNER_RX_CRD)) u_rx
             (.clk(clk),.rst_n(rst_n),.arrival_v(rxv),.arrival_data(rxdata),.arrival_tag(rxtag),
              .receiver_ready(owner_h_r),.send_v(h_v),.send_data(h_d),.return_v(rv),.return_tag(rtag),
              .quiet(rq),.fault(rf));
          end else begin:g_rx_ready
          ot_ha2_truecredit_receiver #(.W(HW),.INJ(INJ),.AW(OWNER_HUB_QAW),.TAGW(TW)) u_rx
           (.clk(clk),.rst_n(rst_n),.arrival_v(rxv),.arrival_data(rxdata),.arrival_tag(rxtag),
            .receiver_ready(owner_h_r),.send_v(h_v),.send_data(h_d),.return_v(rv),.return_tag(rtag),
            .quiet(rq),.fault(rf));
          end
          assign hub_sender_quiet=tq&&rq;assign hub_sender_fault=tf||rf;
          initial if(OWNER_RX_CREDIT!=0 && OWNER_RX_CRD>8)$fatal(1,"HA2 rx credits exceed the half owner FIFO (FD=8)");
        end else if(OWNER_BANKED_HALF && NC>1)begin:g_hub_credit
          initial if((1<<OWNER_HUB_QAW)<HUBW+2)$fatal(1,"HA2 hub credits do not cover flight");
          ot_ha2_hub_credit_sender #(.W(32+FW),.INJ(INJ),.AW(OWNER_HUB_QAW)) u_sender
            (.clk(clk),.rst_n(rst_n),.issue_v(r_rd),.arrival_v(hub_raw_v),
             .arrival_data(hub_raw_d),.receiver_ready(owner_h_r),.issue_ready(hub_issue_ready),
             .send_v(h_v),.send_data(h_d),.quiet(hub_sender_quiet),.fault(hub_sender_fault));
        end else begin:g_hub_legacy
          assign h_v=hub_raw_v;assign h_d=hub_raw_d;assign hub_issue_ready='1;
          assign hub_sender_quiet=1;assign hub_sender_fault=0;
        end

        // ================= per-port transmit queues, arbiter, switch-ingress credits ==============
        reg  [NPT-1:0] qp_push, qr_push, qp_pop, qr_pop;
        reg  [PWT-1:0] qp_din [0:NPT-1];
        reg  [PWT-1:0] qr_din [0:NPT-1];
        wire [NPT-1:0] qp_empty, qr_empty, qp_ovf, qr_ovf;
        wire [PWT-1:0] qp_head [0:NPT-1];
        wire [PWT-1:0] qr_head [0:NPT-1];
        integer credit [0:NPT-1];
        wire [NPT-1:0] tx_admit,tx_flight_ready,tx_source_quiet,tx_source_fault;
        reg [31:0] cstall;
        reg [NPT-1:0] tv;
        reg [PWT-1:0] tf [0:NPT-1];
        wire [NPT-1:0] lfault,tx_core_idle,rx_core_idle,phy_idle,tx_read_idle;
        for (genvar p = 0; p < NPT; p = p + 1) begin : g_txq
            wire [QAW:0] c0, c1;
            ot_hbm_collective_fifo_adapter #(.ENABLE_SRAM(PACKET_SRAM),.W(PWT), .AW(QAW)) u_qp (.clk(clk), .rst_n(rst_n), .push(qp_push[p]), .din(qp_din[p]),
                .pop(qp_pop[p]), .empty(qp_empty[p]), .dout(qp_head[p]), .ovf(qp_ovf[p]), .count(c0));
            ot_hbm_collective_fifo_adapter #(.ENABLE_SRAM(PACKET_SRAM),.W(PWT), .AW(QAW)) u_qr (.clk(clk), .rst_n(rst_n), .push(qr_push[p]), .din(qr_din[p]),
                .pop(qr_pop[p]), .empty(qr_empty[p]), .dout(qr_head[p]), .ovf(qr_ovf[p]), .count(c1));
            // TX half of the link: wire stages -> TX CDC -> serializer pacing
            wire tx_wire_idle,tx_write_empty;
            wire         w1_v;
            wire [PWT-1:0] w1_d;
            wire tx_empty, tx_ovf, tx_full;
            wire [PWT-1:0] tx_head;
            wire [TXAW:0] tx_freed, tx_cnt;
            reg tx_pop;
            if(LINK_PROTECTION)begin:g_protected_tx
              wire cdc_ready,cdc_fault,cdc_valid,flight_fault,source_ready,local_debt_zero,source_ack_seen;
              ot_hbm_credit_source_session #(.ENABLE(1)) u_credit_source(
                .clk(clk),.rst_n(rst_n),.cold_link_start(cold_link_start),.link_epoch(link_epoch),
                .reserve_valid(tv[p]),.reserve_ready(source_ready),
                .grant_valid(tx_grant_valid[p]),.grant_ready(tx_grant_ready[p]),.grant_word(tx_grant_word[p*72+:72]),
                .ack_valid(tx_ack_valid[p]),.ack_ready(tx_ack_ready[p]),.ack_word(tx_ack_word[p*72+:72]),
                .debt_zero(local_debt_zero),.initial_ack_seen(source_ack_seen),.fault(tx_source_fault[p]));
              assign tx_admit[p]=source_ready&&session_admit&&tx_flight_ready[p]&&!tx_source_fault[p];
              assign tx_source_quiet[p]=local_debt_zero&&!tx_ack_valid[p]&&!tx_grant_valid[p]&&!tx_source_fault[p];
              assign source_debt_zero[p]=local_debt_zero;
              assign source_initial_ack_seen[p]=source_ack_seen;
              ot_hbm_collective_protected_flight #(.ENABLE(1),.W(PWT),.D(WSTG)) u_wtx(
                .clk(clk),.rst_n(rst_n),.in_v(tv[p]),.in_r(tx_flight_ready[p]),.in_d(tf[p]),
                .out_v(w1_v),.out_r(cdc_ready),.out_d(w1_d),.quiet(tx_wire_idle),.fault(flight_fault));
              ot_hbm_collective_protected_cdc_refill #(.ENABLE(1),.W(PWT),.AW(TXAW)) u_txcdc(
                .wclk(clk),.wrst_n(rst_n),.in_v(w1_v),.in_r(cdc_ready),.in_d(w1_d),
                .rclk(pclk),.rrst_n(prst_n),.out_v(cdc_valid),.out_r(tx_pop),.out_d(tx_head),
                .wempty(tx_write_empty),.rempty(),.fault(cdc_fault));
              assign tx_empty=!cdc_valid;
              assign tx_ovf=cdc_fault|flight_fault|tx_source_fault[p];
              assign tx_full=!cdc_ready;assign tx_freed=0;assign tx_cnt=0;
            end else begin:g_legacy_tx
              assign tx_admit[p]=credit[p]>0;assign tx_source_quiet[p]=credit[p]==SWCRED&&!sw_cr_ret[p];
              assign tx_flight_ready[p]=1;assign tx_source_fault[p]=0;
              ot_ha2_delay_quiet #(.W(PWT), .D(WSTG)) u_wtx (.clk(clk), .rst_n(rst_n), .v_in(tv[p]), .d_in(tf[p]),
                .quiet(tx_wire_idle), .v_out(w1_v), .d_out(w1_d));
              ot_link_afifo_quiet #(.W(PWT), .AW(TXAW)) u_txcdc (.wclk(clk), .wrst_n(rst_n), .wr(w1_v), .wdata(w1_d),
                .wempty(tx_write_empty), .wfull(tx_full), .wfreed(tx_freed), .ovf(tx_ovf), .rclk(pclk), .rrst_n(prst_n), .rd(tx_pop),
                .rempty(tx_empty), .rdata(tx_head), .rcount(tx_cnt));
            end
            if(LINK_PROTECTION)begin:g_full_flit_pace
              always @* tx_pop=!tx_empty;
            end else begin:g_legacy_pace
            integer acc;
            always @* tx_pop = !tx_empty && (acc + BITS_X100 >= PWB * 100);
            always @(posedge pclk or negedge prst_n)
                if (!prst_n) acc <= 0;
                else begin : pace
                    integer a;
                    a = acc + BITS_X100;
                    if (a > PWB * 100) a = PWB * 100;
                    if (tx_pop) a = a - PWB * 100;
                    acc <= a;
                end
            end
            assign tx_read_idle[p]=tx_empty&&!tx_pop;
            assign ph_tx_v[p] = tx_pop;
            assign ph_tx_flit[p*PWT +: PWT] = tx_head;
            assign lfault[p] = tx_ovf;
            assign tx_core_idle[p]=(c0==0)&&(c1==0)&&!tv[p]&&tx_wire_idle&&
                tx_write_empty&&tx_source_quiet[p];
        end
        always @* begin
            qp_pop = '0; qr_pop = '0; tv = '0;
            for (integer p = 0; p < NPT; p = p + 1) begin
                tf[p] = '0;
                if (tx_admit[p]) begin
                    if (!qp_empty[p]) begin qp_pop[p] = 1'b1; tv[p] = 1'b1; tf[p] = qp_head[p]; end
                    else if (!qr_empty[p]) begin qr_pop[p] = 1'b1; tv[p] = 1'b1; tf[p] = qr_head[p]; end
                end
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                for (integer p = 0; p < NPT; p = p + 1) credit[p] <= SWCRED;
                cstall <= 0;
            end else begin
                for (integer p = 0; p < NPT; p = p + 1) begin
                    if(!LINK_PROTECTION) credit[p] <= credit[p] - (tv[p] ? 1 : 0) + (sw_cr_ret[p] ? 1 : 0);
                    if (!tx_admit[p] && !(qp_empty[p] && qr_empty[p])) cstall <= cstall + 1;
                end
            end
        assign stat_credit_stall = cstall;

        // ================= RX half of each link + receive buffers ==================================
        reg  [NPT-1:0] rb_pop;
        wire [NPT-1:0] rb_empty, rb_ovf, rx_ovf;
        wire [PWT-1:0] rb_head [0:NPT-1];
        for (genvar p = 0; p < NPT; p = p + 1) begin : g_rx
            if(LINK_PROTECTION)begin:g_protected_rx
              wire ingress_valid,ingress_fault,ingress_quiet_phy;
              ot_hbm_collective_protected_ingress #(.ENABLE(1)) u_ingress(
                .clk(clk),.rst_n(rst_n),.pclk(pclk),.prst_n(prst_n),
                .cold_link_start(cold_link_start),.link_epoch(link_epoch),
                .ph_rx_v(ph_rx_v[p]),.ph_rx_flit(ph_rx_flit[p*PWT+:PWT]),
                .grant_valid(rx_grant_valid[p]),.grant_ready(rx_grant_ready[p]),.grant_word(rx_grant_word[p*72+:72]),
                .ack_valid(rx_ack_valid[p]),.ack_ready(rx_ack_ready[p]),.ack_word(rx_ack_word[p*72+:72]),
                .out_v(ingress_valid),.out_r(rb_pop[p]),.out_d(rb_head[p]),.final_retire(),
                .quiet_core(rx_core_idle[p]),.quiet_phy(ingress_quiet_phy),.fault(ingress_fault),
                .landing_count(),.receive_count());
              assign rb_empty[p]=!ingress_valid;assign rb_ovf[p]=ingress_fault;assign rx_ovf[p]=0;
              assign phy_idle[p]=tx_read_idle[p]&&ingress_quiet_phy;
            end else begin:g_legacy_rx
            wire rx_empty, rx_full,rx_write_empty,rx_wire_idle;
            wire [PWT-1:0] rx_head;
            wire [TXAW:0] rx_freed, rx_cnt;
            ot_link_afifo_quiet #(.W(PWT), .AW(TXAW)) u_rxcdc (.wclk(pclk), .wrst_n(prst_n), .wr(ph_rx_v[p]),
                .wdata(ph_rx_flit[p*PWT +: PWT]), .wempty(rx_write_empty), .wfull(rx_full), .wfreed(rx_freed), .ovf(rx_ovf[p]),
                .rclk(clk), .rrst_n(rst_n), .rd(!rx_empty), .rempty(rx_empty), .rdata(rx_head), .rcount(rx_cnt));
            wire         w2_v;
            wire [PWT-1:0] w2_d;
            ot_ha2_delay_quiet #(.W(PWT), .D(WSTG)) u_wrx (.clk(clk), .rst_n(rst_n), .v_in(!rx_empty), .d_in(rx_head),
                .quiet(rx_wire_idle), .v_out(w2_v), .d_out(w2_d));
            wire [RXAW:0] cnt;
            ot_hbm_collective_fifo_adapter #(.ENABLE_SRAM(PACKET_SRAM),.W(PWT), .AW(RXAW)) u_rb (.clk(clk), .rst_n(rst_n), .push(w2_v), .din(w2_d),
                .pop(rb_pop[p]), .empty(rb_empty[p]), .dout(rb_head[p]), .ovf(rb_ovf[p]), .count(cnt));
            assign rx_core_idle[p]=(cnt==0)&&!rb_pop[p]&&rx_empty&&rx_wire_idle;
            assign phy_idle[p]=tx_read_idle[p]&&!ph_rx_v[p]&&rx_write_empty;
            end
        end
        assign rx_credit = rb_pop;

        wire r_v,dupe,owner_quiet,owner_issue;
        wire [15:0] r_m;wire [FW-1:0] r_d;
        wire [NPT-1:0] partial_v;
        wire [NPT*PWT-1:0] partial_flit;
        wire [NPT-1:0] partial_raw_v;
        wire [NPT*PWT-1:0] partial_raw_flit;
        wire [NPT-1:0] invalid_partial_port;
        wire invalid_partial=|invalid_partial_port;
        for(genvar p=0;p<NPT;p=p+1)begin:g_owner_ports
          assign invalid_partial_port[p]=!rb_empty[p]&&!rb_head[p][PWT-1] &&
            (!context_bound || rb_head[p][FW+24+:8]!=RANK[7:0] ||
             rb_head[p][FW+16+:8]>=NC || rb_head[p][FW+:16]>=OF);
          assign partial_raw_v[p]=rb_pop[p]&&!rb_head[p][PWT-1];
          assign partial_raw_flit[p*PWT+:PWT]=rb_head[p];
        end
        if(OWNER_BANKED_HALF && NC>1)begin:g_peer_launch
          reg [NPT-1:0] pv;
          reg [NPT*PWT-1:0] pd;
          always @(posedge clk or negedge rst_n)if(!rst_n)pv<=0;else pv<=partial_raw_v;
          always @(posedge clk)pd<=partial_raw_flit;
          assign partial_v=pv;assign partial_flit=pd;
        end else begin:g_peer_legacy
          assign partial_v=partial_raw_v;assign partial_flit=partial_raw_flit;
        end
        if(NC>1 && !OWNER_BANKED_HALF)begin:g_owner
          assign owner_h_r='1;assign owner_p_r='1;
          ot_ha2_tu_owner_adapter #(.NC(NC),.NOG(NOG),.PFMAX(PFMAX),.LANES(LANES),.BF16(BF16),
            .INJ(INJ),.NPT(NPT),.LAT(LAT),.SLOTREG(SLOTREG)) u_owner
          (.clk(clk),.rst_n(rst_n),.active(context_bound&&CONTRIB&&!context_fault),.arm(arm),.rank(RANK[7:0]),.pf(PF[15:0]),
            .h_v(h_v),.h_d(h_d),.p_v(partial_v),.p_flit(partial_flit),
            .r_v(r_v),.r_m(r_m),.r_d(r_d),.dupe(dupe),.issue_o(owner_issue),.quiet(owner_quiet));
        end else if(NC>1)begin:g_half_owner
            ot_ha2_tu_owner_banked_half #(.NC(NC),.PFMAX(PFMAX),.LANES(LANES),.BF16(BF16),
              .INJ(INJ),.NPT(NPT),.LAT(LAT),.H_CREDIT((OWNER_RX_CREDIT!=0&&OWNER_TRUE_CREDIT!=0)?1:0)) u_owner
            (.clk(clk),.rst_n(rst_n),.active(context_bound&&CONTRIB&&!context_fault),.arm(arm),.rank(RANK[7:0]),.pf(PF[15:0]),
             .h_v(h_v),.h_d(h_d),.h_r(owner_h_r),.p_v(partial_v),.p_flit(partial_flit),.p_r(owner_p_r),
             .r_v(r_v),.r_m(r_m),.r_d(r_d),.dupe(dupe),.issue_o(owner_issue),.quiet(owner_quiet));
        end else begin:g_gather
          assign owner_h_r='1;assign owner_p_r='1;
          assign r_v=0;assign r_m=0;assign r_d=0;assign dupe=0;assign owner_issue=0;assign owner_quiet=1;
        end
        wire [15:0] my_gi = 16'((OG * NC + J) * ROF + {16'b0, r_m});
        wire [PWT-1:0] res_flit = {1'b1, 8'hFF, 8'(OG), my_gi, r_d};

        // ================= own delivery queue =====================================================
        wire dq_own_empty, dq_own_ovf;
        wire [PWT-1:0] dq_own_head;
        reg dq_own_pop;
        wire [QAW:0] dc0;
        ot_hbm_collective_fifo_adapter #(.ENABLE_SRAM(PACKET_SRAM),.W(PWT), .AW(QAW)) u_dqo (.clk(clk), .rst_n(rst_n), .push(r_v), .din(res_flit),
            .pop(dq_own_pop), .empty(dq_own_empty), .dout(dq_own_head), .ovf(dq_own_ovf), .count(dc0));

        // ================= receive dispatch and delivery =========================================
        integer drot;
        reg [DEL-1:0] dv;
        reg [PWT-1:0] dfl [0:DEL-1];
        always @* begin : dispatch
            integer n, src;
            rb_pop = '0; dq_own_pop = 1'b0; dv = '0;
            for (integer i = 0; i < DEL; i = i + 1) dfl[i] = '0;
            for (integer p = 0; p < NPT; p = p + 1)
                if (!rb_empty[p] && !rb_head[p][PWT-1] && !invalid_partial_port[p] && owner_p_r[p]) rb_pop[p] = 1'b1;        // partials -> slots
            n = 0;
            for (integer i = 0; i < NPT + 1; i = i + 1) begin
                src = (drot + i) % (NPT + 1);
                if (n < DEL) begin
                    if (src == NPT) begin
                        if (!dq_own_empty) begin dq_own_pop = 1'b1; dv[n] = 1'b1; dfl[n] = dq_own_head; n = n + 1; end
                    end else if (!rb_empty[src] && rb_head[src][PWT-1]) begin
                        rb_pop[src] = 1'b1; dv[n] = 1'b1; dfl[n] = rb_head[src]; n = n + 1;
                    end
                end
            end
        end
        wire [DEL-1:0] delivery_idle;
        for (genvar i = 0; i < DEL; i = i + 1) begin : g_del
            ot_ha2_delay_quiet #(.W(PWT), .D(HUBW)) u_d (.clk(clk), .rst_n(rst_n), .v_in(dv[i]), .d_in(dfl[i]),
                .quiet(delivery_idle[i]), .v_out(del_valid[i]), .d_out(del_flit[i*PWT +: PWT]));
        end

        // ================= injection dispatch, result multicast, slot writes =====================
        integer rcnt;                       // results sent (stripe counter)
        always @* begin
            qp_push = '0; qr_push = '0;
            for (integer p = 0; p < NPT; p = p + 1) begin qp_din[p] = '0; qr_din[p] = '0; end
            for (integer i = 0; i < INJ; i = i + 1)
                if (h_v[i]) begin : inj
                    integer ord, f, s, pt;
                    ord = integer'(h_d[(32+FW)*i + FW + 16 +: 16]);
                    f   = integer'(h_d[(32+FW)*i + FW +: 16]);
                    pt  = ord % NPT;
                    if (NC == 1) begin            // gather: the flit IS the result; sent once, multicast
                        qr_push[pt] = 1'b1;
                        qr_din[pt] = {1'b1, 8'hFF, 8'(OG), 16'(OG * PF + f), h_d[(32+FW)*i +: FW]};
                    end else begin
                        s = f / OF;
                        if (s != J) begin
                            qp_push[pt] = 1'b1;
                            qp_din[pt] = {1'b0, 8'(OG * NC + s), 8'(J), 16'(f % OF), h_d[(32+FW)*i +: FW]};
                        end
                    end
                end
            if (r_v) begin
                qr_push[rcnt % NPT] = 1'b1;
                qr_din[rcnt % NPT] = res_flit;
            end
        end
        always @(posedge clk or negedge rst_n)
          if(!rst_n)begin drot<=0;rcnt<=0;end
          else begin drot<=(drot+1)%(NPT+1);if(arm)rcnt<=0;else if(r_v)rcnt<=rcnt+1;end
        reg anyovf;
        always @* begin
            anyovf = dq_own_ovf;
            for (integer p = 0; p < NPT; p = p + 1)
                anyovf = anyovf | qp_ovf[p] | qr_ovf[p] | rb_ovf[p] | rx_ovf[p] | lfault[p];
        end
        assign fault = anyovf | dupe | context_fault | hub_sender_fault;
        // Positive quiet uses actual existing queue/pipe/CDC pointers and credits.
        // It is LOCAL only: shared8 matched fabric release + Dewey publication still required.
        reg [15:0] delivered_words;
        integer delivered_now;
        always @*begin delivered_now=0;for(integer i=0;i<DEL;i=i+1)delivered_now=delivered_now+(del_valid[i]?1:0);end
        always @(posedge clk or negedge rst_n)if(!rst_n)delivered_words<=0;
          else if(arm)delivered_words<=0;else delivered_words<=delivered_words+delivered_now;
        wire [31:0] expected_words=(NC>1)?NOG*NC*ROF:(NOG-1)*PF;
        assign endpoint_quiet_phy=(&phy_idle)&&!(|ph_tx_v)&&!(|ph_rx_v);
        (* ASYNC_REG="TRUE" *)reg phy_q1,phy_q2;
        always @(posedge clk or negedge rst_n)if(!rst_n)begin phy_q1<=0;phy_q2<=0;end
          else begin phy_q1<=endpoint_quiet_phy;phy_q2<=phy_q1;end
        assign endpoint_quiet_core=(&tx_core_idle)&&(&rx_core_idle)&&(&hub_idle)&&(&delivery_idle)&&
          hub_sender_quiet&&!(|partial_v)&&(dc0==0)&&!dq_own_pop&&!(|h_v)&&!(|r_rd)&&!(|del_valid)&&!r_v&&owner_quiet&&
          (!context_bound || ((!CONTRIB||k>=PF)&&delivered_words==expected_words));
        if(LINK_PROTECTION)begin:g_data_quiet
          assign data_queues_quiet=(&tx_core_idle)&&(&rx_core_idle)&&(&hub_idle)&&(&delivery_idle)&&
           hub_sender_quiet&&!(|partial_v)&&(dc0==0)&&!dq_own_pop&&!(|h_v)&&!(|r_rd)&&!(|del_valid)&&!r_v&&owner_quiet&&!fault;
        end
        assign endpoint_rearm_ready=endpoint_quiet_core&&phy_q2&&!fault;
    end
    end endgenerate
endmodule
