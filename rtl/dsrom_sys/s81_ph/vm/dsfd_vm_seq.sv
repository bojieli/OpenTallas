`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_seq (claude s81-grpA r6, 2026-10-14): the S81 VM SEQUENCER ENGINE -- stage-sequencer engine 12 'vm'
// (die decision D1, el1011-s81die.log 17:58: "assign a VM engine port on the sequencer; ARMB/ARMR/ARMN/XMAP/XGO/LARM/
// P2ID/P2RD issue").  Without it no row-completion slot is ever armed on the die and SU / HC inp never assert.
//
// Prototype D1 pulse-credit client contract is diagnostic only after owner 2026-10-14
// static-schedule decision: no production use of credit gating or delayed completion.
// The compiler must replace the client admission contract with fixed issue slots.
// Stream clock (ck = the dsfd_sp_ctrl / slab command clock), one domain.  It sits between the sequencer's engine pins
// and the engine channel of dsfd_sp_vm_m (cv / cd / dv / dt, the VM's own ot_s81_engine_adapter, QD 8):
//   die pins   c_cmd[84:0] = {v, descriptor 84} from sequencer c12 (pin flop) -> ot_s81_engine_adapter (QD 8 credit,
//              pulse CDC run synchronous) ; c_done[8:0] = {v, tag 8} to d12 ; c_st[1:0] = {online, fault} to s12
//   VM side    v_cv / v_cd[83:0] -> dsfd_sp_vm_m cv / cd ; v_dv / v_dt[7:0] <- dv / dt ; v_flt <- flt (serial, synced)
//   clients    t_inp_su / t_inp_hc: CREDIT PULSES, one per SU / HC job, released when that job's armed operand rows
//              have all landed in the VM (the slot's ARMN completion), IN THE CLIENT'S PROGRAM ORDER.  The slab counts
//              them (inp = credits != 0, one consumed when it takes a head) -- latency-tolerant over die wires.
//
// Op = the sequencer command word {jslot, user 10, pos 21, tok 21, arg 24, op 7}; the VM op is arg[23:21]:
//   0  CLIENT  [20] client (0 SU, 1 HC)  [19:10] base row / 16  [9:0] nrows - 1     (compact: ONE program op per job)
//        base16 = 1023 and nrows - 1 = 1023: GIVE (a job with no VM-produced operand): done + credit at once.
//        Otherwise: allocate a free counter slot (NSLOT 4; stall while none is free), issue to the VM
//          ARMB {slot, notify 0, base} -> ARMR {slot, nrows} -> ARMN {slot, nelems = 16 nrows (full-row contract)}
//          -> FENCE (ARMB of the same slot and base: staging only, harmless after the arm; its immediate done proves
//             the ARMN was ACCEPTED by the VM's serial decode, in order)
//        and return the sequencer done at the FENCE done ("done at once": the job's producers take this op as a
//        predecessor, so every producer write reaches the VM order register after the arm -- arm before write).
//        The client credit is released at the slot's ARMN done (all nelems landed); the slot is free again when both
//        its ARMN and FENCE dones are back (the VM's re-arm rule).
//   4..7  P2ID / P2RD / LARM / XMAP-XGO: passed through 1:1, done = the VM's done of that command.
//   1..3  native ARMB / ARMR / ARMN: refused (client slots are owned by this engine) -> sticky fault, never issued.
// VM tags are PRIVATE (the VM adapter faults a duplicate pending tag; 4 commands of one CLIENT op would share the
// sequencer's): arm family {0, kind 3, 00, slot 2} (kind 1 ARMB, 2 ARMR, 3 ARMN, 4 FENCE), pass-through {1, 0000,
// idx 3} from an 8-entry pool; outstanding VM commands <= 8 (the VM adapter's credits, returned by its dones).
// Faults (sticky, on c_st[0]): the adapter's, a refused op code, a VM done for a tag not outstanding, the VM's flt.
// Negative controls (bench tb_dsfd_vm_seq):
//   OT_VMSEQ_MUT_EARLYCR  the client credit is released at the FENCE done (operands not landed): must FAIL
//   OT_VMSEQ_MUT_ORDER    credits released in completion order instead of program order: must FAIL
//   OT_VMSEQ_MUT_NOFENCE  the sequencer done leaves when the ARMN is issued (no fence): producer race, must FAIL
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_seq #(
    parameter integer NSLOT = 4,        // VM row-completion slots owned by this engine (dsfd_sp_vm_m NSLOT)
    parameter integer CQ = 8,           // per-client credit queue (jobs armed / given, not yet credited)
    parameter integer VQD = 8           // VM engine-adapter credits
) (
    input  wire [0:0]   ck,
    input  wire [0:0]   rst,            // async die reset, active low
    input  wire [84:0]  c_cmd,
    output reg  [8:0]   c_done,
    output reg  [1:0]   c_st,
    output reg          v_cv,
    output reg  [83:0]  v_cd,
    input  wire         v_dv,
    input  wire [7:0]   v_dt,
    input  wire         v_flt,
    output reg          t_inp_su,
    output reg          t_inp_hc
);
    wire clk = ck[0];
    reg [1:0] rq;
    always @(posedge clk or negedge rst[0]) if (!rst[0]) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    wire rn = rq[1];
    // ---------------- sequencer side: pin flop + adapter
    reg cv_q; reg [83:0] cd_q;
    always @(posedge clk or negedge rst[0]) if (!rst[0]) cv_q <= 1'b0; else cv_q <= c_cmd[84];
    always @(posedge clk) cd_q <= c_cmd[83:0];
    wire a_dv, a_f, a_on; wire [7:0] a_dt;
    wire e_v; wire [83:0] e_d; wire e_r;
    reg  e_dnv; reg [7:0] e_dnt;
    ot_s81_engine_adapter #(.QD(8)) u_ad (
        .c_clk(clk), .c_rst_n(rst[0]), .c_cmd_v(cv_q), .c_cmd_d(cd_q), .c_done_v(a_dv), .c_done_tag(a_dt),
        .fault(a_f), .online(a_on),
        .e_clk(clk), .e_rst_n(rst[0]), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(1'b1),
        .e_done_v(e_dnv), .e_done_tag(e_dnt));
    // ---------------- head decode
    wire [2:0] h_code = e_d[30:28];
    wire       h_cli  = e_d[27];
    wire [9:0] h_b16  = e_d[26:17];
    wire [9:0] h_nr1  = e_d[16:7];
    wire [7:0] h_tag  = {e_d[83], e_d[6:0]};
    wire       h_give = h_code == 3'd0 && h_b16 == 10'h3FF && h_nr1 == 10'h3FF;
    wire       h_arm  = h_code == 3'd0 && !h_give;
    wire       h_pass = h_code >= 3'd4;
    wire       h_bad  = h_code == 3'd1 || h_code == 3'd2 || h_code == 3'd3;
    // ---------------- state
    localparam integer QB = $clog2(CQ);
    reg [NSLOT-1:0] s_busy, s_ad, s_fd;
    reg             s_cli  [0:NSLOT-1];
    reg [7:0]       s_tag  [0:NSLOT-1];
    reg [QB-1:0]    s_idx  [0:NSLOT-1];
    reg [CQ-1:0]    q_cmp  [0:1], q_done [0:1], q_live [0:1];
    reg [7:0]       q_tag [0:1][0:CQ-1];
    reg [QB-1:0]    q_wp   [0:1], q_rp [0:1];
    reg [QB:0]      q_n    [0:1];
    reg [7:0]       p_tag  [0:7];
    reg [7:0]       p_busy;
    reg [$clog2(VQD+1)-1:0] vused;
    reg [2:0]       st;                 // 0 idle, 1 ARMB, 2 ARMR, 3 ARMN, 4 FENCE, 5 PASS
    reg [83:0]      w_d;                // the command being expanded
    reg [1:0]       w_s;                // its slot
    reg [2:0]       w_p;                // its pass-through index
    reg             flt_bad, flt_tag;
    reg [1:0]       vf_s;
    always @(posedge clk) vf_s <= {vf_s[0], v_flt};
    // free slot / pass index (lowest)
    reg [1:0] f_s; reg f_ok; reg [2:0] f_p; reg f_pok; integer i;
    always @* begin
        f_ok = 1'b0; f_s = 2'd0; f_pok = 1'b0; f_p = 3'd0;
        for (i = NSLOT - 1; i >= 0; i = i - 1) if (!s_busy[i]) begin f_ok = 1'b1; f_s = i[1:0]; end
        for (i = 7; i >= 0; i = i - 1) if (!p_busy[i]) begin f_pok = 1'b1; f_p = i[2:0]; end
    end
    // done queue to the adapter (<= 2 pushes a cycle: GIVE take + one VM-done-driven done)
    localparam integer DQ = 16;
    reg [7:0] dq [0:DQ-1]; reg [3:0] dq_h, dq_t; reg [4:0] dq_n;
    wire dq_room2 = dq_n <= DQ - 2;
    wire cq_room  = q_n[h_cli] < CQ;
    // take the head (idle only, so client entries are pushed in command order)
    wire tk_give = e_v && st == 3'd0 && h_give && cq_room && dq_room2;
    wire tk_arm  = e_v && st == 3'd0 && h_arm  && cq_room && f_ok;
    wire tk_pass = e_v && st == 3'd0 && h_pass && f_pok;
    wire tk_bad  = e_v && st == 3'd0 && h_bad;
    assign e_r = tk_give || tk_arm || tk_pass || tk_bad;
    // VM issue (one command a cycle, within the VM adapter's credits)
    wire v_ok = vused < VQD;
    wire is_b = st == 3'd1 && v_ok, is_r = st == 3'd2 && v_ok, is_n = st == 3'd3 && v_ok, is_f = st == 3'd4 && v_ok,
         is_p = st == 3'd5 && v_ok;
    wire v_iss = is_b || is_r || is_n || is_f || is_p;
    wire [13:0] w_base = {w_d[26:17], 4'd0};
    wire [14:0] w_nr   = {5'd0, w_d[16:7]} + 15'd1;
    wire [18:0] w_ne   = {w_nr, 4'd0};
    // VM done decode
    wire       d_pass = v_dv && v_dt[7];
    wire [2:0] d_pi   = v_dt[2:0];
    wire [2:0] d_kind = v_dt[6:4];
    wire [1:0] d_sl   = v_dt[1:0];
    wire       d_armn = v_dv && !v_dt[7] && d_kind == 3'd3;
    wire       d_fen  = v_dv && !v_dt[7] && d_kind == 3'd4;
    wire       d_imm  = v_dv && !v_dt[7] && (d_kind == 3'd1 || d_kind == 3'd2);
    wire       d_ok   = d_pass ? p_busy[d_pi] : (d_armn || d_fen || d_imm) ? s_busy[d_sl] : 1'b0;
    // a done to the sequencer driven by a VM done (fence of an arm, or a pass-through command)
`ifdef OT_VMSEQ_MUT_NOFENCE
    wire       vd_push = (d_pass && d_ok) || is_n;                    // MUTANT: done when the ARMN is issued
    wire [7:0] vd_tag  = is_n ? s_tag[w_s] : p_tag[d_pi];
`else
    wire       vd_push = (d_pass || d_fen) && d_ok;
    wire [7:0] vd_tag  = d_pass ? p_tag[d_pi] : s_tag[d_sl];
`endif
    // credit release: per client, head entry complete -> pulse, pop
`ifdef OT_VMSEQ_MUT_EARLYCR
    wire       c_ev = d_fen && d_ok;                                   // MUTANT: credit at the fence (not landed)
`else
    wire       c_ev = d_armn && d_ok;
`endif
    wire [1:0] cr_pop;
`ifdef OT_VMSEQ_MUT_ORDER
    // MUTANT: any complete entry is credited (completion order), not only the head
    reg [1:0] cr_any;
    always @* begin : p_any integer c2; for (c2 = 0; c2 < 2; c2 = c2 + 1) cr_any[c2] = q_n[c2] != 0 && (|q_cmp[c2]); end
    assign cr_pop = cr_any;
`else
    assign cr_pop = {q_n[1] != 0 && q_cmp[1][q_rp[1]] && q_done[1][q_rp[1]], q_n[0] != 0 && q_cmp[0][q_rp[0]] && q_done[0][q_rp[0]]};
`endif
    always @(posedge clk) begin : p_main integer c, k;
        if (!rn) begin
            st <= 3'd0; s_busy <= 0; s_ad <= 0; s_fd <= 0; p_busy <= 8'd0; vused <= 0; v_cv <= 1'b0;
            for (c = 0; c < 2; c = c + 1) begin q_cmp[c] <= 0; q_done[c] <= 0; q_live[c] <= 0; q_wp[c] <= 0; q_rp[c] <= 0; q_n[c] <= 0; end
            dq_h <= 0; dq_t <= 0; dq_n <= 0; e_dnv <= 1'b0; t_inp_su <= 1'b0; t_inp_hc <= 1'b0;
            flt_bad <= 1'b0; flt_tag <= 1'b0;
        end else begin
            // ---- take
            if (tk_arm)  begin st <= 3'd1; w_d <= e_d; w_s <= f_s; end
            if (tk_pass) begin st <= 3'd5; w_d <= e_d; w_p <= f_p; end
            if (tk_bad)  flt_bad <= 1'b1;
            if (tk_arm) begin
                s_busy[f_s] <= 1'b1; s_ad[f_s] <= 1'b0; s_fd[f_s] <= 1'b0; s_cli[f_s] <= h_cli; s_tag[f_s] <= h_tag;
                s_idx[f_s] <= q_wp[h_cli];
            end
            if (tk_pass) begin p_busy[f_p] <= 1'b1; p_tag[f_p] <= h_tag; end
            // ---- VM issue
            v_cv <= v_iss;
            if (is_b) v_cd <= {1'b0, w_d[82:31], 3'd1, w_s, 1'b0, 4'd0, w_base, 3'd1, 2'd0, w_s};
            if (is_r) v_cd <= {1'b0, w_d[82:31], 3'd2, w_s, 4'd0, w_nr, 3'd2, 2'd0, w_s};
            if (is_n) v_cd <= {1'b0, w_d[82:31], 3'd3, w_s, w_ne, 3'd3, 2'd0, w_s};
            if (is_f) v_cd <= {1'b0, w_d[82:31], 3'd1, w_s, 1'b0, 4'd0, w_base, 3'd4, 2'd0, w_s};
            if (is_p) v_cd <= {1'b1, w_d[82:7], 4'd0, w_p};
            if (is_b) st <= 3'd2; if (is_r) st <= 3'd3; if (is_n) st <= 3'd4; if (is_f || is_p) st <= 3'd0;
            vused <= vused + (v_iss ? 1 : 0) - (v_dv ? 1 : 0);
            // ---- VM dones
            if (v_dv && !d_ok) flt_tag <= 1'b1;
            if (d_pass && d_ok) p_busy[d_pi] <= 1'b0;
            if (d_armn && d_ok) s_ad[d_sl] <= 1'b1;
            if (d_fen && d_ok)  s_fd[d_sl] <= 1'b1;
            for (k = 0; k < NSLOT; k = k + 1)
                if (s_busy[k] && (s_ad[k] || (d_armn && d_ok && d_sl == k)) && (s_fd[k] || (d_fen && d_ok && d_sl == k)))
                    s_busy[k] <= 1'b0;
            // ---- client queues: push (take), complete (ARMN done), pop (credit)
            for (c = 0; c < 2; c = c + 1) begin
                if ((tk_arm || tk_give) && h_cli == c) begin
                    q_cmp[c][q_wp[c]] <= tk_give;
                    q_done[c][q_wp[c]] <= 1'b0; q_live[c][q_wp[c]] <= 1'b1; q_tag[c][q_wp[c]] <= h_tag;
                    q_wp[c] <= (q_wp[c] == CQ - 1) ? 0 : q_wp[c] + 1'b1;
                end
                if (c_ev && s_cli[d_sl] == c) q_cmp[c][s_idx[d_sl]] <= 1'b1;
                // Credit cannot overtake the endpoint's command completion. In particular GIVE
                // has no VM latency, whereas the adapter completion crosses its return FIFO.
                for (k = 0; k < CQ; k = k + 1)
                    if (a_dv && q_live[c][k] && q_tag[c][k] == a_dt) q_done[c][k] <= 1'b1;
                if (cr_pop[c]) q_live[c][q_rp[c]] <= 1'b0;
`ifdef OT_VMSEQ_MUT_ORDER
                if (cr_pop[c]) begin : p_mo integer z; reg fnd; fnd = 1'b0;
                    for (z = 0; z < CQ; z = z + 1) if (!fnd && q_cmp[c][z]) begin q_cmp[c][z] <= 1'b0; fnd = 1'b1; end
                    q_rp[c] <= (q_rp[c] == CQ - 1) ? 0 : q_rp[c] + 1'b1;
                end
`else
                if (cr_pop[c]) begin q_cmp[c][q_rp[c]] <= 1'b0; q_rp[c] <= (q_rp[c] == CQ - 1) ? 0 : q_rp[c] + 1'b1; end
`endif
                q_n[c] <= q_n[c] + (((tk_arm || tk_give) && h_cli == c) ? 1 : 0) - (cr_pop[c] ? 1 : 0);
            end
            t_inp_su <= cr_pop[0]; t_inp_hc <= cr_pop[1];
            // ---- done queue -> adapter (one a cycle)
            begin : p_dq reg [3:0] t; reg [4:0] n;
                t = dq_t; n = dq_n;
                if (tk_give) begin dq[t] <= h_tag; t = t + 1'b1; n = n + 1'b1; end
                if (vd_push) begin dq[t] <= vd_tag; t = t + 1'b1; n = n + 1'b1; end
                e_dnv <= dq_n != 0;
                if (dq_n != 0) begin e_dnt <= dq[dq_h]; dq_h <= dq_h + 1'b1; n = n - 1'b1; end
                dq_t <= t; dq_n <= n;
            end
        end
    end
    // ---------------- die outputs (flops)
    always @(posedge clk or negedge rst[0])
        if (!rst[0]) begin c_done <= 9'd0; c_st <= 2'b00; end
        else begin c_done <= {a_dv, a_dt}; c_st <= {a_on, a_f | flt_bad | flt_tag | vf_s[1]}; end
endmodule
