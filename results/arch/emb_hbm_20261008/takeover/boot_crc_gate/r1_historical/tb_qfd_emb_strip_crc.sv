`timescale 1ns/1fs
module tb_qfd_emb_strip_crc;
 parameter integer TWIN=0;
 reg clk=0;always #0.4166666665 clk=~clk;reg rst_n=0,i_v=0;reg[522:0]i_d=0;
 reg[31:0]s_cr=0;reg[31:0]e_v=0;reg[8255:0]e_d=0;
 wire cr0,cr1,cr2,ov0,ov1,ov2;wire[522:0]od0,od1,od2;reg oc0=0,oc1=0,oc2=0;
 wire[31:0]sm0,sm1,sm2,wm0,wm1,wm2;wire sw0,sw1,sw2;wire[4:0]sb0,sb1,sb2,sc0,sc1,sc2;wire[18:0]sr0,sr1,sr2;wire[255:0]wd0,wd1,wd2;
 wire f0,f1,f2;wire[7:0]fc0,fc1,fc2;wire[31:0]ce0,ce1,ce2,ue0,ue1,ue2;
 ot_qfd_emb_strip #(.TWIN(TWIN))original(.clk(clk),.rst_n(rst_n),.i_v(i_v),.i_d(i_d),.i_cr(cr0),.o_v(ov0),.o_d(od0),.o_cr(oc0),.s_m(sm0),.s_we(sw0),.s_bank(sb0),.s_col(sc0),.s_row(sr0),.s_cr(s_cr),.w_m(wm0),.w_d(wd0),.e_v(e_v),.e_d(e_d),.fault(f0),.fault_code(fc0),.ce_cnt(ce0),.ue_info(ue0));
 ot_qfd_emb_strip_crc #(.TWIN(TWIN),.CRC_PIPE(0))disabled(.clk(clk),.rst_n(rst_n),.i_v(i_v),.i_d(i_d),.i_cr(cr1),.o_v(ov1),.o_d(od1),.o_cr(oc1),.s_m(sm1),.s_we(sw1),.s_bank(sb1),.s_col(sc1),.s_row(sr1),.s_cr(s_cr),.w_m(wm1),.w_d(wd1),.e_v(e_v),.e_d(e_d),.fault(f1),.fault_code(fc1),.ce_cnt(ce1),.ue_info(ue1));
 ot_qfd_emb_strip_crc #(.TWIN(TWIN),.CRC_PIPE(1))enabled(.clk(clk),.rst_n(rst_n),.i_v(i_v),.i_d(i_d),.i_cr(cr2),.o_v(ov2),.o_d(od2),.o_cr(oc2),.s_m(sm2),.s_we(sw2),.s_bank(sb2),.s_col(sc2),.s_row(sr2),.s_cr(s_cr),.w_m(wm2),.w_d(wd2),.e_v(e_v),.e_d(e_d),.fault(f2),.fault_code(fc2),.ce_cnt(ce2),.ue_info(ue2));
 reg[319:0]messages[0:255];reg[31:0]expected=0;integer issued=0,statuses=0,cycles=0;
 always @(negedge clk)if(rst_n)begin
 s_cr=sm0;oc0=ov0;oc1=ov1;oc2=ov2;
 if({cr0,ov0,sm0,wm0,sw0,sb0,sc0,sr0,wd0,f0,fc0,ce0,ue0,original.csum,original.wcnt}!=={cr1,ov1,sm1,wm1,sw1,sb1,sc1,sr1,wd1,f1,fc1,ce1,ue1,disabled.csum,disabled.wcnt})$fatal(1,"CRC_PIPE0 changed cycle");
 if(ov0 && od0!==od1)$fatal(1,"disabled status changed");
 if({sm0,wm0,sw0,sb0,sc0,sr0,wd0}!=={sm2,wm2,sw2,sb2,sc2,sr2,wd2})$fatal(1,"enabled commandcyclechanged");
 if(f0||f1||f2)$fatal(1,"strip fault");
 if(|wm2)issued=issued+1;
 if(ov2)begin statuses=statuses+1;if(od2[63:32]!==expected||od2[31:0]!==32'd256)$fatal(1,"status checksum/count mismatch %h %h",od2[63:32],expected);end
 end
 always @(posedge clk)if(rst_n)begin cycles<=cycles+1;if(cycles>3000)$fatal(1,"finite strip gate incomplete");end
 integer i;initial begin
 $readmemh("boot_messages.mem",messages);repeat(4)@(posedge clk);@(negedge clk);rst_n=1;
 for(i=0;i<256;i=i+1)begin
 @(posedge clk);i_d={1'b1,2'd1,239'd0,messages[i][287:32],messages[i][24:0]};i_v=1;
 @(posedge clk);i_v=0;
 wait(cr0);expected=expected+messages[i][319:288];
 end
 @(posedge clk);i_d={1'b1,2'd2,520'd0};i_v=1;@(posedge clk);i_v=0;
 repeat(25)@(posedge clk);
 if(statuses!=1||issued!=256*(TWIN+1)||enabled.csum!==expected)$fatal(1,"strip final counters/status");
 $display("PASS original cycleexact CRC_PIPE0, CRC_PIPE1 boot commands256 checksum=%h TWIN=%0d actual833.333333ps",expected,TWIN);$finish;
 end
endmodule
