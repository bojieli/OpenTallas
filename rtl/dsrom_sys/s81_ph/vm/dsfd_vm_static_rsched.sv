`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_static_rsched (claude S81 VM owner r8, 2026-10-14): the fixed-rule READ schedule of the static VM, in front of
// dsfd_vm_static512_suhc (FSR -> 2 relay levels -> 128 real 1R1W SRAM banks -> return store -> native return map).
// No ready, credit, queue, arbitration or schedule extension: every output is a fixed function of the compiled request
// pattern, delayed by a fixed number of edges.
//   P     pin register: SU 16 + HC 2 native read requests (row 14), 12 auxiliary requests (row 14), sampled at edge P.
//         RETURN SLOT (fixed function, the FSR legality table): SU p (2..15) -> slot p; SU0 -> row[1:0];
//         SU1 -> row[1:0] unless that slot is taken this edge by SU0 / SU2 / SU3, then 4 + row[1:0];
//         HC h -> 16 + row[1:0]; aux a -> 20 + a.  Collisions / illegal low bits are FSR schedule faults.
//         GROUP = free-running edge counter mod 8 (every edge is its own return group; two parity buffers suffice
//         because every group is released exactly 10 edges after its FSR sample).
//   P+1   FSR samples (E0 of the static512 timeline)            P+11  fixed release (E0 + 10): return store -> o_v
//   native_v / native_data / aux group rows are valid in the cycle after P+11 (a die output register samples at P+12).
//   The release chain is the request vector itself delayed 10 edges: release_mask = the slots of that edge's requests,
//   native_expected_v / native_release_slot = that edge's SU/HC requests and slots, aux_expected = its aux requests.
//   A row missing at its release edge is a fault of the return leaf (never waited for).
// ---------------------------------------------------------------------------------------------------------------
// PINREG=1 (READ_PIPE 4, L16; native pin audit 2026-10-15, rsched r1 view capture 389.7 / launch 264.7): every input is a
// pin register (+1 edge on every output, uniform), release_v / prepare_v are registered ORs of the chain (same edge), and
// expected_v / release_slot / aux_expected / mx_expected / mx_rslot are registered (+1 more: they align with the
// pin-registered return lanes, whose o_v is one edge later).  The hard master is dsfd_vm_static_rsched_p.
module dsfd_vm_static_rsched #(parameter integer PINREG=0) (
    input  wire          ck, rst_n,
    input  wire [15:0]   su_v,  input wire [223:0] su_row,
    input  wire [1:0]    hc_v,  input wire [27:0]  hc_row,
    input  wire [11:0]   aux_v, input wire [167:0] aux_row,
    // Engram MIX4 endpoint (dsfd_engram_mix4_c rq_v / rq_row): 20 reads an edge.  RETURN SLOT (fixed function): lane i
    // -> slot {G(i), row[1:0]}, G = 0, 1, 2, 3 for lanes 0..15 (SU ports 4G .. 4G+3), G = 5 for lanes 16..19 (aux 0..3);
    // the MIX4 layout's rows (row[1:0] = lane[1:0] ^ beat[1:0]) give each group four distinct low bits.  Slot s rides
    // logical port s (0..15: SU ports, 20..31: aux s - 20; HC slots 16..19 are never used by MIX).  The compiler gives
    // MIX its own edges: a port carrying an SU/HC/aux request and a MIX request on one edge is a schedule fault.
    input  wire [19:0]   mx_v,  input wire [279:0] mx_row,
    output wire [19:0]   mx_expected, output wire [99:0] mx_rslot,
    output reg           sched_fault,
    output reg  [17:0]   n_v,   output reg [251:0] n_row, output reg [89:0] n_slot, output reg [2:0] n_group,
    output reg  [11:0]   a_v,   output reg [167:0] a_row,
    output wire          release_v, output wire [2:0] release_group, output wire [31:0] release_mask,
    // Same compiled descriptor one edge early: return lanes register completion
    // after accepting the E9 records and consume all four tokens at E10 release.
    output wire          prepare_v, output wire [2:0] prepare_group, output wire [31:0] prepare_mask,
    output wire [17:0]   expected_v, output wire [89:0] release_slot, output wire [11:0] aux_expected,
    output wire [14*30-1:0] obs_row       // logical rows of the FSR-sampled requests (engine early-read assertion)
);
    reg [1:0] rr;
    always @(posedge ck or negedge rst_n) if (!rst_n) rr <= 2'b00; else rr <= {rr[0], 1'b1};
    wire rn = rr[1];

    reg [17:0] qv; reg [251:0] qr; reg [11:0] qav; reg [167:0] qar; reg [2:0] grp;
    reg [19:0] qmv; reg [279:0] qmr; reg [99:0] qms;
    always @* begin : p_mxs integer i;
        for (i = 0; i < 20; i = i + 1)
`ifdef OT_VM_RSCHED_MUT_MIXSLOT
            qms[5*i +: 5] = {3'(i >> 2), qmr[14*i +: 2]};          // MUTANT: lanes 16..19 onto the HC slots 16..19
`else
            qms[5*i +: 5] = {(i < 16) ? 3'(i >> 2) : 3'd5, qmr[14*i +: 2]};
`endif
    end
    // Native1b: the request merge/slot logic now runs on the PIN side and its results are the registered stage
    // (same edge the q registers used to capture): every die output n_* / a_* is a flop (measured reg->out -10.1/-5.2 ps
    // through the merge after the q registers).  Zero cycles; the descriptor chain and faults keep their edges.
    always @(posedge ck) if (!rn) grp <= 3'd0; else grp <= grp + 3'd1;
    generate if (PINREG != 0) begin : g_pin
        reg [17:0] iv; reg [251:0] ir; reg [11:0] iav; reg [167:0] iar; reg [19:0] imv; reg [279:0] imr;
        always @(posedge ck) begin
            if (!rn) begin iv <= 18'd0; iav <= 12'd0; imv <= 20'd0; end
            else begin iv <= {hc_v, su_v}; iav <= aux_v; imv <= mx_v; end
            ir <= {hc_row, su_row}; iar <= aux_row; imr <= mx_row;
        end
        always @* begin qv = iv; qav = iav; qmv = imv; qr = ir; qar = iar; qmr = imr; end
    end else begin : g_nopin
        always @* begin qv = {hc_v, su_v}; qav = aux_v; qmv = mx_v; qr = {hc_row, su_row}; qar = aux_row; qmr = mx_row; end
    end endgenerate
    // MIX merge onto the 30 logical ports (fixed function of the compiled slots).
    // Native1 structural repair (measured rsched CTS: reg->out n_row -10.1 ps TT placement at 770; the 20-deep
    // last-writer-wins chain of runtime-indexed writes sat between the q registers and the die pins): each MIX lane's
    // target port is decoded in parallel and every port takes a one-hot AND-OR of its lanes.  Identical for every legal
    // compiled schedule; a collision (two writers on one port, or a writer on an occupied port) is the unchanged sticky
    // m_bad fault and its row value is then the OR of the writers (a fault, never a production value).  Zero cycles.
    reg [17:0] pv_n; reg [251:0] pr_n; reg [11:0] pav_n; reg [167:0] par_n; reg [29:0] mo_n; reg m_bad;
    reg [4:0] mport [0:19];
    always @* begin : p_port integer i; reg [4:0] s; reg hc0;
        hc0 = 1'b0;
        for (i = 0; i < 20; i = i + 1) begin
            s = qms[5*i +: 5];
            if (s < 5'd16) mport[i] = s;
            else if (s < 5'd20) begin mport[i] = (qmv[i] && hc0) ? 5'd17 : 5'd16; if (qmv[i]) hc0 = 1'b1; end
            else mport[i] = 5'd18 + (s - 5'd20);
        end
    end
    always @* begin : p_merge integer i, port; reg [13:0] row; reg any; reg [29:0] hits;
        m_bad = 1'b0; mo_n = 30'd0;
        for (port = 0; port < 30; port = port + 1) begin
            any = 1'b0; row = 14'd0; hits[port] = 1'b0;
            for (i = 0; i < 20; i = i + 1) if (qmv[i] && mport[i] == port[4:0]) begin
                if (any) m_bad = 1'b1;
                any = 1'b1; row = row | qmr[14*i +: 14];
            end
            mo_n[port] = any;
            if (port < 18) begin
                if (any && qv[port]) m_bad = 1'b1;
                pv_n[port] = qv[port] | any; pr_n[14*port +: 14] = any ? row : qr[14*port +: 14];
            end else begin
                if (any && qav[port-18]) m_bad = 1'b1;
                pav_n[port-18] = qav[port-18] | any; par_n[14*(port-18) +: 14] = any ? row : qar[14*(port-18) +: 14];
            end
        end
        for (i = 0; i < 20; i = i + 1) if (qmv[i] && qms[5*i +: 2] != qmr[14*i +: 2]) m_bad = 1'b1;  // slot lane = row[1:0]
    end

    reg [89:0] slot_n;
    always @* begin : p_slot integer p; reg [1:0] l0, l1;
        for (p = 2; p < 16; p = p + 1) slot_n[5*p +: 5] = p[4:0];
        l0 = pr_n[0 +: 2]; l1 = pr_n[14 +: 2];
        slot_n[0 +: 5] = {3'd0, l0};
`ifdef OT_VM_RSCHED_MUT_SLOT
        slot_n[5 +: 5] = {3'd0, l1};                      // MUTANT: SU1 never moves off a taken slot
`else
        slot_n[5 +: 5] = ((pv_n[0] && l0 == l1) || (pv_n[2] && l1 == 2'd2) || (pv_n[3] && l1 == 2'd3)) ? {3'd1, l1} : {3'd0, l1};
`endif
        slot_n[80 +: 5] = {3'd4, pr_n[14*16 +: 2]};
        slot_n[85 +: 5] = {3'd4, pr_n[14*17 +: 2]};
    end
    // every MIX request must land on exactly its compiler slot (SU0 / SU1 / HC slot functions included)
    reg s_bad;
    always @* begin : p_mchk integer i; reg [4:0] s; integer port; reg hc0;
        s_bad = 1'b0; hc0 = 1'b0;
        for (i = 0; i < 20; i = i + 1) if (qmv[i]) begin
            s = qms[5*i +: 5];
            if (s < 5'd16) port = s; else if (s < 5'd20) begin port = hc0 ? 17 : 16; hc0 = 1'b1; end else port = 18 + (s - 20);
            if (port < 18 && slot_n[5*port +: 5] != s) s_bad = 1'b1;
        end
    end
    // registered request stage (the die pin registers of n_* / a_*)
    reg [17:0] pv; reg [251:0] pr; reg [11:0] pav; reg [167:0] par; reg [29:0] mo; reg [89:0] slot;
    reg [19:0] qmv_r; reg [99:0] qms_r; reg bad0;
    always @(posedge ck) begin
        if (!rn) begin pv <= 18'd0; pav <= 12'd0; mo <= 30'd0; qmv_r <= 20'd0; bad0 <= 1'b0; end
        else begin pv <= pv_n; pav <= pav_n; mo <= mo_n; qmv_r <= qmv; bad0 <= m_bad || s_bad; end
        pr <= pr_n; par <= par_n; slot <= slot_n; qms_r <= qms;
    end
    always @(posedge ck) if (!rn) sched_fault <= 1'b0; else if (bad0) sched_fault <= 1'b1;

    // FSR pin feed (registered: the FSR's own pin stage samples these at P+1 -- this stage is the die pin register)
    always @* begin n_v = pv; n_row = pr; n_slot = slot; n_group = grp; a_v = pav; a_row = par; end
    assign obs_row = {par, pr};

    // release chain: stage k holds the FSR sample of edge (P+1)+(k-1); stage 10 is sampled by the return leaves at E0+10
    // (the static512 template: request E0, bank E4..E6, response relays E7/E8, return store E9, fixed release E10)
    reg [17:0] dv [1:11]; reg [89:0] ds [1:11]; reg [2:0] dg [1:10]; reg [11:0] da [1:11]; reg [29:0] dm [1:11];
    reg [19:0] dxv [1:11]; reg [99:0] dxs [1:11];
    reg [31:0] masks [1:10]; reg [31:0] pin_mask;
    always @* begin : p_pin_mask integer p;
        pin_mask=32'd0;
        for(p=0;p<18;p=p+1)if(pv[p])pin_mask[slot[5*p+:5]]=1'b1;
        for(p=0;p<12;p=p+1)if(pav[p])pin_mask[20+p]=1'b1;
    end
    // Registered masks move with the already registered descriptor. This adds
    // 320 control FF and no data/request/release edge; output pins are registers.
    always @(posedge ck) begin : p_masks integer k;
        if(!rn)for(k=1;k<=10;k=k+1)masks[k]<=32'd0;
        else begin masks[1]<=pin_mask;for(k=2;k<=10;k=k+1)masks[k]<=masks[k-1];end
    end
    always @(posedge ck) begin : p_chain integer k;
        if (!rn) for (k = 1; k <= 11; k = k + 1) begin dv[k] <= 18'd0; da[k] <= 12'd0; dm[k] <= 30'd0; dxv[k] <= 20'd0; end
        else begin
            dv[1] <= pv; ds[1] <= slot; dg[1] <= grp; da[1] <= pav; dm[1] <= mo; dxv[1] <= qmv_r; dxs[1] <= qms_r;
            for (k = 2; k <= 10; k = k + 1) begin dv[k] <= dv[k-1]; ds[k] <= ds[k-1]; dg[k] <= dg[k-1]; da[k] <= da[k-1]; end
            for (k = 2; k <= 11; k = k + 1) begin dm[k] <= dm[k-1]; dxv[k] <= dxv[k-1]; dxs[k] <= dxs[k-1]; end
            dv[11] <= dv[10]; ds[11] <= ds[10]; da[11] <= da[10];
        end
    end
    generate if (PINREG != 0) begin : g_pout
        reg rel_v_q, pre_v_q; reg [17:0] ev_q; reg [89:0] es_q; reg [11:0] ea_q; reg [19:0] mxe_q; reg [99:0] mxs_q;
        always @(posedge ck) begin
            if (!rn) begin rel_v_q <= 1'b0; pre_v_q <= 1'b0; ev_q <= 18'd0; ea_q <= 12'd0; mxe_q <= 20'd0; end
            else begin
                rel_v_q <= |dv[9] | |da[9];                  // = |dv[10] | |da[10] at the same edge
                pre_v_q <= |dv[8] | |da[8];                  // = |dv[9]  | |da[9]
                ev_q <= dv[11] & ~dm[11][17:0]; ea_q <= da[11] & ~dm[11][29:18]; mxe_q <= dxv[11];
            end
            es_q <= ds[11]; mxs_q <= dxs[11];
        end
        assign release_v = rel_v_q; assign prepare_v = pre_v_q;
        assign expected_v = ev_q; assign release_slot = es_q; assign aux_expected = ea_q;
        assign mx_expected = mxe_q; assign mx_rslot = mxs_q;
    end else begin : g_nopout
        assign release_v = |dv[10] | |da[10];
        assign prepare_v = |dv[9] | |da[9];
        assign expected_v = dv[11] & ~dm[11][17:0];
        assign release_slot = ds[11];
        assign aux_expected = da[11] & ~dm[11][29:18];
        assign mx_expected = dxv[11];
        assign mx_rslot = dxs[11];
    end endgenerate
    assign release_group = dg[10];
    assign release_mask = masks[10];
    assign prepare_group = dg[9];
`ifdef OT_VM_RSCHED_MUT_PREPARE
    assign prepare_mask = masks[8]; // DUT mutant: stale completion descriptor.
`else
    assign prepare_mask = masks[9];
`endif
endmodule
// Hard master of the READ_PIPE 4 (L16) native read: every input pin-registered, every output a flop.
module dsfd_vm_static_rsched_p (
    input  wire          ck, rst_n,
    input  wire [15:0]   su_v,  input wire [223:0] su_row,
    input  wire [1:0]    hc_v,  input wire [27:0]  hc_row,
    input  wire [11:0]   aux_v, input wire [167:0] aux_row,
    input  wire [19:0]   mx_v,  input wire [279:0] mx_row,
    output wire [19:0]   mx_expected, output wire [99:0] mx_rslot,
    output wire          sched_fault,
    output wire [17:0]   n_v,   output wire [251:0] n_row, output wire [89:0] n_slot, output wire [2:0] n_group,
    output wire [11:0]   a_v,   output wire [167:0] a_row,
    output wire          release_v, output wire [2:0] release_group, output wire [31:0] release_mask,
    output wire          prepare_v, output wire [2:0] prepare_group, output wire [31:0] prepare_mask,
    output wire [17:0]   expected_v, output wire [89:0] release_slot, output wire [11:0] aux_expected,
    output wire [14*30-1:0] obs_row
);
    dsfd_vm_static_rsched #(.PINREG(1)) u (.ck(ck), .rst_n(rst_n), .su_v(su_v), .su_row(su_row), .hc_v(hc_v), .hc_row(hc_row),
        .aux_v(aux_v), .aux_row(aux_row), .mx_v(mx_v), .mx_row(mx_row), .mx_expected(mx_expected), .mx_rslot(mx_rslot),
        .sched_fault(sched_fault), .n_v(n_v), .n_row(n_row), .n_slot(n_slot), .n_group(n_group), .a_v(a_v), .a_row(a_row),
        .release_v(release_v), .release_group(release_group), .release_mask(release_mask),
        .prepare_v(prepare_v), .prepare_group(prepare_group), .prepare_mask(prepare_mask),
        .expected_v(expected_v), .release_slot(release_slot), .aux_expected(aux_expected), .obs_row(obs_row));
endmodule
`default_nettype wire
