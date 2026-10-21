// Exact selected8af L0 leaf: real CSR/ingest consumer after new registeredlanding.
// KS remains a checked transport descriptor, not a fabricated starter launch.
 wire [514:0] consumer_host;wire [52:0] cks,eks;wire [2:0] landing_fault;
 wire [76:0] actual_th;wire [53:0] actual_tk;wire [35:0] pw;wire [8:0] pl;
 wire [193:0] tw;wire [266:0] cf;
 reg [35:0] expectedpw[0:9999];reg [8:0] expectedpl[0:9999];reg [193:0] expectedtw[0:9999];
 integer pwgot=0,plgot=0,twgot=0;
 dsdv_hostb_landing #(.ENABLE(1)) landing(.ck(ck),.rst_n(rst_n),.select_hbe(1'b1),.legacy_f_host(515'd0),
 .hbe_f_host(host1),.legacy_f_ks(53'd0),.starter_f_ks(53'd0),.seq_f_host(consumer_host),.seq_f_ks(cks),.engram_f_ks(eks),.fault(landing_fault));
 dsdv_sh_lk #(.V(276),.MUT(0),.RL(1)) real_l0(.ck(ck),.rst_n(rst_n),.f_host(consumer_host),.t_host(actual_th),.f_lf(4'b0101),
 .f_ks(cks),.t_kd(actual_tk),.s_j(),.s_jd_w(2'd0),.s_jd_e(2'd0),.s_hw_w(),.s_hw_e(),.s_hc_w(9'd0),.s_hc_e(9'd0),
 .st_rg_w(2'b01),.st_rg_e(2'b01),.vi_s(276'd0),.vo_s(),.rn_o(),.rs_i(276'd0),.pw_o(pw),.pl_o(pl),.tw_o(tw),.cf_o(cf),
 .ks_o(),.kd_i(54'd0),.j_i(33'd0),.jd_o(),.sq_i(6'd0),.vf_i(1'b0));
 initial begin
  // Main initial has parsed VECTORS before the first clock; use first fallingedge.
  @(negedge ck);
  $readmemh({vectors,"/expectedpw.memh"},expectedpw);$readmemh({vectors,"/expectedpl.memh"},expectedpl);$readmemh({vectors,"/expectedtw.memh"},expectedtw);
 end
 always @(posedge ck)begin
  #0.02;
  if(cyc>=0)begin
   if((pw[35]||expectedpw[cyc][35])&&pw!==expectedpw[cyc])begin bad++;$display("BAD realPW %0d got%h exp%h",cyc,pw,expectedpw[cyc]);end
   if((pl[8]||expectedpl[cyc][8])&&pl!==expectedpl[cyc])begin bad++;$display("BAD realPL %0d",cyc);end
   if((tw[193]||expectedtw[cyc][193])&&tw!==expectedtw[cyc])begin bad++;$display("BAD realTW %0d",cyc);end
   if(pw[35])pwgot++;if(pl[8])plgot++;if(tw[193])twgot++;
   if(cyc==stopat-1)begin
    if(landing_fault||pwgot!=314||plgot!=1||twgot!=102)$fatal(1,"FAIL realconsumer %0d/%0d/%0d fault%h",pwgot,plgot,twgot,landing_fault);
    $display("PASS actual8afL0 consumer PW%0d/LEN%0d/TEMPLATE%0d byte/cycleexact; KSstarter/wholeprogrammeOPEN",pwgot,plgot,twgot);
   end
  end
 end
