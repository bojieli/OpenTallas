`timescale 1ns/1ps
module tb_dsfd_vm_static_fsr_split;
 reg ck=0,rst=0;always #0.417 ck=~ck;
 reg[17:0]v=0;reg[251:0]row=0;reg[89:0]slot=0;reg[2:0]group=0;reg[11:0]av=0;reg[167:0]ar=0;
 wire[31:0]ov,rv;wire[287:0]oa,ra;wire[255:0]ot,rt;wire[3:0]f;wire rf;
 dsfd_vm_static_suhc_fsr_split dut(.ck({4{ck}}),.rst_n({4{rst}}),.i_v(v),.i_row(row),.i_slot(slot),.i_group(group),.i_aux_v(av),.i_aux_row(ar),.o_v(ov),.o_addr(oa),.o_tag(ot),.fault(f));
 dsfd_vm_static_suhc_fsr refdut(.ck(ck),.rst_n(rst),.i_v(v),.i_row(row),.i_slot(slot),.i_group(group),.i_aux_v(av),.i_aux_row(ar),.o_v(rv),.o_addr(ra),.o_tag(rt),.fault(rf));
 integer mode=0,bad=0,checks=0,j,p,a,bank,rr,seed=1;
 always @(posedge ck)if(rst)begin
 #0.01;
 if(ov!==rv||(|f)!==rf)begin bad=bad+1;if(bad<8)$display("VALIDFAULT got%h/%h ref%h/%b",ov,f,rv,rf);end
 for(integer q=0;q<32;q=q+1)if(rv[q])begin
  checks=checks+1;
  if(oa[9*q+:9]!==ra[9*q+:9]||ot[8*q+:8]!==rt[8*q+:8])begin bad=bad+1;if(bad<8)$display("BANK q%0d addr%h/%h tag%h/%h",q,oa[9*q+:9],ra[9*q+:9],ot[8*q+:8],rt[8*q+:8]);end
 end
 end
 initial begin
 if(!$value$plusargs("mode=%d",mode))mode=0;if(!$value$plusargs("seed=%d",seed))seed=1;
 repeat(4)@(negedge ck);rst=1;repeat(5)@(negedge ck);
 for(j=0;j<500;j=j+1)begin
 @(negedge ck);v=0;av=0;group=3'(j%8);
 for(p=0;p<30;p=p+1)begin
  bank=p<18?p: p+2; // Slots18/19 unused;30unique slot/bank pairs.
  a=(j*37+p*13+seed)%512;rr=32*a+(bank^((a%8)<<2));
  if(p<18)begin v[p]=(j%3==0)||((p+j)%4!=0);row[14*p+:14]=14'(rr);slot[5*p+:5]=5'(bank);end
  else begin av[p-18]=(j%3==0)||((p+j)%4!=0);ar[14*(p-18)+:14]=14'(rr);end
 end
 if(j==42&&mode==1)slot[5*2+:5]=7;
 if(j==42&&mode==2)row[14*3+:14]=row[14*2+:14];
 if(j==42&&mode==3)slot[5*3+:5]=slot[5*2+:5];
 end
 @(negedge ck);v=0;av=0;repeat(5)@(negedge ck);
 if(mode==0&&(|f))bad=bad+1;
 if(mode!=0&&!(|f))bad=bad+1;
 $display("FSR_SPLIT %s mode%0d banks%0d fault%h bad%0d",bad==0&&checks>10000?"PASS":"FAIL",mode,checks,f,bad);$finish;
 end
endmodule
