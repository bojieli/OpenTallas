`timescale 1ns/1ps
// Current dsdv_svc_att API, two exact SRAM_MACRO=1 shares, differing only NTP and compiled PO/PVO.
// Actual locally-owned selected-row HBM replies; independent finite per-PC queues and all16 offset codes.
module tb_attn1_current_att;
 reg clk=0; always #0.5 clk=~clk;
 reg raw=0,qv=0;wire rst_n;reg[10:0]lp11;reg[1:0]early2;
 always@(posedge clk)begin lp11<={lp11[9:0],raw};early2<={early2[0],raw};end
 dsdv_svc_rs_rl u_actual_rl(.ck(clk),.rst(lp11[10]),.sid(4'd0),.rn(rst_n)); reg [511:0] qd[0:1];
 wire [1:0] lv,pv,done,fault,go; wire[2131:0]ld[0:1]; wire[512:0]pd[0:1];
 wire[31:0]fc[0:1]; wire[15:0]pio[0:1],pvo[0:1],jc[0:1];wire[1:0]st[0:1];wire[681:0]rq[0:1];
 integer copy_checks=0;
 always @(negedge clk) if(rst_n) begin
  copy_checks=copy_checks+1;
  if(E[1].DUT.u.reset_leaf132 !== {132{rst_n}})$fatal(1,"actual profile reset leaf age");
  if(E[1].DUT.u.u_core.pv_v_reps !== {9{E[1].DUT.u.u_core.pv_v}}) $fatal(1,"PV valid replicas differ");
 end
 integer T=46,seed=1,ns[0:1],np[0:1],ng[0:1],mism=0,cycles=0;
 reg [1:0] qrk_reply[0:1],qrv_reply[0:1]; reg [33:0] tag_reply[0:1];
 integer scale_reads[0:1],local_reads[0:1],single_reads[0:1],double_reads[0:1];
 reg[511:0]data_reply[0:1];reg[7:0]beat_reply[0:1];reg[15:0]seen_codes[0:1];
 localparam integer QDEPTH=128,SB_IMAGE=4096;
 reg[29:0]req_addr[0:1][0:1][0:QDEPTH-1];reg[16:0]req_tag[0:1][0:1][0:QDEPTH-1];
 reg[3:0]req_len[0:1][0:1][0:QDEPTH-1];integer qhead[0:1][0:1],qtail[0:1][0:1],qbeat[0:1][0:1];
 function automatic[255:0]image_sector(input[29:0]addr,input[16:0]tag_);
  reg[2303:0]block_;integer block_id,sector_,r,x;
  begin
   if(tag_[16:15]==2'd1)image_sector={32{8'd127}};
   else begin
    block_id=(32'(addr)-SB_IMAGE)/9;sector_=(32'(addr)-SB_IMAGE)%9;block_=0;
    for(r=0;r<16;r=r+1)begin
     for(x=0;x<32;x=x+1)block_[144*r+4*x+:4]=4'(7*block_id+3*r+x);
     block_[144*r+128+:16]=16'h7f7f;
    end
    image_sector=block_[256*sector_+:256];
   end
  end
 endfunction
 // WIN_LOAD fetches two scale metadata sectors on each PC even for zero window rows.
 // The fixture's HBM image has WB0 sectors64/65 filled with UE8M0 scale127.
 // Return exactly one credit and one tagged read response per real request.
 reg [2131:0]scores[0:159];reg[512:0]words[0:39];
 for(genvar e=0;e<2;e++)begin:E
 if(e==0) begin:REF
 dsdv_svc_att_ref #(.SRAM_MACRO(1),.DIE_ID(0),.ST(1),.NTP(0)) u(
 .clk(clk),.rst_n(rst_n),.sid(4'd0),.tile(4'd0),.gd(8'd4),.pvs(8'd0),.root(1'b0),
 .q_v(qv),.q_d(qd[e]),.hw_v(1'b0),.hw_d(291'd0),.qrq(rq[e]),.qrk(qrk_reply[e]),.qwd(2'd0),.qrv(qrv_reply[e]),
 .qr_data(data_reply[e]),.qr_tag(tag_reply[e]),.qr_beat(beat_reply[e]),.l_v(lv[e]),.l_d(ld[e]),.pv_ov(pv[e]),.pv_od(pd[e]),
 .sm_st(),.sm_kind(),.sm_jid(),.sm_rv(),.sm_rp(),.sm_rj(),.sm_rd(),.go_o(go[e]),.tjob_o(),.done(done[e]),.tagj(),
 .hcr(),.hack(),.fault(fault[e]),.fault_code(fc[e]),.pio_o(pio[e]),.pvo_o(pvo[e]),.jc_o(jc[e]),.st_o(st[e]));
 end else begin:DUT
 dsdv_svc_att_reset9 #(.SRAM_MACRO(1),.DIE_ID(0),.ST(1),.NTP(1),.PMEM(1),.QMEM_SRAM(0)) u(
 .clk(clk),.rst_n(rst_n),.reset_early9(early2[1]),.sid(4'd0),.tile(4'd0),.gd(8'd4),.pvs(8'd0),.root(1'b0),
 .q_v(qv),.q_d(qd[e]),.hw_v(1'b0),.hw_d(291'd0),.qrq(rq[e]),.qrk(qrk_reply[e]),.qwd(2'd0),.qrv(qrv_reply[e]),
 .qr_data(data_reply[e]),.qr_tag(tag_reply[e]),.qr_beat(beat_reply[e]),.l_v(lv[e]),.l_d(ld[e]),.pv_ov(pv[e]),.pv_od(pd[e]),
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
 for(integer e=0;e<2;e++)begin
 qrk_reply[e]=0;qrv_reply[e]=0;tag_reply[e]=0;data_reply[e]=0;beat_reply[e]=0;
 scale_reads[e]=0;local_reads[e]=0;single_reads[e]=0;double_reads[e]=0;seen_codes[e]=0;
 for(integer pc=0;pc<2;pc++)begin qhead[e][pc]=0;qtail[e][pc]=0;qbeat[e][pc]=0;end
 end
 void'($value$plusargs("t=%d",T));void'($value$plusargs("seed=%d",seed));void'($urandom(seed));
 if(T<1 || T>512)$fatal(1,"selected-row test supports1..512");
 repeat(6)@(negedge clk);raw=1;wait(rst_n);repeat(6)@(negedge clk);
 sp=0;sp[32]=1;sp[31:30]=0;both(hdr(12,0,sp)); // dynamic CFG overrides parameter ST1
 sp=0;sp[29:0]=30'(SB_IMAGE);sp[98:89]=10'(T);both(hdr(2,0,sp));
 sp=0;sp[19:10]=10'(T);both(hdr(7,12'((T+15)/16),sp));
 for(i=0;i<(T+15)/16;i++)begin word_=0;for(j=0;j<16;j++)word_[32*j+:32]=(32'(16*i+j)<<9)|((32'(16*i+j)%2)<<8)|(32'(16*i+j)%16);both(word_);end
 for(k=0;k<2;k++)begin sp=0;sp[448]=k[0];both(hdr(1,128,sp));for(i=0;i<128;i++)begin
 word_=0;for(j=0;j<32;j++)word_[16*j+:16]={1'b0,5'd14,10'($urandom)};both(word_);end end
 // Locally-owned selected rows are fetched through actual HBM requests; no ROWS injection.
 // All P words are loaded before GO; production FIFO read and frame parsing remain active.
 both(hdr(5,12'((T+1)/2),0));for(i=0;i<(T+1)/2;i++)begin word_=0;
 for(j=0;j<32;j++)word_[16*j+:16]={1'b0,5'd12,10'($urandom)};both(word_);end
 repeat(32)begin @(negedge clk);qv=0;end
 sp=0;sp[15:0]=300;sp[31:16]=1600;sp[47:32]=123;a=hdr(13,0,sp);
 sp[15:0]=800;sp[31:16]=2600;b=hdr(13,0,sp);send(a,b);@(negedge clk);qv=0;
 repeat(4000)@(negedge clk);
 $display("FMEM_PV_VALID_COPIES checks=%0d",copy_checks);
 $display("CURRENT_ATT T=%0d SRAM=1 NTP=0/1 scores=%0d/%0d pv_words=%0d/%0d go=%0d/%0d done=%b faults=%h/%h mismatch=%0d pio=%0d/%0d st=%0d/%0d",T,ns[0],ns[1],np[0],np[1],ng[0],ng[1],done,fc[0],fc[1],mism,pio[0],pio[1],st[0],st[1]);
 if(mism || ns[0]!=(T+3)/4 || ns[1]!=ns[0] || np[0]!=40 || np[1]!=40 || ng[0]!=1 || ng[1]!=1 || done!=3 || fault!=0 || pio[0]!=123 || pio[1]!=123 || st[0]!=0 || st[1]!=0 || scale_reads[0]!=4 || scale_reads[1]!=4)$fatal(1,"CURRENT_ATT FAIL");
 for(integer e=0;e<2;e++)begin
  if(local_reads[e]!=T || single_reads[e]+double_reads[e]!=T)$fatal(1,"local selected read count");
  if(T>=16&&seen_codes[e]!=16'hffff)$fatal(1,"missing offset code");
  for(integer pc=0;pc<2;pc++)if(qhead[e][pc]!=qtail[e][pc]||qbeat[e][pc]!=0)$fatal(1,"undrained real HBM response queue");
  $display("LOCAL_HBM e=%0d reads=%0d single=%0d double=%0d codes=%h",e,local_reads[e],single_reads[e],double_reads[e],seen_codes[e]);
 end
 $display("CURRENT_ATT PASS");$finish;
 end
 always@(posedge clk)if(rst_n)begin
 cycles++;for(integer e=0;e<2;e++)begin
 if(go[e])ng[e]++;
 if(lv[e])begin if(e==0)scores[ns[0]]=ld[0];else if(ns[1]>=ns[0] || ld[1]!==scores[ns[1]])mism++;ns[e]++;end
 if(pv[e])begin if(e==0)words[np[0]]=pd[0];else if(np[1]>=np[0] || pd[1]!==words[np[1]])mism++;np[e]++;end
 for(integer pc=0;pc<2;pc++)begin
   qrk_reply[e][pc]<=rq[e][341*pc];qrv_reply[e][pc]<=0;
   if(rq[e][341*pc])begin
     reg[340:0]request_;reg[16:0]tag_;reg[29:0]addr_;integer n;
     request_=rq[e][341*pc+:341];tag_=request_[52:36];addr_=request_[31:2];n=qtail[e][pc]%QDEPTH;
     if(request_[1]||!(request_[35:32] inside {4'd1,4'd2}))$fatal(1,"illegal HBM read");
     if(qtail[e][pc]-qhead[e][pc]>=QDEPTH)$fatal(1,"finite HBM queue overflow");
     if(tag_[16:15]==2'd1)begin
       if(!(addr_ inside {30'd64,30'd65})||request_[35:32]!=1)$fatal(1,"illegal scale request");scale_reads[e]++;
     end else if(tag_[16:15]==2'd2)begin
       integer code_,off_,block_;
       code_=int'(tag_[13:10]);off_=(code_*144)%256;block_=int'(tag_[9:0]);
       if(addr_!=30'(SB_IMAGE+9*block_+(code_*144)/256)||request_[35:32]!=(off_+144>256?2:1))$fatal(1,"illegal selected descriptor/sector request");
       if(pc!=(block_%2))$fatal(1,"selected descriptor wrong PC");
       local_reads[e]++;seen_codes[e][code_]=1;
       if(request_[35:32]==1)single_reads[e]++;else double_reads[e]++;
     end else $fatal(1,"unexpected HBM kind");
     req_addr[e][pc][n]=addr_;req_tag[e][pc][n]=tag_;req_len[e][pc][n]=request_[35:32];qtail[e][pc]++;
   end
   if(qhead[e][pc]<qtail[e][pc])begin
     integer n;n=qhead[e][pc]%QDEPTH;
     qrv_reply[e][pc]<=1;tag_reply[e][17*pc+:17]<=req_tag[e][pc][n];beat_reply[e][4*pc+:4]<=4'(qbeat[e][pc]);
     data_reply[e][256*pc+:256]<=image_sector(req_addr[e][pc][n]+30'(qbeat[e][pc]),req_tag[e][pc][n]);
     if(qbeat[e][pc]+1==int'(req_len[e][pc][n]))begin qhead[e][pc]++;qbeat[e][pc]=0;end else qbeat[e][pc]++;
   end

 end
 end end
endmodule
