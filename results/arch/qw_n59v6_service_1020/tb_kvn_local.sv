`timescale 1ns/1ps
module tb_kvn_local #(parameter integer MUT=0);
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,wv=0,sv=0;reg[10:0]tag=0;reg[511:0]data=0;reg[58:0]id=0;reg[1:0]gen=0;
 wire[523:0]a,b;wire[58:0]ai,bi;wire[1:0]ag,bg;wire af,bf;
 qfd_kvn_static_transport refq(.ck(ck),.rst_n(rst_n),.word_v(wv),.word_tag(tag),.word_data(data),.word_identity(id),.word_generation(gen),.slot_v(sv),.word_ctl_pub({10{wv,tag[10:8]}}),.slot_pub({10{sv}}),.x3(a),.x3_identity(ai),.x3_generation(ag),.fault(af));
 qfd_kvn_static_transport #(.LOCAL32(1),.LOCAL_MUT(MUT)) dut(.ck(ck),.rst_n(rst_n),.word_v(wv),.word_tag(tag),.word_data(data),.word_identity(id),.word_generation(gen),.slot_v(sv),.word_ctl_pub({10{wv,tag[10:8]}}),.slot_pub({10{sv}}),.x3(b),.x3_identity(bi),.x3_generation(bg),.fault(bf));
 integer i,j,n=0,checks=0,pops=0,pushes=0,diffs=0;
 initial begin
  repeat(8)@(negedge ck);rst_n=1;
  for(i=0;i<10000;i=i+1)begin
   sv=(n>0)&&((i*7%17)<12);
   wv=(n<2||sv)&&((i*13%23)<16);
   tag={3'b010,8'(i)};id=59'(i*7919+1);gen=2'(i);
   for(j=0;j<16;j=j+1)data[32*j+:32]=32'(i*2654435761+j*65537+1);
   n=n+int'(wv)-int'(sv);pushes+=int'(wv);pops+=int'(sv);
   @(negedge ck);checks++;
   if({a,ai,ag,af}!={b,bi,bg,bf})begin
    diffs++;if(diffs<3)$display("KVN_LOCAL_DIFF i=%0d a=%h b=%h",i,a,b);
   end
  end
  $display("KVN_LOCAL_RESULT MUT=%0d checks=%0d pushes=%0d pops=%0d diffs=%0d fault=%0d/%0d",MUT,checks,pushes,pops,diffs,af,bf);
  if(MUT==0&&diffs==0&&!af&&!bf)$display("KVN_LOCAL_PASS");
  else if(MUT!=0&&diffs>0)$display("KVN_LOCAL_MUTANT_REJECTED");
  else $fatal(1,"KVN_LOCAL_FAIL_OR_SURVIVED");
  $finish;
 end
endmodule
