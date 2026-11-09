`timescale 1ps/1ps
// S81-TRANSPORT-FIX 11-08 (from the TRANSPORT-2 bench): real ot_s81ph_ctrl_pcr (one PC) -> bound-depth delay lines (+DN, +UP,
// free running like ot_dp_dly) -> real ot_s81_hbm_pcc + device model.  Exactly-once, in-order PHY acceptance, per-tag beat
// counts, write-done counts, no PHY refusal, no response refusal.  MODE 0 saturated, 1 random rate, 2 bursts, 3 window load.
// +FK=1 forces k_rdy low while idle (the sticky k_bad fault must fire).  run_ctrl_pcr_transport.sh is the gate.
module tb_krdy;
  integer BURST=4, DN=0, UP=0, MODE=0, N=4000, SEED=1, CKH=900, CKS=833, WP=-1, MAXL=1, FK=0;
  reg cks=0, ckh=0, rst=0;
  initial begin
    void'($value$plusargs("DN=%d",DN)); void'($value$plusargs("UP=%d",UP)); void'($value$plusargs("MODE=%d",MODE));
    void'($value$plusargs("N=%d",N)); void'($value$plusargs("FK=%d",FK)); void'($value$plusargs("WP=%d",WP)); void'($value$plusargs("MAXL=%d",MAXL)); void'($value$plusargs("SEED=%d",SEED)); void'($value$plusargs("BURST=%d",BURST));
  end
  always #(CKS/2) cks=~cks;
  always #(CKH/2) ckh=~ckh;
  initial begin repeat(40) @(posedge ckh); rst=1; end

  // stream side
  reg [340:0] rq=0; wire rk, rv, wd, s_ovf; wire [255:0] r_data; wire [16:0] r_tag; wire [3:0] r_beat; wire [1:0] co;
  // HBM face at the controller
  wire k_v, k_we, kr_rdy; reg k_rdy_d=0, k_wr_done_d=0, kr_v_d=0; wire [29:0] k_addr; wire [3:0] k_len; wire [16:0] k_tag;
  wire [255:0] k_wdata; wire [31:0] k_wstrb; reg [16:0] kr_tag_d=0; reg [3:0] kr_beat_d=0; reg [255:0] kr_data_d=0;
  ot_s81ph_ctrl_pcr u_ctl(.cks(cks),.ckh(ckh),.rst(rst),.ci(2'b01),.co(co),.rq(rq),.rk(rk),.rv(rv),.r_data(r_data),.r_tag(r_tag),
    .r_beat(r_beat),.wd(wd),.s_ovf(s_ovf),.k_v(k_v),.k_rdy(k_rdy_d),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),
    .k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done_d),.kr_v(kr_v_d),.kr_rdy(kr_rdy),.kr_tag(kr_tag_d),.kr_beat(kr_beat_d),.kr_data(kr_data_d));
  // PHY face
  reg q_v=0, q_we=0, r_rdy=0; reg [29:0] q_addr=0; reg [3:0] q_len=0; reg [16:0] q_tag=0; reg [255:0] q_wdata=0; reg [31:0] q_wstrb=0;
  wire q_rdy, wr_done, r_v; wire [16:0] p_tag; wire [3:0] p_beat; wire [255:0] p_data;
  wire [2:0] c; wire [3:0] b; wire [20:0] r; wire [4:0] col; wire [255:0] wdd, rdd; wire [31:0] ws; wire drv; wire [3:0] vc; wire viol; wire [31:0] nref, nrd;
  ot_s81_hbm_pcc #(.AW(30),.LENW(4),.TAGW(17),.BEATW(4)) u_c(.clk(ckh),.rst_n(rst),.q_v(q_v),.q_rdy(q_rdy),.q_addr(q_addr),.q_len(q_len),.q_tag(q_tag),
    .q_we(q_we),.q_wdata(q_wdata),.q_wstrb(q_wstrb),.wr_done(wr_done),.r_v(r_v),.r_rdy(r_rdy),.r_tag(p_tag),.r_beat(p_beat),.r_data(p_data),
    .d_cmd(c),.d_bank(b),.d_row(r),.d_col(col),.d_wdata(wdd),.d_wstrb(ws),.d_rv(drv),.d_rdata(rdd),.n_ref(nref),.n_rd(nrd));
  ot_s81_hbm3e_dev_bm #(.AW(30)) u_d(.clk(ckh),.rst_n(rst),.d_cmd(c),.d_bank(b),.d_row(r),.d_col(col),.d_wdata(wdd),.d_wstrb(ws),.d_rv(drv),.d_rdata(rdd),.viol(viol),.viol_code(vc));

  // bound-depth pipelines (DN controller->PHY, UP PHY->controller), each stage one ckh register
  localparam W_DN = 1+1+30+4+17+256+32+1;
  localparam W_UP = 1+1+1+17+4+256;
  reg [W_DN-1:0] dn_p [0:31]; reg [W_UP-1:0] up_p [0:31];
  integer i;
  wire [W_DN-1:0] dn_i = {kr_rdy,k_v,k_we,k_addr,k_len,k_tag,k_wdata,k_wstrb};
  wire [W_UP-1:0] up_i = {q_rdy,wr_done,r_v,p_tag,p_beat,p_data};
  wire [W_DN-1:0] dn_o = (DN==0)? dn_i : dn_p[DN-1];
  wire [W_UP-1:0] up_o = (UP==0)? up_i : up_p[UP-1];
  always @(posedge ckh) begin
    dn_p[0] <= dn_i; for(i=1;i<32;i=i+1) dn_p[i] <= dn_p[i-1];
    up_p[0] <= up_i; for(i=1;i<32;i=i+1) up_p[i] <= up_p[i-1];
  end
  always @* begin
    {r_rdy,q_v,q_we,q_addr,q_len,q_tag,q_wdata,q_wstrb} = dn_o;
    {k_rdy_d,k_wr_done_d,kr_v_d,kr_tag_d,kr_beat_d,kr_data_d} = up_o; if (FK>0 && hcyc>=lim-300 && hcyc<lim-290) k_rdy_d = 1'b0;
  end

  // request source (stream clock) with DQ=8 credits
  integer rlens[0:131071]; reg rwes[0:131071]; reg [3:0] rlen; integer beats[0:131071]; integer wn=0, first_iss=0;
  integer cred=8, issued=0; reg [63:0] lf=64'h1234_5678_9abc_def1;
  function [63:0] mix(input [63:0] x); mix = (x ^ (x<<13)) ^ ((x ^ (x<<13))>>7) ^ (((x ^ (x<<13)) ^ ((x ^ (x<<13))>>7))<<17); endfunction
  integer burst=0, gap=0;
  always @(posedge cks) if(rst && hcyc>100) begin
    lf <= mix(lf + SEED);
    rq[0] <= 0;
    if (rk) cred = cred + 1;
    gap = (gap>0)? gap-1 : 0;
    if (MODE==2 && gap==0 && burst==0) begin burst = BURST; gap = 576; end
    if (cred>0 && issued<N && (MODE!=2 || hcyc < lim - 1500) && (MODE==0 || MODE==3 || (MODE==1 && lf[7:0]<8'd8) || (MODE==2 && burst>0))) begin
      if (MODE==2) burst = burst-1; if (issued==0) first_iss = hcyc;
      rlen = 4'(1 + (lf[15:12] % MAXL)); rq[340:0] <= {256'(issued*64'h11), 32'hffff_ffff, 17'(issued), rlen, ((MODE==3)? 30'(issued) : (MODE==0)? {lf[29:9],lf[4:0],4'd0} : (MODE==2)? {lf[29:9],lf[8:5],lf[4:0]} : {lf[29:9],lf[8:5],5'd0}), (((WP<0)&&(MODE==0)&&(lf[10:8]==0))||((WP>=0)&&((lf[22:16]%100)<WP))), 1'b1}; rlens[issued] = rlen; rwes[issued] = (((WP<0)&&(MODE==0)&&(lf[10:8]==0))||((WP>=0)&&((lf[22:16]%100)<WP)));
      cred = cred - 1; issued = issued + 1;
    end
  end

  // PHY acceptance monitor: exact order, exactly once
  integer acc=0, lost=0, dup=0, phy_rejects=0, hcyc=0, stall=0; integer t_acc[0:131071]; integer lat, latmax=0, latsum=0, latn=0;
  reg [131071:0] seen=0, isrd=0; integer nextt=0;
  always @(posedge ckh) if(rst) begin
    hcyc <= hcyc+1;
    if (q_v && !q_rdy) phy_rejects <= phy_rejects+1;
    if (q_v && q_rdy) begin
      acc <= acc+1; t_acc[q_tag] = hcyc; if(!q_we) isrd[q_tag]=1;
      if (seen[q_tag]) begin dup <= dup+1; if(dup<5) $display("DUP tag %0d at %0d",q_tag,hcyc); end
      else if (q_tag != nextt) begin lost <= lost+1; if(lost<5) $display("OOO tag %0d expect %0d at %0d",q_tag,nextt,hcyc); end
      seen[q_tag] = 1; if (q_tag>=nextt) nextt = q_tag+1;
    end
    if (r_v && r_rdy) begin lat = hcyc - t_acc[p_tag]; if(lat>latmax) latmax=lat; latsum=latsum+lat; latn=latn+1; end
    stall <= (q_v && !q_rdy) ? stall : stall;
  end
  // read data check at the stream side
  integer rn=0, rbad=0, expr=0, wdn=0, last_ev=0, kr_rej=0;
  always @(posedge cks) if (rst) begin
    if (wd) begin wdn <= wdn+1; last_ev = hcyc; end
    if (rv) begin rn <= rn+1; last_ev = hcyc; beats[r_tag] = beats[r_tag] + 1;
      if (r_tag>= issued || !seen[r_tag] || rwes[r_tag] || r_beat != beats[r_tag]-1) rbad <= rbad+1; end
  end
  always @(posedge ckh) if (rst && r_v && !r_rdy) kr_rej <= kr_rej+1;
  // finish
  integer lim, hit=0;
  initial begin
    lim = 2000 + N*((MODE==2)?2:(MODE==3)?40:60) + 400*(DN+UP+10);
    repeat(lim) @(posedge ckh);
    hit = 0; begin : chk integer t; for (t=0;t<issued;t=t+1) begin if (rwes[t]) wn = wn+1; else if (beats[t] != rlens[t]) rbad = rbad+1; end end
    $display("RESULT MODE %0d DN %0d UP %0d SEED %0d issued %0d phy_accept %0d dup %0d ooo_lost %0d reads_resp %0d phy_rejects %0d latmax %0d latavg %0d viol %0d ovf %0d fault %0d last_ev %0d kr_rej %0d rbad %0d wd %0d/%0d phyrej %0d first %0d %s",
      MODE,DN,UP,SEED,issued,acc,dup,lost,rn,phy_rejects,latmax,(latn>0)?latsum/latn:0,viol,s_ovf,co[1],last_ev,kr_rej,rbad,wdn,wn,phy_rejects,first_iss,
      (dup==0 && lost==0 && acc==issued && rbad==0 && kr_rej==0 && wdn==wn && !viol && !s_ovf && !co[1]) ? "PASS" : "FAIL");
    $finish;
  end
endmodule
