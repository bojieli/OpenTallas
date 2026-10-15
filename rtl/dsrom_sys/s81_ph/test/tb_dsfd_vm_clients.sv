`timescale 1ns/1ps
module tb_dsfd_vm_clients;
 reg clk=0,cks=0; always #2 clk=~clk; always #1.5 cks=~cks;
 reg rst_n=0,rss_n=0;
    wire t_swg, t_srg, t_err, vrv, dv, c_wv, c_l0v; wire [52:0] t_ks; wire [1025:0] t_srq; wire [511:0] vrq;
    wire [7:0] dt; wire [16*513-1:0] t_bl; wire [2:0] t_cts; wire [9:0] c_wd; wire [603:0] c_l0d; wire flt; wire [31:0] fvec;
    wire [2:0] max_occ; wire [3:0] t_rdy;
    wire vwe, vre; wire [13:0] vwa, vra; wire [511:0] vwd; wire vready; wire [15:0] vwm; wire [7:0] vwt,vack_tag; wire vwv; wire [15:0] vack_mask;
    reg cv=0; reg [83:0] cd=0;
    reg [84:0] c_cmd = 0; wire [8:0] c_done; wire [1:0] c_st; wire inp_su, inp_hc;
    dsfd_sp_vm_m #(.MACRO(1),.WCOMMIT(1)) u_vm (
        .ck(clk), .rst(rst_n), .cks(cks), .rss(rss_n),
        .f_swv(1'b0), .f_swd(527'd0), .t_swg(t_swg), .f_srv(1'b0), .f_srd(31'd0), .t_srg(t_srg),
        .t_ks(t_ks), .t_srq(t_srq), .t_err(t_err), .f_cap(13376'd0),
        .vwm(vwm),.vwt(vwt),.vwv(vwv),.vack_tag(vack_tag),.vack_mask(vack_mask),.vready(vready), .vwe(vwe), .vwa(vwa), .vwd(vwd), .vre(vre), .vra(vra), .vrv(vrv), .vrq(vrq), .cv(cv), .cd(cd), .dv(dv), .dt(dt),
        .f_svc(1027'd0), .f_coll(2100'd0), .t_cts(t_cts), .f_sel(515'd0), .f_col(515'd0), .f_hc(1026'd0), .t_bl(t_bl),
        .c_wv(c_wv), .c_wd(c_wd), .c_wr(1'b1), .t_rdy(t_rdy), .c_l0v(c_l0v), .c_l0d(c_l0d), .c_l0r(1'b1),
        .flt(flt), .fvec(fvec), .max_occ(max_occ));

 reg [17:0] rq_v=0; reg [251:0] rq_row=0; wire [17:0] rq_credit,rs_v;
 wire [9215:0] rs_d;
 reg [23:0] wq_v=0; reg [335:0] wq_row=0; reg [383:0] wq_mask=0; reg [12287:0] wq_data=0;
 wire [23:0] wq_credit; wire fault;
 dsfd_vm_clients #(.WCOMMIT(1)) u_cli(.ck(cks),.rst_n(rss_n),.rq_v(rq_v),.rq_row(rq_row),.rq_credit(rq_credit),
 .rs_v(rs_v),.rs_d(rs_d),.wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),.wq_data(wq_data),
 .wq_credit(wq_credit),.vwm(vwm),.vwt(vwt),.vwv(vwv),.vack_tag(vack_tag),.vack_mask(vack_mask),.v_ready(vready),.vwe(vwe),.vwa(vwa),.vwd(vwd),.vre(vre),.vra(vra),.vrv(vrv),.vrq(vrq),.fault(fault));
 integer trace_fd;
 initial trace_fd=$fopen("service_trace.csv","w");
 always @(posedge cks) begin
  if(vwe)$fwrite(trace_fd,"issue_write,%0.3f,%0d,%0d,%0h\n",$realtime,vwt,vwa,vwm);
  if(vre)$fwrite(trace_fd,"issue_read,%0.3f,0,%0d,0\n",$realtime,vra);
  if(vrv)$fwrite(trace_fd,"read_return,%0.3f,0,0,0\n",$realtime);
  if(vwv)$fwrite(trace_fd,"write_ack,%0.3f,%0d,0,%0h\n",$realtime,vack_tag,vack_mask);
 end
 genvar th,tt,ts,tb;
 generate for(th=0;th<4;th=th+1)begin:tr_h
  for(tt=0;tt<4;tt=tt+1)begin:tr_t
   for(ts=0;ts<4;ts=ts+1)begin:tr_s
    for(tb=0;tb<2;tb=tb+1)begin:tr_b
     always @(posedge clk)begin
      for(integer qe=0;qe<4;qe=qe+1)begin
       if(u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].k_v[qe] &&
        u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].occ-
        u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].serve+qe<4 &&
        (u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].k_p[qe]==3 ||
         u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].k_p[qe]==4))
        $fwrite(trace_fd,"bank_enqueue,%0.3f,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\n",$realtime,
         u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].k_tag[qe],
         {u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].k_r[qe],
          u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].gidq},th,tt,ts*2+tb,
         u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].k_we[qe],
         u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].occ,
         u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].serve);
      end
      if(u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].s_we &&
       (u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].s_p==3 ||
        u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].s_p==4))
       $fwrite(trace_fd,"macro_write,%0.3f,%0d,%0d,%0d,%0d,%0d\n",$realtime,
        u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].s_tag,
        {u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].s_r,
         u_vm.g_h[th].g_t[tt].u_bg.g_s[ts].g_bank[tb].gidq},th,tt,ts*2+tb);
     end
    end
   end
  end
 end endgenerate
 reg [23:0] wt=0; reg [17:0] rt=0; reg [511:0] gold[0:23]; integer cyc=0, nr=0, bad=0, expected=0;
 integer base=0; reg partial_done=0;
 always @(posedge cks) if(dv && dt==203) partial_done<=1;
 task command(input [23:0] arg,input [7:0] tag);
 begin @(negedge cks);cd={tag[7],52'd0,arg,tag[6:0]};cv=1;@(negedge cks);cv=0;end
 endtask
 always @(posedge cks) begin
  cyc=cyc+1; wt=wt|wq_credit; rt=rt|rq_credit;
  for(integer x=0;x<18;x=x+1) if(rs_v[x]) begin
   if(x+base!=expected) begin $display("ORDER_BAD got%0d expected%0d",x+base,expected); bad=bad+1; end
   if(rs_d[512*x+:512]!==gold[x+base]) begin $display("DATA_BAD slot%0d",x+base); bad=bad+1; end
   expected=expected+1; nr=nr+1;
  end
 end
 task writes(input integer round, input integer partial);
 begin
  wait(&wt); @(negedge cks); wt=0;
  for(integer x=0;x<24;x=x+1) begin
   wq_row[14*x+:14]=32*x+(7*x)%32; wq_mask[16*x+:16]=partial ? 16'h5555 :16'hffff;
   for(integer w=0;w<16;w=w+1) begin
    wq_data[512*x+32*w+:32]=round*32'h13579+x*32'hfed+w;
    if(!partial || !(w%2)) gold[x][32*w+:32]=wq_data[512*x+32*w+:32];
   end
  end
  wq_v='1; @(negedge cks); wq_v=0; wait(&wt);
 end endtask
 task reads;
 begin
  wait(&rt); @(negedge cks); rt=0; expected=0;base=0;
  for(integer x=0;x<18;x=x+1) rq_row[14*x+:14]=32*x+(7*x)%32;
  rq_v='1; @(negedge cks); rq_v=0;wait(expected==18);wait(&rt);
  @(negedge cks); rt=rt & ~18'h3f; base=18;
  for(integer x=0;x<6;x=x+1) rq_row[14*x+:14]=32*(18+x)+(7*(18+x))%32;
  rq_v=18'h3f; @(negedge cks); rq_v=0;wait(expected==24);wait(&rt);
 end endtask
 initial begin
  #200; rst_n=1;rss_n=1;
  for(integer r=0;r<8;r=r+1) begin writes(2*r,0);writes(2*r+1,1);reads();end
  // An exact eight-element write must complete an eight-element ARM;
  // rewriting a full row after a masked read would incorrectly count16.
  command({3'd1,2'd0,1'b0,4'd0,14'd1024},8'd201);
  command({3'd2,2'd0,4'd0,15'd1},8'd202);
  command({3'd3,2'd0,19'd8},8'd203);
  command({3'd1,2'd0,1'b0,4'd0,14'd1024},8'd204);
  wait(dv && dt==204);
  @(negedge cks); wt[0]=0; wq_row[13:0]=1024;wq_mask[15:0]=16'h5555;wq_data[511:0]='1;wq_v=1;
  @(negedge cks);wq_v=0;wait(wt[0]);wait(partial_done);
  repeat(40)@(posedge cks);
  if(u_vm.u_fe.sl_cnt[0]!=8)begin $display("MASK_COUNT_BAD %0d",u_vm.u_fe.sl_cnt[0]);bad=bad+1;end
  $display("RESULT reads%0d cycles%0d bad%0d fault%0b VM%0b",nr,cyc,bad,fault,flt);
  if(bad==0 && !fault && !flt && !u_vm.g_commit.u_ack.fault && nr==192) $display("PASS"); else $display("FAIL");$finish;
 end
 initial begin #2000000; $display("FAIL TIMEOUT");$finish;end
endmodule
