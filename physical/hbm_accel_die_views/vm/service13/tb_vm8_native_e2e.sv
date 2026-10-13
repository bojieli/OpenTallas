`timescale 1ns/1ps
// Minimum actual gate of the native VM8 service path:
//   real held producer (ot_hgi_sm_xload, XW_FLOW=1, the nine production records of tb_xload_cadence)
//   -> vm_service_root (22 real SRAM macros, 18 checker islands, ticket table)
//   -> 4 x ot_hbm_b2_vm8_sm_sink (PIPE=1), 8 SM x-write ports each.
// Golden: beats.txt (sink 0, port 0) is compared by tools/vm8_service/xload_flow_compare.py with the
// baseline emission of the unmodified producer; in the bench every SM port of every sink must carry the
// accepted beats in acceptance order, exactly once.
// Plusargs: +ACK_DELAY=n +ACK_SKEW=k (receiver r returns its ACK n + r k edges late), +TAP_LFSR=seed +TAP_BITS=b (per-receiver tap throttle),
//  +INJ_CE=n (single-bit flip on every n-th returned row), +INJ_UE=g / +INJ_UEV=g (double-bit flip on the
//  publication / verify read of accepted beat g), +INJ_WR=g (valid-code wrong write of beat g),
//  +INJ_EXP=g (uncorrectable expected seat at the publication check of beat g), +INJ_STALE=g (replay of the ACK
//  of the released beat g), +STALE_SINK=r (sink 2 keeps the old owner from record r on),
//  +EXPECT_FAULT=code (the run must end in the root quarantine with this code).
// Mutants: MUT_SINK_DATA, MUT_SINK_TICKET, MUT_SINK_EARLYACK (sink 3), MUT_XW_CREDIT, MUT_XW_RDPIN (producer),
//  and every root / checker / slice mutant by its own define.
//  +SEL=1..4 picks a mutated commit tracker (1 one stage short, 2 dispatch on the release, 3 release and sinks
//  ignored, 4 in-flight writes dropped from the count); +DROP_X=g drops beat g before the SM pins (E2E_XSM).
module tb_vm8_native_e2e;
`ifdef MUT_XW_CREDIT
 localparam integer MUTX=1;
`elsif MUT_XW_RDPIN
 localparam integer MUTX=2;
`else
 localparam integer MUTX=0;
`endif
`ifdef MUT_SINK_DATA
 localparam integer SMUT=1;
`elsif MUT_SINK_TICKET
 localparam integer SMUT=2;
`elsif MUT_SINK_EARLYACK
 localparam integer SMUT=3;
`else
 localparam integer SMUT=0;
`endif
 localparam integer MAXB=8192;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0,x_v=0; reg[39:0] base=0; reg[20:0] n=0; reg[3:0] p=0; reg[31:0] stride=0; reg[1:0] fmt=0;
 wire ready,done,xfault,en,req,last_beat; wire[6:0] addr,grp; wire[2047:0] data;
 wire[1351:0] vmq; wire[1095:0] vmr; wire[511:0] q; wire[31:0] cr; wire[8223:0] rsp;
 wire wr_ready;
 ot_hgi_sm_xload #(.XW_FLOW(1),.MUT_XW(MUTX),.BD(1),.BW8(1),.PMAX(8),.W8LQ(10)) u (.clk(clk),.rst_n(rst_n),.x_v(x_v),.x_rdy(ready),
 .x_base(base),.x_n(n),.x_p(p),.x_stride(stride),.x_space(2'd1),.x_fmt(fmt),.x_xb(7'd0),
 .xw_ready(wr_ready),.xw_last(last_beat),.x_done(done),.x_fault(xfault),.xw_en(en),.xw_addr(addr),.xw_grp(grp),.xw_data(data),
 .vmq(vmq),.vmr(vmr),.rg_req(req),.rg_gnt(1'b1),.wrq(q),.wrq_cr(cr),.wrr(rsp));
 function automatic [255:0] sector(input integer s);
  for(integer t=0;t<8;t=t+1) sector[32*t+:32]=32'h3f800000+32'(((s*8+t)%127)<<16);
 endfunction
 genvar b,gr;
 generate for(b=0;b<8;b=b+1) begin:g_l
  reg[256:0] pipe[0:7];
  always @(posedge clk) begin
   pipe[0]<=rst_n&&q[b*16+15]?{1'b1,sector(q[b*16+:15])}:257'd0;
   for(integer z=1;z<8;z=z+1) pipe[z]<=pipe[z-1];
  end
  assign rsp[b*257+:257]=pipe[7]; assign cr[b]=pipe[7][256];
 end endgenerate
 assign rsp[8223:2056]=0; assign cr[31:8]=0;
 generate for(b=0;b<4;b=b+1) begin:g_p
  reg[273:0] pipe[0:7];
  always @(posedge clk) begin
   pipe[0]<=rst_n&&vmq[b*338+337]?{1'b1,vmq[b*338+:16],1'b0,sector(vmq[b*338+309+:27])}:274'd0;
   for(integer z=1;z<8;z=z+1) pipe[z]<=pipe[z-1];
  end
  assign vmr[b*274+:274]=pipe[7];
 end endgenerate
 // ---------------- root ----------------
 function automatic [191:0] own(input integer id);
  own={6{32'h1b873593*(id+3)}}^192'(id);
 endfunction
 reg [191:0] wr_owner=0;reg [191:0] sink_owner[0:3];
 wire [3:0] tap_v,tap_ready;wire [2062:0] tap_data;wire [191:0] tap_owner;wire [15:0] tap_ticket;wire tap_last;
 wire [3:0] tap_ACK_v;wire [4*192-1:0] tap_ACK_owner;wire [4*16-1:0] tap_ACK_ticket;
 wire native_release;wire [15:0] release_ticket;wire release_last;
 wire drained,fault;wire [3:0] fault_code;wire [15:0] stale_count,dup_count,wrap_epochs;
 vm_service_root root(.clk(clk),.rst_n(rst_n),.rcv_mask(4'hf),
  .wr_v(en),.wr_ready(wr_ready),.wr_data({1'b1,addr,grp,data}),.wr_last(last_beat),.wr_owner(wr_owner),
  .tap_v(tap_v),.tap_ready(tap_ready),.tap_data(tap_data),.tap_owner(tap_owner),.tap_ticket(tap_ticket),.tap_last(tap_last),
  .tap_ACK_v(tap_ACK_v),.tap_ACK_owner(tap_ACK_owner),.tap_ACK_ticket(tap_ACK_ticket),
  .native_release(native_release),.release_ticket(release_ticket),.release_last(release_last),
  .drained(drained),.fault(fault),.fault_code(fault_code),.stale_count(stale_count),.dup_count(dup_count),.wrap_epochs(wrap_epochs));
 // ---------------- sinks, tap throttle, ACK delay ----------------
 integer ack_delay=0,ack_skew=0,tap_seed=0,tap_bits=1,inj_ce=0,inj_ue=-1,inj_uev=-1,inj_wr=-1,inj_exp=-1,inj_stale=-1,stale_sink=-1,expect_fault=0;
 reg [31:0] tl=32'd7;reg [3:0] gate=4'hf;reg hold0=0;integer reopen=0,inj_k=-1,relcyc=0,fasts=0,pubreads=0;
 always @(posedge clk)begin:g_gate
  reg [31:0] x;x=tl;x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);tl<=x;
  for(integer r=0;r<4;r=r+1)gate[r]<=(tap_seed==0||((x>>(r*5))&((32'd1<<tap_bits)-32'd1))!=0)&&!(r==0&&hold0);
 end
 wire [3:0] s_ready,s_ack_v,s_fault,s_drained;wire [191:0] s_ack_o[0:3];wire [15:0] s_ack_t[0:3];
 wire [7:0] s_en[0:3];wire [55:0] s_addr[0:3],s_grp[0:3];wire [8*2048-1:0] s_data[0:3];
 reg [208:0] dl[0:3][0:63];
 reg [3:0] st_v=0;reg [15:0] st_t=0;reg [191:0] st_o=0;
 generate for(gr=0;gr<4;gr=gr+1)begin:g_s
  ot_hbm_b2_vm8_sm_sink #(.MUT(gr==3?SMUT:0),.PIPE(1)) u_sink(.clk(clk),.rst_n(rst_n),.permit(1'b1),
   .expected_owner(sink_owner[gr]),.sm_mask(8'hff),
   .tap_v(tap_v[gr]&&gate[gr]),.tap_ready(s_ready[gr]),.tap_data(tap_data),.tap_owner(tap_owner),.tap_ticket(tap_ticket),
   .tap_ACK_v(s_ack_v[gr]),.tap_ACK_owner(s_ack_o[gr]),.tap_ACK_ticket(s_ack_t[gr]),
   .xw_en(s_en[gr]),.xw_addr(s_addr[gr]),.xw_grp(s_grp[gr]),.xw_data(s_data[gr]),.fault(s_fault[gr]),.drained(s_drained[gr]));
  assign tap_ready[gr]=s_ready[gr]&&gate[gr];
  always @(posedge clk)begin
   dl[gr][0]<={s_ack_v[gr]&&rst_n,s_ack_o[gr],s_ack_t[gr]};
   for(integer z=1;z<64;z=z+1)dl[gr][z]<=dl[gr][z-1];
  end
  wire [31:0] dly=ack_delay+gr*ack_skew;
  wire [208:0] d=dly==0?{s_ack_v[gr],s_ack_o[gr],s_ack_t[gr]}:dl[gr][dly-1];
  wire dv=d[208]===1'b1;
  assign tap_ACK_v[gr]=dv||st_v[gr];
  assign tap_ACK_owner[gr*192+:192]=dv?d[16+:192]:st_o;
  assign tap_ACK_ticket[gr*16+:16]=dv?d[15:0]:st_t;
 end endgenerate
 // ---------------- scoreboard ----------------
 reg [2061:0] acc_pay[0:MAXB-1];reg [7:0] acc_id[0:MAXB-1];reg acc_last[0:MAXB-1];
 integer xcyc[0:3][0:MAXB-1];
 integer n_acc=0,n_rel=0,n_x[0:3],n_sa[0:3],n_ra[0:3];
 integer cyc=0,fd,id=0,startcyc=0,count=0,run=0,maxrun=0,first=-1,last=-1,prev=-2;
 integer overlap=0,rowwraps=0,rewinds=0,ce_n=0,cap_n=0,max_out=0,held_cyc=0,inj_hit=0;
 reg held=0;reg [2062:0] held_payload;reg quiet=0;integer quiet_x[0:3];integer quiet_rel=0;
 function automatic [15:0] tick(input integer g);
  tick={11'(g/32),1'(g%2),4'((g/2)%16)};
 endfunction
 integer k,rr,ss;
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(rst_n)begin
   if(held&&(!en||{addr,grp,data,last_beat}!==held_payload))$fatal(1,"E2E FAIL held producer changed before acceptance");
   held<=en&&!wr_ready;if(en&&!wr_ready)begin held_payload<={addr,grp,data,last_beat};held_cyc=held_cyc+1;end
   if(xfault)$fatal(1,"E2E FAIL producer fault");
   if(fault&&expect_fault==0)begin $display("root fault code%0d at cycle%0d",fault_code,cyc);$fatal(1,"E2E FAIL unexpected root fault");end
   if(s_fault!=0&&stale_sink<0)begin $display("sink fault%b at cycle%0d",s_fault,cyc);$fatal(1,"E2E FAIL unexpected sink fault");end
   if(en&&wr_ready)begin
    acc_pay[n_acc]={addr,grp,data};acc_id[n_acc]=8'(id);acc_last[n_acc]=last_beat;
    count=count+1;if(first<0)first=cyc;run=cyc==prev+1?run+1:1;if(run>maxrun)maxrun=run;prev=cyc;last=cyc;
    if(root.rowseq==8'hff)rowwraps=rowwraps+1;
    n_acc=n_acc+1;
   end
   if(root.slices[0].u_slice.wv_q&&root.slices[0].u_slice.re_q!=0)overlap=overlap+1;
   if(root.rewind)rewinds=rewinds+1;
   if(root.fast)fasts=fasts+1;if(root.load_pub)pubreads=pubreads+1;
   for(rr=0;rr<4;rr=rr+1)begin
    if(s_en[rr]!=0)begin
     k=n_x[rr];
     if(s_en[rr]!==8'hff||k>=n_acc)begin $display("sink%0d x-write en%02h beat%0d accepted%0d",rr,s_en[rr],k,n_acc);$fatal(1,"E2E FAIL sink strobe");end
     for(ss=0;ss<8;ss=ss+1)
      if({s_addr[rr][ss*7+:7],s_grp[rr][ss*7+:7],s_data[rr][ss*2048+:2048]}!==acc_pay[k])begin
       $display("sink%0d SM%0d beat%0d payload/order mismatch at cycle%0d",rr,ss,k,cyc);$fatal(1,"E2E FAIL x-write payload");
      end
     if(rr==0)$fdisplay(fd,"%0d %0d %0d %0d %0512h",acc_id[k],cyc,s_addr[0][6:0],s_grp[0][6:0],s_data[0][2047:0]);
     xcyc[rr][k]=cyc;n_x[rr]=k+1;
    end
    if(s_ack_v[rr])begin
     k=n_sa[rr];
     if(k>=n_x[rr]||xcyc[rr][k]>=cyc)begin $display("sink%0d ACK%0d before the SM sampling edge",rr,k);$fatal(1,"E2E FAIL early ACK");end
     n_sa[rr]=k+1;
    end
    if(tap_ACK_v[rr]&&!st_v[rr])n_ra[rr]=n_ra[rr]+1;
   end
   if(native_release)begin
    k=n_rel;
    if(k>=n_acc||release_ticket!==tick(k)||release_last!==acc_last[k]||n_ra[0]<=k||n_ra[1]<=k||n_ra[2]<=k||n_ra[3]<=k)begin
     $display("release%0d ticket%04h want%04h acks%0d,%0d,%0d,%0d",k,release_ticket,tick(k),n_ra[0],n_ra[1],n_ra[2],n_ra[3]);
     $fatal(1,"E2E FAIL release before every receiver ACK or out of order");
    end
    n_rel=n_rel+1;relcyc=cyc;
   end
   if(n_acc-n_rel>32)$fatal(1,"E2E FAIL more than 32 outstanding");
   if(n_acc-n_rel>max_out)max_out=n_acc-n_rel;
   if(quiet)begin
    if(wr_ready||tap_v!=0)$fatal(1,"E2E FAIL acceptance/publication after the fault");
   end
  end
 end
 // ---------------- x-store commit / drain join (ot_hbm_b2_xcommit) and the dispatch edge ----------------
 // The ACK / release proves only that the SM pins sampled a beat.  The dispatcher start passes the tracker's
 // registered start gate: final release && every sink drained && the last SRAM write edge has passed.
 // Five trackers (MUT 0..4) run in parallel, +SEL picks the one that dispatches.  With E2E_XSM the REAL native SM
 // (ot_hbm_accel_smh, production defines, no parameter overrides) hangs on sink 0 port 5: its start_ready gates
 // the dispatch and, at the dispatch edge, all 256 x-store macros are read back against a shadow of the beats the
 // SM pins sampled (every bit of every group sampled since reset).  The op itself is not started in this bench
 // (start to the SM stays 0: op execution after the gated start is the scope of tb_hbm_b2_xcommit).
 // +DROP_X=g: beat g never reaches the SM pins (a dropped commit).
 localparam integer SMI=5,XC=3152,NSR=256;
 integer sel=0,drop_x=-1,n_disp=0,dcyc=0,exp_beats=-1,xs_words=0,xs_bad=0;
 reg cmd_begin=0,start_in=0,drop_now=0,rb_q=0;
 wire [4:0] t_start,t_taken,t_fault,t_ok;wire sm_start_ready;
 genvar gm;
 generate for(gm=0;gm<5;gm=gm+1)begin:g_trk
  ot_hbm_b2_xcommit #(.NSM(32),.NSINK(4),.MUT(gm)) u(.clk(clk),.rst_n(rst_n),.xw_en({s_en[3],s_en[2],s_en[1],s_en[0]}),
   .sink_drained(s_drained),.cmd_begin(cmd_begin),.release_final(native_release&&release_last),.start_in(start_in),
   .start_committed(1'b0),.start_ready(sm_start_ready&&sel==gm),.x_inflight(),.x_drained(),.dispatch_ok(t_ok[gm]),
   .start_out(t_start[gm]),.start_taken(t_taken[gm]),.fault(t_fault[gm]));
 end endgenerate
 wire rb_fire=t_start[sel[2:0]]&&sm_start_ready;   // the dispatcher takes the command on the upcoming edge
 integer xbad[0:NSR-1],xchk[0:NSR-1];
 initial for(integer i=0;i<NSR;i=i+1)begin xbad[i]=0;xchk[i]=0;end
`ifdef E2E_XSM
 reg [13*2048-1:0] fragx[0:127],fragm[0:127];
 initial for(integer i=0;i<128;i=i+1)begin fragx[i]=0;fragm[i]=0;end
 reg cg_wake=1;
 wire sm_xw_en=s_en[0][SMI]&&!drop_now;
 wire sm_busy,sm_fault;
 ot_hbm_accel_smh xsm(.clk(clk),.rst_n(rst_n),.start(1'b0),.start_ready(sm_start_ready),.op_rows(13'd0),.op_c(16'd0),
  .op_g(8'd0),.op_gs(1'b0),.op_fmt(2'd0),.op_xb(7'd0),.busy(sm_busy),.d_valid(1'b0),.d_ready(),.d_base(32'd0),.d_lines(24'd0),
  .req_v(),.req_ready(1'b1),.req_addr(),.req_tag(),.rsp_v(1'b0),.rsp_tag(10'd0),.rsp_data(1088'd0),.xw_en(sm_xw_en),
  .xw_addr(s_addr[0][SMI*7+:7]),.xw_grp(s_grp[0][SMI*7+:7]),.xw_data(s_data[0][SMI*2048+:2048]),.rv(),.rrow(),.rdata(),
  .fault(sm_fault),.arrive(),.release_in(1'b0),.released(),.cg_en(cg_wake));
 initial if(xsm.DEF!=1||xsm.NBEAT!=13||xsm.TAGW!=16||xsm.REQCR!=1||xsm.RMAX!=4096)$fatal(1,"E2E FAIL the SM is not the selected native configuration");
 always @(negedge clk)begin
  drop_now=drop_x>=0&&n_x[0]==drop_x;
  cg_wake<=!rst_n||s_en[0][SMI];
  if(rst_n&&s_en[0][SMI])begin
   fragx[s_addr[0][SMI*7+:7]][s_grp[0][SMI*7+:7]*2048+:2048]=s_data[0][SMI*2048+:2048];
   fragm[s_addr[0][SMI*7+:7]][s_grp[0][SMI*7+:7]*2048+:2048]={2048{1'b1}};
  end
  if(rst_n&&sm_fault)$fatal(1,"E2E FAIL SM fault");
 end
 genvar gc,gp,gj,gx;
 generate for(gc=0;gc<8;gc=gc+1)begin:m_c for(gp=0;gp<2;gp=gp+1)begin:m_p for(gj=0;gj<2;gj=gj+1)begin:m_j for(gx=0;gx<4;gx=gx+1)begin:m_x
  localparam integer IDX=((gc*2+gp)*2+gj)*4+gx;
  localparam integer R=gp*2+gj;
  localparam integer BK=gc*XC+R*532;
  localparam integer BF=gc*XC+2128+R*256;
  localparam integer NV=(gx==3)?20:256;
  `define XCM(BR) xsm.g_c[gc].g_p[gp].BR.u_t.u.u.g_lf[gj].u_lh.u_xs.u_leaf.g_xm[gx].u_x
  `define XCB(BR) \
   integer q,ad; reg [255:0] g,x,mk,df; reg [1023:0] w,wm; \
   initial for(q=0;q<130;q=q+1) `XCM(BR).arr[q]={8{32'h5a5a_0000^(IDX*32'h0001_0193)^(q*32'h0100_01b3)}}|258'd1; \
   always @(negedge clk) if(rst_n&&rb_fire)begin \
    xbad[IDX]=0;xchk[IDX]=0; \
    for(ad=0;ad<128;ad=ad+1)begin \
     g=`XCM(BR).arr[ad][255:0]; \
     w=1024'd0;w[531:0]=fragx[ad][BK+:532];w[787:532]=fragx[ad][BF+:256];x=w[gx*256+:256]; \
     wm=1024'd0;wm[531:0]=fragm[ad][BK+:532];wm[787:532]=fragm[ad][BF+:256];mk=wm[gx*256+:256]; \
     df=(g^x)&mk; \
     if(mk[NV-1:0]!=0)xchk[IDX]=xchk[IDX]+1; \
     if(df[NV-1:0]!=0)begin xbad[IDX]=xbad[IDX]+1;if(xbad[IDX]==1)$display("x-store macro c%0d R%0d m%0d addr%0d differs from the sampled beats at dispatch%0d",gc,R,gx,ad,n_disp);end \
    end \
   end
  if(gc<4)begin:g_s
   `XCB(g_tw)
  end else begin:g_s
   `XCB(g_te)
  end
  `undef XCB
  `undef XCM
 end end end end endgenerate
`else
 assign sm_start_ready=1'b1;
`endif
 always @(negedge clk)if(rst_n)begin
  if(t_fault[sel[2:0]])$fatal(1,"E2E FAIL commit tracker fault");
  if(rb_q)begin
   xs_bad=0;xs_words=0;for(integer i=0;i<NSR;i=i+1)begin xs_bad=xs_bad+xbad[i];xs_words=xs_words+xchk[i];end
   if(xs_bad!=0)begin $display("dispatch%0d: %0d x-store words not committed (of %0d checked)",n_disp-1,xs_bad,xs_words);$fatal(1,"E2E FAIL dispatch before the x-store commit");end
`ifdef E2E_XSM
   if(xs_words==0)$fatal(1,"E2E FAIL x-store readback checked nothing");
`endif
  end
  rb_q<=rb_fire;
  if(rb_fire)begin
   if(count!=exp_beats||n_rel!=n_acc||n_x[0]!=n_acc||n_x[1]!=n_acc||n_x[2]!=n_acc||n_x[3]!=n_acc)begin
    $display("dispatch%0d at cycle%0d beats%0d expected%0d accepted%0d released%0d",n_disp,cyc,count,exp_beats,n_acc,n_rel);
    $fatal(1,"E2E FAIL dispatch before the final release");
   end
   dcyc=cyc;n_disp=n_disp+1;
  end
 end
 // ---------------- injections (root bench hooks) ----------------
 integer bi;
 // A publication-read fault needs a publication read: receiver 0 is held for 20 accepted beats before the
 // target, so the beats behind it are published by publication reads; the first one captured after the
 // receiver is ready again takes the fault.
 wire integer pub_tgt=inj_ue>=0?inj_ue:inj_exp;
 wire pub_go=reopen!=0&&cyc>reopen+3;
 function automatic integer flight(input [4:0] tag);
  flight=n_rel+((32+tag-(n_rel%32))%32);
 endfunction
 always @(negedge clk)begin
  if(pub_tgt>=0&&reopen==0)begin
   if(n_acc>=pub_tgt-10&&hold0)begin hold0=0;reopen=cyc;end
   else if(n_acc>=pub_tgt-30&&n_acc<pub_tgt-10)hold0=1;
  end
  root.tb_rd_xor[0]=0;root.tb_rd_xor[1]=0;root.tb_wr_xor=0;root.tb_exp_xor[0]=0;root.tb_exp_xor[1]=0;root.tb_upset=0;
  for(bi=0;bi<2;bi=bi+1)if(root.t_v[3][bi])begin
   cap_n=cap_n+1;
   if(inj_ce>0&&(cap_n%inj_ce)==0)begin root.tb_rd_xor[bi][(cap_n*397)%2592]=1'b1;ce_n=ce_n+1;end
   if(inj_ue>=0&&pub_go&&inj_hit==0&&root.t_k[3][bi])begin
    root.tb_rd_xor[bi][301]=1'b1;root.tb_rd_xor[bi][322]=1'b1;inj_hit=inj_hit+1;inj_k=flight(root.t_n[3][bi]);
   end
   if(inj_uev>=0&&n_acc>inj_uev&&n_rel<=inj_uev&&!root.t_k[3][bi]&&root.t_n[3][bi]==5'(inj_uev))begin
    root.tb_rd_xor[bi][1500]=1'b1;root.tb_rd_xor[bi][1511]=1'b1;inj_hit=inj_hit+1;inj_k=inj_uev;
   end
   if(inj_exp>=0&&pub_go&&inj_hit==0&&root.t_k[3][bi])begin
    root.tb_exp_word=4'd5;root.tb_exp_xor[bi][10]=1'b1;root.tb_exp_xor[bi][44]=1'b1;inj_hit=inj_hit+1;inj_k=flight(root.t_n[3][bi]);
   end
  end
  if(inj_wr>=0&&root.w0_v&&n_acc==inj_wr+1&&{root.w0_slot,root.w0_bank}==5'(inj_wr))begin
   root.tb_wr_xor[3*72+:72]=root.banks[0].words[0].u_wb.encode64(64'h20);inj_hit=inj_hit+1;inj_k=inj_wr;
  end
  st_v=0;
  if(inj_stale>=0&&n_rel>inj_stale+40&&!fault&&inj_hit==0&&ack_delay>0&&!(dl[1][ack_delay+ack_skew-1][208]===1'b1))begin
   st_v[1]=1;st_t=tick(inj_stale);st_o=wr_owner;inj_hit=1;
  end
 end
 // ---------------- records ----------------
 integer base_service[0:8];integer svc[0:8],tails[0:8];
 task automatic quarantine_end;
  integer worst;
  begin
   if(fault_code!=4'(expect_fault))begin $display("fault code%0d expected%0d",fault_code,expect_fault);$fatal(1,"E2E FAIL wrong fault code");end
   repeat(4)@(negedge clk);quiet=1;repeat(300)@(negedge clk);
   worst=0;for(integer r=0;r<4;r=r+1)if(n_x[r]>worst)worst=n_x[r];
   k=inj_k;
   if(k>=0&&worst>k)begin $display("bad beat%0d reached an SM (published%0d)",k,worst);$fatal(1,"E2E FAIL bad beat published");end
   if(inj_hit==0)$fatal(1,"E2E FAIL injection missed");
   $display("E2E QUARANTINE PASS code=%0d bad_beat=%0d published_before=%0d accepted=%0d released=%0d stale=%0d dup=%0d",fault_code,k,worst,n_acc,n_rel,stale_count,dup_count);
   $fclose(fd);$finish;
  end
 endtask
 task automatic stale_owner_end;
  integer x2,r2;
  begin
   repeat(4)@(negedge clk);x2=n_x[2];r2=n_rel;repeat(400)@(negedge clk);
   if(n_x[2]!=x2||n_rel!=r2||!s_fault[2])begin $display("stale-owner sink sampled%0d->%0d released%0d->%0d",x2,n_x[2],r2,n_rel);$fatal(1,"E2E FAIL stale owner");end
   for(integer g=0;g<n_acc;g=g+1)if(acc_id[g]>=stale_sink&&g<n_rel)$fatal(1,"E2E FAIL beat released without the stale-owner receiver");
   $display("E2E STALE_OWNER PASS sink2_fault=1 sink2_sampled=%0d released=%0d accepted=%0d outstanding=%0d",n_x[2],n_rel,n_acc,n_acc-n_rel);
   $fclose(fd);$finish;
  end
 endtask
 task automatic command(input integer kk,input integer slots,input integer f);
  integer expected,timeout,completed,donecyc,lastacc;
  begin
   while(!ready) @(negedge clk);
   n=kk;p=slots;fmt=f;stride=kk;count=0;run=0;maxrun=0;first=-1;last=-1;prev=-2;
   wr_owner=own(id);for(integer r=0;r<4;r=r+1)if(!(r==2&&stale_sink>=0&&id>=stale_sink))sink_owner[r]=own(id);
   exp_beats=((kk+(f==0?511:f==1?1023:2047))/(f==0?512:f==1?1024:2048))*8*((slots*3152+2047)/2048);
   startcyc=cyc; @(negedge clk);x_v=1;cmd_begin=1;start_in=1;@(negedge clk);x_v=0;cmd_begin=0;
   timeout=0;
   while(!done&&timeout<400000)begin
    @(negedge clk);timeout=timeout+1;
    if(fault&&expect_fault!=0)quarantine_end();
    if(s_fault[2]&&stale_sink>=0)stale_owner_end();
   end
   completed=done;repeat(2)@(negedge clk);donecyc=cyc-startcyc;lastacc=last-startcyc;
   timeout=0;
   while(!(drained&&n_rel==n_acc&&(&s_drained))&&timeout<20000)begin
    @(negedge clk);timeout=timeout+1;
    if(fault&&expect_fault!=0)quarantine_end();
    if(s_fault[2]&&stale_sink>=0)stale_owner_end();
   end
   expected=((kk+(f==0?511:f==1?1023:2047))/(f==0?512:f==1?1024:2048))*8*((slots*3152+2047)/2048);
   if(!completed||!drained||n_rel!=n_acc||count!=expected)begin
    $display("record%0d k%0d p%0d f%0d count%0d expected%0d done%0d accepted%0d released%0d",id,kk,slots,f,count,expected,completed,n_acc,n_rel);
    $fatal(1,"E2E FAIL record incomplete");
   end
   for(integer r=0;r<4;r=r+1)if(n_x[r]!=n_acc||n_sa[r]!=n_acc)$fatal(1,"E2E FAIL receiver missed beats");
   timeout=0;while(n_disp<=id&&timeout<2000)begin @(negedge clk);timeout=timeout+1;end
   if(n_disp!=id+1)$fatal(1,"E2E FAIL no dispatch after the final release");
   @(negedge clk);start_in=0;
   // service ends on the edge that shows the release of the last beat (every receiver sampled and ACKed);
   // the baseline price ends two edges after x_done, when the last SM has sampled
   // and, since round 3, the service ends on the DISPATCH edge: the edge at which the dispatcher samples the
   // tracker's start (final release, sinks drained, x-store committed).  release= is the round-2 end point.
   svc[id]=dcyc-startcyc;tails[id]=svc[id]-lastacc;
   $display("E2E id=%0d K=%0d P=%0d fmt=%0d beats=%0d max_contiguous=%0d first=%0d last_accept=%0d producer_done=%0d release=%0d service=%0d tail=%0d price=%0d ratio=%0d.%04d",
    id,kk,slots,f,count,maxrun,first-startcyc,lastacc,donecyc,relcyc-startcyc,svc[id],tails[id],base_service[id],
    svc[id]/base_service[id],((svc[id]%base_service[id])*10000)/base_service[id]);
   $fflush();
   id=id+1;repeat(2)@(negedge clk);
  end
 endtask
 integer worst_num=0,worst_den=1;
 initial begin
  base_service[0]=2164;base_service[1]=181;base_service[2]=139;base_service[3]=11648;base_service[4]=499;
  base_service[5]=545;base_service[6]=26366;base_service[7]=2111;base_service[8]=4159;
  for(integer r=0;r<4;r=r+1)begin n_x[r]=0;n_sa[r]=0;n_ra[r]=0;sink_owner[r]=0;end
  void'($value$plusargs("ACK_DELAY=%d",ack_delay));void'($value$plusargs("ACK_SKEW=%d",ack_skew));void'($value$plusargs("TAP_BITS=%d",tap_bits));
  if($value$plusargs("TAP_LFSR=%d",tap_seed)&&tap_seed!=0)tl=tap_seed;
  void'($value$plusargs("INJ_CE=%d",inj_ce));void'($value$plusargs("INJ_UE=%d",inj_ue));void'($value$plusargs("INJ_UEV=%d",inj_uev));
  void'($value$plusargs("INJ_WR=%d",inj_wr));void'($value$plusargs("INJ_EXP=%d",inj_exp));void'($value$plusargs("INJ_STALE=%d",inj_stale));
  void'($value$plusargs("SEL=%d",sel));void'($value$plusargs("DROP_X=%d",drop_x));if(sel<0||sel>4)$fatal(1,"SEL 0..4");
  void'($value$plusargs("STALE_SINK=%d",stale_sink));void'($value$plusargs("EXPECT_FAULT=%d",expect_fault));
  if(ack_delay<0||ack_skew<0||ack_delay+3*ack_skew>64)$fatal(1,"ACK_DELAY + 3 ACK_SKEW 0..64");
  root.tb_rd_xor[0]=0;root.tb_rd_xor[1]=0;root.tb_wr_xor=0;root.tb_exp_xor[0]=0;root.tb_exp_xor[1]=0;root.tb_exp_word=0;root.tb_upset=0;
  fd=$fopen("beats.txt","w");repeat(5)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  command(5120,1,0);command(5120,1,1);command(5120,1,2);
  command(7168,4,0);command(7168,4,1);command(7168,4,2);
  command(8192,8,0);command(16384,8,1);command(32768,8,2);
  $fclose(fd);
  if(expect_fault!=0||stale_sink>=0)$fatal(1,"E2E FAIL expected fault never raised");
  if(inj_ce>0&&ce_n==0)$fatal(1,"E2E FAIL no corrected read injected");
  for(integer i=0;i<9;i=i+1)if(svc[i]*worst_den>worst_num*base_service[i])begin worst_num=svc[i];worst_den=base_service[i];end
  $display("E2E SUMMARY records=9 beats=%0d write_read_overlap_cycles=%0d row_wraps=%0d rewinds=%0d verify_read_publications=%0d publication_reads=%0d corrected_reads=%0d max_outstanding=%0d dispatches=%0d xstore_words_checked=%0d producer_held_cycles=%0d wrap_epochs=%0d worst_ratio=%0d.%04d rate_ok=%0d",
   n_acc,overlap,rowwraps,rewinds,fasts,pubreads,ce_n,max_out,n_disp,xs_words,held_cyc,wrap_epochs,worst_num/worst_den,((worst_num%worst_den)*10000)/worst_den,worst_num*10<=worst_den*11);
  if(overlap==0||rowwraps==0)$fatal(1,"E2E FAIL coverage: no write/read overlap or row wrap");
  $display("E2E PASS records=9");$finish;
 end
endmodule
