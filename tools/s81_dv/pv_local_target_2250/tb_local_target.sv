`timescale 1ps/1ps
// Existing source4 ring plus the exact program -> join -> ingress wiring.
// The peer port is an explicitly already-landed component stimulus.
module tb_local_target;
 localparam T=834;reg cks=0,ck=0;always #(T/2)cks=~cks;always @(cks)ck<=cks;
 integer ns=-1,m=-1,mut=0,bad=0,njoin=0,nout=0,npin=0,nwrite=0;
 integer cfg_edge=-1,param_edge=-1,param_commit=-1;
 reg rs=1;initial #1 rs=0;
 reg enq=0,enl=0;always @(cks or enq)if(!cks)enl=enq;
 wire ckf0=cks&enl;wire ckf;assign #115 ckf=ckf0;
 reg[561:0]src=0;wire[827:0]lane_i={266'd0,src};wire[827:0]forwarded_i;assign #115 forwarded_i=lane_i;
 wire[827:0]lane_o;wire[2:0]land_fault;
 for(genvar l=0;l<3;l=l+1)begin:g_land
  dsdv_pv_local_land_n32_source4_276 dut(.ck_f(ckf),.i(forwarded_i[276*l+:276]),.ck(ck),.rs(rs),.k(6'd17),.o(lane_o[276*l+:276]),.fault(land_fault[l]));
 end
 reg[514:0]q=0;reg[561:0]peer=0;reg[511:0]ctl[0:7],expected[0:533];reg[8191:0]dir;
 wire[514:0]qp;wire cv,pp,launch,pfault;wire[19:0]owner,po;wire[20:0]pos,pop;wire[7:0]se,so;wire[15:0]lf,pf;wire[2:0]pr;wire[511:0]par;
 dsdv_pv_so_program #(.ENABLE(1))u_program(.clk(ck),.rst_n(rs),.q(q),.q_pass(qp),.cfg_v(cv),.owner(owner),.position(pos),.se_jid(se),.so_jid(so),.local_first(lf),.peer_first(pf),.param_v(pp),.param_row(pr),.param_owner(po),.param_position(pop),.param_d(par),.launch(launch),.fault(pfault));
 wire jv,jfault;wire[1:0]jq;wire[512:0]jd;
 dsdv_pv_half_join u_join(.clk(ck),.rst_n(rs),.cfg_v(cv),.local_first(lf),.peer_first(pf),.local_pv(lane_o[561:0]),.peer_pv(peer),.pv_v(jv),.pv_quarter(jq),.pv_d(jd),.fault(jfault));
 wire qv,ready,done,ifault;wire[511:0]qd;wire[11:0]fc;
 dsdv_pv_so_ingress #(.ENABLE(1),.HEADER_DEN(1))u_ingress(.clk(ck),.rst_n(rs),.cfg_v(cv),.cfg_owner(owner),.cfg_position(pos),.cfg_se_jid(se),.cfg_so_jid(so),
  .pv_v(jv),.pv_quarter(jq),.pv_d(jd),.param_v(pp),.param_row(pr),.param_owner(po),.param_position(pop),.param_d(par),
  .den_v(1'b0),.den_mask(16'd0),.den_owner(20'd0),.den_jid(8'd0),.launch(launch),.q_v(qv),.q_d(qd),.ready(ready),.done(done),.fault(ifault),.fault_code(fc));
 function automatic[31:0]val(input integer h,d);val=32'h3f000000^(32'(h)<<17)^32'(d*101);endfunction
 function automatic[512:0]word_(input integer n);
  integer t,b,w;reg[512:0]d;begin t=n/40;b=(n%40)/5;w=n%5;d=0;
   if(w==0)begin d[512]=1;d[98]=1;d[97:94]=4'(t);d[93:92]=2'(t/4);d[91:72]=20'h92345;d[119:99]=777;d[71:64]=8'(b);d[120]=1;d[128:121]=8'h31;end
   else for(integer h=0;h<16;h=h+1)d[32*h+:32]=val(h,32*t+8*(w-1)+b);
   word_=d;end
 endfunction
 always @(posedge cks)begin
  ns=ns+1;enq<=(ns>=15);
  if(ns>=100&&ns<420)src<=#20 {48'd0,word_(ns-100),1'b1};else src<=#20 0;
 end
 always @(negedge ck)begin
  q=0;peer=0;
  if(m+1==40)q={2'd0,ctl[0],1'b1};
  if(m+1>=45&&m+1<=50)q={2'd0,ctl[1+m+1-45],1'b1};
  if(m+1==780)q={2'd0,ctl[7],1'b1};
  if(m+1>=444&&m+1<764)peer={48'd0,word_(320+m+1-444),1'b1};
 end
 initial begin
  if($value$plusargs("mut=%d",mut));if(!$value$plusargs("DIR=%s",dir))$fatal;
  if(mut==0)$readmemh({dir,"/control.hex"},ctl);else $readmemh({dir,"/control_early.hex"},ctl);
  $readmemh({dir,"/expected.hex"},expected);
 end
 always @(posedge ck)begin
  m=m+1;if(m==11)rs<=#10 1;
  if(rs)begin
   if(q[0]&&q[512:509]==15)$display("EVENT PRIVATE_HEADER edge=%0d subtype=%0d",m,q[448:445]);
   if(cv)begin cfg_edge=m;$display("EVENT CFG_PIN_CAPTURE edge=%0d local_first=%0d peer_first=%0d",m,lf,pf);end
   if(pp)begin npin=npin+1;param_edge=m;$display("EVENT PARAM_PIN_CAPTURE edge=%0d row=%0d",m,pr);end
   if(u_ingress.g_enabled.cv)$display("EVENT INGRESS_CFG_CONSUME edge=%0d",m);
   if(u_ingress.g_enabled.pp_ok)begin nwrite=nwrite+1;param_commit=m;$display("EVENT PARAM_SRAM_COMMIT edge=%0d row=%0d data=%0128h",m,u_ingress.g_enabled.pr,u_ingress.g_enabled.par);end
  end
  #1;
  if(m>=118&&m<438)begin
   if(lane_o[561:0]!=={48'd0,word_(m-118),1'b1})begin bad=bad+1;$display("PIN_MISMATCH edge=%0d",m);end
   if(m==118)$display("EVENT LOCAL_PIN_FIRST edge=%0d departure=100 age=18",m);
  end
  if(jv)begin
   if(mut==0&&(njoin>=640||jd!==word_(njoin)||jq!==2'((njoin/40)/4)))begin bad=bad+1;$display("JOIN_MISMATCH edge=%0d n=%0d",m,njoin);end
   if(njoin==0)$display("EVENT JOIN_FIRST edge=%0d departure=100 age=%0d",m,m-100);
   njoin=njoin+1;
  end
  if(qv)begin
   if(nout>=534||qd!==expected[nout])begin bad=bad+1;$display("TARGET_MISMATCH edge=%0d word=%0d",m,nout);end
   if(nout==0)$display("EVENT TARGET_Q_FIRST edge=%0d",m);
   nout=nout+1;
  end
  if(m==1350)begin
   if(mut==0)begin
    if(bad||pfault||jfault||ifault||(|land_fault)||njoin!=640||nout!=534||npin!=5||nwrite!=5||cfg_edge!=41||param_edge!=51||param_commit!=52)$fatal(1,"LOCAL_TARGET_FAIL bad=%0d join=%0d output=%0d pf=%0d jf=%0d if=%0d lf=%b",bad,njoin,nout,pfault,jfault,ifault,land_fault);
    $display("LOCAL_TARGET_PASS pin18 join19 cfg41 param_pin51 param_commit52 joined640 output534");
   end else begin if(!jfault)$fatal(1,"LOCAL_TARGET_CAUSAL_ESCAPED");$display("LOCAL_TARGET_CAUGHT early_CFG_window join_fault=1");end
   $finish;
  end
 end
 initial begin #(T*1400);$fatal(1,"LOCAL_TARGET_TIMEOUT");end
endmodule
