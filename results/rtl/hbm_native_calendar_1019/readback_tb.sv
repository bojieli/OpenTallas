`timescale 1ns/1ps
module tb;
reg refclk=0;always #5 refclk=~refclk;reg por_n=0;wire clk,stream,rs,rq,br,brfault;
hfd_ckgen cg(.refclk(refclk),.por_n(por_n),.pll_stream(stream),.pll_serial(clk),.por_serial(rq),.por_stream(rs));
ot_hbm_su_bridge_release_s rel(.clk_serial(clk),.rst_n(rq),.prog_busy(busy),.bridge_rst_n(br),.fault(brfault));
integer st=-1,qt=-1;always @(posedge stream)if(rs)st=st+1;always @(posedge clk)if(rq)qt=qt+1;
wire[16:0] srq_unused,rrq_unused;wire[256:0] ret;wire bf;assign srq_unused=0;
ot_hbm_su_multirate_bridge bridge(.serial_clk(clk),.stream_clk(stream),.rst_n(br),.serial_rq(srq_unused),.serial_wq(281'b0),.stream_rq(rrq_unused),.stream_rr(257'b0),.stream_done(1'b0),.fault(bf));
always @(posedge stream)begin #0.001;if(rs && rrq_unused[16])$display("TIMING rq stream=%0d ps=%0t sector=%h phase=%d",st,$realtime,rrq_unused[15:0],bridge.phase);end
always @(posedge br)$display("TIMING bridge release ps=%0t st=%0d qt=%0d",$realtime,st,qt);
reg rst_n=0,we=0,start=0;reg[15:0] bank=0;reg[6:0] row=0;reg[255:0] data=0;
wire busy,valid,done,fault;wire[15:0] edge_index;wire[2421:0] command;
reg[279:0] cfg[0:4095];reg[2421:0] exp[0:7110];integer cyc=-1,s=-1,n=0,first=-1;string fn;integer want_startup=9,N=44,W=56;string goldfile;
ot_hbm_su_programme_pslice_c5 dut(.clk(clk),.rst_n(rst_n),.cfg_we(we),.cfg_bank(bank),.cfg_row(row),.cfg_data(data),.start(start),.length(16'(N)),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),.command(command));
always @(posedge clk) if(rst_n) begin
 cyc=cyc+1;
 if(start)s=cyc;
 if(valid)begin
  if(first<0)begin first=cyc;if(cyc-s!=want_startup)$fatal(1,"PRODUCER FAIL startup got=%0d expected=%0d",cyc-s,want_startup);end
  $display("CMD e=%0d serial=%0d stream=%0d delta=%0d ps=%0t",edge_index,qt,st,cyc-s,$time);
  if(edge_index!=n || command!==exp[n] || fault)$fatal(1,"PRODUCER FAIL edge=%0d n=%0d fault=%b",edge_index,n,fault);
  n=n+1;
 end
end

reg cv=0,dv=0,lv=0;reg[7:0] ct=96;reg[11:0] ca=0;reg[255:0] cd=0;reg[12:0] dl=160;
wire acv,adv,alv;wire[7:0] act;wire[11:0] aca,adb;wire[255:0] acd;wire[12:0] adl;wire[15:0] adlp;
ot_hbm_host_cfg_leaf_sw leaf(.clk(stream),.rst_n(rs),.cfg_v(cv),.cfg_target(ct),.cfg_addr(ca),.cfg_data(cd),.desc_v(dv),.desc_base(12'b0),.desc_limit(dl),.desc_loops(16'd1),.launch_v(lv),.a_cfg_v(acv),.a_cfg_target(act),.a_cfg_addr(aca),.a_cfg_data(acd),.a_desc_v(adv),.a_desc_base(adb),.a_desc_limit(adl),.a_desc_loops(adlp),.a_launch_v(alv),.t_ready(14'b0),.t_active(14'b0),.t_fault(23'b0));
wire tf,cf,calv;wire[23:0] lr,lw,rslot,wslot;wire[7:0] rv,wv;wire[31:0] ordinal;
hfd_hgi_vm_calendar_f20 cal(.clk(stream),.clk_cap(stream),.clk_mem(stream),.clk_tgt(stream),.rst_n(rs),.tgt(8'd96),.cfg_v(acv),.cfg_target(act),.cfg_addr(aca),.cfg_data(acd),.desc_v(adv),.desc_base(adb),.desc_limit(adl),.desc_loops(adlp),.launch_v(alv),.tgt_fault(tf),.fault(cf),.calendar_v(calv),.ordinal(ordinal),.lg_local_read(lr),.lg_local_write(lw),.rslot_v(rv),.wslot_v(wv),.rslot(rslot),.wslot(wslot));
reg[255:0] image[0:159];integer mut=0;
initial begin
 $value$plusargs("MUT=%d",mut);$readmemh("calendar.mem",image);wait(rs);repeat(20)@(negedge stream);
 for(integer i=0;i<160;i++)begin cv=1;ca=i;cd=image[i];if(mut==1)cd[162:139]=0;if(mut==2)cd[88:81]=8'h01;@(negedge stream);end
 cv=0;repeat(10)@(negedge stream);dv=1;@(negedge stream);dv=0;
 while(st<(3500+(mut==3?1:0)))@(negedge stream);lv=1;@(negedge stream);lv=0;
end
wire[7:0] b_fault,t_fault;wire[7:0] faults=b_fault|t_fault;integer read_count=0,write_count=0;
for(genvar b=0;b<8;b++)begin:B
 integer local_reads=0;
 wire[16:0] sq={command[469+30*b],command[453+30*b+:16]};
 reg[280:0] wd[0:3];wire[38:0] wc=command[128+39*b+:39];
 always @(posedge clk)begin wd[0]<={wc[38],wc[23:8],{8{16'had51,wc[23:8]}},wc[7:0]};for(integer k=1;k<4;k++)wd[k]<=wd[k-1];end
 wire[16:0] rq,nrq;
 always @(posedge stream)if(b==0 && (tap.read_due || tap.write_due || tap.rr_v || tap.done_d))$display("DUE st=%d read_due=%b rr_v=%b write_due=%b done_d=%b",st,tap.read_due,tap.rr_v,tap.write_due,tap.done_d);
 always @(posedge stream)if(rq[16] || nrq[16])$display("REQ b=%d st=%d local=%h near=%h lr=%b rv=%b",b,st,rq,nrq,lr[b],rv[b]);wire[280:0] wq,nwq;wire[256:0] rr,nrr,serrr;wire done,ndone,serdone;
 ot_hbm_su_multirate_bridge #(.READ_RETURN(11),.WRITE_RETURN(8)) brg(.serial_clk(clk),.stream_clk(stream),.rst_n(br),.serial_rq(sq),.serial_wq(wd[3]),.serial_rr(serrr),.serial_done(serdone),.stream_rq(rq),.stream_wq(wq),.stream_rr(rr),.stream_done(done),.fault(b_fault[b]));
 ot_hbm_vm_lg_static_bank_m60 #(.READ_RETURN(11),.WRITE_RETURN(8)) tap(.clk(stream),.rst_n(rs),.rret(5'b0),.wret(5'b0),.local_rq(rq),.local_wq(wq),.far_rq(17'b0),.far_wq(281'b0),.local_read(lr[b]),.local_write(lw[b]),.near_rq(nrq),.near_wq(nwq),.near_rr(nrr),.near_w_done(ndone),.local_rr(rr),.local_w_done(done),.fault(t_fault[b]));
 hfd_vms_bank_native_q0_faces vm(.rq0(nrq),.rr0(nrr),.rq1(17'b0),.rq2(17'b0),.rq3(17'b0),.rq4(17'b0),.wq0(nwq),.wq_done0(ndone),.wq1(281'b0),.bid(3'(b)),.sid(2'b0),.clk(stream),.clk_n(stream),.clk_s(stream),.clk_e(stream),.clk_w(stream),.clk_macro0(stream),.clk_macro1(stream),.clk_macro2(stream),.rst_n(rs),.rslot_v(rv[b]),.rslot(rslot[b*3+:3]),.wslot_v(wv[b]),.wslot(wslot[b*3+:3]),.dq(281'b0),.kq(281'b0),.xq(276'b0),.xq2(276'b0),.pq(285'b0));
 always @(posedge clk)if(br)begin if(serrr[256])begin
   if(local_reads<2)begin if(serrr[255:0]!==256'b0)$fatal(1,"NATIVE_DATA FAIL initial word b=%d",b);end
   else begin
    if(serrr[255:0]!=={8{16'had51,16'(16'h0118+(local_reads-2)*8+b)}})$fatal(1,"NATIVE_DATA FAIL readback b=%d n=%d got=%h",b,read_count,serrr[255:0]);
   end
   read_count=read_count+1;local_reads=local_reads+1;
  end if(serdone)write_count=write_count+1;end
end
always @(posedge stream)begin #0.001;if(rs && (|lr || |lw || |rv || |wv))$display("CAL cycle=%0d ord=%0d lr=%h lw=%h rv=%h wv=%h",st,ordinal,lr,lw,rv,wv);end
initial begin
 if(!$value$plusargs("CFG=%s",fn))$fatal;
 $value$plusargs("STARTUP=%d",want_startup);
 $value$plusargs("N=%d",N);$value$plusargs("W=%d",W);if(!$value$plusargs("GOLD=%s",goldfile))goldfile="expected.mem";
 $readmemh(fn,cfg);$readmemh(goldfile,exp);
 por_n=0;#100 por_n=1;wait(rq);rst_n=1;repeat(12)@(negedge clk);
 for(integer i=0;i<W;i=i+1)begin we=1;bank=cfg[i][279:264];row=cfg[i][262:256];data=cfg[i][255:0];@(negedge clk);end
 we=0;while(qt<2665)@(negedge clk);start=1;@(negedge clk);start=0;
 repeat(N+60)@(negedge clk);
 $display("COUNTS reads=%d writes=%d bridge=%h tap=%h target=%b cal=%b release=%b",read_count,write_count,b_fault,t_fault,tf,cf,brfault);
 if(n!=N || fault || faults || tf || cf || brfault || read_count!=32 || write_count!=16)$fatal(1,"PRODUCER FAIL count=%0d fault=%b",n,fault);
 $display("NATIVE_CALENDAR PASS commands=%0d reads=%0d writes=%0d startup=%0d",n,read_count,write_count,first-s);$finish;
end
endmodule
