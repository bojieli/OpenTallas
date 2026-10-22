`timescale 1ns/1ps
// Bounded production configuration producer: real CTL->XR->DL4->VP SRAM
// ->RDOUT->DL4->XR HB1 B->actual SVC job gate. No direct q injection.
// Direct local q wire scopes this component; parent q route remains unproved.
module tb_qf_config #(parameter integer UNIFORM=0);
 reg clk=0; always #0.4165 clk=~clk;
 reg rst=0; reg ev=0; reg[1103:0] eb=0;
 wire [4:0] cv,swv;wire[159:0] cd;
 wire[49:0] swa;wire[39:0] swm;wire[1279:0] swd;
 wire lv;wire[255:0] ld;wire xf,vf;wire[1103:0] bo;
 wire[2:0] cid;wire[1103:0] cib;
 wire[4:0] lov={4'd0,lv};wire[1279:0] lod={1024'd0,ld};
 ot_s81sl_xr #(.HB(1)) u_xr(.clk(clk),.rst_n(rst),.sid(4'd6),
 .dl_ev(ev),.dl_e(eb),.dl_wv(1'b0),.dl_w(1104'd0),.dl_vv(1'b0),.dl_vb(276'd0),
 .ci_dir(cid),.ci_b(cib),.bi(1104'd0),.bo(bo),.c_v(cv),.c_d(cd),
 .sw_v(swv),.sw_a(swa),.sw_m(swm),.sw_d(swd),.lo_v(lov),.lo_d(lod),
 .p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),
 .eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.fault(xf));
 wire cvp,swvp;wire[159:0] cdp;wire[9:0] swap;wire[7:0] swmp;wire[255:0] swdp;
 ot_s81sl_rly #(.W(436),.D(4)) u_dn(.clk(clk),
 .d({cv[0],cd,swv[0],swa[9:0],swm[7:0],swd[255:0]}),
 .q({cvp,cdp,swvp,swap,swmp,swdp}));
 wire lvl;wire[255:0] ldl;
 ot_s81sl_rly #(.W(257),.D(4)) u_up(.clk(clk),.d({lvl,ldl}),.q({lv,ld}));
 ot_s81sl_vp u_vp(.clk(clk),.rst_n(rst),.c_v(cvp),.c_d(cdp),.sw_v(swvp),
 .sw_a(swap),.sw_m(swmp),.sw_d(swdp),.cw_v(2'd0),.cw_a(24'd0),.cw_d(64'd0),
 .lo_v(lvl),.lo_d(ldl),.x_rv(1'b0),.x_ra(10'd0),.x_wv(1'b0),.x_wa(10'd0),
 .x_wm(8'd0),.x_wd(256'd0),.hq_v(1'b0),.hq_d(256'd0),.fault(vf));
 reg[32:0] jc=0;wire[1:0] jd;wire[514:0] cq;
 wire[511:0] data;
 genvar qi;generate for(qi=0;qi<32;qi=qi+1)begin:g_compact_wire
  assign data[16*qi+:16]=UNIFORM?bo[52+32*qi+16+:16]:bo[52+16*qi+:16];
 end endgenerate
 reg[514:0] qp=0;
 integer mut=0;
 // This is exactly the existing entry q pin capture, followed by its u_job.
 always @(posedge clk or negedge rst) if(!rst) qp[0]<=0;else qp[0]<=bo[0] && mut!=4;
 always @(posedge clk) qp[514:1]<={2'b00,data ^ ((mut==1)?512'h1:512'h0)
                                      ^ ((mut==2)?(512'h1<<495):512'h0)};
 ot_s81_svc_job u_job(.ck(clk),.rs_n(rst),.j_cmd(jc),.j_dn(jd),.q(qp),.core_q(cq),
 .ad(1026'd0),.xd(514'd0),.od(514'd0));
 reg[511:0] gold[0:2];integer cyc,n=0,nc=0,fd,rc,t,tag=0,errors=0,first=-1;
 reg[185:0] payload;reg[1103:0] beat;
 string dir,stimfile,goldfile;
 task tick;begin @(posedge clk);#0.001;end endtask
 initial begin
 if(!$value$plusargs("DIR=%s",dir))$fatal(1,"NO_DIR");
 rc=$value$plusargs("TAG=%d",tag);rc=$value$plusargs("MUT=%d",mut);
 stimfile=$sformatf("%s/ctl_%0d.hex",dir,tag);goldfile=$sformatf("%s/gold_%0d.hex",dir,tag);
 $readmemh(goldfile,gold);fd=$fopen(stimfile,"r");if(!fd)$fatal(1,"NO_STIM");
 repeat(12)tick();@(negedge clk);rst=1;
 rc=$fscanf(fd,"%h %h\n",t,payload);
 for(cyc=0;cyc<280;cyc=cyc+1)begin
 @(negedge clk);ev=0;eb=0;jc=0;
 if(cyc==10)jc={1'b1,24'd385,8'(tag)}; //3frames, END source0.
 if(rc==2 && cyc==t+((mut==5)?-1:(mut==6)?1:0))begin
 beat=0;beat[0]=1;beat[3:1]=0;beat[21+:186]=payload;
 // Wrong slice destination must suppress real SRAM/config work.
 if(mut==3)beat[21+:16]=16'd0;
 ev=1;eb=beat;rc=$fscanf(fd,"%h %h\n",t,payload);
 end
 tick();
 if(cv[0])$display("STAGE xr_cmd=%0d",cyc);
 if(cvp)$display("STAGE vp_cmd=%0d",cyc);
 if(lvl)$display("STAGE vp_lo=%0d",cyc);
 if(lv)$display("STAGE xr_lo_pin=%0d",cyc);
 if(bo[0])begin
 $display("SOURCE cyc=%0d index=%0d data=%0128h",cyc,n,bo[563:52]);
 if(n>=3 || data!==gold[n])begin errors++;$display("CONFIG_SOURCE_MISMATCH");end
 if(n<3 && cyc!=((n==2)?(212+2*UNIFORM):(112+2*UNIFORM+(2+2*UNIFORM)*n)))begin errors++;$display("SOURCE_AGE_MISMATCH got=%0d",cyc);end
 n++;
 end
 if(cq[0])begin
 if(first<0)first=cyc;
 $display("CONSUMER cyc=%0d data=%0128h",cyc,cq[512:1]);
 if(nc>=3 || cq[512:1]!==gold[nc])begin errors++;$display("CONSUMER_CORRUPT_WORD");end
 if(nc<3 && cyc!=((nc==2)?(213+2*UNIFORM):(113+2*UNIFORM+((mut==7)?nc:(2+2*UNIFORM)*nc))))begin errors++;$display("CONSUMER_AGE_MISMATCH original_ii1=%0d",mut==7);end
 nc++;
 end
 if(cyc>20 && (xf || vf || jd[1]))begin errors++;$display("ACTUAL_SOURCE_CONSUMER_FAULT cyc=%0d xr=%b vp=%b job=%b",cyc,xf,vf,jd);end
 end
 if(n!=3 || nc!=3 || first<0)begin errors++;$display("MISSING_SOURCE_OR_CONSUMER n=%0d nc=%0d first=%0d",n,nc,first);end
 if(errors)$fatal(1,"QF_CONFIG_FAIL errors=%0d tag=%0d mut=%0d",errors,tag,mut);
 $display("QF_CONFIG_PASS tag=%0d source_words=%0d first_consumer=%0d",tag,n,first);$finish;
 end
endmodule
