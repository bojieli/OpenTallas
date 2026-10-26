// Generated A0-only ABI from ot_s81_svc_job: absent result channels have no pins.
// All retained job/query behavior is edge-identical; no registers/stages added.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_svc_job (s81-svceng-1011, 2026-10-11): the per-slab job endpoint of the S81 HBM scan service (engine 4 of
// ADAPTER_CONTRACT_1011).  One dsfd_svc slab per HBM stack; the NS slabs of a die share engine 4 through dsfd_svc_join
// (the single pinned adapter), which sends every slab each descriptor as a job pulse j_cmd = {v, arg 24, tag 8} and
// joins the slabs' in-order job dones j_dn = {fault, done}.
// Frame protocol: s81-svceng-1011.log "SVC FRAME PROTOCOL v1.1".  Header word (the 512-bit data word of the first
// beat): [511:508] type, [507] END, [506:503] q: quadrant mask / results: source id (0..3 quadrant, 4 index reader),
// [502:495] tag {slot, op}, [491:480] len (payload words that follow).
//   q side (die pin q 515 = {fault, live, data 512, v}, valid-only, no ready): a q frame passes to the slab core
//     only while the job at the issue head is armed, carries its tag and does not exceed the job's q-frame count
//     arg[14:7]; otherwise the WHOLE frame is discarded and the sticky fault set (fail closed: never delivered).  The
//     issue head advances when the job's last q frame has passed.  Same cycle (no register: the q pin flop is the core's).
//   result side: observes the core's output pins ad (a0 / a1), xd and od (no added cycle); a result frame whose
//     header has END marks its source done for the job named by its tag; the head job is done (j_dn[0] pulse, in
//     order) when every source of arg[4:0] (bit i = source i) has sent its END.  An END for a tag that is not pending,
//     a duplicate END, or an END from a source not in the job's set is a fault.
//   arg[6:5], arg[23:15] reserved (0); arg[14:7] = 0 or arg[4:0] = 0 is a wrong descriptor (fault).
// MUT: 1 q frames pass without an armed job (dropped-start check off), 5 early done (done at the job's first END).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_svc_job_a0 #(parameter integer JQ = 8, MUT = 0) (
    input  wire          ck, rs_n,
    input  wire [32:0]   j_cmd,          // {v, arg 24, tag 8} from dsfd_svc_join (pin-registered here)
    output reg  [1:0]    j_dn,           // {fault, done}
    input  wire [514:0]  q,              // die pin (VM query frames)
    output wire [514:0]  core_q,         // to the slab core
    input  wire [512:0]  ad              // sole a0 result channel (live valid+payload)
);
    localparam integer AW = $clog2(JQ);
    reg jv; reg [31:0] jc;
    always @(posedge ck or negedge rs_n) if (!rs_n) jv <= 1'b0; else jv <= j_cmd[32];
    always @(posedge ck) jc <= j_cmd[31:0];
    // job table (ring, in order): tag, arg, END-seen
    reg [7:0]  tg [0:JQ-1]; reg [23:0] ar [0:JQ-1]; reg [4:0] sn [0:JQ-1]; reg vl [0:JQ-1];
    reg [AW-1:0] wp, ip, dp; reg [AW:0] n, ni;   // n: jobs pending done, ni: jobs not yet fully issued
    reg flt;
    // ---------------- q side
    wire qv = q[0]; wire [511:0] qd = q[512:1];
    reg  qin; reg [11:0] qrem; reg qpass; reg [7:0] qcnt;
    wire hdr = qv && !qin;
    wire [7:0] htag = qd[502:495];
    wire armed = (ni != 0);
    wire hok = armed && (htag == tg[ip]) && (qcnt < ar[ip][14:7]) || (MUT == 1);
    wire pass_now = hdr ? hok : qpass;
    assign core_q = (qv && pass_now) ? q : 515'd0;
    wire qlast = qv && (hdr ? (qd[491:480] == 12'd0) : (qrem == 12'd1));
    // ---------------- result side: header parsers of a0 / a1 / xd / od
    wire [3:0] ov = {3'b000, ad[0]};
    wire [511:0] o0 = ad[512:1], o1 = 512'd0, o2 = 512'd0, o3 = 512'd0;
    reg  [3:0] oin; reg [11:0] orem [0:3];
    reg  [3:0] endv; reg [7:0] endt [0:3]; reg [2:0] ends [0:3];
    integer k, m, nend;
    always @* begin
        for (k = 0; k < 4; k = k + 1) begin
            endv[k] = 1'b0; endt[k] = 8'd0; ends[k] = 3'd0;
        end
        if (ov[0] && !oin[0] && o0[507]) begin endv[0] = 1'b1; endt[0] = o0[502:495]; ends[0] = o0[505:503]; end
        if (ov[1] && !oin[1] && o1[507]) begin endv[1] = 1'b1; endt[1] = o1[502:495]; ends[1] = o1[505:503]; end
        if (ov[2] && !oin[2] && o2[507]) begin endv[2] = 1'b1; endt[2] = o2[502:495]; ends[2] = o2[505:503]; end
        if (ov[3] && !oin[3] && o3[507]) begin endv[3] = 1'b1; endt[3] = o3[502:495]; ends[3] = o3[505:503]; end
    end
    wire [11:0] olen0 = o0[491:480], olen1 = o1[491:480], olen2 = o2[491:480], olen3 = o3[491:480];
    reg [4:0] sn_n [0:JQ-1]; reg fl_n; reg [AW:0] slot;
    wire [AW-1:0] dpn = dp;
    always @* begin
        fl_n = 1'b0;
        for (m = 0; m < JQ; m = m + 1) sn_n[m] = sn[m];
        for (k = 0; k < 4; k = k + 1) if (endv[k]) begin
            nend = 0;
            for (m = 0; m < JQ; m = m + 1)
                if (vl[m] && tg[m] == endt[k]) begin
                    nend = nend + 1;
                    if (ends[k] > 3'd4 || !ar[m][ends[k]] || sn_n[m][ends[k]]) fl_n = 1'b1;
                    else sn_n[m][ends[k]] = 1'b1;
                end
            if (nend != 1) fl_n = 1'b1;
        end
    end
    wire [4:0] need = ar[dp][4:0];
    wire hd_done = (n != 0) && ((MUT == 5) ? (sn_n[dp] != 5'd0) : ((sn_n[dp] & need) == need));
    always @(posedge ck or negedge rs_n)
        if (!rs_n) begin
            wp <= 0; ip <= 0; dp <= 0; n <= 0; ni <= 0; flt <= 1'b0; j_dn <= 2'b00;
            qin <= 1'b0; qrem <= 0; qpass <= 1'b0; qcnt <= 0; oin <= 4'd0;
            for (m = 0; m < JQ; m = m + 1) begin vl[m] <= 1'b0; sn[m] <= 5'd0; end
            for (k = 0; k < 4; k = k + 1) orem[k] <= 0;
        end else begin
            // job push
            if (jv) begin
                tg[wp] <= jc[7:0]; ar[wp] <= jc[31:8]; vl[wp] <= 1'b1; wp <= wp + 1'b1;
                if (jc[31:23] != 0 || jc[14:13] != 0 || jc[22:15] == 8'd0 || jc[12:8] == 5'd0 || n == JQ) flt <= 1'b1;
            end
            // q frames
            if (qv) begin
                if (hdr) begin qin <= (qd[491:480] != 12'd0); qrem <= qd[491:480]; qpass <= hok; if (!hok) flt <= 1'b1; end
                else begin qrem <= qrem - 1'b1; if (qrem == 12'd1) qin <= 1'b0; end
            end
            if (qlast && pass_now && armed) begin
                if (qcnt + 1'b1 == ar[ip][14:7]) begin qcnt <= 0; ip <= ip + 1'b1; end else qcnt <= qcnt + 1'b1;
            end
            // result parsers
            if (ov[0]) begin if (!oin[0]) begin oin[0] <= (olen0 != 0); orem[0] <= olen0; end else begin orem[0] <= orem[0] - 1'b1; if (orem[0] == 1) oin[0] <= 1'b0; end end
            if (ov[1]) begin if (!oin[1]) begin oin[1] <= (olen1 != 0); orem[1] <= olen1; end else begin orem[1] <= orem[1] - 1'b1; if (orem[1] == 1) oin[1] <= 1'b0; end end
            if (ov[2]) begin if (!oin[2]) begin oin[2] <= (olen2 != 0); orem[2] <= olen2; end else begin orem[2] <= orem[2] - 1'b1; if (orem[2] == 1) oin[2] <= 1'b0; end end
            if (ov[3]) begin if (!oin[3]) begin oin[3] <= (olen3 != 0); orem[3] <= olen3; end else begin orem[3] <= orem[3] - 1'b1; if (orem[3] == 1) oin[3] <= 1'b0; end end
            for (m = 0; m < JQ; m = m + 1) sn[m] <= sn_n[m];
            if (fl_n) flt <= 1'b1;
            // in-order done
            j_dn[0] <= 1'b0;
            if (hd_done) begin j_dn[0] <= 1'b1; vl[dp] <= 1'b0; sn[dp] <= 5'd0; dp <= dp + 1'b1; end
            if (jv && !hd_done) n <= n + 1'b1; else if (!jv && hd_done) n <= n - 1'b1;
            if (jv && !(qlast && pass_now && armed && qcnt + 1'b1 == ar[ip][14:7])) ni <= ni + 1'b1;
            else if (!jv && (qlast && pass_now && armed && qcnt + 1'b1 == ar[ip][14:7])) ni <= ni - 1'b1;
            if (hd_done && (ni == n) && !(qlast && pass_now && armed)) flt <= 1'b1;   // done before its q frames passed
            j_dn[1] <= flt;
`ifdef OT_SVCJOB_TRACE
            if (!flt && (fl_n || (qv && hdr && !hok) || (jv && (jc[31:23] != 0 || jc[14:13] != 0 || jc[22:15] == 8'd0 || jc[12:8] == 5'd0 || n == JQ))))
                $display("SVCJOB_FAULT %m t=%0t fl_n=%b qhdr_bad=%b tag=%h head=%h armed=%b qcnt=%0d nq=%0d jv=%b n=%0d", $time, fl_n,
                         qv && hdr && !hok, htag, tg[ip], armed, qcnt, ar[ip][14:7], jv, n);
`endif
        end
endmodule

