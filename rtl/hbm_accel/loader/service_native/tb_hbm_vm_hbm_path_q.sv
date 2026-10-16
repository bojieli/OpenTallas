`timescale 1ns/1ps
`default_nettype none
// Quadrant integration bench of the static HBM -> VM write path (G-VM-HBM-PATH), the die composition of one quadrant
// exactly as tools/hbm_die_v15/v16_specs/vmsm.json + full_die_v16.engine_region wire it: fill calendar
// ot_vms_calendar_static #(W=89) (programme loaded through its cfg port, launched once), 8 x ot_hbm_svc_vm_kshare
// (SM=k), 8 x ot_hbm_svc_vmdel_lane (bank_id=b, cross-lane status fan-out), 32 controller models on the K ports (K-port
// legality of ot_hbm_svc_pc_ctrl_leaf, random accept / out-of-order return / gaps), SM groups streaming random reads.
// Programme: two blocks (landing banks 0 and 1, different rows/epochs/VM bases): begin + window at word 0 / 1,
// start at word START0 / START1 (compiler-placed, fixed).  Checks every dq word the VM bank would write:
// 2 x 2048 sectors, sector = base + slot*32 + PC, data = HBM word of (PC, slot) at the window's address, mask ff,
// each sector exactly once, dq only during the 256-edge readouts; no fault anywhere; group reads all complete.
// MUT=1: start one block too early (start word 30) -> landing not ready -> fault / missing dq (must FAIL).
module tb_hbm_vm_hbm_path_q;
 parameter integer MUT=0;
 localparam integer W=89;
 reg hc=0,sc=0,hr=0,sr=0;always #0.6 hc=~hc;always #0.5 sc=~sc;
 // calendar
 reg cfg_we=0;reg[9:0]cfg_addr=0;reg[255:0]cfg_data=0;reg st_v=0;reg[9:0]st_base=0;reg[10:0]st_limit=0;reg[15:0]st_loops=0;
 wire[W-1:0]cal;wire cal_v,cal_act,cal_done,cal_fault;wire[31:0]ord;
 ot_vms_calendar_static #(.W(W)) u_cal(.clk(sc),.rst_n(sr),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_v(st_v),
  .start_base(st_base),.start_limit(st_limit),.start_loops(st_loops),.calendar(cal),.calendar_v(cal_v),.ordinal(ord),
  .active(cal_act),.done(cal_done),.fault(cal_fault));
 // fills / lanes
 wire[31:0]fv,fb;wire[191:0]fs;wire[511:0]fe;wire[8191:0]fd;   // by PC p
 wire[7:0]full0,full1,pcbad,lfault,lbusy;wire[1:0]bready[0:7];wire[2247:0]dq;
 genvar b,k;
 generate for(b=0;b<8;b=b+1)begin:lane
  ot_hbm_svc_vmdel_lane u(.clk(sc),.rst_n(sr),.bank_id(3'(b)),
   .begin_v_i(cal[0]),.begin_bank_i(cal[1]),.begin_epoch_i(cal[17:2]),.start_i(cal[18]),.start_bank_i(cal[19]),
   .start_epoch_i(cal[35:20]),.start_base_sector_i(cal[51:36]),
   .fill_v_i({fv[24+b],fv[16+b],fv[8+b],fv[b]}),.fill_bank_i({fb[24+b],fb[16+b],fb[8+b],fb[b]}),
   .fill_slot_i({fs[(24+b)*6+:6],fs[(16+b)*6+:6],fs[(8+b)*6+:6],fs[b*6+:6]}),
   .fill_epoch_i({fe[(24+b)*16+:16],fe[(16+b)*16+:16],fe[(8+b)*16+:16],fe[b*16+:16]}),
   .fill_data_i({fd[(24+b)*256+:256],fd[(16+b)*256+:256],fd[(8+b)*256+:256],fd[b*256+:256]}),
   .full0_all(full0),.full1_all(full1),.pcbad_all(pcbad),.full0(full0[b]),.full1(full1[b]),.pcbad(pcbad[b]),
   .block_ready(bready[b]),.busy(lbusy[b]),.fault(lfault[b]),.dq(dq[b*281+:281]));
 end endgenerate
 // K ports per PC p (controller side) and group side per SM k
 wire[31:0]ck_v,ck_we;reg[31:0]ck_rdy;wire[959:0]ck_addr;wire[127:0]ck_len;wire[543:0]ck_tag;
 reg[31:0]ckr_v;wire[31:0]ckr_rdy;reg[543:0]ckr_tag;reg[127:0]ckr_beat;reg[8191:0]ckr_data;
 reg[31:0]gk_v;wire[31:0]gk_rdy;reg[959:0]gk_addr;reg[127:0]gk_len;reg[543:0]gk_tag;
 wire[31:0]gkr_v;reg[31:0]gkr_rdy;wire[543:0]gkr_tag;wire[127:0]gkr_beat;wire[8191:0]gkr_data;wire[7:0]sfault;
 generate for(k=0;k<8;k=k+1)begin:share
  ot_hbm_svc_vm_kshare #(.SM(k)) u(.hbm_clk(hc),.hbm_rst_n(hr),.stream_clk(sc),.stream_rst_n(sr),
   .g_k_v(gk_v[4*k+:4]),.g_k_rdy(gk_rdy[4*k+:4]),.g_k_addr(gk_addr[120*k+:120]),.g_k_len(gk_len[16*k+:16]),.g_k_tag(gk_tag[68*k+:68]),
   .g_k_we(4'b0),.g_k_wdata(1024'b0),.g_k_wstrb(128'b0),.g_k_wr_done(),
   .g_kr_v(gkr_v[4*k+:4]),.g_kr_rdy(gkr_rdy[4*k+:4]),.g_kr_tag(gkr_tag[68*k+:68]),.g_kr_beat(gkr_beat[16*k+:16]),.g_kr_data(gkr_data[1024*k+:1024]),
   .c_k_v(ck_v[4*k+:4]),.c_k_rdy(ck_rdy[4*k+:4]),.c_k_addr(ck_addr[120*k+:120]),.c_k_len(ck_len[16*k+:16]),.c_k_tag(ck_tag[68*k+:68]),
   .c_k_we(ck_we[4*k+:4]),.c_k_wdata(),.c_k_wstrb(),.c_k_wr_done(4'b0),
   .c_kr_v(ckr_v[4*k+:4]),.c_kr_rdy(ckr_rdy[4*k+:4]),.c_kr_tag(ckr_tag[68*k+:68]),.c_kr_beat(ckr_beat[16*k+:16]),.c_kr_data(ckr_data[1024*k+:1024]),
   .vm_v(cal[52]),.vm_bank(cal[53]),.vm_epoch(cal[69:54]),.vm_row(cal[84:70]),.vm_col(cal[88:85]),
   .fill_v(fv[4*k+:4]),.fill_bank(fb[4*k+:4]),.fill_slot(fs[24*k+:24]),.fill_epoch(fe[64*k+:64]),.fill_data(fd[1024*k+:1024]),.fault(sfault[k]));
 end endgenerate
 function automatic [255:0] f(input [29:0] a, input [3:0] bt);
  reg[255:0]r;integer i;begin for(i=0;i<8;i=i+1)r[32*i+:32]=32'h9e3779b9*(a+bt+1)+i*32'h85ebca6b^{a[13:0],bt,i[3:0],10'h2a5};f=r;end
 endfunction
 function automatic [29:0] vaddr(input integer pc,input [5:0] slot,input [14:0] row,input [3:0] col);
  reg[3:0]j;reg[4:0]c,h;begin j=slot[5:2];c={col,j[3]};h={row[1:0],j[2:0]};vaddr={row,j[2:0],c,5'(pc)^c^h,2'b00};end
 endfunction
 integer errors=0;
 // ---------------- 32 controller models
 localparam integer QD=32;
 reg[29:0]qa[0:31][0:QD-1];reg[16:0]qt[0:31][0:QD-1];reg[3:0]ql[0:31][0:QD-1];reg[3:0]qs[0:31][0:QD-1];reg qv[0:31][0:QD-1];integer pick[0:31];
 always @(posedge hc) if(hr) begin : ctlm
  integer p,i,kk,n;reg[29:0]a;reg[3:0]ln;
  for(p=0;p<32;p=p+1)begin
   if(ckr_v[p]&&ckr_rdy[p])begin kk=pick[p];qs[p][kk]=qs[p][kk]|(4'b1<<ckr_beat[4*p+:4]);if(qs[p][kk]==((4'b1<<ql[p][kk])-1))qv[p][kk]=0;ckr_v[p]<=0;end
   if(ck_v[p]&&ck_rdy[p])begin
    a=ck_addr[30*p+:30];ln=ck_len[4*p+:4];
    if(ln<1||ln>4||{1'b0,a[1:0]}+ln>4||(a[6:2]^a[11:7]^a[16:12])!=5'(p)||ck_we[p])begin errors=errors+1;if(errors<10)$display("ILLEGAL K pc %0d %h",p,a);end
    n=-1;for(i=0;i<QD;i=i+1)if(!qv[p][i]&&n<0)n=i;
    qv[p][n]=1;qa[p][n]=a;qt[p][n]=ck_tag[17*p+:17];ql[p][n]=ln;qs[p][n]=0;
   end
   n=0;for(i=0;i<QD;i=i+1)if(qv[p][i])n=n+1;
   ck_rdy[p]<=($urandom%4)!=0&&n<16;
   if(!(ckr_v[p]&&!ckr_rdy[p])&&($urandom%3)!=0&&n>0)begin
    kk=$urandom%QD;while(!qv[p][kk])kk=(kk+1)%QD;
    i=$urandom%ql[p][kk];while(qs[p][kk][i])i=(i+1)%ql[p][kk];
    pick[p]=kk;ckr_v[p]<=1;ckr_tag[17*p+:17]<=qt[p][kk];ckr_beat[4*p+:4]<=i;ckr_data[256*p+:256]<=f(qa[p][kk],i);
   end
  end
 end
 // ---------------- SM group models: random reads (tickets), all beats must return with the right data
 integer gi[0:31],gdone[0:31];reg[29:0]ga[0:31][0:63];reg[3:0]gl[0:31][0:63];reg[3:0]gs[0:31][0:63];reg[16:0]gt[0:31][0:63];
 localparam integer GN=60;
 always @(posedge hc) if(hr) begin : grpm
  integer p,i,n;reg[3:0]ln;reg[29:0]a;reg[4:0]lo;
  for(p=0;p<32;p=p+1)begin
   if(gk_v[p]&&gk_rdy[p])begin gi[p]=gi[p]+1;gk_v[p]<=0;end
   if(!(gk_v[p]&&!gk_rdy[p])&&gi[p]<GN&&($urandom%6)==0)begin
    ln=1+$urandom%4;lo=$urandom%(5-ln);a={$urandom}%30'h3fff0000;a[1:0]=lo[1:0];a[6:2]=5'(p)^a[11:7]^a[16:12];
    ga[p][gi[p]]=a;gl[p][gi[p]]=ln;gs[p][gi[p]]=0;gt[p][gi[p]]=17'(gi[p]&7);
    gk_v[p]<=1;gk_addr[30*p+:30]<=a;gk_len[4*p+:4]<=ln;gk_tag[17*p+:17]<=17'(gi[p]&7);
   end
   gkr_rdy[p]<=($urandom%4)!=0;
   if(gkr_v[p]&&gkr_rdy[p])begin
    n=-1;for(i=0;i<gi[p];i=i+1)if(n<0&&gt[p][i]==gkr_tag[17*p+:17]&&!gs[p][i][gkr_beat[4*p+:4]]&&gkr_beat[4*p+:4]<gl[p][i]&&gkr_data[256*p+:256]==f(ga[p][i],gkr_beat[4*p+:4]))n=i;
    if(n<0)begin errors=errors+1;if(errors<10)$display("GROUP pc %0d bad beat",p);end
    else begin gs[p][n]=gs[p][n]|(4'b1<<gkr_beat[4*p+:4]);if(gs[p][n]==((4'b1<<gl[p][n])-1))gdone[p]=gdone[p]+1;end
   end
  end
 end
 // ---------------- programme
 localparam integer START0=600, START1=900;
 reg[14:0]row[0:1];reg[3:0]col[0:1];reg[15:0]ep[0:1],base[0:1];
 task automatic word(input integer a,input [W-1:0] pl);begin
  @(negedge sc);cfg_we=1;cfg_addr=a;cfg_data=0;cfg_data[255:240]=16'hc7a1;cfg_data[233:224]=a;cfg_data[W-1:0]=pl;
  @(negedge sc);cfg_we=0;end endtask
 function automatic [W-1:0] wbegin_win(input bk,input [15:0] e,input [14:0] r,input [3:0] c);
  reg[W-1:0]x;begin x=0;x[0]=1;x[1]=bk;x[17:2]=e;x[52]=1;x[53]=bk;x[69:54]=e;x[84:70]=r;x[88:85]=c;wbegin_win=x;end endfunction
 function automatic [W-1:0] wstart(input bk,input [15:0] e,input [15:0] s);
  reg[W-1:0]x;begin x=0;x[18]=1;x[19]=bk;x[35:20]=e;x[51:36]=s;wstart=x;end endfunction
 // ---------------- dq checker
 reg[2047:0]seenq[0:1];integer dqn[0:1];
 always @(posedge sc) if(sr) begin : dqm
  integer bb,blk,off,pc,slot;reg[15:0]s;
  for(bb=0;bb<8;bb=bb+1)if(dq[bb*281+280])begin
   s=dq[bb*281+264+:16];blk=-1;
   if(s>=base[0]&&s<base[0]+2048)blk=0;else if(s>=base[1]&&s<base[1]+2048)blk=1;
   if(blk<0)begin errors=errors+1;if(errors<10)$display("dq sector %h outside both blocks",s);end
   else begin
    off=s-base[blk];pc=off%32;slot=off/32;
    if(s[2:0]!=bb||seenq[blk][off]||dq[bb*281+:8]!==8'hff||dq[bb*281+8+:256]!==f(vaddr(pc,slot,row[blk],col[blk]),slot%4))begin
     errors=errors+1;if(errors<10)$display("dq bank %0d sector %h bad (dup %b)",bb,s,seenq[blk][off]);end
    seenq[blk][off]=1;dqn[blk]=dqn[blk]+1;
   end
  end
 end
 integer i,t,p;
 initial begin
  row[0]=15'h1234;col[0]=4'h5;ep[0]=16'h0a01;base[0]=16'h0000;row[1]=15'h2ef1;col[1]=4'hc;ep[1]=16'h0b07;base[1]=16'h0800;
  seenq[0]=0;seenq[1]=0;dqn[0]=0;dqn[1]=0;ck_rdy=0;ckr_v=0;ckr_tag=0;ckr_beat=0;ckr_data=0;gk_v=0;gk_addr=0;gk_len=0;gk_tag=0;gkr_rdy=0;
  for(p=0;p<32;p=p+1)begin gi[p]=0;gdone[p]=0;pick[p]=0;for(i=0;i<QD;i=i+1)qv[p][i]=0;end
  #5;sr=1;hr=1;repeat(10)@(negedge sc);
  for(i=0;i<1024;i=i+1)if(i==0)word(i,wbegin_win(0,ep[0],row[0],col[0]));
   else if(i==1)word(i,wbegin_win(1,ep[1],row[1],col[1]));
   else if(i==(MUT==1?30:START0))word(i,wstart(0,ep[0],base[0]));
   else if(i==START1)word(i,wstart(1,ep[1],base[1]));
   else if(i<1200)word(i,0);
  @(negedge sc);st_v=1;st_base=0;st_limit=11'd1024;st_loops=1;@(negedge sc);st_v=0;
  t=0;while(!cal_done&&t<5000)begin @(posedge sc);t=t+1;end
  repeat(400)@(posedge sc);
  t=0;for(p=0;p<32;p=p+1)t=t+gdone[p];
  if(dqn[0]!=2048||dqn[1]!=2048)begin errors=errors+1;$display("dq words %0d / %0d of 2048",dqn[0],dqn[1]);end
  if(cal_fault||(|sfault)||(|lfault))begin errors=errors+1;$display("fault cal %b share %b lane %b",cal_fault,sfault,lfault);end
  if(t!=32*GN)begin errors=errors+1;$display("group reads done %0d of %0d",t,32*GN);end
  $display("%s tb_hbm_vm_hbm_path_q MUT=%0d dq_words=%0d+%0d group_reads=%0d errors=%0d",errors==0?"PASS":"FAIL",MUT,dqn[0],dqn[1],t,errors);
  $finish;
 end
endmodule
`default_nettype wire
