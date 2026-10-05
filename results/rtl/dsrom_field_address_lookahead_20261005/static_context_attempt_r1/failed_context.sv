// ONE contextual measurement component; not a replacement whole-field engine.
// Source: ot_v41_spine_pq_static_w17w10 issuer/stream recurrence and capture banks.
// mode_legacy is a measurement-only path selector, never an engine feature.
module ot_v41_static_provider_context # (parameter integer CONTROL_STAGE=37)(
 input wire clk,rst_n,input wire [9:0] phase,input wire [1:0] accept_tag,issue_tag,
 input wire accept,can_go,sm_run,sw_v,s_ok,mode_legacy,
 output wire [319:0] phase_captures,output wire [47:0] stream_capture,
 output wire [46:0] lookahead_state,output wire [13:0] observed_legacy_addr);
 (* keep *) reg [9:0] phase_launch;
 (* keep *) reg [63:0] s_pw[0:3];
 (* keep *) reg [15:0] s_rs[0:3];
 reg [1:0] sm_tag;
 reg [15:0] sm_i;
 reg active_fam;reg [15:0] active_nbeat,active_base;reg [13:0] active_addr;
 reg legacy_select;
 wire [63:0] spw=s_pw[sm_tag];
 wire [15:0] nbeat=legacy_select?spw[29:14]:active_nbeat;
 wire [15:0] sbase=legacy_select?spw[45:30]:active_base;
 wire s_last=sm_i+16'd1==nbeat;
 wire [15:0] ahead_i=sm_i+16'd2;
 (* keep *) wire [13:0] legacy_st_a=14'(sbase)+14'(!sw_v?sm_i:(s_last?16'd0:sm_i+16'd1));
 // Shared real provider, both source paths conservatively pass a fixture mux.
 (* keep *) wire [13:0] provider_addr=legacy_select?legacy_st_a:active_addr;
 (* keep *) wire [63:0] ph_q0,ph_q1;
 (* keep *) wire [47:0] st_q;
 generate if(CONTROL_STAGE==37) begin:g37
 ot_v41_stage37_control_rom u_controls(.phase(phase_launch),.stream_addr(provider_addr),.pq0(ph_q0),.pq1(ph_q1),.sq(st_q));
 end else if(CONTROL_STAGE==38) begin:g38
 ot_v41_stage38_control_rom u_controls(.phase(phase_launch),.stream_addr(provider_addr),.pq0(ph_q0),.pq1(ph_q1),.sq(st_q));
 end else begin:bad initial $fatal(1,"unbound provider stage");end endgenerate
 reg [47:0] sw;
 integer k;
 always @(posedge clk) begin
   phase_launch<=phase;legacy_select<=mode_legacy;
   if(rst_n) begin
     if(accept) begin s_pw[accept_tag]<=ph_q0;s_rs[accept_tag]<=ph_q1[15:0];end
     if(can_go) begin
       active_fam<=s_pw[issue_tag][0];active_nbeat<=s_pw[issue_tag][29:14];
       active_base<=s_pw[issue_tag][45:30];active_addr<=14'(s_pw[issue_tag][45:30]);
     end else if(sm_run&&(!sw_v||s_ok)) begin
       if(!sw_v||s_last) active_addr<=14'(active_base)+14'(active_nbeat==16'd1?16'd0:16'd1);
       else active_addr<=14'(active_base)+14'(ahead_i==active_nbeat?16'd0:ahead_i);
     end
     if(sm_run&&!sw_v) sw<=st_q;
     else if(sm_run&&sw_v&&s_ok) sw<=st_q;
   end
 end
 // Existing source index and tag launch state; no synthetic ROM-address stimulus.
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin sm_i<=0;sm_tag<=0;end
   else if(can_go) begin sm_i<=0;sm_tag<=issue_tag;end
   else if(sm_run&&sw_v&&s_ok) begin
     if(s_last) sm_i<=0;else sm_i<=sm_i+16'd1;
   end
 end
 generate for(genvar g=0;g<4;g=g+1) begin:observe
 assign phase_captures[80*g+:80]={s_rs[g],s_pw[g]};end endgenerate
 assign stream_capture=sw;
 assign lookahead_state={active_fam,active_nbeat,active_base,active_addr};
 assign observed_legacy_addr=legacy_st_a;
endmodule
