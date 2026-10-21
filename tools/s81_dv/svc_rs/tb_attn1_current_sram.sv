`timescale 1ns/1ps
// Current dsdv_svc_att API, two exact SRAM_MACRO=1 shares, differing only NTP and compiled PO/PVO.
// One tile receives complete remotely-owned ROWS frames; no HBM transactions are required by this selected-row case.
module tb_attn1_current_att;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0,qv=0; reg [511:0] qd[0:1];
 wire [1:0] lv,pv,done,fault,go; wire[2131:0]ld[0:1]; wire[512:0]pd[0:1];
 wire[31:0]fc[0:1]; wire[15:0]pio[0:1],pvo[0:1],jc[0:1];wire[1:0]st[0:1];wire[681:0]rq[0:1];
 integer T=46,seed=1,ns[0:1],np[0:1],ng[0:1],mism=0,cycles=0;
 reg [2131:0]scores[0:159];reg[512:0]words[0:39];
 for(genvar e=0;e<2;e++)begin:E
 if(e==0) begin:REF
 dsdv_svc_att_ref #(.SRAM_MACRO(1),.DIE_ID(0),.ST(1),.NTP(0)) u(
 .clk(clk),.rst_n(rst_n),.sid(4'd0),.tile(4'd0),.gd(8'd4),.pvs(8'd0),.root(1'b0),
 .q_v(qv),.q_d(qd[e]),.hw_v(1'b0),.hw_d(291'd0),.qrq(rq[e]),.qrk(2'b11),.qwd(2'd0),.qrv(2'd0),
 .qr_data(512'd0),.qr_tag(34'd0),.qr_beat(8'd0),.l_v(lv[e]),.l_d(ld[e]),.pv_ov(pv[e]),.pv_od(pd[e]),
 .sm_st(),.sm_kind(),.sm_jid(),.sm_rv(),.sm_rp(),.sm_rj(),.sm_rd(),.go_o(go[e]),.tjob_o(),.done(done[e]),.tagj(),
 .hcr(),.hack(),.fault(fault[e]),.fault_code(fc[e]),.pio_o(pio[e]),.pvo_o(pvo[e]),.jc_o(jc[e]),.st_o(st[e]));
 end else begin:DUT
 dsdv_svc_att #(.SRAM_MACRO(1),.DIE_ID(0),.ST(1),.NTP(1),.PMEM(1),.QMEM_SRAM(0)) u(
 .clk(clk),.rst_n(rst_n),.sid(4'd0),.tile(4'd0),.gd(8'd4),.pvs(8'd0),.root(1'b0),
 .q_v(qv),.q_d(qd[e]),.hw_v(1'b0),.hw_d(291'd0),.qrq(rq[e]),.qrk(2'b11),.qwd(2'd0),.qrv(2'd0),
 .qr_data(512'd0),.qr_tag(34'd0),.qr_beat(8'd0),.l_v(lv[e]),.l_d(ld[e]),.pv_ov(pv[e]),.pv_od(pd[e]),
 .sm_st(),.sm_kind(),.sm_jid(),.sm_rv(),.sm_rp(),.sm_rj(),.sm_rd(),.go_o(go[e]),.tjob_o(),.done(done[e]),.tagj(),
 .hcr(),.hack(),.fault(fault[e]),.fault_code(fc[e]),.pio_o(pio[e]),.pvo_o(pvo[e]),.jc_o(jc[e]),.st_o(st[e]),.tx_i(),.tx_o(529'd0));
 end
 end
 function automatic [511:0] hdr(input[3:0]typ,input[11:0]len,input[448:0]sp);
 hdr={typ,1'b0,4'b0001,8'h21,3'd0,len,21'd777,10'd0,sp};endfunction
 task automatic send(input[511:0]a,input[511:0]b);@(negedge clk);qv=1;qd[0]=a;qd[1]=b;endtask
 task automatic both(input[511:0]a);send(a,a);endtask
 reg[448:0]sp;reg[511:0]word_,a,b;integer i,j,k;
 initial begin
 ns[0]=0;ns[1]=0;np[0]=0;np[1]=0;ng[0]=0;ng[1]=0;
 void'($value$plusargs("t=%d",T));void'($value$plusargs("seed=%d",seed));void'($urandom(seed));
 if(T<1 || T>512)$fatal(1,"selected-row test supports1..512");
 repeat(6)@(negedge clk);rst_n=1;repeat(6)@(negedge clk);
 sp=0;sp[32]=1;sp[31:30]=0;both(hdr(12,0,sp)); // dynamic CFG overrides parameter ST1
 sp=0;sp[98:89]=10'(T);both(hdr(2,0,sp));
 sp=0;sp[19:10]=10'(T);both(hdr(7,12'((T+15)/16),sp));
 for(i=0;i<(T+15)/16;i++)begin word_=0;for(j=0;j<16;j++)word_[32*j+:32]=32'h40|(32'(16*i+j)<<9);both(word_);end
 for(k=0;k<2;k++)begin sp=0;sp[448]=k[0];both(hdr(1,128,sp));for(i=0;i<128;i++)begin
 word_=0;for(j=0;j<32;j++)word_[16*j+:16]={1'b0,5'd14,10'($urandom)};both(word_);end end
 // Complete tile0 pair for every selected remote row. FP4 codes and UE8 scales vary.
 for(k=0;k<T;k+=200)begin both(hdr(6,12'((T-k>200)?200:T-k),0));
 for(i=k;i<T && i<k+200;i++)begin word_=0;word_[9:0]=10'(i);word_[30:10]=21'h40|(21'(i)<<9);word_[33:31]=0;
 for(j=0;j<8;j++)word_[34+32*j+:32]=$urandom;word_[321:290]=32'h7f7f7f7f;both(word_);end end
 // All P words are loaded before GO; production FIFO read and frame parsing remain active.
 both(hdr(5,12'((T+1)/2),0));for(i=0;i<(T+1)/2;i++)begin word_=0;
 for(j=0;j<32;j++)word_[16*j+:16]={1'b0,5'd12,10'($urandom)};both(word_);end
 repeat(32)begin @(negedge clk);qv=0;end
 sp=0;sp[15:0]=300;sp[31:16]=1600;sp[47:32]=123;a=hdr(13,0,sp);
 sp[15:0]=800;sp[31:16]=2600;b=hdr(13,0,sp);send(a,b);@(negedge clk);qv=0;
 repeat(4000)@(negedge clk);
 $display("CURRENT_ATT T=%0d SRAM=1 NTP=0/1 scores=%0d/%0d pv_words=%0d/%0d go=%0d/%0d done=%b faults=%h/%h mismatch=%0d pio=%0d/%0d st=%0d/%0d",T,ns[0],ns[1],np[0],np[1],ng[0],ng[1],done,fc[0],fc[1],mism,pio[0],pio[1],st[0],st[1]);
 if(mism || ns[0]!=(T+3)/4 || ns[1]!=ns[0] || np[0]!=40 || np[1]!=40 || ng[0]!=1 || ng[1]!=1 || done!=3 || fault!=0 || pio[0]!=123 || pio[1]!=123 || st[0]!=0 || st[1]!=0)$fatal(1,"CURRENT_ATT FAIL");
 $display("CURRENT_ATT PASS");$finish;
 end
 always@(posedge clk)if(rst_n)begin
 cycles++;for(integer e=0;e<2;e++)begin
 if(go[e])ng[e]++;
 if(lv[e])begin if(e==0)scores[ns[0]]=ld[0];else if(ns[1]>=ns[0] || ld[1]!==scores[ns[1]])mism++;ns[e]++;end
 if(pv[e])begin if(e==0)words[np[0]]=pd[0];else if(np[1]>=np[0] || pd[1]!==words[np[1]])mism++;np[e]++;end
 if(rq[e][0] || rq[e][341])$fatal(1,"unexpected HBM request");
 end end
endmodule
