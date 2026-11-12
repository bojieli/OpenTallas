`timescale 1ns/100fs
// DH55-HSPLIT lockstep: original ot_s81hd_host_ep_core (REF) vs the split pair ot_s81hd_host_w_core +
// ot_s81hd_host_e_core (DUT), each with its own real peer safe8 lanes, fed the same peer stimulus.
// MODE 0 (boot, closed loop): the TEST boot profile of tb_s81hd_host_ctl_boot (3 real HBC records on lane0, TRACER
//   HFWD, 7 CSR frames on lane1) with a real ctl core per system; both must boot and configure identically.
// MODE 1 (open loop): h_tx_i from a host276 encoder (RESULT type 9 / STATUS type 8 / bad type frames, job_active),
//   sparse random peer frames on both lanes (HFWD, CSR, bad types), one lane1 bit error (absorbed by the safe8 replay)
//   and a forced 4-cycle lane1 flt vector on both systems (lane1 fault landing checked every cycle at E2W).
// Frame-exact checks (every frame, content and date):
//   peer0 RX (RESULT via lane0) date +0; lane1 TX INPUT (u_lane1.tx_v/tx_d, the seam contract) date exactly +W2E
//   (W->E seam); peer1 RX (STATUS via lane1) same content/order, date +1 within one gearbox slot (the safe8 link
//   launches on its 3-flits-per-4-edges gearbox phase, so a 1-edge input shift can arrive +0..+2 at the peer);
//   h_rx_o frames: type 7 HFWD +0, type 6 CSR (host1) +1 (E->W seam), type 8 fault STATUS same payload, date +0/+1;
//   no other frame, same counts.
// DH56: the DUT seam carries the two generated wrapper boundary flops of each plan port (gen.py ot_dp_st u_bout_* in
//   the source wrapper, u_bin_* in the destination wrapper; data reset-free) in addition to the W core landing / face
//   register and the E core lane1 mid stage (DH56 MID=1), i.e. the die-level seam = plan lane cycles 4 (boundary 2 +
//   fixed 2). Expected offsets: E2W=4, W2E=4; peer1 RX additionally +P1X=1 (E co_m relay on the HOST1 egress flits).
// DH58-RFRTL (l48rf): the W core lane0 RX stage (L0_STAGE=1) adds W0X=1 to every lane0 ingress frame: h_rx_o type 7
//   HFWD +1, and the DUT HBC runs on dates +1 (BOOT_HEADER_EDGE 502 / BOOT_COMMIT_EDGE 512, the HBC header / COMMIT
//   record date fields [289:242] +1; the body and its CRC32C are unchanged -- gen_vectors.py CRCs the body only).
//   MODE 0 also checks the DUT HBC receiver_edge / context_valid equal the REF ones one cycle earlier (the whole
//   receiver timeline is shifted by exactly W0X).  SPLIT_MUT 5 (stage dropped) must FAIL.
module tb_s81hd_host_split_lockstep #(parameter integer SPLIT_MUT=0, parameter integer MODE=0, parameter integer TX_STAGE=0, parameter integer TX_EXP=0);
 reg ck=0,rn=0,start=0;always #0.4165 ck=~ck;
 localparam integer E2W=4, W2E=4, P1X=1, W0X=1, TXX=TX_EXP;   // TXX: HEAD-94 TX_STAGE, +1 on every h_rx_o frame
 // ---------------- shared stimulus
 reg[1:0]pv=0;reg[552:0]pd0=0,pd0d=0,pd1=0;reg flip1=0;
 // ---------------- REF system
 wire[511:0]rh_tx0,rh_tx1,rp_tx0,rp_tx1;wire[1:0]rprv;wire[552:0]rprd0,rprd1;wire[3:0]rpf0,rpf1;
 wire[276:0]r_htx;wire[275:0]r_hrx;
 ot_s81hd_mesh_lane rp0(.ck(ck),.rst_n(rn),.chb(1'b1),.rx({2'b10,rh_tx0}),.tx(rp_tx0),.tx_v(pv[0]),.tx_d(pd0),.rx_v(rprv[0]),.rx_d(rprd0),.flt(rpf0));
 ot_s81hd_mesh_lane rp1(.ck(ck),.rst_n(rn),.chb(1'b1),.rx({2'b10,rh_tx1}),.tx(rp_tx1),.tx_v(pv[1]),.tx_d(pd1),.rx_v(rprv[1]),.rx_d(rprd1),.flt(rpf1));
 ot_s81hd_host_ep_core #(.LOCAL_STAGE(1),.LOCAL_RANK(0),.PHASE_BOUND(1),.CLOCK_RESET_ID(64'h5381C7C0DE1021),
  .BOOT_HEADER_EDGE(48'd501),.BOOT_COMMIT_EDGE(48'd511))ref_host(.ck(ck),.rst_n(rn),.start_i(start),
  .coll_i0({2'b10,rp_tx0}),.coll_i1({2'b10,rp_tx1^{511'd0,flip1}}),.coll_o0(rh_tx0),.coll_o1(rh_tx1),.h_tx_i(r_htx),.h_rx_o(r_hrx));
 // ---------------- DUT system
 wire[511:0]dh_tx0,dh_tx1,dp_tx0,dp_tx1;wire[1:0]dprv;wire[552:0]dprd0,dprd1;wire[3:0]dpf0,dpf1;
 wire[276:0]d_htx;wire[275:0]d_hrx;wire[557:0]seam_rx,seam_rx_e;wire[553:0]seam_tx,seam_tx_w;
 // wrapper boundary flops of the two seam ports (E u_bout_l1_rx_o -> W u_bin_l1_rx_i; W u_bout_l1_tx_o -> E u_bin_l1_tx_i)
 reg[557:0]wb_rx0=0,wb_rx1=0;reg[553:0]wb_tx0=0,wb_tx1=0;
 always@(posedge ck)begin wb_rx0<=seam_rx_e;wb_rx1<=wb_rx0;wb_tx0<=seam_tx_w;wb_tx1<=wb_tx0;end
 assign seam_rx=wb_rx1;assign seam_tx=wb_tx1;
 ot_s81hd_mesh_lane dp0(.ck(ck),.rst_n(rn),.chb(1'b1),.rx({2'b10,dh_tx0}),.tx(dp_tx0),.tx_v(pv[0]),.tx_d(pd0d),.rx_v(dprv[0]),.rx_d(dprd0),.flt(dpf0));
 ot_s81hd_mesh_lane dp1(.ck(ck),.rst_n(rn),.chb(1'b1),.rx({2'b10,dh_tx1}),.tx(dp_tx1),.tx_v(pv[1]),.tx_d(pd1),.rx_v(dprv[1]),.rx_d(dprd1),.flt(dpf1));
 ot_s81hd_host_w_core #(.SPLIT_MUT(SPLIT_MUT),.TX_STAGE(TX_STAGE),.LOCAL_STAGE(1),.LOCAL_RANK(0),.PHASE_BOUND(1),.CLOCK_RESET_ID(64'h5381C7C0DE1021),
  .BOOT_HEADER_EDGE(48'd501+W0X),.BOOT_COMMIT_EDGE(48'd511+W0X))dut_w(.ck(ck),.rst_n(rn),.start_i(start),
  .coll_i0({2'b10,dp_tx0}),.coll_o0(dh_tx0),.h_tx_i(d_htx),.h_rx_o(d_hrx),.l1_rx_i(seam_rx),.l1_tx_o(seam_tx_w));
 ot_s81hd_host_e_core dut_e(.ck(ck),.rst_n(rn),.coll_i1({2'b10,dp_tx1^{511'd0,flip1}}),.coll_o1(dh_tx1),.l1_rx_o(seam_rx_e),.l1_tx_i(seam_tx));
 // ---------------- h_tx source: real ctl per system (MODE 0) or one shared open-loop encoder (MODE 1)
 wire[1103:0]rring,dring;wire rcf,dcf;
 reg ev=0;reg[552:0]ef=0;reg job=0;wire[275:0]elane;wire efault;
 ot_s81hd_host276_tx u_enc(.ck(ck),.rn(rn),.v(ev),.frame(ef),.lane(elane),.fault(efault));
 wire[276:0]rctl_tx,dctl_tx;
 wire[31:0]r_off,d_off,r_per,d_per,d_plen,d_rbase,d_mdl;wire d_run;
 generate if(MODE==0)begin:g_ctl
  wire[44:0]ub0,ub1;wire[564:0]st0,st1;wire[63:0]a0,b0,n0,a1,b1,n1;
  ot_s81hd_ctl_core rctl(.ck(ck),.rst_n(rn),.start_i(start),.lep_fault_i(1'b0),.lw_i(11'd0),
   .lepk_i0(1104'd0),.lepk_o0(rring),.lepf_o0(rcf),.unit_o0(ub0),.ctrl_i0(32'd0),.x_o(st0),.b_i(565'd0),
   .h_tx_o(rctl_tx),.h_rx_i(r_hrx),.a_tx_o(a0),.b7_tx_o(b0),.n_tx_o(n0),.a_rx_i(64'd0),.b7_rx_i(64'd0),.n_rx_i(64'd0));
  ot_s81hd_ctl_core dctl(.ck(ck),.rst_n(rn),.start_i(start),.lep_fault_i(1'b0),.lw_i(11'd0),
   .lepk_i0(1104'd0),.lepk_o0(dring),.lepf_o0(dcf),.unit_o0(ub1),.ctrl_i0(32'd0),.x_o(st1),.b_i(565'd0),
   .h_tx_o(dctl_tx),.h_rx_i(d_hrx),.a_tx_o(a1),.b7_tx_o(b1),.n_tx_o(n1),.a_rx_i(64'd0),.b7_rx_i(64'd0),.n_rx_i(64'd0));
  assign r_htx=rctl_tx;assign d_htx=dctl_tx;
  assign r_off=32'(rctl.u_logic.c_iss_off);assign d_off=32'(dctl.u_logic.c_iss_off);
  assign r_per=32'(rctl.u_logic.c_iss_per);assign d_per=32'(dctl.u_logic.c_iss_per);
  assign d_plen=32'(dctl.u_logic.c_plen);assign d_rbase=32'(dctl.u_logic.c_rbase);
  assign d_mdl=32'(dctl.u_logic.c_merge_dl);assign d_run=dctl.u_logic.c_run;
 end else begin:g_open
  assign rring=0;assign dring=0;assign rcf=0;assign dcf=0;
  assign r_htx={job,elane};assign d_htx={job,elane};
  assign r_off=0;assign d_off=0;assign r_per=0;assign d_per=0;assign d_plen=0;assign d_rbase=0;assign d_mdl=0;assign d_run=0;
 end endgenerate
 // ---------------- h_rx decoders (independent host276 RX per system)
 wire rdv,ddv,rdf,ddf;wire[552:0]rdd,ddd;
 ot_s81hd_host276_rx u_rdec(.ck(ck),.rn(rn),.lane(r_hrx),.v(rdv),.frame(rdd),.fault(rdf));
 ot_s81hd_host276_rx u_ddec(.ck(ck),.rn(rn),.lane(d_hrx),.v(ddv),.frame(ddd),.fault(ddf));
 // ---------------- frame scoreboards: REF frames queued with their expected DUT date
 typedef struct {int date;logic[552:0]f;} rec_t;
 rec_t q_hrx[$],q_p0[$],q_p1[$],q_l1[$];
 int n_l1=0,n_hrx=0,n_p0=0,n_p1=0,n_t6=0,n_t7=0,n_t8=0,n_err=0;
 int c=0;reg[3:0]ref_lf1_q[0:E2W-1];reg ref_ctxv_q=0;reg[47:0]ref_re_q=0;initial foreach(ref_lf1_q[k])ref_lf1_q[k]=0;
 function automatic int hrx_off(input logic[552:0]f);
  case(f[3:0])4'd7:return W0X+TXX;4'd6:return E2W+TXX;default:return -1;endcase
 endfunction
 task automatic fail(input string m);$display("LOCKSTEP MISMATCH cyc%0d: %s",c,m);n_err++;if(n_err>4)$fatal(1,"HEAD_HOST_SPLIT LOCKSTEP FAIL");endtask
 task automatic expect_rx(ref rec_t q[$],input logic[552:0]f,input string nm,input int lo,input int hi);
  if(q.size()==0)begin fail({nm," DUT frame with no REF frame"});return;end
  if(q[0].f!==f)begin fail($sformatf("%s content differs ref%h dut%h",nm,q[0].f[87:0],f[87:0]));void'(q.pop_front());return;end
  if(c<q[0].date+lo||c>q[0].date+hi)fail($sformatf("%s date dut%0d expected%0d",nm,c,q[0].date));
  void'(q.pop_front());
 endtask
 // ---------------- MODE 0 boot stimulus (tb_s81hd_host_ctl_boot)
 reg[559:0]records[0:15],recd[0:15];integer age=29;reg[63:0]data;reg[7:0]addr;string vec;
 localparam[511:0]TRACER=512'hFEDCBA9876543210_0123456789ABCDEF_89ABCDEF01234567_76543210FEDCBA98_ABCDEF0123456789_3210FEDCBA987654_9ABCDEF012345678_456789ABCDEF0123;
 function automatic[552:0]hf(input[511:0]payload);hf={1'b1,24'd0,payload,12'd0,4'd7};endfunction
 function automatic[552:0]csr(input[7:0]a,input[63:0]d);reg[552:0]f;begin f=0;f[552]=1;f[3:0]=6;f[23:16]=a;f[87:24]=d;csr=f;end endfunction
 function automatic[552:0]ctlf(input[3:0]t,input[63:0]d);reg[552:0]f;begin f=0;f[552]=1;f[3:0]=t;f[87:24]=d;f[151:88]=~d;ctlf=f;end endfunction
 integer i,seed=1;integer last0=-100,last1=-100,lastc=-100;
 initial begin
  if(MODE==0)begin
   if(!$value$plusargs("VEC=%s",vec))$fatal(1,"VEC required");$readmemh({vec,"/m0.memh"},records);
   records[0][559:512]=501;records[0][289:242]=505;records[1][559:512]=505;records[2][559:512]=511;records[2][289:242]=511;
   foreach(recd[k])recd[k]=records[k];recd[0][289:242]=505+W0X;recd[2][289:242]=511+W0X;   // header / COMMIT dates
  end
  void'($value$plusargs("SEED=%d",seed));void'($urandom(seed));
 end
 wire[47:0]rboot=ref_host.u_hbc.boot_edge,dboot=dut_w.u_hbc.boot_edge;
 always@(negedge ck)begin
  c++;rn=(c>=8);pv=0;ev=0;flip1=0;pd0d=pd0;
  if(rn&&MODE==0)begin
   if(age>0)for(i=0;i<3;i++)if(int'(rboot)==int'(records[i][559:512])-age)begin pv[0]=1;pd0=hf(records[i][511:0]);pd0d=hf(recd[i][511:0]);end
   if(rboot==621)begin pv[0]=1;pd0=hf(TRACER);pd0d=pd0;end
   if(rboot>=580&&rboot<=604&&rboot[1:0]==0)begin
    case(rboot)580:begin addr=0;data=9;end 584:begin addr=1;data=0;end 588:begin addr=4;data=17'h1abcd;end
     592:begin addr=9;data={32'd0,16'd10000,16'd20000};end 596:begin addr=10;data=999;end 600:begin addr=3;data=4;end
     default:begin addr=8;data=1;end endcase
    pv[1]=1;pd1=csr(addr,data);
   end
   if(rboot==750)start=1;
  end
  if(rn&&MODE==1&&c>40&&c<6000)begin
   // sparse independent traffic; each source >= 12 cycles apart, cross-source >= 6 (no schedule collisions)
   if(c-last0>=12&&c-lastc>=6&&$urandom%9==0)begin pv[0]=1;pd0=($urandom%5==0)?ctlf(4'd3,{$urandom,$urandom}):hf({16{$urandom}});pd0d=pd0;last0=c;end
   else if(c-last1>=12&&c-last0>=6&&$urandom%9==0)begin pv[1]=1;pd1=($urandom%5==0)?ctlf(4'd2,{$urandom,$urandom}):csr($urandom,{$urandom,$urandom});last1=c;end
   if(c-lastc>=12&&$urandom%7==0)begin ev=1;lastc=c;
    case($urandom%6)0,1,2:ef=ctlf(4'd9,{$urandom,$urandom});3,4:ef=ctlf(4'd8,{$urandom,$urandom});default:ef=ctlf(4'd5,{$urandom,$urandom});endcase
   end
   if(c==1500)job=1;
   if(c==3000)flip1=1;
   // lane1 fault injection (DH56): the safe8 replay absorbs single bit errors, so the lane1 flt vector is forced
   // identically at the lane1 flt net of both systems (REF u_lane1 -> lf1, DUT u_lane1 in hd_host_e) for 4 cycles.
   // lf1 bit 0 lands in host_fault[4], which no frame-mux event sets in this profile.
   if(c==3200)begin force ref_host.lf1=4'b0001;force dut_e.flt=4'b0001;end
   if(c==3204)begin release ref_host.lf1;release dut_e.flt;end
  end
  // ---------- scoreboards (sampled after the posedge settled)
  if(rn)begin
   if(rdv)begin
    if(hrx_off(rdd)>=0)q_hrx.push_back('{c+hrx_off(rdd),rdd});else q_hrx.push_back('{c+TXX,rdd});
    n_hrx++;if(rdd[3:0]==6)n_t6++;else if(rdd[3:0]==7)n_t7++;else n_t8++;
   end
   if(rprv[0])begin q_p0.push_back('{c,rprd0});n_p0++;end
   if(rprv[1])begin q_p1.push_back('{c+W2E+P1X,rprd1});n_p1++;end
   if(ref_host.u_lane1.tx_v)begin q_l1.push_back('{c+W2E,ref_host.u_lane1.tx_d});n_l1++;end
   if(ddv)expect_rx(q_hrx,ddd,"h_rx_o",0,(ddd[3:0]!=6&&ddd[3:0]!=7)?E2W:0);
   if(dprv[0])expect_rx(q_p0,dprd0,"peer0_rx",0,0);
   if(dprv[1])expect_rx(q_p1,dprd1,"peer1_rx",-1,1);
   if(dut_e.u_lane1.tx_v)expect_rx(q_l1,dut_e.u_lane1.tx_d,"lane1_tx_in",0,0);
   foreach(q_hrx[k])if(q_hrx[k].date+E2W+TXX<c)begin fail("h_rx_o REF frame never seen at DUT");q_hrx.delete(k);break;end
   foreach(q_p0[k])if(q_p0[k].date<c)begin fail("peer0 REF frame never seen at DUT");q_p0.delete(k);break;end
   foreach(q_l1[k])if(q_l1[k].date<c)begin fail("lane1 TX input REF frame never seen at DUT");q_l1.delete(k);break;end
   foreach(q_p1[k])if(q_p1[k].date+1<c)begin fail("peer1 REF frame never seen at DUT");q_p1.delete(k);break;end
   // seam landing contract: the W lane1 fault landing equals the REF lane1 fault E2W cycles earlier
   if(dut_w.lf1!==ref_lf1_q[E2W-1])fail($sformatf("lane1 fault landing dut%h expected%h",dut_w.lf1,ref_lf1_q[E2W-1]));
   if(rdf||ddf)fail("host276 decode fault");
   if(MODE==0&&c>100&&((|ref_host.host_fault)||(|dut_w.host_fault)||rcf||dcf))fail("host/ctl fault in boot profile");
   if(MODE==0&&rboot!=dboot)fail("HBC boot counters diverge");
   if(MODE==0&&{dut_w.ctxv,dut_w.receiver_edge}!=={ref_ctxv_q,ref_re_q})
    fail($sformatf("HBC receiver timeline dut ctx%b edge%0d expected ctx%b edge%0d (REF one cycle earlier)",dut_w.ctxv,dut_w.receiver_edge,ref_ctxv_q,ref_re_q));
  end
  if(MODE==0&&rboot==850)begin
   if(!ref_host.ctxv||!dut_w.ctxv||r_off!=10000||d_off!=10000||d_plen!=9||d_rbase!=32'h1abcd||d_mdl!=999||!d_run||
      d_per!=r_per||n_t6!=7||n_t7!=1)
    fail($sformatf("boot/config mismatch dut ctx%b off%0d plen%0d t6=%0d t7=%0d",dut_w.ctxv,d_off,d_plen,n_t6,n_t7));
   finish_check();
  end
  if(MODE==1&&c==6400)begin
   if(n_p1==0||n_p0==0||n_l1!=n_p1||n_t8==0||!ref_host.host_fault[4])fail($sformatf("open-loop coverage too thin p0=%0d p1=%0d t8=%0d lf1=%h",n_p0,n_p1,n_t8,ref_host.host_fault[7:4]));
   if(ref_host.host_fault!==dut_w.host_fault)fail($sformatf("sticky fault vector ref%h dut%h",ref_host.host_fault,dut_w.host_fault));
   finish_check();
  end
  if(c>20000)$fatal(1,"no progress");
  for(int k=E2W-1;k>0;k--)ref_lf1_q[k]=ref_lf1_q[k-1];ref_lf1_q[0]=ref_host.lf1;ref_ctxv_q=ref_host.ctxv;ref_re_q=ref_host.receiver_edge;
 end
 task automatic finish_check();
  if(q_hrx.size()||q_p0.size()||q_p1.size()||q_l1.size())fail("REF frames left unmatched");
  if(n_err)$fatal(1,"HEAD_HOST_SPLIT LOCKSTEP FAIL errors%0d",n_err);
  $display("HEAD_HOST_SPLIT LOCKSTEP PASS MODE%0d SPLIT_MUT%0d E2W+%0d W2E+%0d h_rx frames%0d (t6 %0d t7 %0d t8/other %0d) peer0 %0d peer1 %0d lane1_tx_in %0d",
   MODE,SPLIT_MUT,E2W,W2E,n_hrx,n_t6,n_t7,n_t8,n_p0,n_p1,n_l1);
  $finish;
 endtask
endmodule
