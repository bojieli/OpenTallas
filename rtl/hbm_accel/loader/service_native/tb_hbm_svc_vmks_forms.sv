`timescale 1ns/1ps
`default_nettype none
// HBM-CONS-2/KSH: proof benches of the kshare forms against the master RTL ot_hbm_svc_vm_kshare_splitstrap.
// One environment (controller + group + WB source + command calendar) drives the master and the form.
// CHECK=0 LOCK-STEP (one tile, stream_clk = hbm_clk): master inputs drive both; the master gets wbw_* one edge later (WCNT_STAGE PIN CYCLE).
//   Every output must match every edge; fill_* of the form must equal the master's +1 edge (FILL_STAGE PIN CYCLE).
// CHECK=1 TRACE (two tiles): each DUT has its own env with the same seeds for content; handshake stall patterns are env-owned and equal,
//   the seam shifts window starts by 2 edges so cycles differ.  Sequences per lane and class must match: group requests at K, VM requests,
//   WB writes, group response beats, group wr_done count, WB wr_done count, fills.
// Exit: PASS line, or $fatal.  Plusargs +WINDOWS +SEED +HBM_HALF +STR_HALF.
module vmks_env #(parameter integer SM=2)(
 input wire hbm_clk,stream_clk,output reg hbm_rst_n,stream_rst_n,
 output reg[3:0]g_k_v,input wire[3:0]g_k_rdy,output reg[119:0]g_k_addr,output reg[15:0]g_k_len,output reg[67:0]g_k_tag,output reg[3:0]g_k_we,output reg[1023:0]g_k_wdata,output reg[127:0]g_k_wstrb,
 input wire[3:0]g_k_wr_done,input wire[3:0]g_kr_v,output reg[3:0]g_kr_rdy,input wire[67:0]g_kr_tag,input wire[15:0]g_kr_beat,input wire[1023:0]g_kr_data,
 input wire[3:0]c_k_v,output reg[3:0]c_k_rdy,input wire[119:0]c_k_addr,input wire[15:0]c_k_len,input wire[67:0]c_k_tag,input wire[3:0]c_k_we,input wire[1023:0]c_k_wdata,input wire[127:0]c_k_wstrb,
 output reg[3:0]c_k_wr_done,output reg[3:0]c_kr_v,input wire[3:0]c_kr_rdy,output reg[67:0]c_kr_tag,output reg[15:0]c_kr_beat,output reg[1023:0]c_kr_data,
 output reg vm_v,vm_bank,output reg[15:0]vm_epoch,output reg[14:0]vm_row,output reg[3:0]vm_col,
 output reg wbw_v,output reg[29:0]wbw_base,output reg[11:0]wbw_total,
 output reg[3:0]w_k_v,input wire[3:0]w_k_rdy,output reg[119:0]w_k_addr,output reg[1023:0]w_k_wdata,input wire[3:0]w_k_wr_done,
 input wire[3:0]fill_v,fill_bank,input wire[23:0]fill_slot,input wire[63:0]fill_epoch,input wire[1023:0]fill_data,input wire fault,
 output reg done,output integer errors
);
 integer WINDOWS=12,SEED=1,wbonly=0,badtag=0,waitt=24,farslow=0;
 function automatic [255:0] f(input [29:0] a,input [3:0] b);
  reg[255:0]r;integer i;begin for(i=0;i<8;i=i+1)r[32*i+:32]=32'h9e3779b9*(a+b+1)+i*32'h85ebca6b^{a[13:0],b,i[3:0],10'h2a5};f=r;end
 endfunction
 // xorshift per stream so content does not depend on handshake timing
 function automatic [31:0] xs(input [31:0] x);reg[31:0]y;begin y=x^(x<<13);y=y^(y>>17);y=y^(y<<5);xs=y;end endfunction
 reg[31:0]rc[0:3],rg[0:3],rr[0:3];
 // controller: FIFO per lane of read beats pending, delayed write done
 localparam integer QD=512;
 reg[29:0]qa[0:3][0:QD-1];reg[16:0]qt[0:3][0:QD-1];reg[3:0]qb[0:3][0:QD-1];integer qh[0:3],qn[0:3];integer wdq[0:3];integer rdy_hold[0:3];reg[3:0]rdy_seen;
 integer gdone_rd[0:3];
 integer gsent[0:3],gn;
 integer wdc[0:3],tg1[0:3],tg2[0:3]; // WBONLY=3: cumulative write-done counts per lane; the env keeps the 4-entry window FIFO from overflowing (a schedule rule, the master faults on overflow)
 integer wleft[0:3];reg[29:0]wnext[0:3];reg[29:0]wend[0:3];integer wstart;
 integer l,i;
 task automatic bad(input string s);begin errors=errors+1;if(errors<12)$display("ENV %m: %s t=%0t",s,$time);if(errors>=4)begin $display("FAIL env errors");$finish;end end endtask
 always @(posedge hbm_clk)rdy_seen<=hbm_rst_n?c_kr_rdy:4'b0;
 always @(posedge hbm_clk) if(hbm_rst_n)begin:ctl
  integer l,b;reg[29:0]a;reg[3:0]ln;
  for(l=0;l<4;l=l+1)begin
   rc[l]=xs(rc[l]);
   c_k_wr_done[l]<=0;
   if(c_kr_v[l]&&rdy_seen[l])begin
    qh[l]=(qh[l]+1)%QD;qn[l]=qn[l]-1;c_kr_v[l]<=0;
   end
   if(c_k_v[l]&&c_k_rdy[l])begin
    a=c_k_addr[30*l+:30];ln=c_k_len[4*l+:4];
    if((a[6:2]^a[11:7]^a[16:12])!=5'(4*SM+l))bad("K pc hash");
    if(c_k_we[l])wdq[l]=wdq[l]+1;
    else for(b=0;b<ln;b=b+1)begin
     qa[l][(qh[l]+qn[l])%QD]=a;qt[l][(qh[l]+qn[l])%QD]=(badtag!=0&&l==3&&c_k_tag[17*l+13+:4]==0)?(c_k_tag[17*l+:17]^17'h100):c_k_tag[17*l+:17];qb[l][(qh[l]+qn[l])%QD]=b;qn[l]=qn[l]+1;
    end
   end
   if(wdq[l]>0&&((farslow!=0&&l>=2)?(rc[l][5:0]==0):(rc[l][3:0]<5)))begin c_k_wr_done[l]<=1;wdq[l]=wdq[l]-1;end
   c_k_rdy[l]<=rc[l][5:4]!=0&&qn[l]<64&&wdq[l]<16;
   if(!(c_kr_v[l]&&!rdy_seen[l])&&qn[l]>0&&rc[l][7:6]!=0)begin
    c_kr_v[l]<=1;c_kr_tag[17*l+:17]<=qt[l][qh[l]];c_kr_beat[4*l+:4]<=qb[l][qh[l]];c_kr_data[256*l+:256]<=f(qa[l][qh[l]],qb[l][qh[l]]);
   end
  end
 end
 // group: reads and writes, tag top bits 0111 mark them for the trace checker
 always @(posedge hbm_clk) if(hbm_rst_n)begin:grp
  integer l;reg[29:0]a;reg[3:0]ln;reg[1:0]lo;reg we;integer tg;
  for(l=0;l<4;l=l+1)begin
   if(g_k_v[l]&&g_k_rdy[l])begin g_k_v[l]<=0;gsent[l]=gsent[l]+1;end
   if(!(g_k_v[l]&&!g_k_rdy[l])&&gsent[l]<gn)begin
    rg[l]=xs(rg[l]);
    if(rg[l][1:0]==0)begin
     we=rg[l][2]&&rg[l][3];
     ln=we?4'd1:(4'd1+4'(rg[l][5:4]));lo=2'(rg[l][7:6]%(5-ln));
     a={rg[l][31:16],7'b0,rg[l][14:8]};a[1:0]=lo;a[6:2]=5'(4*SM+l)^a[11:7]^a[16:12];
     g_k_v[l]<=1;g_k_we[l]<=we;g_k_addr[30*l+:30]<=a;g_k_len[4*l+:4]<=ln;tg=gsent[l]&1023;g_k_tag[17*l+:17]<={4'b0111,3'b0,10'(tg)};
     g_k_wstrb[32*l+:32]<=rg[l];g_k_wdata[256*l+:256]<=f(a,4'd9);
    end
   end
   rr[l]=xs(rr[l]);g_kr_rdy[l]<=(rr[l][9:8]!=0);
  end
 end
 // WB source
 always @(posedge hbm_clk) if(hbm_rst_n)begin:wbs
  integer l;reg[29:0]s;
  for(l=0;l<4;l=l+1)begin
   if(w_k_v[l]&&w_k_rdy[l])begin w_k_v[l]<=0;wleft[l]=wleft[l]-1;end
   if(w_k_wr_done[l])wdc[l]=wdc[l]+1;
   if(!(w_k_v[l]&&!w_k_rdy[l])&&wleft[l]>0)begin
    s=wnext[l];
    while(s<wend[l]&&(s[6:2]^s[11:7]^s[16:12])!=5'(4*SM+l))s=s+1;
    if(s<wend[l])begin w_k_v[l]<=1;w_k_addr[30*l+:30]<=s;w_k_wdata[256*l+:256]<=f(s,4'd3);wnext[l]=s+1;end
   end
  end
 end
 integer w,t,gap;reg[31:0]rw;
 function automatic integer cnt_lane(input integer ll,input [29:0] b,input integer tot);
  integer n,k;reg[29:0]s;begin n=0;for(k=0;k<tot;k=k+1)begin s=b+k;if((s[6:2]^s[11:7]^s[16:12])==5'(4*SM+ll))n=n+1;end cnt_lane=n;end
 endfunction
 initial begin
  errors=0;done=0;
  if($value$plusargs("WINDOWS=%d",WINDOWS));if($value$plusargs("SEED=%d",SEED));if($value$plusargs("WBONLY=%d",wbonly));if($value$plusargs("BADTAG=%d",badtag));if($value$plusargs("WAITT=%d",waitt));if($value$plusargs("FARSLOW=%d",farslow));
  gn=2000;if($value$plusargs("GN=%d",gn));
  hbm_rst_n=0;stream_rst_n=0;g_k_v=0;g_kr_rdy=0;c_k_rdy=0;c_k_wr_done=0;c_kr_v=0;vm_v=0;vm_bank=0;vm_epoch=0;vm_row=0;vm_col=0;wbw_v=0;wbw_base=0;wbw_total=0;w_k_v=0;
  g_k_addr=0;g_k_len=0;g_k_tag=0;g_k_we=0;g_k_wdata=0;g_k_wstrb=0;c_kr_tag=0;c_kr_beat=0;c_kr_data=0;w_k_addr=0;w_k_wdata=0;rdy_seen=0;
  for(l=0;l<4;l=l+1)begin rc[l]=32'h1234567+SEED*77+l;rg[l]=32'h7654321+SEED*131+l*3;rr[l]=32'h5a5a123+SEED*7+l*11;qh[l]=0;qn[l]=0;wdq[l]=0;gsent[l]=0;wleft[l]=0;wnext[l]=0;wend[l]=0;wdc[l]=0;tg1[l]=0;tg2[l]=0;end
  rw=32'hABCDEF1+SEED;
  #(30ns);hbm_rst_n=1;stream_rst_n=1;
  for(w=0;w<WINDOWS;w=w+1)begin
   rw=xs(rw);gap=(wbonly==3)?1:wbonly?8+rw[4:0]:60+rw[7:0];
   repeat(gap)@(posedge stream_clk);
   @(negedge stream_clk);
   if(rw[8]&&!wbonly)begin
    // VM window: epoch top bits 0 so tag top nibble is 0000 (trace class)
    vm_v=1;vm_bank=0;vm_epoch={4'b0,w[3:0],rw[15:8]};vm_epoch[11:9]=0;vm_row=15'(rw[30:16]);vm_col=4'(rw[12:9]);
    @(negedge stream_clk);vm_v=0;
   end else begin
    reg[29:0]b;integer tot;
    b={rw[29:12],12'(rw[11:0])};tot=((rw[9]||farslow!=0)?1+rw[7:0]:1+rw[10:0]);
    if(wbonly==3)begin while(wdc[0]<tg2[0]||wdc[1]<tg2[1]||wdc[2]<tg2[2]||wdc[3]<tg2[3])@(posedge stream_clk);@(negedge stream_clk);end
    for(l=0;l<4;l=l+1)begin wleft[l]=cnt_lane(l,b,tot);wnext[l]=b;wend[l]=b+tot;tg2[l]=tg1[l];tg1[l]=tg1[l]+wleft[l];end
    // WBONLY=2,3 (3 = no gap, next window comes as soon as the source has pushed): an empty window just ahead, queued so the next take comes right after the lanes return to NORM (the seam norm guard)
    if(wbonly==2)begin
     reg[29:0]za;za=b^30'h15555;
     while(cnt_lane(0,za,4)!=0||cnt_lane(1,za,4)!=0||cnt_lane(2,za,4)!=0||cnt_lane(3,za,4)!=0)za=za+30'd37;
     wbw_v=1;wbw_base=za;wbw_total=12'd4;@(negedge stream_clk);wbw_v=0;
    end
    wbw_v=1;wbw_base=b;wbw_total=12'(tot);
    @(negedge stream_clk);wbw_v=0;
   end
   // wait for this window to finish on every lane by counting the env's own queues: fixed long gap covers VM (64 beats)/WB (<=68)
   t=0;while(t<30000&&!(wleft[0]==0&&wleft[1]==0&&wleft[2]==0&&wleft[3]==0&&t>((wbonly==3)?waitt:wbonly?40:1200)))begin @(posedge stream_clk);t=t+1;end
   if(t>=30000)bad("window timeout");
  end
  t=0;
  while(t<400000&&!(gsent[0]>=gn&&gsent[1]>=gn&&gsent[2]>=gn&&gsent[3]>=gn))begin @(posedge hbm_clk);t=t+1;end
  if(t>=400000)bad("group traffic timeout");
  repeat(600)@(posedge hbm_clk);
  if(fault!=(badtag!=0))bad("fault wrong");
  done=1;
 end
endmodule

// two tiles + bench seam (kit face shells: +1 out, +1 in).  MUT 13 cmd bit, 14 count bit, 15 norm stuck high, 16 far fault lost.  cmd/wn/base/end are held for the whole window, so their arrival edge is not critical
module vmks_comp #(parameter integer MUT=0)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,input wire[2:0]sm_stream,sm_hbm,
 input wire[3:0]g_k_v,output wire[3:0]g_k_rdy,input wire[119:0]g_k_addr,input wire[15:0]g_k_len,input wire[67:0]g_k_tag,
 input wire[3:0]g_k_we,input wire[1023:0]g_k_wdata,input wire[127:0]g_k_wstrb,output wire[3:0]g_k_wr_done,
 output wire[3:0]g_kr_v,input wire[3:0]g_kr_rdy,output wire[67:0]g_kr_tag,output wire[15:0]g_kr_beat,output wire[1023:0]g_kr_data,
 output wire[3:0]c_k_v,input wire[3:0]c_k_rdy,output wire[119:0]c_k_addr,output wire[15:0]c_k_len,output wire[67:0]c_k_tag,
 output wire[3:0]c_k_we,output wire[1023:0]c_k_wdata,output wire[127:0]c_k_wstrb,input wire[3:0]c_k_wr_done,
 input wire[3:0]c_kr_v,output wire[3:0]c_kr_rdy,input wire[67:0]c_kr_tag,input wire[15:0]c_kr_beat,input wire[1023:0]c_kr_data,
 input wire vm_v,vm_bank,input wire[15:0]vm_epoch,input wire[14:0]vm_row,input wire[3:0]vm_col,
 input wire wbw_v,input wire[29:0]wbw_base,input wire[11:0]wbw_total,
 input wire[3:0]w_k_v,output wire[3:0]w_k_rdy,input wire[119:0]w_k_addr,input wire[1023:0]w_k_wdata,output wire[3:0]w_k_wr_done,
 output wire[3:0]fill_v,output wire[3:0]fill_bank,output wire[23:0]fill_slot,output wire[63:0]fill_epoch,output wire[1023:0]fill_data,output wire fault
);
 wire tc,tw;wire[35:0]cm;wire[15:0]wn;wire[29:0]wb;wire[30:0]we;wire[1:0]nm;wire sf;
 reg[1:0]tc_r,tw_r;reg[35:0]cm_r[0:2];reg[15:0]wn_r[0:1];reg[29:0]wb_r[0:1];reg[30:0]we_r[0:1];reg[1:0]nm_r[0:1];reg[1:0]sf_r;
 always @(posedge hbm_clk)begin
  tc_r<={tc_r[0],tc};tw_r<={tw_r[0],tw};cm_r[0]<=cm;cm_r[1]<=cm_r[0];cm_r[2]<=cm_r[1];wn_r[0]<=wn;wn_r[1]<=wn_r[0];wb_r[0]<=wb;wb_r[1]<=wb_r[0];we_r[0]<=we;we_r[1]<=we_r[0];
  nm_r[0]<=nm;nm_r[1]<=nm_r[0];sf_r<={sf_r[0],sf};
 end
 ot_hbm_svc_vmks_t0 #(.MUT(MUT)) u_t0(.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.sm_stream(sm_stream),.sm_hbm(sm_hbm),
  .g_k_v(g_k_v[1:0]),.g_k_rdy(g_k_rdy[1:0]),.g_k_addr(g_k_addr[59:0]),.g_k_len(g_k_len[7:0]),.g_k_tag(g_k_tag[33:0]),.g_k_we(g_k_we[1:0]),.g_k_wdata(g_k_wdata[511:0]),.g_k_wstrb(g_k_wstrb[63:0]),.g_k_wr_done(g_k_wr_done[1:0]),
  .g_kr_v(g_kr_v[1:0]),.g_kr_rdy(g_kr_rdy[1:0]),.g_kr_tag(g_kr_tag[33:0]),.g_kr_beat(g_kr_beat[7:0]),.g_kr_data(g_kr_data[511:0]),
  .c_k_v(c_k_v[1:0]),.c_k_rdy(c_k_rdy[1:0]),.c_k_addr(c_k_addr[59:0]),.c_k_len(c_k_len[7:0]),.c_k_tag(c_k_tag[33:0]),.c_k_we(c_k_we[1:0]),.c_k_wdata(c_k_wdata[511:0]),.c_k_wstrb(c_k_wstrb[63:0]),.c_k_wr_done(c_k_wr_done[1:0]),
  .c_kr_v(c_kr_v[1:0]),.c_kr_rdy(c_kr_rdy[1:0]),.c_kr_tag(c_kr_tag[33:0]),.c_kr_beat(c_kr_beat[7:0]),.c_kr_data(c_kr_data[511:0]),
  .vm_v(vm_v),.vm_bank(vm_bank),.vm_epoch(vm_epoch),.vm_row(vm_row),.vm_col(vm_col),.wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),
  .w_k_v(w_k_v[1:0]),.w_k_rdy(w_k_rdy[1:0]),.w_k_addr(w_k_addr[59:0]),.w_k_wdata(w_k_wdata[511:0]),.w_k_wr_done(w_k_wr_done[1:0]),
  .fill_v(fill_v[1:0]),.fill_bank(fill_bank[1:0]),.fill_slot(fill_slot[11:0]),.fill_epoch(fill_epoch[31:0]),.fill_data(fill_data[511:0]),.fault(fault),
  .s_take_cmd(tc),.s_take_wb(tw),.s_cmd(cm),.s_wn(wn),.s_wbase(wb),.s_wend(we),.s_norm(MUT==15?2'b11:nm_r[1]),.s_fault(MUT==16?1'b0:sf_r[1]));
 ot_hbm_svc_vmks_t1 #(.MUT(MUT)) u_t1(.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.sm_hbm(sm_hbm),
  .g_k_v(g_k_v[3:2]),.g_k_rdy(g_k_rdy[3:2]),.g_k_addr(g_k_addr[119:60]),.g_k_len(g_k_len[15:8]),.g_k_tag(g_k_tag[67:34]),.g_k_we(g_k_we[3:2]),.g_k_wdata(g_k_wdata[1023:512]),.g_k_wstrb(g_k_wstrb[127:64]),.g_k_wr_done(g_k_wr_done[3:2]),
  .g_kr_v(g_kr_v[3:2]),.g_kr_rdy(g_kr_rdy[3:2]),.g_kr_tag(g_kr_tag[67:34]),.g_kr_beat(g_kr_beat[15:8]),.g_kr_data(g_kr_data[1023:512]),
  .c_k_v(c_k_v[3:2]),.c_k_rdy(c_k_rdy[3:2]),.c_k_addr(c_k_addr[119:60]),.c_k_len(c_k_len[15:8]),.c_k_tag(c_k_tag[67:34]),.c_k_we(c_k_we[3:2]),.c_k_wdata(c_k_wdata[1023:512]),.c_k_wstrb(c_k_wstrb[127:64]),.c_k_wr_done(c_k_wr_done[3:2]),
  .c_kr_v(c_kr_v[3:2]),.c_kr_rdy(c_kr_rdy[3:2]),.c_kr_tag(c_kr_tag[67:34]),.c_kr_beat(c_kr_beat[15:8]),.c_kr_data(c_kr_data[1023:512]),
  .w_k_v(w_k_v[3:2]),.w_k_rdy(w_k_rdy[3:2]),.w_k_addr(w_k_addr[119:60]),.w_k_wdata(w_k_wdata[1023:512]),.w_k_wr_done(w_k_wr_done[3:2]),
  .fill_v(fill_v[3:2]),.fill_bank(fill_bank[3:2]),.fill_slot(fill_slot[23:12]),.fill_epoch(fill_epoch[63:32]),.fill_data(fill_data[1023:512]),
  .s_take_cmd(tc_r[1]),.s_take_wb(tw_r[1]),.s_cmd(MUT==13?(cm_r[1]^36'h8):cm_r[1]),.s_wn(MUT==14?(wn_r[1]^16'h1):wn_r[1]),.s_wbase(wb_r[1]),.s_wend(we_r[1]),.s_norm(nm),.s_fault(sf));
endmodule

`define VMKS_PORTS(P) .hbm_clk(hbm_clk),.stream_clk(stream_clk),.hbm_rst_n(P``hbm_rst_n),.stream_rst_n(P``stream_rst_n),\
 .g_k_v(P``g_k_v),.g_k_rdy(P``g_k_rdy),.g_k_addr(P``g_k_addr),.g_k_len(P``g_k_len),.g_k_tag(P``g_k_tag),.g_k_we(P``g_k_we),.g_k_wdata(P``g_k_wdata),.g_k_wstrb(P``g_k_wstrb),.g_k_wr_done(P``g_k_wr_done),\
 .g_kr_v(P``g_kr_v),.g_kr_rdy(P``g_kr_rdy),.g_kr_tag(P``g_kr_tag),.g_kr_beat(P``g_kr_beat),.g_kr_data(P``g_kr_data),\
 .c_k_v(P``c_k_v),.c_k_rdy(P``c_k_rdy),.c_k_addr(P``c_k_addr),.c_k_len(P``c_k_len),.c_k_tag(P``c_k_tag),.c_k_we(P``c_k_we),.c_k_wdata(P``c_k_wdata),.c_k_wstrb(P``c_k_wstrb),.c_k_wr_done(P``c_k_wr_done),\
 .c_kr_v(P``c_kr_v),.c_kr_rdy(P``c_kr_rdy),.c_kr_tag(P``c_kr_tag),.c_kr_beat(P``c_kr_beat),.c_kr_data(P``c_kr_data),\
 .vm_v(P``vm_v),.vm_bank(P``vm_bank),.vm_epoch(P``vm_epoch),.vm_row(P``vm_row),.vm_col(P``vm_col),\
 .w_k_v(P``w_k_v),.w_k_rdy(P``w_k_rdy),.w_k_addr(P``w_k_addr),.w_k_wdata(P``w_k_wdata),.w_k_wr_done(P``w_k_wr_done),\
 .fill_v(P``fill_v),.fill_bank(P``fill_bank),.fill_slot(P``fill_slot),.fill_epoch(P``fill_epoch),.fill_data(P``fill_data),.fault(P``fault)

`define VMKS_WIRES(P) wire P``hbm_rst_n,P``stream_rst_n;wire[3:0]P``g_k_v,P``g_k_rdy;wire[119:0]P``g_k_addr;wire[15:0]P``g_k_len;wire[67:0]P``g_k_tag;wire[3:0]P``g_k_we;wire[1023:0]P``g_k_wdata;wire[127:0]P``g_k_wstrb;wire[3:0]P``g_k_wr_done;\
 wire[3:0]P``g_kr_v,P``g_kr_rdy;wire[67:0]P``g_kr_tag;wire[15:0]P``g_kr_beat;wire[1023:0]P``g_kr_data;\
 wire[3:0]P``c_k_v,P``c_k_rdy;wire[119:0]P``c_k_addr;wire[15:0]P``c_k_len;wire[67:0]P``c_k_tag;wire[3:0]P``c_k_we;wire[1023:0]P``c_k_wdata;wire[127:0]P``c_k_wstrb;wire[3:0]P``c_k_wr_done;\
 wire[3:0]P``c_kr_v,P``c_kr_rdy;wire[67:0]P``c_kr_tag;wire[15:0]P``c_kr_beat;wire[1023:0]P``c_kr_data;\
 wire P``vm_v,P``vm_bank;wire[15:0]P``vm_epoch;wire[14:0]P``vm_row;wire[3:0]P``vm_col;wire P``wbw_v;wire[29:0]P``wbw_base;wire[11:0]P``wbw_total;\
 wire[3:0]P``w_k_v,P``w_k_rdy;wire[119:0]P``w_k_addr;wire[1023:0]P``w_k_wdata;wire[3:0]P``w_k_wr_done;\
 wire[3:0]P``fill_v,P``fill_bank;wire[23:0]P``fill_slot;wire[63:0]P``fill_epoch;wire[1023:0]P``fill_data;wire P``fault

module tb_hbm_svc_vmks_forms;
 parameter integer CHECK=0,SM=2,MUT=0,PTR=1,FILLS=1,WCNT=1;
 integer HBM_HALF=416,STR_HALF=416,wbo=0;
 initial if($value$plusargs("WBONLY=%d",wbo));
 reg hbm_clk=0,stream_clk=0;
 initial begin if($value$plusargs("HBM_HALF=%d",HBM_HALF));if($value$plusargs("STR_HALF=%d",STR_HALF));end
 always #(HBM_HALF*1ps)hbm_clk=~hbm_clk;
 generate if(CHECK==0)begin:g_same end endgenerate
 wire str_clk_use;
 // CHECK=0 needs both DUT edges together: stream_clk is the same net
 assign str_clk_use=(CHECK==0)?hbm_clk:stream_clk;
 always #(STR_HALF*1ps)stream_clk=~stream_clk;
 `VMKS_WIRES(a_);`VMKS_WIRES(b_);
 wire adone,bdone;integer aerr,berr;
 vmks_env #(.SM(SM)) u_ea(.hbm_clk(hbm_clk),.stream_clk(str_clk_use),.hbm_rst_n(a_hbm_rst_n),.stream_rst_n(a_stream_rst_n),
  .g_k_v(a_g_k_v),.g_k_rdy(a_g_k_rdy),.g_k_addr(a_g_k_addr),.g_k_len(a_g_k_len),.g_k_tag(a_g_k_tag),.g_k_we(a_g_k_we),.g_k_wdata(a_g_k_wdata),.g_k_wstrb(a_g_k_wstrb),.g_k_wr_done(a_g_k_wr_done),
  .g_kr_v(a_g_kr_v),.g_kr_rdy(a_g_kr_rdy),.g_kr_tag(a_g_kr_tag),.g_kr_beat(a_g_kr_beat),.g_kr_data(a_g_kr_data),
  .c_k_v(a_c_k_v),.c_k_rdy(a_c_k_rdy),.c_k_addr(a_c_k_addr),.c_k_len(a_c_k_len),.c_k_tag(a_c_k_tag),.c_k_we(a_c_k_we),.c_k_wdata(a_c_k_wdata),.c_k_wstrb(a_c_k_wstrb),.c_k_wr_done(a_c_k_wr_done),
  .c_kr_v(a_c_kr_v),.c_kr_rdy(a_c_kr_rdy),.c_kr_tag(a_c_kr_tag),.c_kr_beat(a_c_kr_beat),.c_kr_data(a_c_kr_data),
  .vm_v(a_vm_v),.vm_bank(a_vm_bank),.vm_epoch(a_vm_epoch),.vm_row(a_vm_row),.vm_col(a_vm_col),.wbw_v(a_wbw_v),.wbw_base(a_wbw_base),.wbw_total(a_wbw_total),
  .w_k_v(a_w_k_v),.w_k_rdy(a_w_k_rdy),.w_k_addr(a_w_k_addr),.w_k_wdata(a_w_k_wdata),.w_k_wr_done(a_w_k_wr_done),
  .fill_v(a_fill_v),.fill_bank(a_fill_bank),.fill_slot(a_fill_slot),.fill_epoch(a_fill_epoch),.fill_data(a_fill_data),.fault(a_fault),.done(adone),.errors(aerr));
 // gold: master RTL (in CHECK=0 its wbw_* come one edge later, WCNT_STAGE)
 reg gw_v;reg[29:0]gw_b;reg[11:0]gw_t;
 always @(posedge hbm_clk)begin gw_v<=a_wbw_v;gw_b<=a_wbw_base;gw_t<=a_wbw_total;end
 ot_hbm_svc_vm_kshare_splitstrap #(.KRL1(1)) u_gold(`VMKS_PORTS(a_),.sm_stream(3'(SM)),.sm_hbm(3'(SM)),
  .wbw_v((CHECK==0&&WCNT!=0)?gw_v:a_wbw_v),.wbw_base((CHECK==0&&WCNT!=0)?gw_b:a_wbw_base),.wbw_total((CHECK==0&&WCNT!=0)?gw_t:a_wbw_total));
 generate if(CHECK==0)begin:g_lock
  // form sees the env's inputs; own outputs only compared
  wire[3:0]d_g_k_rdy,d_g_k_wr_done,d_g_kr_v,d_c_k_v,d_c_k_we,d_c_kr_rdy,d_w_k_rdy,d_w_k_wr_done,d_fill_v,d_fill_bank;
  wire[67:0]d_g_kr_tag,d_c_k_tag;wire[15:0]d_g_kr_beat,d_c_k_len;wire[1023:0]d_g_kr_data,d_c_k_wdata,d_fill_data;wire[119:0]d_c_k_addr;wire[127:0]d_c_k_wstrb;
  wire[23:0]d_fill_slot;wire[63:0]d_fill_epoch;wire d_fault;
  ot_hbm_svc_vm_kshare_splitstrap_f1 #(.MUT(MUT),.PTR_SKID(PTR),.FILL_STAGE(FILLS),.WCNT_STAGE(WCNT)) u_dut(.hbm_clk(hbm_clk),.stream_clk(hbm_clk),.hbm_rst_n(a_hbm_rst_n),.stream_rst_n(a_stream_rst_n),.sm_stream(3'(SM)),.sm_hbm(3'(SM)),
   .g_k_v(a_g_k_v),.g_k_rdy(d_g_k_rdy),.g_k_addr(a_g_k_addr),.g_k_len(a_g_k_len),.g_k_tag(a_g_k_tag),.g_k_we(a_g_k_we),.g_k_wdata(a_g_k_wdata),.g_k_wstrb(a_g_k_wstrb),.g_k_wr_done(d_g_k_wr_done),
   .g_kr_v(d_g_kr_v),.g_kr_rdy(a_g_kr_rdy),.g_kr_tag(d_g_kr_tag),.g_kr_beat(d_g_kr_beat),.g_kr_data(d_g_kr_data),
   .c_k_v(d_c_k_v),.c_k_rdy(a_c_k_rdy),.c_k_addr(d_c_k_addr),.c_k_len(d_c_k_len),.c_k_tag(d_c_k_tag),.c_k_we(d_c_k_we),.c_k_wdata(d_c_k_wdata),.c_k_wstrb(d_c_k_wstrb),.c_k_wr_done(a_c_k_wr_done),
   .c_kr_v(a_c_kr_v),.c_kr_rdy(d_c_kr_rdy),.c_kr_tag(a_c_kr_tag),.c_kr_beat(a_c_kr_beat),.c_kr_data(a_c_kr_data),
   .vm_v(a_vm_v),.vm_bank(a_vm_bank),.vm_epoch(a_vm_epoch),.vm_row(a_vm_row),.vm_col(a_vm_col),.wbw_v(a_wbw_v),.wbw_base(a_wbw_base),.wbw_total(a_wbw_total),
   .w_k_v(a_w_k_v),.w_k_rdy(d_w_k_rdy),.w_k_addr(a_w_k_addr),.w_k_wdata(a_w_k_wdata),.w_k_wr_done(d_w_k_wr_done),
   .fill_v(d_fill_v),.fill_bank(d_fill_bank),.fill_slot(d_fill_slot),.fill_epoch(d_fill_epoch),.fill_data(d_fill_data),.fault(d_fault));
  reg[3:0]gf_v,gf_b;reg[23:0]gf_s;reg[63:0]gf_e;reg[1023:0]gf_d;
  always @(posedge hbm_clk)begin gf_v<=a_fill_v;gf_b<=a_fill_bank;gf_s<=a_fill_slot;gf_e<=a_fill_epoch;gf_d<=a_fill_data;end
  integer mism=0,cyc=0,fills=0,vms=0,wbs=0;integer ll;
  wire [3:0] fv_exp=FILLS?gf_v:a_fill_v;
  always @(negedge hbm_clk) if(a_hbm_rst_n)begin
   cyc=cyc+1;
   if(cyc>30)begin
   if(d_g_k_rdy!==a_g_k_rdy||d_g_k_wr_done!==a_g_k_wr_done||d_g_kr_v!==a_g_kr_v||d_c_k_v!==a_c_k_v||d_c_kr_rdy!==a_c_kr_rdy||d_w_k_rdy!==a_w_k_rdy||d_w_k_wr_done!==a_w_k_wr_done||d_fault!==a_fault||d_fill_v!==fv_exp)begin mism=mism+1;if(mism<8)$display("LOCK ctl mismatch cyc %0d gkrdy %b/%b gkrv %b/%b ckv %b/%b crdy %b/%b wrdy %b/%b wd %b/%b fv %b/%b fault %b/%b",cyc,d_g_k_rdy,a_g_k_rdy,d_g_kr_v,a_g_kr_v,d_c_k_v,a_c_k_v,d_c_kr_rdy,a_c_kr_rdy,d_w_k_rdy,a_w_k_rdy,d_w_k_wr_done,a_w_k_wr_done,d_fill_v,fv_exp,d_fault,a_fault);end
   for(ll=0;ll<4;ll=ll+1)begin
    if(a_c_k_v[ll]&&(d_c_k_addr[30*ll+:30]!==a_c_k_addr[30*ll+:30]||d_c_k_len[4*ll+:4]!==a_c_k_len[4*ll+:4]||d_c_k_tag[17*ll+:17]!==a_c_k_tag[17*ll+:17]||d_c_k_we[ll]!==a_c_k_we[ll]||d_c_k_wdata[256*ll+:256]!==a_c_k_wdata[256*ll+:256]||d_c_k_wstrb[32*ll+:32]!==a_c_k_wstrb[32*ll+:32]))begin mism=mism+1;if(mism<8)$display("LOCK K data mismatch lane %0d cyc %0d",ll,cyc);end
    if(a_g_kr_v[ll]&&(d_g_kr_tag[17*ll+:17]!==a_g_kr_tag[17*ll+:17]||d_g_kr_beat[4*ll+:4]!==a_g_kr_beat[4*ll+:4]||d_g_kr_data[256*ll+:256]!==a_g_kr_data[256*ll+:256]))begin mism=mism+1;if(mism<8)$display("LOCK response data mismatch lane %0d cyc %0d",ll,cyc);end
    if(fv_exp[ll]&&FILLS&&(d_fill_bank[ll]!==gf_b[ll]||d_fill_slot[6*ll+:6]!==gf_s[6*ll+:6]||d_fill_epoch[16*ll+:16]!==gf_e[16*ll+:16]||d_fill_data[256*ll+:256]!==gf_d[256*ll+:256]))begin mism=mism+1;if(mism<8)$display("LOCK fill data mismatch lane %0d cyc %0d",ll,cyc);end
    if(a_c_k_v[ll]&&a_c_k_rdy[ll]&&a_c_k_tag[17*ll+16]==1'b1)wbs=wbs+1;
    if(a_c_k_v[ll]&&a_c_k_rdy[ll]&&a_c_k_tag[17*ll+13+:4]==0)vms=vms+1;
    if(a_fill_v[ll])fills=fills+1;
   end
   end
  end
  always @(posedge adone)begin
   if(wbs==0||(!wbo&&(fills==0||vms==0)))$display("FAIL vacuous fills %0d vm %0d wb %0d",fills,vms,wbs);
   else if(mism==0&&aerr==0)$display("PASS LOCK MUT=%0d PTR=%0d FILL=%0d WCNT=%0d cycles %0d fills %0d vm_reqs %0d wb_writes %0d",MUT,PTR,FILLS,WCNT,cyc,fills,vms,wbs);
   else $display("FAIL LOCK MUT=%0d mismatches %0d env errors %0d",MUT,mism,aerr);
   $finish;
  end
 end else begin:g_trace
  // form with its own environment, own trace; same content seeds, independent timing.
  wire bdone_w;integer berr_w;
  vmks_env #(.SM(SM)) u_eb(.hbm_clk(hbm_clk),.stream_clk(stream_clk),.hbm_rst_n(b_hbm_rst_n),.stream_rst_n(b_stream_rst_n),
  .g_k_v(b_g_k_v),.g_k_rdy(b_g_k_rdy),.g_k_addr(b_g_k_addr),.g_k_len(b_g_k_len),.g_k_tag(b_g_k_tag),.g_k_we(b_g_k_we),.g_k_wdata(b_g_k_wdata),.g_k_wstrb(b_g_k_wstrb),.g_k_wr_done(b_g_k_wr_done),
  .g_kr_v(b_g_kr_v),.g_kr_rdy(b_g_kr_rdy),.g_kr_tag(b_g_kr_tag),.g_kr_beat(b_g_kr_beat),.g_kr_data(b_g_kr_data),
  .c_k_v(b_c_k_v),.c_k_rdy(b_c_k_rdy),.c_k_addr(b_c_k_addr),.c_k_len(b_c_k_len),.c_k_tag(b_c_k_tag),.c_k_we(b_c_k_we),.c_k_wdata(b_c_k_wdata),.c_k_wstrb(b_c_k_wstrb),.c_k_wr_done(b_c_k_wr_done),
  .c_kr_v(b_c_kr_v),.c_kr_rdy(b_c_kr_rdy),.c_kr_tag(b_c_kr_tag),.c_kr_beat(b_c_kr_beat),.c_kr_data(b_c_kr_data),
  .vm_v(b_vm_v),.vm_bank(b_vm_bank),.vm_epoch(b_vm_epoch),.vm_row(b_vm_row),.vm_col(b_vm_col),.wbw_v(b_wbw_v),.wbw_base(b_wbw_base),.wbw_total(b_wbw_total),
  .w_k_v(b_w_k_v),.w_k_rdy(b_w_k_rdy),.w_k_addr(b_w_k_addr),.w_k_wdata(b_w_k_wdata),.w_k_wr_done(b_w_k_wr_done),
  .fill_v(b_fill_v),.fill_bank(b_fill_bank),.fill_slot(b_fill_slot),.fill_epoch(b_fill_epoch),.fill_data(b_fill_data),.fault(b_fault),.done(bdone_w),.errors(berr_w));
  vmks_comp #(.MUT(MUT)) u_dut(`VMKS_PORTS(b_),.sm_stream(3'(SM)),.sm_hbm(3'(SM)),.wbw_v(b_wbw_v),.wbw_base(b_wbw_base),.wbw_total(b_wbw_total));
  // per lane, per class 64-bit rolling hash and count; order inside a class matters, not cycles
  typedef struct packed {longint unsigned h;longint unsigned n;} tr_t;
  tr_t ta[0:3][0:6],tb[0:3][0:6];
  function automatic tr_t push(input tr_t t,input [511:0] v);
   longint unsigned x;integer i;begin x=t.h;for(i=0;i<8;i=i+1)x=(x^v[64*i+:64])*64'h100000001b3+64'h9e3779b97f4a7c15;push.h=x;push.n=t.n+1;end
  endfunction
  function automatic integer clsk(input [16:0] tg);begin clsk=(tg[16:13]==4'b0111)?0:((tg[16:13]==0)?1:2);end endfunction
  `define TRACE(P,T) \
   always @(posedge hbm_clk) if(P``hbm_rst_n)begin:tr_``P integer l,c; \
    for(l=0;l<4;l=l+1)begin \
     if(P``c_k_v[l]&&P``c_k_rdy[l])begin c=clsk(P``c_k_tag[17*l+:17]);T[l][c]=push(T[l][c],{P``c_k_wdata[256*l+:256],P``c_k_wstrb[32*l+:32],P``c_k_we[l],P``c_k_addr[30*l+:30],P``c_k_len[4*l+:4],P``c_k_tag[17*l+:17]});end \
     if(P``g_kr_v[l]&&P``g_kr_rdy[l])T[l][3]=push(T[l][3],{P``g_kr_data[256*l+:256],P``g_kr_tag[17*l+:17],P``g_kr_beat[4*l+:4]}); \
     if(P``g_k_wr_done[l])T[l][4]=push(T[l][4],512'd1); \
     if(P``w_k_wr_done[l])T[l][5]=push(T[l][5],512'd1); \
    end end \
   always @(posedge stream_clk) if(P``stream_rst_n)begin:trf_``P integer l;for(l=0;l<4;l=l+1) if(P``fill_v[l])T[l][6]=push(T[l][6],{P``fill_data[256*l+:256],P``fill_slot[6*l+:6],P``fill_epoch[16*l+:16],P``fill_bank[l]});end
  `TRACE(b_,tb)
  // the gold uses str_clk_use = stream_clk in CHECK=1
  `TRACE(a_,ta)
  initial begin integer l,c;for(l=0;l<4;l=l+1)for(c=0;c<7;c=c+1)begin ta[l][c]='0;tb[l][c]='0;end end
  always @(posedge hbm_clk) if(adone&&bdone_w)begin:fin
   integer l,c,bad;longint unsigned nv=0,nw=0,nf=0,ng=0;bad=0;
   for(l=0;l<4;l=l+1)for(c=0;c<7;c=c+1)begin
    if(ta[l][c]!==tb[l][c])begin bad=bad+1;if(bad<10)$display("TRACE lane %0d class %0d: gold n=%0d form n=%0d",l,c,ta[l][c].n,tb[l][c].n);end
    if(c==1)nv+=ta[l][c].n;if(c==2)nw+=ta[l][c].n;if(c==6)nf+=ta[l][c].n;if(c==0)ng+=ta[l][c].n;
   end
   if(nw==0||ng==0||(!wbo&&(nv==0||nf==0)))$display("FAIL vacuous");
   else if(bad==0&&aerr==0&&berr_w==0)$display("PASS TRACE MUT=%0d group %0d vm %0d wb %0d fills %0d",MUT,ng,nv,nw,nf);
   else $display("FAIL TRACE MUT=%0d classes differ %0d env %0d/%0d",MUT,bad,aerr,berr_w);
   $finish;
  end
 end endgenerate
 initial begin #(40ms);$display("FAIL timeout");$finish;end
endmodule
`default_nettype wire
