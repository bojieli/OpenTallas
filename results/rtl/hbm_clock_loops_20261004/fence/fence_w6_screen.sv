// Default-off, one retained owner46+RFslot9 per selected SM port.
// This is NOT an adapter for the original bare RF ACK. Each identity-bearing
// input must be supplied by an admitted source retention/validation adapter.
// alldrain_live is CURRENT source state under admission-stop, including both
// CDC directions and pending certificates. A delayed historical flag packet
// cannot satisfy this contract. Child completion is aggregate validated reverse.
module ot_gpu_rf_visibility_fence_w6 #(
  parameter bit ENABLE=1'b0
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
    // Sole retained register: no unprotected shadow state or duplicate gen.
    reg [143:0] protected_state;
    wire [65:0] lo=decode64(protected_state[71:0]);
    wire [65:0] hi=decode64(protected_state[143:72]);
    wire row_bad=lo[65] | hi[65] | (|hi[63:7]);
    wire [70:0] raw={hi[6:0],lo[63:0]};
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
    assign fault=row_bad || raw[60];
    assign quarantine=!por_n || !rst_n || row_bad || raw[60] || reset_phase;
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
    localparam [70:0] BOOT=(71'd10 << 55);
    // Cold POR assumes coordinated global reset; grants still wait source drain.
    // Runtime reset is synchronous and NEVER drops the retained owner identity.
    always @(posedge clk or negedge por_n) begin
      if (!por_n) protected_state<=encode_row(BOOT);
      else if (!row_bad) begin
        if (!rst_n) begin
          protected_state<=encode_row(reset_raw);
        end else protected_state<=encode_row(next_raw);
      end
      // UE: hold corrupted protected bits, fail closed until global cold recovery.
    end
  end endgenerate
endmodule
