`timescale 1ns/1ps
module tb_s81_hop_vm #(parameter integer QD=4, MUT=0, STALL=0, RET_DELAY=0);
 localparam integer XW=640,BASE=2048;
 reg ck=0,rst=0;always #0.4166 ck=~ck;
 reg we=0;reg[13:0] wa=0;reg[511:0] wd=0;
 wire re;wire[13:0] ra;wire rv;wire[511:0] rq;
 wire[1:0] iv,iw,ov;wire[27:0] rows;wire[31:0] masks;wire[1023:0] data,od;
 wire af,mf;wire[1:0] raw_ov;wire[1023:0] raw_od;wire[2:0] mfc;wire[$clog2(QD):0] occ;
 ot_s81_vm_adapter bridge(.clk(ck),.rst_n(rst),.we(we),.wa(wa),.wd(wd),.re(re),.ra(ra),
 .i_v(iv),.i_we(iw),.i_row(rows),.i_mask(masks),.i_d(data),.o_v(ov),.o_d(od),.vm_fault(mf),.rq_v(rv),.rq(rq),.fault(af));
 // Production bank/address/port widths; behavioural macro mode isolates the
 // control mechanism. The VM implementation itself retains its exact bank,
 // request ordering and QD+6 read-return pipeline.
 ot_s81ph_vm_mem #(.NP(2),.NB(32),.QD(QD),.RQ(16),.MACRO(0)) vm(.clk(ck),.rst_n(rst),.grp(1'b0),
 .i_v(iv),.i_we(iw),.i_row(rows),.i_mask(masks),.i_d(data),.o_v(raw_ov),.o_d(raw_od),.fault(mf),.fault_code(mfc),.max_occ(occ));
 generate if(RET_DELAY==0)begin
 assign ov=raw_ov;assign od=raw_od;
 end else begin
 reg[1:0] vp[0:RET_DELAY-1];reg[1023:0] dp[0:RET_DELAY-1];
 always @(posedge ck or negedge rst)if(!rst)for(integer k=0;k<RET_DELAY;k=k+1)vp[k]<=0;
 else begin vp[0]<=raw_ov;for(integer k=1;k<RET_DELAY;k=k+1)vp[k]<=vp[k-1];end
 always @(posedge ck)begin dp[0]<=raw_od;for(integer k=1;k<RET_DELAY;k=k+1)dp[k]<=dp[k-1];end
 assign ov=vp[RET_DELAY-1];assign od=dp[RET_DELAY-1];
 end endgenerate
 reg cv=0,go=0;reg[83:0] cd=0;wire dv;wire[7:0] dt;wire hv,hl,hf;wire[511:0] hd;wire[3:0] hfc;wire[31:0] msgs;
 reg ready=1;
 ot_s81_hop_tx #(.MY_ID(17),.FLIT(512),.XW(XW),.TXB(BASE),.CMDW(84),.SUW(10),.QD(8),
 .USE_VM_RVALID(1),.OUT_DEPTH(32)) hop(.clk(ck),.rst_n(rst),.cmd_v(cv),.cmd_d(cd),.dn_v(dv),.dn_tag(dt),
 .go(go),.res_v(1'b0),.res_tok(21'd0),.res_val(32'd0),.res_stop(1'b0),.run_eosen(1'b1),.run_eos(21'd7),.run_maxl(22'd2048),
 .vm_re(re),.vm_raddr(ra),.vm_rq((MUT==1)?rq^512'd1:rq),.vm_rvalid((MUT==2)?1'b0:rv),
 .out_valid(hv),.out_ready(ready),.out_data(hd),.out_last(hl),.fault(hf),.fault_code(hfc),.st_msgs(msgs));
 function automatic[511:0] word(input integer row);
 for(integer j=0;j<16;j=j+1)word[32*j+:32]=32'(row*2654435761+j*97);
 endfunction
 integer cycles=0,beats=0,errors=0,completed=0,startcy=0,endcy=0,firstcy=0,maxpending=0;
 always @(posedge ck)if(rst)begin
 cycles=cycles+1;
 if(hv&&ready)begin
  if(beats==0)begin
   if(hd[23:12]!=17||hd[11:0]!=18||hd[27:24]!=1||hd[39:28]!=XW||hd[51:40]!=613||hd[72:52]!=1048575)errors=errors+1;
  end else begin
   if(hd!==word(BASE+beats-1)||hl!=(beats==XW))errors=errors+1;
   if(beats==1)firstcy=cycles-startcy;
  end
  beats=beats+1;
 end
 if(hop.read_pending>maxpending)maxpending=hop.read_pending;
 if(dv)begin completed=completed+1;endcy=cycles-startcy;if(dt!=8'd3)errors=errors+1;end
 end
 always @(negedge ck)if(rst)ready=!(STALL&&cycles%11<5);
 initial begin
 repeat(6)@(negedge ck);rst=1;repeat(6)@(negedge ck);
 for(integer i=0;i<XW;i=i+1)begin we=1;wa=BASE+i;wd=word(BASE+i);@(negedge ck);end
 we=0;repeat(32)@(negedge ck);
 cd={1'b0,10'd613,21'd1048575,21'd62000,24'((18<<4)|1),7'd3};cv=1;@(negedge ck);cv=0;
 repeat(4)@(negedge ck);startcy=cycles;go=1;@(negedge ck);go=0;
 repeat(2200)@(negedge ck);
 if(beats!=XW+1||completed!=1||hf||mf||af)errors=errors+1;
 $display("TB_S81_HOP_VM qd=%0d relay=%0d stall=%0d mut=%0d native_bits=512 payload=%0d beats=%0d done=%0d errors=%0d faults=%b%b%b first_payload_cycles=%0d completion_cycles=%0d maxpending=%0d %s",QD,RET_DELAY,STALL,MUT,XW,beats,completed,errors,hf,mf,af,firstcy,endcy,maxpending,errors==0?"PASS":"FAIL");
 $finish;
 end
endmodule
