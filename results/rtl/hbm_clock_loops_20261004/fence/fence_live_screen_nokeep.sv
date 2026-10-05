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
function automatic logic [71:0] encode64(input logic [63:0] data);
    logic [71:0] c; integer p, k, j;
    begin
      c='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin c[p-1]=data[j]; j=j+1; end
      for (k=0;k<7;k=k+1)
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0 && p!=(1<<k)) c[(1<<k)-1]=c[(1<<k)-1]^c[p-1];
      c[71]=^c[70:0]; encode64=c;
    end
  endfunction
  // {uncorrectable, corrected, data64}; overall parity is bit71.
  function automatic logic [65:0] decode64(input logic [71:0] code);
    logic [71:0] c; logic [6:0] syndrome; logic overall, ue, corrected;
    logic [63:0] data; integer p,k,j;
    begin
      c=code; syndrome='0; overall=^code; ue=0; corrected=0;
      for (k=0;k<7;k=k+1)
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0) syndrome[k]=syndrome[k]^code[p-1];
      if (syndrome!=0) begin
        if (overall && syndrome<=71) begin c[syndrome-1]=~c[syndrome-1]; corrected=1; end
        else ue=1;
      end else if (overall) begin c[71]=~c[71]; corrected=1; end
      data='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin data[j]=c[p-1]; j=j+1; end
      decode64={ue,corrected,data};
    end
  endfunction
  function automatic logic [143:0] encode_row(input logic [70:0] raw);
    encode_row={encode64({57'b0,raw[70:64]}),encode64(raw[63:0])};
  endfunction
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
    wire [7:0] s_lo=synd72(protected_state[71:0]), s_hi=synd72(protected_state[143:72]);
    wire [127:0] diff_now={data72(protected_state[143:72]) ^ {57'b0,live_raw[70:64]},
                           data72(protected_state[71:0]) ^ live_raw[63:0]};
    // in-cycle conservative flag: zero exactly when protected_state==encode_row(live_raw)
    wire dirty=(|s_lo) | (|s_hi) | (|diff_now);
    reg [7:0] so_lo_q, so_hi_q; reg [127:0] diff_q; reg bad_q, held_dirty_q;
    wire [64:0] cr_lo=corr72(so_lo_q), cr_hi=corr72(so_hi_q);
    wire late_bad=cr_lo[64] | cr_hi[64] | (|(diff_q ^ {cr_hi[63:0],cr_lo[63:0]}));
    // write: never on a dirty row, except the scrub of a row held since the last edge whose
    // exact check found it correctable; never after an uncorrectable row (sticky bad_q).
    wire late_we=!bad_q && (!dirty || (held_dirty_q && !late_bad));
    always @(posedge clk or negedge por_n)
      if (!por_n) begin so_lo_q<=0; so_hi_q<=0; diff_q<=0; bad_q<=1'b0; held_dirty_q<=1'b0; end
      else begin
        so_lo_q<=s_lo; so_hi_q<=s_hi; diff_q<=diff_now;
        held_dirty_q<=dirty && !late_we;
        if (late_bad) bad_q<=1'b1;
      end
    // release gate (in-cycle) and reported fault (exact, late) for LATE_CHECK
    wire row_bad=LATE_CHECK ? (bad_q | dirty) : row_bad_now;
    wire fault_bad=LATE_CHECK ? (bad_q | late_bad) : row_bad_now;
    wire [70:0] raw=live_raw;
    wire [54:0] identity={raw[45:0],raw[54:46]};
    wire [3:0] phase=raw[58:55];
    wire reset_phase=(phase==RESET_REQ || phase==RESET_WAIT);
    wire age_ok=(raw[70:69]>=1);
    wire cdc_age_ok=(raw[70:69]>=2);
    wire normal=por_n && rst_n && !row_bad && !raw[60] && !reset_phase;
    wire drain_match=(drain_rsp_identity==identity &&
      drain_rsp_has_owner==raw[59] && drain_rsp_reset_scope==reset_phase);
    // Foreign/wrong-origin/out-of-order completions never advance any boundary.
    wire invalid_input=(host_ack_valid && (phase!=ACK || raw[61] || host_ack_identity!=identity)) ||
      (simd_ack_retire_valid && (phase!=ACK || !raw[61] || simd_ack_retire_identity!=identity)) ||
      (consumer_valid && (phase!=CONSUMER || consumer_identity!=identity)) ||
      (child_reverse_valid && (phase!=CHILD || child_reverse_identity!=identity)) ||
      (parent_reverse_valid && (phase!=PARENT || parent_reverse_identity!=identity)) ||
      (reverse_CDC_valid && (phase!=CDC || reverse_CDC_identity!=identity)) ||
      (drain_rsp_valid && (phase!=DRAIN_WAIT || !drain_match)) ||
      (req_valid && phase==IDLE && req_identity[47:45]>=6);
    wire live=normal && !invalid_input;
    assign req_ready=live && phase==IDLE && age_ok && req_identity[47:45]<6;
    assign host_ack_ready=live && phase==ACK && !raw[61] && age_ok && host_ack_identity==identity;
    assign simd_ack_retire_ready=live && phase==ACK && raw[61] && age_ok && simd_ack_retire_identity==identity;
    assign visible_valid=live && phase==VISIBLE && age_ok;
    assign visible_identity=identity;
    assign consumer_ready=live && phase==CONSUMER && age_ok && consumer_identity==identity;
    assign child_reverse_ready=live && phase==CHILD && age_ok && child_reverse_identity==identity;
    assign parent_reverse_ready=live && phase==PARENT && age_ok && parent_reverse_identity==identity;
    assign reverse_CDC_ready=live && phase==CDC && cdc_age_ok && reverse_CDC_identity==identity;
    assign drain_req_valid=por_n && rst_n && !row_bad && age_ok &&
      ((live && phase==DRAIN_REQ) || phase==RESET_REQ);
    assign drain_req_identity=identity;
    assign drain_req_has_owner=raw[59];
    assign drain_req_reset_scope=reset_phase;
    assign drain_rsp_ready=por_n && rst_n && !row_bad && age_ok && raw[68] && drain_match &&
      (&alldrain_live) && ((live && phase==DRAIN_WAIT) || phase==RESET_WAIT);
    assign retire_valid=live && phase==RETIRE && age_ok && raw[67];
    assign retire_identity=identity;
    assign fault=fault_bad || raw[60];
    assign quarantine=!por_n || !rst_n || fault_bad || raw[60] || reset_phase;
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
    // Each 55-bit identity compare is balanced in kept 8-bit groups (no linear OR chains).
    function automatic [6:0] neq8(input [54:0] a, input [54:0] b);
      integer g; begin for (g=0;g<7;g=g+1) neq8[g]=|((a ^ b) >> (8*g) & 55'hff); end
    endfunction
    wire [6:0] g_host; assign g_host=neq8(host_ack_identity,identity);
    wire [6:0] g_simd; assign g_simd=neq8(simd_ack_retire_identity,identity);
    wire [6:0] g_con; assign g_con=neq8(consumer_identity,identity);
    wire [6:0] g_chd; assign g_chd=neq8(child_reverse_identity,identity);
    wire [6:0] g_par; assign g_par=neq8(parent_reverse_identity,identity);
    wire [6:0] g_cdc; assign g_cdc=neq8(reverse_CDC_identity,identity);
    wire [6:0] g_drsp; assign g_drsp=neq8(drain_rsp_identity,identity);
    wire m_host=!(|g_host), m_simd=!(|g_simd), m_con=!(|g_con), m_chd=!(|g_chd),
         m_par=!(|g_par), m_cdc=!(|g_cdc);
    wire m_drsp=!(|g_drsp) && drain_rsp_has_owner==raw[59] && drain_rsp_reset_scope==reset_phase;
    wire lc_W=(host_ack_valid && (phase!=ACK || raw[61])) ||
      (simd_ack_retire_valid && (phase!=ACK || !raw[61])) ||
      (consumer_valid && phase!=CONSUMER) || (child_reverse_valid && phase!=CHILD) ||
      (parent_reverse_valid && phase!=PARENT) || (reverse_CDC_valid && phase!=CDC) ||
      (drain_rsp_valid && phase!=DRAIN_WAIT) || (req_valid && phase==IDLE && req_identity[47:45]>=6);
    wire lc_X=(host_ack_valid && !m_host) || (simd_ack_retire_valid && !m_simd) ||
      (consumer_valid && !m_con) || (child_reverse_valid && !m_chd) ||
      (parent_reverse_valid && !m_par) || (reverse_CDC_valid && !m_cdc) || (drain_rsp_valid && !m_drsp);
    wire alld=&alldrain_live;
    wire lc_A=(phase==IDLE && age_ok && req_valid && req_identity[47:45]<6) ||
      (phase==ACK && age_ok && ((host_ack_valid && !raw[61] && m_host) || (simd_ack_retire_valid && raw[61] && m_simd))) ||
      (phase==VISIBLE && age_ok && visible_ready) ||
      (phase==CONSUMER && age_ok && consumer_valid && m_con) ||
      (phase==CHILD && age_ok && child_reverse_valid && m_chd) ||
      (phase==PARENT && age_ok && parent_reverse_valid && m_par) ||
      (phase==CDC && cdc_age_ok && reverse_CDC_valid && m_cdc) ||
      (phase==DRAIN_REQ && age_ok && drain_req_ready) ||
      (phase==DRAIN_WAIT && age_ok && raw[68] && alld && drain_rsp_valid && m_drsp) ||
      (phase==RETIRE && age_ok && raw[67] && retire_ready);
    wire lc_B=por_n && rst_n && !row_bad && age_ok &&
      ((phase==RESET_REQ && drain_req_ready) || (phase==RESET_WAIT && raw[68] && alld && drain_rsp_valid && m_drsp));
    wire f0=normal && (lc_W || lc_X);
    wire fire=(normal && !lc_W && lc_A) || lc_B;
    reg [143:0] e_ph; reg [70:0] r_ph;
    always @* begin
      case (phase)
        IDLE:      begin e_ph=e_req;  r_ph=r_req;  end
        ACK:       begin e_ph=e_ack;  r_ph=r_ack;  end
        VISIBLE:   begin e_ph=e_vis;  r_ph=r_vis;  end
        CONSUMER:  begin e_ph=e_con;  r_ph=r_con;  end
        CHILD:     begin e_ph=e_chd;  r_ph=r_chd;  end
        PARENT:    begin e_ph=e_par;  r_ph=r_par;  end
        CDC:       begin e_ph=e_cdc;  r_ph=r_cdc;  end
        DRAIN_REQ, RESET_REQ:  begin e_ph=e_dreq; r_ph=r_dreq; end
        DRAIN_WAIT, RESET_WAIT: begin e_ph=e_drsp; r_ph=r_drsp; end
        RETIRE:    begin e_ph=e_ret;  r_ph=r_ret;  end
        default:   begin e_ph=e_base; r_ph=r_base; end
      endcase
    end
    // f0/fire are 0 while !rst_n (every ready and f0 include rst_n), so the reset choice is
    // folded into the hold candidate off the handshake path; one AO222 level per bit.
    wire hold=!f0 && !fire;
    wire [143:0] e_hold=rst_n ? e_base : e_rst;
    wire [70:0] r_hold=rst_n ? r_base : reset_raw;
    wire [143:0] enc_next=({144{f0}} & e_inv) | ({144{fire}} & e_ph) | ({144{hold}} & e_hold);
    wire [70:0] raw_ao=({71{f0}} & r_inv) | ({71{fire}} & r_ph) | ({71{hold}} & r_hold);
    wire [70:0] live_next=LATE_CHECK ? raw_ao : next_raw;
`ifndef SYNTHESIS
    // simulation proof obligation: the selected candidate encoding equals encode(next_raw)
    // (cycles whose next state is X in simulation, e.g. undriven bench inputs, are skipped)
    wire [70:0] ref_next=rst_n ? next_raw : reset_raw;
    always @(posedge clk) if (LATE_CHECK && por_n && !row_bad && !$isunknown(encode_row(ref_next))
                              && (enc_next!==encode_row(ref_next) || raw_ao!==ref_next))
      $fatal(1,"FENCE_LATE_CHECK_ENCODE_MISMATCH %h %h",enc_next,encode_row(ref_next));
    always @(posedge clk) if (LATE_CHECK && por_n && (f0!==(normal && invalid_input) || fire!==(f1|f2|f3|f4|f5|f6|f7|f8|f9|f10)))
      $fatal(1,"FENCE_LATE_CHECK_DECISION_MISMATCH f0=%b fire=%b",f0,fire);
    // safety obligation: no handshake ever fires on a row whose witness disagrees with live
    always @(posedge clk) if (LATE_CHECK && por_n && dirty && (f0 || fire || visible_valid || retire_valid || drain_req_valid))
      $fatal(1,"FENCE_LATE_CHECK_RELEASE_ON_DIRTY_ROW");
`endif
    localparam [70:0] BOOT=(71'd10 << 55);
    // Cold POR assumes coordinated global reset; grants still wait source drain.
    // Runtime reset is synchronous and NEVER drops the retained owner identity.
    always @(posedge clk or negedge por_n) begin
      if (!por_n) begin
        protected_state<=encode_row(BOOT);
        live_a<=BOOT;live_b<=BOOT;live_c<=BOOT;
      end
      else if (LATE_CHECK) begin
        // enc_next/raw_ao already select the runtime-reset row while !rst_n
        if (late_we) begin
          protected_state<=enc_next;
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
  end endgenerate
endmodule
