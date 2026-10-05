// Default-off, one retained owner46+RFslot9 per selected SM port.
// This is NOT an adapter for the original bare RF ACK. Each identity-bearing
// input must be supplied by an admitted source retention/validation adapter.
// alldrain_live is CURRENT source state under admission-stop, including both
// CDC directions and pending certificates. A delayed historical flag packet
// cannot satisfy this contract. Child completion is aggregate validated reverse.
module ot_hbm_rf_visibility_fence_live #(
  parameter bit ENABLE=1'b0,
  // LATE_CHECK=1 (default off): the SECDED decode/correct leaves the per-cycle feedback.
  // In-cycle, a conservative dirty flag (witness syndrome nonzero, or witness data bits differ
  // from the live majority) blocks every release and every state write; it needs no
  // correction, only XOR trees. The exact decode (correction, UE, corrected-witness vs live)
  // runs on registered syndromes one edge later: an uncorrectable row raises the sticky fault
  // and stays held; a correctable witness is scrubbed from the live majority. Fault-free
  // cycles are identical to LATE_CHECK=0; a corrupted row never releases. Under injection:
  // fault/quarantine rise one edge later, a witness CE stalls two edges and scrubs.
  parameter bit LATE_CHECK=1'b0
)(
  input wire clk, por_n, rst_n,
  input wire req_valid, input wire [54:0] req_identity,
  input wire req_internal_SIMD, output wire req_ready,
  input wire host_ack_valid, input wire [54:0] host_ack_identity,
  output wire host_ack_ready,
  input wire simd_ack_retire_valid, input wire [54:0] simd_ack_retire_identity,
  output wire simd_ack_retire_ready,
  output wire visible_valid, output wire [54:0] visible_identity,
  input wire visible_ready,
  input wire consumer_valid, input wire [54:0] consumer_identity,
  output wire consumer_ready,
  input wire child_reverse_valid, input wire [54:0] child_reverse_identity,
  output wire child_reverse_ready,
  input wire parent_reverse_valid, input wire [54:0] parent_reverse_identity,
  output wire parent_reverse_ready,
  input wire reverse_CDC_valid, input wire [54:0] reverse_CDC_identity,
  output wire reverse_CDC_ready,
  output wire drain_req_valid, output wire [54:0] drain_req_identity,
  output wire drain_req_has_owner, drain_req_reset_scope,
  input wire drain_req_ready,
  input wire drain_rsp_valid, input wire [54:0] drain_rsp_identity,
  input wire drain_rsp_has_owner, drain_rsp_reset_scope,
  input wire [8:0] alldrain_live, output wire drain_rsp_ready,
  output wire retire_valid, output wire [54:0] retire_identity,
  input wire retire_ready,
  output wire fault, quarantine
);
  import ot_gpu_w6_secded_pkg::*;
  generate if (!ENABLE) begin: disabled
    assign req_ready=0; assign host_ack_ready=0; assign simd_ack_retire_ready=0;
    assign visible_valid=0; assign visible_identity=0;
    assign consumer_ready=0; assign child_reverse_ready=0;
    assign parent_reverse_ready=0; assign reverse_CDC_ready=0;
    assign drain_req_valid=0; assign drain_req_identity=0;
    assign drain_req_has_owner=0; assign drain_req_reset_scope=0;
    assign drain_rsp_ready=0; assign retire_valid=0; assign retire_identity=0;
    assign fault=0; assign quarantine=0;
  end else begin: enabled
    localparam [3:0] IDLE=0, ACK=1, VISIBLE=2, CONSUMER=3, CHILD=4,
      PARENT=5, CDC=6, DRAIN_REQ=7, DRAIN_WAIT=8, RETIRE=9,
      RESET_REQ=10, RESET_WAIT=11;
    // Protected live feedback: majority corrects one live-copy upset. Original
    // SECDED witness detects disagreement/UE before any visible handshake.
    // No late unchecked release. Witness remains in control-enable paths:
    // this candidate requires measurement; no clock-closure credit is implied.
    reg [143:0] protected_state;
    reg [70:0] live_a,live_b,live_c;
    wire [70:0] live_raw=(live_a&live_b)|(live_a&live_c)|(live_b&live_c);
    wire [65:0] lo=decode64(protected_state[71:0]);
    wire [65:0] hi=decode64(protected_state[143:72]);
    wire [70:0] witness={hi[6:0],lo[63:0]};
    wire row_bad_now=lo[65] | hi[65] | (|hi[63:7]) | (witness!=live_raw);
    // LATE_CHECK exact check, registered: edge 1 captures per-half {overall, syndrome} and the
    // witness-data XOR live-majority; the next cycle applies the syndrome's single-bit
    // correction to that difference (late_bad), exactly row_bad_now of the captured row.
    function automatic [7:0] synd72(input [71:0] code);   // {overall, syndrome[6:0]}
      integer k, q; reg [6:0] sy;
      begin sy=0;
        for (k=0;k<7;k=k+1) for (q=1;q<=71;q=q+1) if ((q & (1<<k)) != 0) sy[k]=sy[k]^code[q-1];
        synd72={^code,sy};
      end
    endfunction
    function automatic [63:0] data72(input [71:0] code);
      integer q, j; begin data72=0; j=0;
        for (q=1;q<=71;q=q+1) if ((q & (q-1)) != 0) begin data72[j]=code[q-1]; j=j+1; end end
    endfunction
    function automatic [64:0] corr72(input [7:0] so);     // {ue, data correction vector}
      integer q, j; reg [63:0] v; reg ue;
      begin v=0; j=0; ue=0;
        if (so[6:0]!=0) begin
          if (so[7] && so[6:0]<=71) begin
            for (q=1;q<=71;q=q+1) if ((q & (q-1)) != 0) begin if (so[6:0]==q) v[j]=1'b1; j=j+1; end
          end else ue=1;
        end
        corr72={ue,v};
      end
    endfunction
    // In-cycle dirty uses no syndrome: a duplicate witness register (written with the witness)
    // exposes any witness upset as witness!=duplicate, and any live-majority error as witness
    // data!=majority; both are one XOR per bit plus an OR tree. The exact SECDED syndrome is
    // computed from the witness alone and only registered (late check).
    reg [143:0] ps_dup;
    wire [7:0] s_lo=synd72(protected_state[71:0]);
    wire [7:0] s_hi=synd72(protected_state[143:72]);
    wire [127:0] diff_now={data72(protected_state[143:72]) ^ {57'b0,live_raw[70:64]},
                           data72(protected_state[71:0]) ^ live_raw[63:0]};
    // in-cycle conservative flag: zero only when the witness equals its duplicate and its data
    // bits equal the live majority (then the row is releasable: every released field comes from
    // the majority, which the witness confirms; a witness-parity fault the duplicate shares is
    // raises the sticky fault through the registered exact check one edge later)
    // plus live-copy disagreement: on a releasable row all three copies are equal, so the
    // handshake compares may read single copies (no voter, a third of the fan-out each)
    // (the witness-data compare reads live_a, not the voter: whenever the three copies agree
    // they equal the majority, and when they disagree the row is dirty either way)
    wire [127:0] diff_a={data72(protected_state[143:72]) ^ {57'b0,live_a[70:64]},
                         data72(protected_state[71:0]) ^ live_a[63:0]};
    // the 414-bit OR is a balanced NOR3/NAND3 tree with kept levels (ot_hbm_fence_or_tree)
    wire dirty;
    ot_hbm_fence_or_tree #(.N(414)) u_dirty_or(.x({protected_state ^ ps_dup, diff_a, live_a ^ live_b, live_a ^ live_c}), .y(dirty));
`ifndef SYNTHESIS
    always @(posedge clk) if (por_n && dirty!==((|(protected_state ^ ps_dup)) | (|diff_now) | (|(live_a ^ live_b)) | (|(live_a ^ live_c))))
      $fatal(1,"FENCE_DIRTY_FORM_MISMATCH");
`endif
    // The registered exact check holds the decoded syndromes already applied to the witness/live
    // difference (the decode is a function of the same flops as the syndrome, so registering
    // its result instead of the syndrome changes no edge): late_bad is one kept OR tree.
    wire [64:0] cr_lo=corr72(s_lo), cr_hi=corr72(s_hi);
    reg ue_lo_q, ue_hi_q; reg [127:0] x_q; reg bad_q, held_dirty_q;
    wire late_bad;
    ot_hbm_fence_or_tree #(.N(130)) u_late_or(.x({ue_lo_q, ue_hi_q, x_q}), .y(late_bad));
    // write: never on a dirty row, except the scrub of a row held since the last edge whose
    // exact check found it correctable; never after an uncorrectable row (sticky bad_q).
    // dirty acts only through this enable and the release outputs, never the next-state select:
    // the select sees flop flags alone (bad_q, held_dirty_q), and a held row is never written
    // with a transition (a scrub edge forces the hold candidate).
    wire late_we=!bad_q && !late_bad && (!dirty || held_dirty_q);
    always @(posedge clk or negedge por_n)
      if (!por_n) begin ue_lo_q<=1'b0; ue_hi_q<=1'b0; x_q<=0; bad_q<=1'b0; held_dirty_q<=1'b0; end
      else begin
        ue_lo_q<=cr_lo[64]; ue_hi_q<=cr_hi[64]; x_q<=diff_now ^ {cr_hi[63:0],cr_lo[63:0]};
        held_dirty_q<=dirty && !late_we;
        if (late_bad) bad_q<=1'b1;
      end
    // release gate (in-cycle) and reported fault (exact, late) for LATE_CHECK
    wire row_bad=LATE_CHECK ? (bad_q | dirty | held_dirty_q) : row_bad_now;
    wire row_bad_sel=bad_q | held_dirty_q;   // LATE_CHECK next-state select (flops only)
    wire fault_bad=LATE_CHECK ? (bad_q | late_bad) : row_bad_now;
    wire [70:0] raw=live_raw;
    wire [54:0] identity={raw[45:0],raw[54:46]};
    // LATE_CHECK: decisions and released handshakes read one live copy (rawd), not the voter.
    // A transition or release only happens on a clean row, where the copies equal the majority;
    // a dirty row releases nothing and writes nothing but the majority hold row (scrub), which
    // the candidate path still forms from the voter (raw). Fault/quarantine/data outputs keep raw.
    wire [70:0] rawd=LATE_CHECK ? live_b : live_raw;
    wire [3:0] phase=rawd[58:55];
    wire reset_phase=(phase==RESET_REQ || phase==RESET_WAIT);
    wire reset_phase_m=(raw[58:55]==RESET_REQ || raw[58:55]==RESET_WAIT);
    wire age_ok=(rawd[70:69]>=1);
    wire cdc_age_ok=(rawd[70:69]>=2);
    // On a releasable row (dirty==0) live_a==live_b==live_c==majority, so each compare reads
    // one copy; a row whose copies disagree is dirty and never fires (held, then scrubbed).
    wire [54:0] id_a={live_a[45:0],live_a[54:46]}, id_b={live_b[45:0],live_b[54:46]}, id_c={live_c[45:0],live_c[54:46]};
    // each 55-bit identity compare: XOR into a kept 4-level NOR3/NAND3 tree (ot_hbm_fence_or_tree81)
    wire n_host, n_simd, n_con, n_chd, n_par, n_cdc, n_drsp;
    wire hg_host, hg_simd, hg_con, hg_chd, hg_par, hg_cdc, hg_drsp, h_host, h_simd, h_con, h_chd, h_par, h_cdc, h_drsp;
    ot_hbm_fence_or_tree81 #(.N(55)) u_c_host(.x(host_ack_identity ^ id_a), .g(hg_host), .y(n_host), .h(h_host));
    ot_hbm_fence_or_tree81 #(.N(55)) u_c_simd(.x(simd_ack_retire_identity ^ id_a), .g(hg_simd), .y(n_simd), .h(h_simd));
    ot_hbm_fence_or_tree81 #(.N(55)) u_c_con(.x(consumer_identity ^ id_b), .g(hg_con), .y(n_con), .h(h_con));
    ot_hbm_fence_or_tree81 #(.N(55)) u_c_chd(.x(child_reverse_identity ^ id_b), .g(hg_chd), .y(n_chd), .h(h_chd));
    ot_hbm_fence_or_tree81 #(.N(55)) u_c_par(.x(parent_reverse_identity ^ id_c), .g(hg_par), .y(n_par), .h(h_par));
    ot_hbm_fence_or_tree81 #(.N(55)) u_c_cdc(.x(reverse_CDC_identity ^ id_c), .g(hg_cdc), .y(n_cdc), .h(h_cdc));
    ot_hbm_fence_or_tree81 #(.N(55)) u_c_drsp(.x(drain_rsp_identity ^ id_c), .g(hg_drsp), .y(n_drsp), .h(h_drsp));
    wire m_host=!n_host, m_simd=!n_simd, m_con=!n_con, m_chd=!n_chd, m_par=!n_par, m_cdc=!n_cdc;
    wire m_drsp=!n_drsp && drain_rsp_has_owner==rawd[59] && drain_rsp_reset_scope==reset_phase;
    wire lc_W=(host_ack_valid && (phase!=ACK || rawd[61])) ||
      (simd_ack_retire_valid && (phase!=ACK || !rawd[61])) ||
      (consumer_valid && phase!=CONSUMER) || (child_reverse_valid && phase!=CHILD) ||
      (parent_reverse_valid && phase!=PARENT) || (reverse_CDC_valid && phase!=CDC) ||
      (drain_rsp_valid && phase!=DRAIN_WAIT) || (req_valid && phase==IDLE && req_identity[47:45]>=6);
    wire lc_X=(host_ack_valid && !m_host) || (simd_ack_retire_valid && !m_simd) ||
      (consumer_valid && !m_con) || (child_reverse_valid && !m_chd) ||
      (parent_reverse_valid && !m_par) || (reverse_CDC_valid && !m_cdc) || (drain_rsp_valid && !m_drsp);
    wire normal=por_n && rst_n && !row_bad && !rawd[60] && !reset_phase;
    wire drain_match=(drain_rsp_identity==identity &&
      drain_rsp_has_owner==rawd[59] && drain_rsp_reset_scope==reset_phase);
    // Foreign/wrong-origin/out-of-order completions never advance any boundary.
    wire invalid_input=(host_ack_valid && (phase!=ACK || rawd[61] || host_ack_identity!=identity)) ||
      (simd_ack_retire_valid && (phase!=ACK || !rawd[61] || simd_ack_retire_identity!=identity)) ||
      (consumer_valid && (phase!=CONSUMER || consumer_identity!=identity)) ||
      (child_reverse_valid && (phase!=CHILD || child_reverse_identity!=identity)) ||
      (parent_reverse_valid && (phase!=PARENT || parent_reverse_identity!=identity)) ||
      (reverse_CDC_valid && (phase!=CDC || reverse_CDC_identity!=identity)) ||
      (drain_rsp_valid && (phase!=DRAIN_WAIT || !drain_match)) ||
      (req_valid && phase==IDLE && req_identity[47:45]>=6);
    // LATE_CHECK: the released handshakes use the factored kept-group compares (identical on
    // every row where they can be observed: a dirty row gates every live-qualified output).
    // A live-qualified output is nonzero only in its own phase, where every other channel's
    // valid is a wrong-phase valid (lc_W) and its own channel's mismatch already zeroes it
    // through its own m_*: so lc_X never decides a released output and only lc_W (valids and
    // the registered phase, no identity compare) gates `live`. One compare per output.
    wire inv_rel=LATE_CHECK ? lc_W : invalid_input;
    wire live=normal && !inv_rel;
    assign req_ready=live && phase==IDLE && age_ok && req_identity[47:45]<6;
    assign host_ack_ready=live && phase==ACK && !rawd[61] && age_ok && (LATE_CHECK ? m_host : host_ack_identity==identity);
    assign simd_ack_retire_ready=live && phase==ACK && rawd[61] && age_ok && (LATE_CHECK ? m_simd : simd_ack_retire_identity==identity);
    assign visible_valid=live && phase==VISIBLE && age_ok;
    assign visible_identity=identity;
    assign consumer_ready=live && phase==CONSUMER && age_ok && (LATE_CHECK ? m_con : consumer_identity==identity);
    assign child_reverse_ready=live && phase==CHILD && age_ok && (LATE_CHECK ? m_chd : child_reverse_identity==identity);
    assign parent_reverse_ready=live && phase==PARENT && age_ok && (LATE_CHECK ? m_par : parent_reverse_identity==identity);
    assign reverse_CDC_ready=live && phase==CDC && cdc_age_ok && (LATE_CHECK ? m_cdc : reverse_CDC_identity==identity);
    assign drain_req_valid=por_n && rst_n && !row_bad && age_ok &&
      ((live && phase==DRAIN_REQ) || phase==RESET_REQ);
    assign drain_req_identity=identity;
    assign drain_req_has_owner=raw[59];
    assign drain_req_reset_scope=reset_phase_m;
    assign drain_rsp_ready=por_n && rst_n && !row_bad && age_ok && rawd[68] && (LATE_CHECK ? m_drsp : drain_match) &&
      (&alldrain_live) && ((live && phase==DRAIN_WAIT) || phase==RESET_WAIT);
    assign retire_valid=live && phase==RETIRE && age_ok && rawd[67];
    assign retire_identity=identity;
    assign fault=fault_bad || raw[60];
    assign quarantine=!por_n || !rst_n || fault_bad || raw[60] || reset_phase_m;
    reg [70:0] next_raw;
    wire [70:0] reset_raw=(raw & ~( (71'd15<<55) | (71'd3<<69) | (71'd1<<67) | (71'd1<<68))) | (71'd10<<55);
    // Boundary ages impose positive protocol edges, not ECC path retiming.
    always @* begin
      next_raw=raw;
      if (raw[70:69]!=3) next_raw[70:69]=raw[70:69]+1'b1;
      if (normal && invalid_input) next_raw[60]=1'b1;
      else if (req_valid && req_ready) begin
        next_raw='0; next_raw[45:0]=req_identity[54:9];
        next_raw[54:46]=req_identity[8:0]; next_raw[59]=1;
        next_raw[61]=req_internal_SIMD; next_raw[58:55]=ACK; next_raw[70:69]=0;
      end else if ((host_ack_valid && host_ack_ready) ||
                   (simd_ack_retire_valid && simd_ack_retire_ready)) begin
        next_raw[62]=1; next_raw[58:55]=VISIBLE; next_raw[70:69]=0;
      end else if (visible_valid && visible_ready) begin
        next_raw[58:55]=CONSUMER; next_raw[70:69]=0;
      end else if (consumer_valid && consumer_ready) begin
        next_raw[63]=1; next_raw[58:55]=CHILD; next_raw[70:69]=0;
      end else if (child_reverse_valid && child_reverse_ready) begin
        next_raw[64]=1; next_raw[58:55]=PARENT; next_raw[70:69]=0;
      end else if (parent_reverse_valid && parent_reverse_ready) begin
        next_raw[65]=1; next_raw[58:55]=CDC; next_raw[70:69]=0;
      end else if (reverse_CDC_valid && reverse_CDC_ready) begin
        next_raw[66]=1; next_raw[58:55]=DRAIN_REQ; next_raw[70:69]=0;
      end else if (drain_req_valid && drain_req_ready) begin
        next_raw[68]=1; next_raw[58:55]=reset_phase ? RESET_WAIT : DRAIN_WAIT;
        next_raw[70:69]=0;
      end else if (drain_rsp_valid && drain_rsp_ready) begin
        next_raw[68]=0; next_raw[67]=1; next_raw[70:69]=0;
        if (reset_phase) begin
          next_raw[58:55]=IDLE; next_raw[59]=0; next_raw[60]=0;
        end else next_raw[58:55]=RETIRE;
      end else if (retire_valid && retire_ready) begin
        next_raw[59]=0; next_raw[58:55]=IDLE; next_raw[70:69]=0;
      end
      if (phase>RESET_WAIT) next_raw[60]=1;
    end
    // LATE_CHECK witness write: SECDED is linear, so encode(next_raw) equals the one-hot
    // selection of the encodings of next_raw's candidates, and every candidate except a new
    // request differs from the hold row only in bits [70:55]: e_X = e_base ^ encode(r_X ^ r_base)
    // is one full encoder plus a few XORs of those 16 bits. Each candidate depends only on
    // raw and the input fields, so its encoder runs beside the handshake decision instead of
    // behind it. Candidates mirror the next_raw priority chain above exactly.
    wire [1:0] age_n=(raw[70:69]!=3) ? raw[70:69]+1'b1 : raw[70:69];
    wire bp=(phase>RESET_WAIT);
    wire [70:0] c_base={age_n,raw[68:0]};
    function automatic [70:0] fin(input [70:0] c, input b); fin=b ? (c | (71'd1<<60)) : c; endfunction
    function automatic [70:0] stp(input [70:0] c, input integer flag, input [3:0] ph);
      begin stp=c; if (flag>=0) stp[flag]=1'b1; stp[58:55]=ph; stp[70:69]=2'd0; end
    endfunction
    wire [70:0] c_req_raw={2'd0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,1'b0,req_internal_SIMD,1'b0,1'b1,ACK,req_identity[8:0],req_identity[54:9]};
    wire [70:0] c_drsp0=stp(c_base & ~(71'd1<<68),67,reset_phase ? IDLE : RETIRE);
    wire [70:0] c_drsp=reset_phase ? (c_drsp0 & ~(71'd1<<59) & ~(71'd1<<60)) : c_drsp0;
        wire [70:0] r_base=fin(c_base,bp);
    (* keep *) wire [143:0] e_base; assign e_base=encode_row(r_base);
        wire [70:0] r_inv=fin(c_base | (71'd1<<60),bp);
    wire [143:0] e_inv=e_base ^ encode_row(r_inv ^ r_base);
        wire [70:0] r_req=fin(c_req_raw,bp);
    (* keep *) wire [143:0] e_req; assign e_req=encode_row(r_req);
        wire [70:0] r_ack=fin(stp(c_base,62,VISIBLE),bp);
    wire [143:0] e_ack=e_base ^ encode_row(r_ack ^ r_base);
        wire [70:0] r_vis=fin(stp(c_base,-1,CONSUMER),bp);
    wire [143:0] e_vis=e_base ^ encode_row(r_vis ^ r_base);
        wire [70:0] r_con=fin(stp(c_base,63,CHILD),bp);
    wire [143:0] e_con=e_base ^ encode_row(r_con ^ r_base);
        wire [70:0] r_chd=fin(stp(c_base,64,PARENT),bp);
    wire [143:0] e_chd=e_base ^ encode_row(r_chd ^ r_base);
        wire [70:0] r_par=fin(stp(c_base,65,CDC),bp);
    wire [143:0] e_par=e_base ^ encode_row(r_par ^ r_base);
        wire [70:0] r_cdc=fin(stp(c_base,66,DRAIN_REQ),bp);
    wire [143:0] e_cdc=e_base ^ encode_row(r_cdc ^ r_base);
        wire [70:0] r_dreq=fin(stp(c_base,68,reset_phase ? RESET_WAIT : DRAIN_WAIT),bp);
    wire [143:0] e_dreq=e_base ^ encode_row(r_dreq ^ r_base);
        wire [70:0] r_drsp=fin(c_drsp,bp);
    wire [143:0] e_drsp=e_base ^ encode_row(r_drsp ^ r_base);
        wire [70:0] r_ret=fin(stp(c_base & ~(71'd1<<59),-1,IDLE),bp);
    wire [143:0] e_ret=e_base ^ encode_row(r_ret ^ r_base);
    wire [143:0] e_rst=e_base ^ encode_row(reset_raw ^ r_base);
    wire f1=req_valid && req_ready;
    wire f2=(host_ack_valid && host_ack_ready) || (simd_ack_retire_valid && simd_ack_retire_ready);
    wire f3=visible_valid && visible_ready;
    wire f4=consumer_valid && consumer_ready;
    wire f5=child_reverse_valid && child_reverse_ready;
    wire f6=parent_reverse_valid && parent_reverse_ready;
    wire f7=reverse_CDC_valid && reverse_CDC_ready;
    wire f8=drain_req_valid && drain_req_ready;
    wire f9=drain_rsp_valid && drain_rsp_ready;
    wire f10=retire_valid && retire_ready;
    // handshake fires are mutually exclusive (distinct phases; f0 excludes every live ready);
    // the selection below is checked against next_raw every cycle in simulation
    // Each phase admits exactly one non-fault transition, so its candidate is pre-selected by
    // the registered phase; the handshake decision only picks fault / fire / hold.
    // Factored decision for the LATE_CHECK write (same function as f0 / f1|..|f10, checked
    // every simulated cycle). A wrong-phase valid (W) needs no compare; a compare result only
    // enters through its own phase's term, never through invalid_input's 9-way OR into `live`.
    // Each 55-bit identity compare is a balanced kept tree (no linear OR chains).
    wire alld=&alldrain_live;
    wire lc_A=(phase==IDLE && age_ok && req_valid && req_identity[47:45]<6) ||
      (phase==ACK && age_ok && ((host_ack_valid && !rawd[61] && m_host) || (simd_ack_retire_valid && rawd[61] && m_simd))) ||
      (phase==VISIBLE && age_ok && visible_ready) ||
      (phase==CONSUMER && age_ok && consumer_valid && m_con) ||
      (phase==CHILD && age_ok && child_reverse_valid && m_chd) ||
      (phase==PARENT && age_ok && parent_reverse_valid && m_par) ||
      (phase==CDC && cdc_age_ok && reverse_CDC_valid && m_cdc) ||
      (phase==DRAIN_REQ && age_ok && drain_req_ready) ||
      (phase==DRAIN_WAIT && age_ok && rawd[68] && alld && drain_rsp_valid && m_drsp) ||
      (phase==RETIRE && age_ok && rawd[67] && retire_ready);
    // por_n is left out of the select: while !por_n every state flop is held in async reset.
    wire normal_sel=rst_n && !row_bad_sel && !rawd[60] && !reset_phase;
    wire lc_B=rst_n && !row_bad_sel && age_ok &&
      ((phase==RESET_REQ && drain_req_ready) || (phase==RESET_WAIT && rawd[68] && alld && drain_rsp_valid && m_drsp));
    wire f0=normal_sel && (lc_W || lc_X);
    wire fire=(normal_sel && !lc_W && lc_A) || lc_B;
    // The request candidate (IDLE) is the only one that rewrites the whole row, and its fire
    // needs no identity compare (in IDLE every completion valid is a wrong-phase valid, lc_W):
    // fire_req is early. Every other transition changes only bits [70:55] (and the fault
    // candidate only bit 60), so the compare-dependent fires act on the row by XOR of a
    // sparse difference, which synthesis folds to the few data and check bits it touches.
    // f0, fire_nr each imply rst_n && !fire_req, i.e. the early candidate is the hold row.
    wire ph_idle=(phase==IDLE);
    wire fire_req=normal_sel && !lc_W && ph_idle && age_ok && req_valid && req_identity[47:45]<6;
    wire fire_nr=fire && !ph_idle;
    reg [70:0] d_pn_ref;
    always @* begin
      case (phase)
        ACK:       d_pn_ref=r_ack ^ r_base;
        VISIBLE:   d_pn_ref=r_vis ^ r_base;
        CONSUMER:  d_pn_ref=r_con ^ r_base;
        CHILD:     d_pn_ref=r_chd ^ r_base;
        PARENT:    d_pn_ref=r_par ^ r_base;
        CDC:       d_pn_ref=r_cdc ^ r_base;
        DRAIN_REQ, RESET_REQ:  d_pn_ref=r_dreq ^ r_base;
        DRAIN_WAIT, RESET_WAIT: d_pn_ref=r_drsp ^ r_base;
        RETIRE:    d_pn_ref=r_ret ^ r_base;
        default:   d_pn_ref='0;
      endcase
    end
    // The transition difference is used only when fire_nr writes, i.e. on a clean row whose
    // phase is the case label and whose copies all equal the majority: each case's difference
    // is constant except the age and the one or two flag bits it sets or clears, so its
    // encoding is a few XORs instead of a full encoder behind the phase select.
    wire [1:0] age_nd=(rawd[70:69]!=3) ? rawd[70:69]+1'b1 : rawd[70:69];
    function automatic [70:0] dx(input [3:0] p, input [3:0] nx, input [1:0] agn);
      dx=({69'b0,agn} << 69) | ({67'b0,(p ^ nx)} << 55);
    endfunction
    reg [70:0] d_pn;
    always @* begin
      case (phase)
        ACK:        d_pn=dx(ACK,VISIBLE,age_nd) | ({70'b0,!rawd[62]} << 62);
        VISIBLE:    d_pn=dx(VISIBLE,CONSUMER,age_nd);
        CONSUMER:   d_pn=dx(CONSUMER,CHILD,age_nd) | ({70'b0,!rawd[63]} << 63);
        CHILD:      d_pn=dx(CHILD,PARENT,age_nd) | ({70'b0,!rawd[64]} << 64);
        PARENT:     d_pn=dx(PARENT,CDC,age_nd) | ({70'b0,!rawd[65]} << 65);
        CDC:        d_pn=dx(CDC,DRAIN_REQ,age_nd) | ({70'b0,!rawd[66]} << 66);
        DRAIN_REQ:  d_pn=dx(DRAIN_REQ,DRAIN_WAIT,age_nd) | ({70'b0,!rawd[68]} << 68);
        RESET_REQ:  d_pn=dx(RESET_REQ,RESET_WAIT,age_nd) | ({70'b0,!rawd[68]} << 68);
        DRAIN_WAIT: d_pn=dx(DRAIN_WAIT,RETIRE,age_nd) | ({70'b0,rawd[68]} << 68) | ({70'b0,!rawd[67]} << 67);
        RESET_WAIT: d_pn=dx(RESET_WAIT,IDLE,age_nd) | ({70'b0,rawd[68]} << 68) | ({70'b0,!rawd[67]} << 67) |
                         ({70'b0,rawd[59]} << 59) | ({70'b0,rawd[60]} << 60);
        RETIRE:     d_pn=dx(RETIRE,IDLE,age_nd) | ({70'b0,rawd[59]} << 59);
        default:    d_pn='0;
      endcase
    end
    wire [70:0] d_inv=r_inv ^ r_base;
    // Late decision with one compare: in each phase at most one channel is the phase's own
    // channel; every other valid is a wrong-phase valid (lc_W, no compare). Each channel keeps
    // its own parallel compare and the registered phase selects the one result (m_sel), so a
    // compare reaches f0/fire through one select and one AO level. F1/F2/N1/N2 are early.
    wire ph_ack_h=(phase==ACK) && !rawd[61], ph_ack_s=(phase==ACK) && rawd[61];
    wire ph_con=(phase==CONSUMER), ph_chd=(phase==CHILD), ph_par=(phase==PARENT), ph_cdc=(phase==CDC);
    wire ph_dw=(phase==DRAIN_WAIT), ph_rw=(phase==RESET_WAIT);
    wire m_sel=(ph_ack_h && m_host) || (ph_ack_s && m_simd) || (ph_con && m_con) || (ph_chd && m_chd) ||
      (ph_par && m_par) || (ph_cdc && m_cdc) || ((ph_dw || ph_rw) && m_drsp);
    wire ownv=(ph_ack_h && host_ack_valid) || (ph_ack_s && simd_ack_retire_valid) ||
      (ph_con && consumer_valid) || (ph_chd && child_reverse_valid) || (ph_par && parent_reverse_valid) ||
      (ph_cdc && reverse_CDC_valid) || (ph_dw && drain_rsp_valid);
    wire own_ok=((ph_ack_h || ph_ack_s || ph_con || ph_chd || ph_par) && age_ok) || (ph_cdc && cdc_age_ok) ||
      (ph_dw && age_ok && rawd[68] && alld);
    wire a_early=((phase==VISIBLE) && age_ok && visible_ready) || ((phase==DRAIN_REQ) && age_ok && drain_req_ready) ||
      ((phase==RETIRE) && age_ok && rawd[67] && retire_ready);
    wire b_ok=rst_n && !row_bad_sel && age_ok;
    wire F1=normal_sel && lc_W, F2=normal_sel && ownv;
    wire N1=(normal_sel && !lc_W && a_early) || (b_ok && phase==RESET_REQ && drain_req_ready);
    wire N2=(normal_sel && !lc_W && own_ok && ownv) || (b_ok && ph_rw && rawd[68] && alld && drain_rsp_valid);
    // one level from each compare tree: the early phase/valid terms gate every channel's own
    // result (sel_i mutually exclusive; with no own channel F2=0), the OR of seven terms decides
    wire sd=ph_dw || ph_rw;
    assign hg_host=N2 && ph_ack_h; assign hg_simd=N2 && ph_ack_s; assign hg_con=N2 && ph_con;
    assign hg_chd=N2 && ph_chd; assign hg_par=N2 && ph_par; assign hg_cdc=N2 && ph_cdc;
    assign hg_drsp=N2 && sd && drain_rsp_has_owner==rawd[59] && drain_rsp_reset_scope==reset_phase;
    wire hit=h_host || h_simd || h_con || h_chd || h_par || h_cdc || h_drsp;
`ifndef SYNTHESIS
    always @(posedge clk) if (LATE_CHECK && por_n && !$isunknown(hit) && hit!==(
      (N2 && ph_ack_h && !n_host) || (N2 && ph_ack_s && !n_simd) || (N2 && ph_con && !n_con) ||
      (N2 && ph_chd && !n_chd) || (N2 && ph_par && !n_par) || (N2 && ph_cdc && !n_cdc) ||
      (N2 && sd && !n_drsp && drain_rsp_has_owner==rawd[59] && drain_rsp_reset_scope==reset_phase)))
      $fatal(1,"FENCE_LATE_CHECK_HIT_MISMATCH");
`endif
    wire miss=(F2 && ph_ack_h && n_host) || (F2 && ph_ack_s && n_simd) || (F2 && ph_con && n_con) ||
      (F2 && ph_chd && n_chd) || (F2 && ph_par && n_par) || (F2 && ph_cdc && n_cdc) ||
      (F2 && sd && !(!n_drsp && drain_rsp_has_owner==rawd[59] && drain_rsp_reset_scope==reset_phase));
    wire f0_l=F1 || miss;
    wire fire_nr_l=N1 || hit;
`ifndef SYNTHESIS
    always @(posedge clk) if (LATE_CHECK && por_n && fire_nr_l && !dirty && d_pn!==d_pn_ref)
      $fatal(1,"FENCE_LATE_CHECK_DPN_MISMATCH %h %h",d_pn,d_pn_ref);
    always @(posedge clk) if (LATE_CHECK && por_n && (f0_l!==f0 || fire_nr_l!==fire_nr) &&
                              !$isunknown({f0,fire_nr}))
      $fatal(1,"FENCE_LATE_CHECK_SELECT_MISMATCH f0=%b/%b fire=%b/%b",f0_l,f0,fire_nr_l,fire_nr);
`endif
    // Hold/reset rows without a full encoder behind the voter: on a clean row the witness is
    // encode(live) (ps==dup and data(ps)==live), so encode(hold) = ps ^ encode(hold ^ live), and
    // hold ^ live is only the age and the bp fault bit (reset: phase, age, bits 67/68): a few
    // XORs per check bit. The only dirty-row write is the scrub of a held row; its majority row
    // is unchanged since the previous edge (a dirty row is not written), so the full majority
    // encodings are registered one edge earlier and selected by the registered held flag.
    wire [70:0] dh_fast=({69'b0,(age_nd ^ rawd[70:69])} << 69) | ({70'b0,(bp && !rawd[60])} << 60);
    wire [70:0] dr_fast=({69'b0,rawd[70:69]} << 69) | ({70'b0,rawd[68]} << 68) | ({70'b0,rawd[67]} << 67) |
                        ({67'b0,(rawd[58:55] ^ RESET_REQ)} << 55);
    wire [143:0] e_base_fast=protected_state ^ encode_row(dh_fast);
    wire [143:0] e_rst_fast=protected_state ^ encode_row(dr_fast);
    reg [143:0] e_base_q, e_rst_q;
    always @(posedge clk or negedge por_n)
      if (!por_n) begin e_base_q<=0; e_rst_q<=0; end
      else begin e_base_q<=e_base; e_rst_q<=e_rst; end
    wire [143:0] e_base_u=held_dirty_q ? e_base_q : e_base_fast;
    wire [143:0] e_rst_u=held_dirty_q ? e_rst_q : e_rst_fast;
    wire [143:0] e_early=rst_n ? (fire_req ? e_req : e_base_u) : e_rst_u;
`ifndef SYNTHESIS
    always @(posedge clk) if (LATE_CHECK && por_n && late_we && !$isunknown({rst_n,fire_req}) &&
                              e_early!==(rst_n ? (fire_req ? e_req : e_base) : e_rst))
      $fatal(1,"FENCE_LATE_CHECK_HOLD_ROW_MISMATCH");
`endif
    wire [70:0] r_early=rst_n ? (fire_req ? r_req : r_base) : reset_raw;
    // encode is linear and f0/fire_nr are scalars: encode the differences off the late path
    wire [143:0] ed_inv=encode_row(d_inv), ed_pn=encode_row(d_pn);
    // the late transition selects between two precomputed rows (f0 and fire_nr exclusive)
    wire [143:0] enc_next=fire_nr_l ? (e_early ^ ed_pn) : (e_early ^ ({144{f0_l}} & ed_inv));
    wire [70:0] raw_ao=fire_nr_l ? (r_early ^ d_pn) : (r_early ^ ({71{f0_l}} & d_inv));
    wire [70:0] live_next=LATE_CHECK ? raw_ao : next_raw;
`ifndef SYNTHESIS
    // simulation proof obligation: the selected candidate encoding equals encode(next_raw)
    // (cycles whose next state is X in simulation, e.g. undriven bench inputs, are skipped)
    wire [70:0] ref_next=rst_n ? next_raw : reset_raw;
    always @(posedge clk) if (LATE_CHECK && por_n && !row_bad && !$isunknown(encode_row(ref_next))
                              && (enc_next!==encode_row(ref_next) || raw_ao!==ref_next))
      $fatal(1,"FENCE_LATE_CHECK_ENCODE_MISMATCH %h %h",enc_next,encode_row(ref_next));
    // on a clean row the select decision equals the released handshakes exactly
    always @(posedge clk) if (LATE_CHECK && por_n && !dirty && (f0!==(normal && invalid_input) || fire!==(f1|f2|f3|f4|f5|f6|f7|f8|f9|f10)))
      $fatal(1,"FENCE_LATE_CHECK_DECISION_MISMATCH f0=%b fire=%b",f0,fire);
    // safety obligation: no handshake ever fires on a row whose witness disagrees with live
    always @(posedge clk) if (LATE_CHECK && por_n && dirty && ((normal && invalid_input) || (f1|f2|f3|f4|f5|f6|f7|f8|f9|f10)
                              || visible_valid || retire_valid || drain_req_valid || req_ready || host_ack_ready
                              || simd_ack_retire_ready || consumer_ready || child_reverse_ready || parent_reverse_ready
                              || reverse_CDC_ready || drain_rsp_ready))
      $fatal(1,"FENCE_LATE_CHECK_RELEASE_ON_DIRTY_ROW");
`endif
    localparam [70:0] BOOT=(71'd10 << 55);
    // Cold POR assumes coordinated global reset; grants still wait source drain.
    // Runtime reset is synchronous and NEVER drops the retained owner identity.
    // The redundancy is physical: the witness duplicate and the three live copies are written
    // with the same values, so a synthesis tool merges them into one register (and folds the
    // dirty compare to zero) unless each copy is its own kept register instance. Synthesis of
    // LATE_CHECK=1 therefore stores every copy in a keep_hierarchy register (identical
    // behaviour to the procedural block below, which simulation keeps so benches can upset
    // individual copies by hierarchical deposit).
`ifdef SYNTHESIS
    localparam bit KEPT=LATE_CHECK;
`else
    localparam bit KEPT=1'b0;
`endif
    if (KEPT) begin: kept_state
      localparam [143:0] BOOT_ENC=encode_row(BOOT);
      // each copy in <=36-bit kept chunks, each forming its own write enable (the enable
      // fan-out is per chunk; late_we is never one net driving every state bit)
      wire [143:0] protected_state_n, ps_dup_n; wire [70:0] live_a_n, live_b_n, live_c_n;
      assign protected_state=~protected_state_n; assign ps_dup=~ps_dup_n;
      assign live_a=~live_a_n; assign live_b=~live_b_n; assign live_c=~live_c_n;
      genvar ck;
      for (ck=0; ck<4; ck=ck+1) begin: ps_ck
        ot_hbm_fence_keep_reg #(.W(36),.INIT(BOOT_ENC[36*ck +: 36])) u_ps(.clk(clk),.por_n(por_n),
          .bad(bad_q),.late_bad(late_bad),.dirty(dirty),.held(held_dirty_q),.d(enc_next[36*ck +: 36]),.qn(protected_state_n[36*ck +: 36]));
        ot_hbm_fence_keep_reg #(.W(36),.INIT(BOOT_ENC[36*ck +: 36])) u_dup(.clk(clk),.por_n(por_n),
          .bad(bad_q),.late_bad(late_bad),.dirty(dirty),.held(held_dirty_q),.d(enc_next[36*ck +: 36]),.qn(ps_dup_n[36*ck +: 36]));
      end
      for (ck=0; ck<2; ck=ck+1) begin: lv_ck
        localparam integer LO=36*ck, W=(ck==0) ? 36 : 35;
        ot_hbm_fence_keep_reg #(.W(W),.INIT(BOOT[LO +: W])) u_la(.clk(clk),.por_n(por_n),
          .bad(bad_q),.late_bad(late_bad),.dirty(dirty),.held(held_dirty_q),.d(live_next[LO +: W]),.qn(live_a_n[LO +: W]));
        ot_hbm_fence_keep_reg #(.W(W),.INIT(BOOT[LO +: W])) u_lb(.clk(clk),.por_n(por_n),
          .bad(bad_q),.late_bad(late_bad),.dirty(dirty),.held(held_dirty_q),.d(live_next[LO +: W]),.qn(live_b_n[LO +: W]));
        ot_hbm_fence_keep_reg #(.W(W),.INIT(BOOT[LO +: W])) u_lc(.clk(clk),.por_n(por_n),
          .bad(bad_q),.late_bad(late_bad),.dirty(dirty),.held(held_dirty_q),.d(live_next[LO +: W]),.qn(live_c_n[LO +: W]));
      end
    end else begin: plain_state
      always @(posedge clk or negedge por_n) begin
        if (!por_n) begin
          protected_state<=encode_row(BOOT); ps_dup<=encode_row(BOOT);
          live_a<=BOOT;live_b<=BOOT;live_c<=BOOT;
        end
        else if (LATE_CHECK) begin
          // enc_next/raw_ao already select the runtime-reset row while !rst_n
          if (late_we) begin
            protected_state<=enc_next; ps_dup<=enc_next;
            live_a<=live_next;live_b<=live_next;live_c<=live_next;
          end
        end
        else if (!row_bad) begin
          if (!rst_n) begin
            protected_state<=encode_row(reset_raw);
            live_a<=reset_raw;live_b<=reset_raw;live_c<=reset_raw;
          end else begin
            protected_state<=encode_row(next_raw);
            live_a<=next_raw;live_b<=next_raw;live_c<=next_raw;
          end
        end
        // UE: hold corrupted protected bits, fail closed until global cold recovery.
      end
    end
  end endgenerate
endmodule

// One physically separate register copy (keep_hierarchy: never merged with an equal copy),
// with its own copy of the LATE_CHECK write enable (same function as late_we).
(* keep_hierarchy *)
module ot_hbm_fence_keep_reg #(parameter integer W=1, parameter [W-1:0] INIT={W{1'b0}})(
  input wire clk, por_n, bad, late_bad, dirty, held, input wire [W-1:0] d, output wire [W-1:0] qn
);
  // the register is read through its inverted output (the ASAP7 async-reset flop has QN only),
  // so a consumer absorbs the inversion instead of paying an inverter behind every copy
  reg [W-1:0] q;
  assign qn=~q;
  // the enable and its complement are kept nets and the hold is an explicit AND-OR, so the
  // late data input meets one AO22 per bit (no enable flop in the library)
  (* keep *) wire en, en_n;
  assign en=!bad && !late_bad && (!dirty || held);
  assign en_n=!en;
  wire [W-1:0] nx=({W{en}} & d) | ({W{en_n}} & q);
  always @(posedge clk or negedge por_n)
    if (!por_n) q<=INIT;
    else q<=nx;
endmodule

// N-input OR (N <= 729) as six alternating NOR3/NAND3 levels whose level outputs are kept, so
// technology mapping cannot rebuild it as a chain of wide OR4/OR5 cells.
module ot_hbm_fence_or_tree #(parameter integer N=1)(input wire [N-1:0] x, output wire y);
  wire [728:0] l0={{(729-N){1'b0}}, x};
  (* keep *) wire [242:0] l1; (* keep *) wire [80:0] l2; (* keep *) wire [26:0] l3;
  (* keep *) wire [8:0] l4; (* keep *) wire [2:0] l5;
  genvar i;
  for (i=0;i<243;i=i+1) begin: g1 assign l1[i]=~(l0[3*i] | l0[3*i+1] | l0[3*i+2]); end
  for (i=0;i<81;i=i+1)  begin: g2 assign l2[i]=~(l1[3*i] & l1[3*i+1] & l1[3*i+2]); end
  for (i=0;i<27;i=i+1)  begin: g3 assign l3[i]=~(l2[3*i] | l2[3*i+1] | l2[3*i+2]); end
  for (i=0;i<9;i=i+1)   begin: g4 assign l4[i]=~(l3[3*i] & l3[3*i+1] & l3[3*i+2]); end
  for (i=0;i<3;i=i+1)   begin: g5 assign l5[i]=~(l4[3*i] | l4[3*i+1] | l4[3*i+2]); end
  assign y=~(l5[0] & l5[1] & l5[2]);
endmodule

// N-input OR (N <= 81) as four alternating NOR3/NAND3 levels with kept level outputs.
module ot_hbm_fence_or_tree81 #(parameter integer N=1)(input wire [N-1:0] x, input wire g,
  output wire y, output wire h);
  wire [80:0] l0={{(81-N){1'b0}}, x};
  (* keep *) wire [26:0] l1; (* keep *) wire [8:0] l2; (* keep *) wire [2:0] l3;
  genvar i;
  for (i=0;i<27;i=i+1) begin: g1 assign l1[i]=~(l0[3*i] | l0[3*i+1] | l0[3*i+2]); end
  for (i=0;i<9;i=i+1)  begin: g2 assign l2[i]=~(l1[3*i] & l1[3*i+1] & l1[3*i+2]); end
  for (i=0;i<3;i=i+1)  begin: g3 assign l3[i]=~(l2[3*i] | l2[3*i+1] | l2[3*i+2]); end
  assign y=~(l3[0] & l3[1] & l3[2]);
  // h = g && (x==0): the early gate joins the last level (one AND4) instead of a later AO
  assign h=l3[0] & l3[1] & l3[2] & g;
endmodule
