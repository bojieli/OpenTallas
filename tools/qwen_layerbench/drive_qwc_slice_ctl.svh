// LAYERBENCH-QWEN smoke drive of the compute-die control slice qwc_slice_ctl (qfd_sys_face + qfd_tt_ctlm_dv + the die's
// relays / landings / reset-tree repeaters between them, cut from dv2f14bn die.v by tools/qwen_layerbench/slice_cut.py).
// ONE PROGRAMME LOAD, as the die does it: after reset the face boots from its config ROM (+OT_ROM_DIR image of
// tools/qwen_split/sys_face_image.py); the KV/system die then sends a HOST kind-13 BEGIN and AUTH record (produced here by
// the REAL KV-side encoder qkd_program_auth_tx = the neighbour die's traffic, injected at the slice edge = the
// qfd_d2d_static output pins rx_payload / prog_rx_v / prog_auth_slot, all on the same edge); the face replays PW0..1023 /
// DW0..7 through the die relays into qfd_tt_ctlm_dv pw / dh; the witness slot then returns a kind-14 record that the REAL
// KV-side receiver qkd_program_witness_rx must accept with the image digest.
// Checks: boot completes; every PW / DW word reaches the tt_ctlm pins bit-exact and in order; the face's ledgers commit
// (rp_program_ready); tt_ctlm reports cal_image_ready; witness accepted; no face / tt_ctlm fault.
// Bench parameter IMG (define SMOKE_IMG) = the image dir (program.memh).
`ifndef SMOKE_IMG
`define SMOKE_IMG "img"
`endif
// QLB-GEN 10-18: the witness pins at the slice edge are the die nets INTO qfd_d2d_static (their relay suffix depends on
// the GEN; dv2f14bn names by default) and the XPF transport probe (SMOKE_HR_OUT = the slice output carrying the hr bus
// at the W5 end, SMOKE_XPF_T = XPF_TRANSPORT_EDGES as elaborated in this slice, slice.json die_params_applied)
`ifndef SMOKE_WIT_V
`define SMOKE_WIT_V o_n_sf_prog_tx_observed_v__r2
`endif
`ifndef SMOKE_WIT_REC
`define SMOKE_WIT_REC o_n_sf_prog_tx_record__r1
`endif
    reg [63:0] prog [0:1031];
    reg [63:0] digest = 64'h51484f5354505247, footer = 0;
    integer pi, pw_seen = 0, dw_seen = 0, pw_bad = 0, dw_bad = 0, boot_cyc = -1, ready_cyc = -1, cal_rdy_cyc = -1;
    reg f_said = 0, c_said = 0;
    reg a_begin = 0, a_auth = 0, a_send = 0; reg [1:0] a_type = 0;
    wire a_tv, a_ov, a_f; wire [547:0] a_rec;
    qkd_program_auth_tx u_kv_atx (.ck(ck), .rst_n(rst_n), .send_slot(a_send), .send_type(a_type), .begin_v(a_begin),
        .begin_epoch(16'h0b0b), .expected_pw(11'd1024), .expected_dw(4'd8), .auth_v(a_auth), .auth_epoch(16'h0b0b),
        .auth_digest(digest), .tx_v(a_tv), .tx_observed_v(a_ov), .tx_record(a_rec), .fault(a_f));
    // the neighbour (KV die, through qfd_d2d_static) at the slice edge: one record in its slot, all pins on one edge
`ifndef SMOKE_COMP_AUTH
    always @* begin
        drv_i_n_sf_prog_rx_v = a_ov; drv_i_n_sf_prog_auth_slot = a_tv;
        drv_i_n_lnk_rx_payload = a_tv ? a_rec : 548'd0;
    end
`else
    // DIAGNOSTIC VARIANT (not the die): the payload / rx_v are held back SMOKE_COMP_AUTH edges at the slice edge so that
    // they meet the auth slot, which the die lands SMOKE_COMP_AUTH edges later (measured by probe()).  Shows what the
    // rest of the programme load does once the landing is fixed.
    reg [547:0] pay_d [0:7]; reg rxv_d [0:7]; integer di;
    always @(posedge ck) begin
        pay_d[0] <= a_tv ? a_rec : 548'd0; rxv_d[0] <= a_ov;
        for (di = 1; di < 8; di = di + 1) begin pay_d[di] <= pay_d[di - 1]; rxv_d[di] <= rxv_d[di - 1]; end
    end
    always @* begin
        drv_i_n_sf_prog_auth_slot = a_tv;
        drv_i_n_sf_prog_rx_v = (`SMOKE_COMP_AUTH == 0) ? a_ov : rxv_d[`SMOKE_COMP_AUTH - 1];
        drv_i_n_lnk_rx_payload = (`SMOKE_COMP_AUTH == 0) ? (a_tv ? a_rec : 548'd0) : pay_d[`SMOKE_COMP_AUTH - 1];
    end
`endif
    // witness: the face's kind-14 record leaves the slice at the qfd_d2d_static input pins
    reg w_rslot = 0; always @(posedge ck) w_rslot <= `SMOKE_WIT_V;
    wire w_commit, w_inst, w_cap, w_f; wire [15:0] w_ep; wire [63:0] w_dg;
    qkd_program_witness_rx u_kv_wrx (.ck(ck), .rst_n(rst_n), .program_begin_v(a_begin), .receive_slot(`SMOKE_WIT_V),
        .rx_v(`SMOKE_WIT_V), .rx_record(`SMOKE_WIT_REC), .expected_epoch(16'h0b0b),
        .expected_digest(digest), .authorized_footer_valid(1'b1), .authorized_footer(footer), .program_commit_v(w_commit),
        .program_commit_epoch(w_ep), .program_commit_digest(w_dg), .program_installed_valid(w_inst), .installed_fusedcap(w_cap),
        .fault(w_f));
    initial begin
        $readmemh({`SMOKE_IMG, "/program.memh"}, prog);
        for (pi = 0; pi < 1032; pi = pi + 1)
            digest = {digest[56:0], digest[63:57]} ^ prog[pi] ^ (pi < 1024 ? 64'(pi) : (64'd1 << 10) | 64'(pi - 1024));
        footer = prog[1023];
    end
    // QLB-GEN: first edge of each record-port fault term (which slot / record raised it)
    reg rp_af_said = 0, rp_sf_said = 0;
    always @(posedge ck) if (rst_n) begin
        if (dut.sys_face.u_record.af === 1'b1 && !rp_af_said) begin rp_af_said = 1;
            $display("SMOKE_INFO record port af rises @%0d (rx_v %b auth_slot %b context_slot %b)", cyc,
                     dut.sys_face.prog_rx_v, dut.sys_face.prog_auth_slot, dut.sys_face.prog_context_slot); end
        if (dut.sys_face.u_record.slot_fault === 1'b1 && !rp_sf_said) begin rp_sf_said = 1;
            $display("SMOKE_INFO record port slot_fault rises @%0d", cyc); end
    end
    // program words at the tt_ctlm pins (after the die relays)
    always @(posedge ck) if (rst_n) begin
        if (dut.tt_ctlm.pw[74]) begin
            if (dut.tt_ctlm.pw[73:64] != pw_seen[9:0] || dut.tt_ctlm.pw[63:0] !== prog[pw_seen]) pw_bad = pw_bad + 1;
            pw_seen = pw_seen + 1;
        end
        if (dut.tt_ctlm.dh[186]) begin
            if (dut.tt_ctlm.dh[185:183] != dw_seen[2:0] || dut.tt_ctlm.dh[182:119] !== prog[1024 + dw_seen]) dw_bad = dw_bad + 1;
            dw_seen = dw_seen + 1;
        end
        if (dut.sys_face.boot_done && boot_cyc < 0) boot_cyc = cyc;
        if (dut.sys_face.rp_program_ready && ready_cyc < 0) ready_cyc = cyc;
        if (dut.tt_ctlm.cal_image_ready && cal_rdy_cyc < 0) cal_rdy_cyc = cyc;
        if (trace_on && (dut.sys_face.fault === 1'b1)) begin
            if (!f_said) $display("SMOKE_INFO face fault @%0d {boot,prog,cal,emb,prov,rp,armed,go} = %b%b%b%b%b%b%b%b st %0d",
                cyc, dut.sys_face.boot_fault, dut.sys_face.prog_fault, dut.sys_face.cal_fault, dut.sys_face.emb_fault,
                dut.sys_face.prov_fault_q, dut.sys_face.rp_fault, dut.sys_face.armed_fault, dut.sys_face.go_fault, dut.sys_face.st);
            if (!f_said) $display("SMOKE_INFO record port {af,jf,cf,wf,slot} = %b%b%b%b%b sink_fault %b sink_ready %b; cal_fault terms t_cf %b l_cf %b e_cf %b cs_fault %b",
                dut.sys_face.u_record.af, dut.sys_face.u_record.jf, dut.sys_face.u_record.cf, dut.sys_face.u_record.wf,
                dut.sys_face.u_record.slot_fault, dut.sys_face.u_record.sink_fault, dut.sys_face.u_record.sink_ready,
                dut.sys_face.t_cf, dut.sys_face.l_cf, dut.sys_face.e_cf, dut.sys_face.cs_fault);
            f_said = 1; smoke_err("sys_face fault");
        end
        if (trace_on && (dut.tt_ctlm.cf === 1'b1)) begin
            if (!c_said) $display("SMOKE_INFO tt_ctlm cf @%0d {head,reloc,cp,start,xpf_ld,xpf_sch} = %b%b%b%b%b%b cal %b", cyc,
                dut.tt_ctlm.head_fault, dut.tt_ctlm.relocation_sticky, dut.tt_ctlm.cp_fault, dut.tt_ctlm.start_fault,
                dut.tt_ctlm.xpf_loader_fault, dut.tt_ctlm.xpf_schedule_fault, dut.tt_ctlm.c_fault);
            c_said = 1; smoke_err("tt_ctlm cf (core / calendar fault)");
        end
        if (a_f) smoke_err("KV-side auth encoder fault");
    end
    // LANDING PROBE (diagnostic, after the load): one-edge pulse on each D2D-end output pin at the slice edge, all on the
    // same edge; the arrival edge at the face pin = the die's relay/landing latency of that pin.  A record bundle must
    // arrive on one edge (static schedule: the face samples payload, valid and slot together).
    integer p0, lat_rxv, lat_auth, lat_ctx, lat_wit, lat_pay, lat_embv, lat_embs, lat_ep, lat_d2df, k;
    task automatic probe(); begin
        lat_rxv = -1; lat_auth = -1; lat_ctx = -1; lat_wit = -1; lat_pay = -1; lat_embv = -1; lat_embs = -1; lat_ep = -1; lat_d2df = -1;
        force drv_i_n_sf_prog_rx_v = 1'b1; force drv_i_n_sf_prog_auth_slot = 1'b1; force drv_i_n_lnk_rx_payload = {548{1'b1}};
        drv_i_n_sf_prog_context_slot = 1; drv_i_n_sf_prog_witness_slot = 1; drv_i_n_sf_emb_rx_v = 1; drv_i_n_sf_emb_rx_slot = 1;
        drv_i_n_lnk_fwd_epoch = 1; drv_i_n_sf_d2d_fault = 1; p0 = cyc;
        @(negedge ck);
        release drv_i_n_sf_prog_rx_v; release drv_i_n_sf_prog_auth_slot; release drv_i_n_lnk_rx_payload;
        drv_i_n_sf_prog_context_slot = 0; drv_i_n_sf_prog_witness_slot = 0; drv_i_n_sf_emb_rx_v = 0; drv_i_n_sf_emb_rx_slot = 0;
        drv_i_n_lnk_fwd_epoch = 0; drv_i_n_sf_d2d_fault = 0;
        for (k = 0; k < 40; k = k + 1) begin
            @(posedge ck); #0.01;
            if (dut.sys_face.prog_rx_v === 1'b1 && lat_rxv < 0) lat_rxv = cyc - p0;
            if (dut.sys_face.prog_auth_slot === 1'b1 && lat_auth < 0) lat_auth = cyc - p0;
            if (dut.sys_face.prog_context_slot === 1'b1 && lat_ctx < 0) lat_ctx = cyc - p0;
            if (dut.sys_face.prog_witness_slot === 1'b1 && lat_wit < 0) lat_wit = cyc - p0;
            if (dut.sys_face.rx_payload[0] === 1'b1 && lat_pay < 0) lat_pay = cyc - p0;
            if (dut.sys_face.emb_rx_v === 1'b1 && lat_embv < 0) lat_embv = cyc - p0;
            if (dut.sys_face.emb_rx_slot === 1'b1 && lat_embs < 0) lat_embs = cyc - p0;
            if (dut.sys_face.fwd_epoch === 1'b1 && lat_ep < 0) lat_ep = cyc - p0;
            if (dut.sys_face.d2d_fault === 1'b1 && lat_d2df < 0) lat_d2df = cyc - p0;
        end
        $display("SMOKE_LAND d2d_rom->sys_face edges: rx_payload %0d prog_rx_v %0d prog_auth_slot %0d prog_context_slot %0d prog_witness_slot %0d emb_rx_v %0d emb_rx_slot %0d fwd_epoch %0d d2d_fault %0d",
                 lat_pay, lat_rxv, lat_auth, lat_ctx, lat_wit, lat_embv, lat_embs, lat_ep, lat_d2df);
        if (!(lat_pay == lat_rxv && lat_rxv == lat_auth && lat_auth == lat_ctx))
            smoke_err("LANDING: record bundle {rx_payload, prog_rx_v, prog_auth_slot, prog_context_slot} not on one edge at the face");
        if (lat_embv != lat_embs) smoke_err("LANDING: emb_rx_v / emb_rx_slot not on one edge at the face (face emb_fault rule)");
    end endtask
`ifdef SMOKE_HR_OUT
    // XPF TRANSPORT PROBE (QLB-GEN, LAYERBENCH G-C1): a one-edge all-ones word on the tt_ctlm hr pin-register output net
    // (as if launched by the hr register on edge X) must leave the slice at the W5 end (landing o register) exactly
    // XPF_TRANSPORT_EDGES - 1 edges later: the compiler's XPF_TRANSPORT_EDGES = hr register + these lane cycles
    integer xp0, lat_hr, kx;
    task automatic xpf_probe(); begin
        lat_hr = -1;
        @(posedge ck); #0.01;                      // just after launch edge X, as the hr register would drive it
        force dut.n_dvw_hr_wi = {453{1'b1}}; xp0 = cyc;
        for (kx = 0; kx < 64 && lat_hr < 0; kx = kx + 1) begin
            @(posedge ck); #0.01;                  // edge X + 1 + kx: a one-flop path shows here with lat 1
            if (kx == 0) release dut.n_dvw_hr_wi;  // one edge wide
            if (&`SMOKE_HR_OUT) lat_hr = cyc - xp0;
        end
        $display("SMOKE_XPF hr lane edges %0d (tt_ctlm.hr -> W5-end slice output); XPF_TRANSPORT_EDGES elaborated %0d (expected %0d = 1 + lane)",
                 lat_hr, `SMOKE_XPF_T, lat_hr + 1);
        if (lat_hr < 0 || `SMOKE_XPF_T != lat_hr + 1) begin
            $display("SMOKE_XPF_MISMATCH XPF_TRANSPORT_EDGES %0d != 1 + measured hr lane edges %0d", `SMOKE_XPF_T, lat_hr);
            smoke_err("XPF_TRANSPORT_EDGES != 1 + measured hr lane edges");
        end else $display("SMOKE_XPF_OK XPF_TRANSPORT_EDGES %0d = 1 + measured hr lane edges %0d", `SMOKE_XPF_T, lat_hr);
    end endtask
`endif
    task automatic slice_programme(); begin
        if (boot_cyc < 0) smoke_err("face boot not done after the idle window");
        $display("SMOKE_INFO boot_done at edge %0d (release %0d)", boot_cyc, rel_cyc);
        a_begin = 1; @(negedge ck); a_begin = 0; a_auth = 1; @(negedge ck); a_auth = 0;
        a_type = 1; a_send = 1; @(negedge ck); a_send = 0; repeat (3) @(negedge ck);
        a_type = 2; a_send = 1; @(negedge ck); a_send = 0;
        for (pi = 0; pi < 4000 && dw_seen < 8; pi = pi + 1) @(negedge ck);
        repeat (40) @(negedge ck);
        $display("SMOKE_INFO PW %0d (bad %0d) DW %0d (bad %0d) at tt_ctlm pins; ledgers ready @%0d; tt cal_image_ready @%0d; control_stores_ready %b",
                 pw_seen, pw_bad, dw_seen, dw_bad, ready_cyc, cal_rdy_cyc, dut.tt_ctlm.control_stores_ready);
        if (pw_seen != 1024 || pw_bad) smoke_err("PW replay at tt_ctlm pins not 1024 bit-exact words");
        if (dw_seen != 8 || dw_bad) smoke_err("DW replay at tt_ctlm pins not 8 bit-exact words");
        if (ready_cyc < 0) smoke_err("face program ledgers did not commit");
        if (cal_rdy_cyc < 0) smoke_err("tt_ctlm calendar image not ready after the programme load");
        drv_i_n_sf_prog_witness_slot = 1; @(negedge ck); drv_i_n_sf_prog_witness_slot = 0;
        repeat (60) @(negedge ck);
        $display("SMOKE_INFO witness installed %b digest %h (expected %h) fault %b", w_inst, w_dg, digest, w_f);
        if (!w_inst || w_dg !== digest) smoke_err("kind-14 witness not accepted by the KV-side receiver");
        probe();
`ifdef SMOKE_HR_OUT
        repeat (20) @(negedge ck);
        xpf_probe();
`endif
    end endtask
