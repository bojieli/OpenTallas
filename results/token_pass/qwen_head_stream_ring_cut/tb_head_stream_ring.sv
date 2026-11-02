`timescale 1fs/1fs
// Exact four count-ring/FT/pad transport cut from frozen821 W5 route.
// Raw equal-phase source is an explicit component premise, not full producer qualification.
module tb_head_stream_ring;
reg ck=0;always #416500 ck=~ck;
integer cyc=0,t,l,v,phase=0,align=0,want=1,frames=0,first=-1;
always @(posedge ck)cyc<=cyc+1;
wire n_stm=cyc>=54,n_c=cyc>=64,n_l0=cyc>=73,n_l1=cyc>=72;
reg[227:0]raw0=0,raw1=0;
wire[227:0]out0,out1;wire e0,e1;
ot_dp_st #(.W(228)) src0(.clk(ck),.rst_n(n_l0),.d(raw0),.ea(1'b1),.q(out0),.eq(e0));
ot_dp_st #(.W(228)) src1(.clk(ck),.rst_n(n_l1),.d(raw1),.ea(1'b1),.q(out1),.eq(e1));
wire[228:0]q00,q10,q01,q11;wire[3:0]ready,r_fault;
ot_dp_clk_landing_cas #(.W(229),.DEPTH(4)) r00(.fclk(ck),.t_rst_n(n_l0),.clk(ck),.rst_n(n_c),.strap_k(6'd11),.d({e0,out0}),.q(q00),.ready(ready[0]),.fault(r_fault[0]));
ot_dp_clk_landing_cas #(.W(229),.DEPTH(4)) r10(.fclk(ck),.t_rst_n(n_l1),.clk(ck),.rst_n(n_c),.strap_k(6'd10),.d({e1,out1}),.q(q10),.ready(ready[1]),.fault(r_fault[1]));
wire[228:0]ft0,ft1;
ot_dp_dly #(.W(229),.D(4)) f0(.clk(ck),.d(q00),.q(ft0));
ot_dp_dly #(.W(229),.D(2)) f1(.clk(ck),.d(q10),.q(ft1));
ot_dp_clk_landing_cas #(.W(229),.DEPTH(4)) r01(.fclk(ck),.t_rst_n(n_c),.clk(ck),.rst_n(n_stm),.strap_k(6'd12),.d(ft0),.q(q01),.ready(ready[2]),.fault(r_fault[2]));
ot_dp_clk_landing_cas #(.W(229),.DEPTH(4)) r11(.fclk(ck),.t_rst_n(n_c),.clk(ck),.rst_n(n_stm),.strap_k(6'd12),.d(ft1),.q(q11),.ready(ready[3]),.fault(r_fault[3]));
wire[227:0]b0,b1,p0,p1,pa0;wire eb0,eb1;
ot_dp_st #(.W(228)) sink0(.clk(ck),.rst_n(n_stm),.d(q01[227:0]),.ea(q01[228]),.q(b0),.eq(eb0));
ot_dp_st #(.W(228)) sink1(.clk(ck),.rst_n(n_stm),.d(q11[227:0]),.ea(q11[228]),.q(b1),.eq(eb1));
ot_dp_dly #(.W(228),.D(5)) p_0(.clk(ck),.d(b0),.q(p0));
ot_dp_dly #(.W(228),.D(8)) p_1(.clk(ck),.d(b1),.q(p1));
ot_dp_dly #(.W(228),.D(1)) p_align(.clk(ck),.d(p0),.q(pa0));
wire[227:0]g0=align?pa0:p0;
wire[7:0]we;wire[191:0]wa;wire[255:0]wd;
for(genvar x=0;x<4;x++)begin
 assign we[x]=g0[57*x];assign wa[24*x+:24]=g0[57*x+1+:24];assign wd[32*x+:32]=g0[57*x+25+:32];
 assign we[x+4]=p1[57*x];assign wa[24*(x+4)+:24]=p1[57*x+1+:24];assign wd[32*(x+4)+:32]=p1[57*x+25+:32];
end
// Exact qfd_dv_s6_stm window01 gating, before the real production tile.
wire[7:0]xwe=(|we&&wa[23:22]==2'b01)?we:8'd0;
reg cfg=0;wire fault,xbad;wire[1087:0]oe,ow;
qfd_dv_stream_tile stream(.ck(ck),.rst_n(n_stm),.sid(4'd0),.cfg_v(cfg),.cfg_dir(2'd1),.cfg_tag(28'h4845414),.sw_lo('0),.sw_v(1'b0),.sw_hi('0),.se_lo('0),.se_v(1'b0),.se_hi('0),.so_e(oe),.so_w(ow),.xw_we(xwe),.xw_addr(wa),.xw_data(wd),.tw_we(),.tw_kind(),.tw_addr(),.tw_data_lo(),.tw_data_hi(),.xt_v(),.xt_a(),.xt_d_lo(),.xt_d_hi(),.xt_bad(xbad),.fault(fault));
always @(negedge ck)if(n_stm)begin
 if(oe[1087])begin
  frames++;
  if(!want)for(integer k=0;k<64;k++)if(oe[16*k+:16]!==16'(16'h3f80+(frames-1)*64+k))$fatal(1,"STREAM_FRAME_VALUE");
 end
 if(fault&&first<0)first=cyc;
end
initial begin
 if(!$value$plusargs("PHASE=%d",phase))phase=0;
 if(!$value$plusargs("ALIGN=%d",align))align=0;
 if(!$value$plusargs("FAULT=%d",want))want=1;
 while(cyc<160)@(negedge ck);
 if(ready!=15||r_fault!=0)$fatal(1,"ACTUAL_COUNT_RING_BOOT");
 cfg=1;@(negedge ck);cfg=0;
 for(t=0;t<320;t++)begin
  @(posedge ck);#1;raw0=0;raw1=0;
  for(l=0;l<8;l++)begin
   v=cyc-200-(l<4?0:phase);
   if(l<4)begin
    raw0[57*l+1+:24]=24'(1<<22);
    if(v>=0&&v<16)begin raw0[57*l]=1;raw0[57*l+1+:24]=24'((1<<22)+8*v+l);raw0[57*l+25+:32]=32'h3f800000+32'((8*v+l)*65536);end
   end else begin
    raw1[57*(l-4)+1+:24]=24'(1<<22);
    if(v>=0&&v<16)begin raw1[57*(l-4)]=1;raw1[57*(l-4)+1+:24]=24'((1<<22)+8*v+l);raw1[57*(l-4)+25+:32]=32'h3f800000+32'((8*v+l)*65536);end
   end
  end
 end
 raw0=0;raw1=0;repeat(32)@(negedge ck);
 $display("EMITTED_RING_STREAM phase=%0d align=%0d frames=%0d fault=%0d first=%0d ready=%h ringfault=%h",phase,align,frames,fault,first,ready,r_fault);
 if(ready!=15||r_fault!=0||fault!=want||xbad||(!want&&frames!=2))$fatal(1,"RING_STREAM_VERDICT");
 $display("PASS_EMITTED_RING_STREAM_CUT");$finish;
end
endmodule
