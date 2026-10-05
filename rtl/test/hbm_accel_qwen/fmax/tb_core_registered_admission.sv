`timescale 1ns/1ps
// Same full physical core context/cuts; compare accepted engine edges, not
// equal wall cycles. Unit stubs are the unchanged source-pinned route actors.
// This qualifies control/retirement only, not arithmetic or a full token.
module tb_core_registered_admission;
 parameter integer TP=2;
 localparam integer SMIN=(TP==2)?6:7,TCUT=SMIN,BD=(TP==2)?31:41,NWS=(TP==2)?4:5,TWS=(TP==2)?30:38,ORD=(TP==2)?4:7,MEX=(TP==2)?0:1;
 localparam integer NP=6144>>SMIN;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,start=0;
 reg [1023:0] rom[0:4095]; reg[1023:0] q0=0,q1=0;
 reg[191:0] sb=0,sl=0;reg[255:0] ss=0;reg[15:0] sk=0;
 reg[31:0] available=0;
 wire[31:0] gray=available^(available>>1);
 wire[1:0] done,fault,pr,ce,hfault,mx,ov,wr;
 wire[11:0] pa[0:1]; wire[17:0] nt[0:1];wire[31:0] nv[0:1],cy[0:1],wc[0:1];
 wire[NP-1:0] mw[0:1];wire[63:0] sw[0:1],kw[0:1];
 ot_qwen_hbmacc_core_ctx_base #(.GATE_OPT(3),.SMIN(SMIN),.TCUT(TCUT),.BD(BD),.NWS(NWS),.TWS(TWS),.ORD(ORD),.MEM_EXTRA(MEX)) u0(
 .clk(clk),.rst_n(rst_n),.start(start),.token(18'd7),.pos(18'd8191),.done(done[0]),.next_token(nt[0]),.next_val(nv[0]),.cycles(cy[0]),.fault(fault[0]),.prog_re(pr[0]),.prog_addr(pa[0]),.prog_q(q0),.fab_fault(1'b0),.me_clk_en(ce[0]),.wrom_re(wr[0]),.me_ov(ov[0]),.vw_me_we(mw[0]),.vw_mx_we(mx[0]),.vw_su_we(sw[0]),.kv_we(kw[0]),.seg_base(sb),.seg_len(sl),.seg_sidx(ss),.seg_kind(sk),.w_a_gray(gray),.w_c_gray(wc[0]),.hbm_fault(hfault[0]));
 ot_qwen_hbmacc_core_ctx_admission #(.ADMISSION_PIPE(1),.GATE_OPT(3),.SMIN(SMIN),.TCUT(TCUT),.BD(BD),.NWS(NWS),.TWS(TWS),.ORD(ORD),.MEM_EXTRA(MEX)) u1(
 .clk(clk),.rst_n(rst_n),.start(start),.token(18'd7),.pos(18'd8191),.done(done[1]),.next_token(nt[1]),.next_val(nv[1]),.cycles(cy[1]),.fault(fault[1]),.prog_re(pr[1]),.prog_addr(pa[1]),.prog_q(q1),.fab_fault(1'b0),.me_clk_en(ce[1]),.wrom_re(wr[1]),.me_ov(ov[1]),.vw_me_we(mw[1]),.vw_mx_we(mx[1]),.vw_su_we(sw[1]),.kv_we(kw[1]),.seg_base(sb),.seg_len(sl),.seg_sidx(ss),.seg_kind(sk),.w_a_gray(gray),.w_c_gray(wc[1]),.hbm_fault(hfault[1]));
 always @(posedge clk) begin q0<=rom[pa[0]];q1<=rom[pa[1]];end
 // Includes source captured command, engine status/read, every write strobe,
 // maxima/argmax/progress, and all aligned address/mask/data output buses.
 localparam integer CW=3*18+13*24+13;
 localparam integer PK= CW+1+1+16+32+1+24+1+NP+1+18+32+1+16+1+NP*(24+16+512)+24+16+512;
 reg[PK-1:0] traces0[0:32767],traces1[0:32767];
 integer n0=0,n1=0,cmd0=0,cmd1=0,c=0,i=0,finished0=-1,finished1=-1;
 always @(posedge clk) if(u0.rst_i && u1.rst_i) begin
 c=c+1;
 if(c>16*1032*3+2000)$fatal(1,"source-bounded finite fixture did not retire");
 if(ce[0]) begin
 traces0[n0]={u0.core.u_me.f,u0.core.u_me.active,u0.core.u_me.pend,u0.core.u_me.left,u0.core.u_me.lfsr,u0.core.int8_wrom_re,u0.core.int8_wrom_addr,ov[0],mw[0],mx[0],u0.core.am_idx,u0.core.am_val,u0.core.am_any,u0.core.me_progress,u0.core.me_fault,u0.core.vw_me_addr,u0.core.vw_me_mask,u0.core.vw_me_data,u0.core.vw_mx_addr,u0.core.vw_mx_mask,u0.core.vw_mx_data};
 n0=n0+1; if(u0.core.me_go && u0.core.me_ready)cmd0=cmd0+1;
 end
 if(ce[1]) begin
 traces1[n1]={u1.core.u_me.f,u1.core.u_me.active,u1.core.u_me.pend,u1.core.u_me.left,u1.core.u_me.lfsr,u1.core.int8_wrom_re,u1.core.int8_wrom_addr,ov[1],mw[1],mx[1],u1.core.am_idx,u1.core.am_val,u1.core.am_any,u1.core.me_progress,u1.core.me_fault,u1.core.vw_me_addr,u1.core.vw_me_mask,u1.core.vw_me_data,u1.core.vw_mx_addr,u1.core.vw_mx_mask,u1.core.vw_mx_data};
 n1=n1+1; if(u1.core.me_go && u1.core.me_ready)cmd1=cmd1+1;
 end
 if(done[0] && finished0<0)finished0=c;
 if(done[1] && finished1<0)finished1=c;
 if((|sw[0]) || (|sw[1]) || (|kw[0]) || (|kw[1]))$fatal(1,"unexpected SU/KV writer");
 if(n0>=32768 || n1>=32768)$fatal(1,"trace storage exhausted");
 end
 initial begin
 for(i=0;i<4096;i=i+1)rom[i]=0;
 for(i=0;i<16;i=i+1)begin
 rom[i][1:0]=1;rom[i][23+:16]=64;rom[i][39+:16]=1;rom[i][55+:16]=4;
 rom[i][72+:24]=i*128;rom[i][193+:24]=i*64;rom[i][217]=1;
 end
 // Deliberately block initial supplied reads, then publish monotonic arrivals.
 sl[23:0]=24'hffffff;sk[1:0]=1;
 repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);start=1;@(negedge clk);start=0;
 repeat(400)@(negedge clk);available=32'h01000000;
 wait(done[0]&&done[1]);repeat(4)@(negedge clk);
 if(n0!=n1 || cmd0!=16 || cmd1!=16)$fatal(1,"advance/command debt %0d/%0d command %0d/%0d",n0,n1,cmd0,cmd1);
 for(i=0;i<n0;i=i+1)if(traces0[i]!==traces1[i])$fatal(1,"accepted output/command mismatch edge=%0d",i);
 if(nt[0]!==nt[1]||nv[0]!==nv[1]||fault[0]!==fault[1]||hfault[0]!==hfault[1]||wc[0]!==wc[1])$fatal(1,"terminal/retirement mismatch");
 $display("PASS core_context TP=%0d advances=%0d commands=%0d baseline_cycles=%0d candidate_cycles=%0d delta=%0d",TP,n0,cmd0,finished0,finished1,finished1-finished0);
 $finish;
 end
endmodule
