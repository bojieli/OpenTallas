#!/bin/bash
# Run the existing full-shape capture/reference comparison on the extracted
# candidate. Only the DUT binding and source list change, never the oracle.
#
# S-VM-CAPT-STATUS 2026-10-16 (DECISION B, dsfd_capt_status_dual = fixed-phase 3-bank x43 transfer,
# ctrl_c/dsfd_capt_status_x43.sv) -- what changed in the comparison, and why it is still exact:
#  * RESET: the new status leaves need the die's EPOCH resets (x34/x43 startup contract: released so the first
#    rising edge of each clock is epoch edge 0).  The shim derives rse from the bench's raw rst/rsv: it rises at the
#    stream-index-3 edge (bench epoch: ck rises at 24k+3, ckv at 24k+4 = edge 0) after both are high, and drives
#    rst AND rsv of BOTH the reference and the candidate.  The oracle logic is unchanged; only its release instant.
#  * t_vm[13311:0] (row lanes) are compared to the reference every serial edge exactly as before.
#  * t_vm[13375:13312] (status lane) is compared every serial edge to st_x = the x43 SAMPLE RULE applied to the
#    REFERENCE's own stream-side status word (u_ref...u_t.sn, the word the reference feeds its ratio FIFO):
#    serial edge 0 <- sample at stream index 2 of the previous epoch, edge 1 <- index 3 (previous epoch),
#    edge 2 <- index 0 (same epoch); 0 for the first two serial edges after release.  The reference's own status
#    lane (elastic ratio FIFO, DEPTH 2) delivers the same words at a varying age; that timing is the semantic delta.
#  * t_cd is compared every serial edge to cx_q: the reference's t_cd logic (ctrl_c/dsfd_sp_capture_c.sv,
#    verbatim) evaluated on st_x, one serial cycle later (the relay), and the ORDERED sequence of completed-phase
#    events (t_cd toggle, phase id) must equal the reference's own sequence (no event lost, added or reordered;
#    at most the last event may still be in flight when the run ends).
set -eu
out=$1
mkdir -p "$out"
python3 - "$out/split_runner.sh" <<'PY'
from pathlib import Path
import sys
s = Path('tools/s81_ph/capc_bench.sh').read_text()
def one(old,new):
    global s
    assert s.count(old)==1,old
    s=s.replace(old,new)
one('dsfd_sp_capture_c u_dut (', 'dsfd_sp_capture_split_candidate u_dut (.ck_status(ck[0]), .ckv_status(ckv[0]), ')
one('  rtl/v41rom/ot_v41_ret.sv', '  rtl/common/ot_ratio_cdc_fifo.sv rtl/v41rom/ot_v41_ret.sv')
one('rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_c_cl.sv $G/capc_shim.sv',
    'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_split.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_split_candidate.sv $G/capc_shim.sv')
one('rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_split.sv ',
    'rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_split.sv rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_capt_status_x43.sv ')
one('    capc_ref u_ref (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv),',
    """    // epoch reset (die startup contract of the x43 status leaves): released at the stream index-3 edge
    reg [1:0] ep_t = 2'd0, ep_s = 2'd0; reg [0:0] rse = 1'b0;
    always @(posedge ck[0]) begin ep_t <= ep_t + 2'd1; if (!(rst[0] && rsv[0])) rse <= 1'b0; else if (ep_t == 2'd3) rse <= 1'b1; end
    always @(posedge ckv[0]) ep_s <= (ep_s == 2'd2) ? 2'd0 : ep_s + 2'd1;
    capc_ref u_ref (.ck(ck), .rst(rse), .ckv(ckv), .rsv(rse),""")
one('.ck_sn(ck[0]), .rst(rst),', '.ck_sn(ck[0]), .rst(rse),')
one('.rsv(rsv), .f_gather(f_gather), .t_vm(t_vm), .t_cd(dc));',
    """.rsv(rse), .f_gather(f_gather), .t_vm(t_vm), .t_cd(dc));
    // x43 sample rule on the REFERENCE's stream-side status word
    wire [63:0] sn_ref = u_ref.u_c.g_t.u_t.sn;
    reg [63:0] m0 = 64'd0, m2 = 64'd0, m3 = 64'd0, st_x = 64'd0; integer nsr = 0;
    always @(posedge ck[0]) case (ep_t) 2'd0: m0 <= sn_ref; 2'd2: m2 <= sn_ref; 2'd3: m3 <= sn_ref; default: ; endcase
    always @(posedge ckv[0] or negedge rse[0])
        if (!rse[0]) begin st_x <= 64'd0; nsr <= 0; end
        else begin nsr <= nsr + 1; if (nsr >= 2) case (ep_s) 2'd0: st_x <= m2; 2'd1: st_x <= m3; default: st_x <= m0; endcase end
    // the reference's t_cd logic (ctrl_c/dsfd_sp_capture_c.sv, verbatim) on st_x
    reg [1:0] xv_s; reg xdr, xarm; reg [11:0] cx, cx_q = 12'd0;
    always @(posedge ckv[0] or negedge rse[0]) if (!rse[0]) xv_s <= 2'b00; else xv_s <= {xv_s[0], 1'b1};
    always @(posedge ckv[0] or negedge xv_s[1])
        if (!xv_s[1]) begin xdr <= 1'b0; xarm <= 1'b0; cx <= 12'd0; end
        else begin
            xdr <= st_x[2];
            cx[10] <= st_x[3];
            if (st_x[0]) xarm <= 1'b1;
            if (st_x[2] && !xdr && xarm && !st_x[0]) begin cx[9:0] <= st_x[13:4]; cx[11] <= ~cx[11]; xarm <= 1'b0; end
        end
    // ordered completed-phase events: reference t_cd vs candidate t_cd
    reg [9:0] evr [0:4095]; integer ner = 0, ned = 0, sqm = 0, smm = 0; reg rtq = 1'b0, dtq = 1'b0;
    always @(posedge ckv[0]) begin
        cx_q <= cx;
        if (rc[11] !== rtq) begin rtq <= rc[11]; evr[ner % 4096] <= rc[9:0]; ner = ner + 1; end
        if (dc[11] !== dtq) begin dtq <= dc[11];
            if (ned >= ner || evr[ned % 4096] !== dc[9:0]) begin sqm = sqm + 1; if (sqm < 5) $display("CAPC_EQ CD_SEQ MISMATCH t=%0t event %0d dut %h", $time, ned, dc[9:0]); end
            ned = ned + 1; end
    end""")
one('            if (rv !== t_vm || rc_q !== dc) begin mm = mm + 1; if (mm < 5) $display("CAPC_EQ MISMATCH t=%0t vm_eq %b cd %h/%h", $time, rv === t_vm, rc_q, dc); end',
    '            if (rv[13311:0] !== t_vm[13311:0] || st_x !== t_vm[13375:13312] || cx_q !== dc) begin mm = mm + 1; if (st_x !== t_vm[13375:13312]) smm = smm + 1; if (mm < 5) $display("CAPC_EQ MISMATCH t=%0t rows_eq %b st %h/%h cd %h/%h", $time, rv[13311:0] === t_vm[13311:0], st_x, t_vm[13375:13312], cx_q, dc); end')
one('    final $display("CAPC_EQ mismatches=%0d tcd_toggles=%0d vm_active_cycles=%0d %s", mm, tg, nw, (mm == 0 && nw > 0) ? "EQ_PASS" : "EQ_FAIL");',
    '    final $display("CAPC_EQ mismatches=%0d status_mm=%0d tcd_toggles=%0d cd_events=%0d/%0d cd_seq_mm=%0d vm_active_cycles=%0d %s", mm, smm, tg, ned, ner, sqm, nw, (mm == 0 && sqm == 0 && ner - ned <= 1 && ner - ned >= 0 && nw > 0) ? "EQ_PASS" : "EQ_FAIL");')
Path(sys.argv[1]).write_text(s)
PY
bash "$out/split_runner.sh" "$@"
