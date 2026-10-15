`timescale 1ns/1ps
module tb_hgi_coll_reduce_static;
 import "DPI-C" function int unsigned f32add(input int unsigned a,input int unsigned b);
 reg clk=0,rst_n=0,clear=0,in_v=0,load_v=0,add_read=0,add_issue=0,pub_read=0,pub_issue=0,pub_bf16=0,pub_release=0;
 reg [544:0] in_flit=0;
 reg [3:0] load_tag=0,read_tag=0,pub_tag_a=0,pub_tag_b=0;
 reg [32:0] pub_meta=0;
 wire out_v,fault;wire [544:0] out_flit;wire [7:0] cause;
 integer cyc=0,checks=0,errors=0,scenario=0,mut=0;
 ot_hgi_coll_reduce_static #(.MUT_TAG(`ifdef MUT_TAG 1 `else 0 `endif),.MUT_BF16(`ifdef MUT_BF16 1 `else 0 `endif)) d(
  .clk_control(clk),.clk_state({16{clk}}),.clk_add({16{clk}}),.rst_n(rst_n),.clear(clear),
  .in_v(in_v),.in_flit(in_flit),.load_v(load_v),.load_tag(load_tag),.add_read(add_read),.read_tag(read_tag),.add_issue(add_issue),
  .pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_bf16(pub_bf16),.pub_meta(pub_meta),.pub_release(pub_release),.pub_issue(pub_issue),
  .out_v(out_v),.out_flit(out_flit),.fault(fault),.fault_cause(cause));
 reg [511:0] data[0:7][0:15],gold[0:7][0:15];
 reg [511:0] result[0:15];
 reg [544:0] want_pub;
 reg want_v;
 function automatic [31:0] sample(input integer groupid,rank,tag,lane);
  reg [31:0] hash;
  begin
   hash=32'h917b23a5^(groupid*32'h3fed92ab)^(rank*32'h18243271)^(tag*32'ha1bfa4c3)^(lane*32'h7b417d93);
   hash=hash^(hash<<13);hash=hash^(hash>>17);hash=hash^(hash<<5);
   // Include cancellation and values spanning exponents, with finite normals.
   sample={hash[31],8'(120+(hash[7:0]%16)),hash[22:0]};
   if(groupid==0 && lane==0)begin
    case(rank)
      0:sample=32'h4b800000;1:sample=32'h3f800000;2:sample=32'hcb800000;3:sample=32'h3f800000;
      default:sample=32'h00000000;
    endcase
   end
  end
 endfunction
 function automatic [511:0] add_gold(input [511:0] a,b);
  begin for(integer l=0;l<16;l=l+1)add_gold[l*32+:32]=f32add(a[l*32+:32],b[l*32+:32]);end
 endfunction
 // Independent integer BF16 reference: upper-half plus exact low-half tie test.
 function automatic [15:0] bf_gold(input [31:0] x);
  reg [15:0] hi,lo;
  begin hi=x[31:16];lo=x[15:0];
   if(x[30:23]==255)bf_gold=hi|((|x[22:0])?16'h40:0);
   else bf_gold=hi+((lo>16'h8000)||((lo==16'h8000)&&hi[0]));
  end
 endfunction
 task defaults;
  begin in_v=0;load_v=0;add_read=0;add_issue=0;pub_read=0;pub_issue=0;clear=0;want_v=0;end
 endtask
 task tick;
  begin #5;clk=1;#1;
   if(out_v!==want_v)begin errors=errors+1;$display("publication edge mismatch cycle%0d",cyc);end
   if(want_v)begin checks=checks+1;if(out_flit!==want_pub)begin errors=errors+1;if(errors<5)$display("payload mismatch cycle%0d got%h want%h",cyc,out_flit,want_pub);end end
   if(scenario==0 && fault)begin errors=errors+1;if(errors<5)$display("unexpected fault cycle%0d cause%h",cyc,cause);end
   #4;clk=0;cyc=cyc+1;
  end
 endtask
 task idle(input integer n);
  begin defaults();repeat(n)tick();end
 endtask
 task load_pair(input integer a,b);
  begin
   for(integer t=0;t<16;t=t+1)begin
    defaults();in_v=1;load_v=1;load_tag=4'(t);in_flit={33'b0,data[a][t]};tick();
   end
   // Consecutive reservations exercise all16 real arithmetic lanes at 1/cycle.
   for(integer t=0;t<17;t=t+1)begin
    defaults();add_issue=t>0;
    if(t<16)begin add_read=1;read_tag=4'(t);in_v=1;in_flit={33'b0,data[b][t]};end
    if(scenario==1 && t==3)in_v=0;
    tick();
   end
   idle(9);
  end
 endtask
 task publish_fp(input integer groupid,node);
  reg [32:0] oldmeta;
  begin
   for(integer t=0;t<17;t=t+1)begin
    defaults();pub_issue=t>0;pub_bf16=0;pub_release=1;
    if(t<16)begin pub_read=1;pub_tag_a=4'(t);pub_tag_b=0;pub_meta=33'(groupid*100+node*16+t);end
    if(t>0)begin want_v=1;want_pub={oldmeta,gold[node][t-1]};end
    tick();
    if(t>0)result[t-1]=out_flit[511:0];oldmeta=pub_meta;
   end
  end
 endtask
 task bf_test;
  reg [511:0] a,b,packed_gold;
  begin
   defaults();clear=1;tick();
   // Both signs, retained even/odd tie, below/above tie, carry into exponent.
   for(integer l=0;l<16;l=l+1)begin
    a[l*32+:32]=32'h3f808000+(l<<16);
    b[l*32+:32]=32'hbf818000+(l<<16);
   end
   defaults();load_v=1;in_v=1;load_tag=0;in_flit={33'b0,a};tick();
   load_tag=1;in_flit={33'b0,b};tick();
   defaults();pub_read=1;pub_tag_a=0;pub_tag_b=1;pub_bf16=1;pub_meta=33'h1abcdef01;pub_release=1;tick();
   for(integer l=0;l<16;l=l+1)begin packed_gold[l*16+:16]=bf_gold(a[l*32+:32]);packed_gold[256+l*16+:16]=bf_gold(b[l*32+:32]);end
   defaults();pub_issue=1;want_v=1;want_pub={33'h1abcdef01,packed_gold};tick();idle(1);
  end
 endtask
 initial begin
  void'($value$plusargs("fault=%d",scenario));void'($value$plusargs("order=%d",mut));
  want_v=0;tick();rst_n=1;idle(2);
  if(scenario>=2)begin
   defaults();
   case(scenario)
    2:begin load_v=1;in_v=0;end // missing ingress
    3:in_v=1; // extra ingress
    4:begin add_read=1;in_v=1;end // unavailable state
    5:pub_read=1; // unavailable publication
    6:add_issue=1; // no prior read
    7:pub_issue=1; // no prior publication read
    8:begin load_v=1;in_v=1;tick();defaults();load_v=1;in_v=1;end // occupied load
    9:begin load_v=1;in_v=1;add_read=1;end // load/read conflict
    10:begin // Read atWBedge forbidden even though new value arrives that edge.
     load_v=1;in_v=1;tick();defaults();add_read=1;in_v=1;tick();defaults();add_issue=1;tick();idle(7);
     defaults();pub_read=1;
    end
    11:begin load_v=1;in_v=1;tick();defaults();add_read=1;in_v=1;tick();defaults();clear=1;end
    12:begin // load/WB same tag leaves data ORed, always faults.
     load_v=1;in_v=1;tick();defaults();add_read=1;in_v=1;tick();defaults();add_issue=1;tick();idle(7);
     defaults();load_v=1;in_v=1;
    end
   endcase
   tick();
   if(!fault)$fatal(1,"missing expected fault scenario%0d",scenario);
   case(scenario)
    2,3:if(!cause[0])$fatal(1,"wrong ingress fault");
    4,5,10:if(!cause[2])$fatal(1,"wrong unavailable fault");
    6,7:if(!cause[1])$fatal(1,"wrong reservation fault");
    8:if(!cause[4])$fatal(1,"wrong occupied fault");
    9,12:if(!cause[3])$fatal(1,"wrong conflict fault");
    11:if(!cause[5])$fatal(1,"wrong clear fault");
   endcase
   defaults();clear=1;tick();if(!fault)$fatal(1,"clear erased sticky fault");
   $display("STATIC_REDUCE FAULT PASS scenario%0d cause%h",scenario,cause);$finish;
  end else begin
   for(integer g=0;g<12;g=g+1)begin
    for(integer r=0;r<8;r=r+1)for(integer t=0;t<16;t=t+1)begin
     for(integer l=0;l<16;l=l+1)data[r][t][l*32+:32]=sample(g,r,t,l);
     gold[r][t]=data[r][t];
    end
    // Golden exact pairwise tree ((0+1)+(2+3))+((4+5)+(6+7)).
    for(integer width=1;width<8;width=width*2)
     for(integer r=0;r<8;r=r+2*width)begin
      for(integer t=0;t<16;t=t+1)gold[r][t]=add_gold(gold[r][t],gold[r+width][t]);
      // Schedule mutant changes first merge partner and must fail exact data.
      load_pair(r,(mut!=0 && width==1 && r==0)?2:r+width);
      publish_fp(g,r);
      for(integer t=0;t<16;t=t+1)data[r][t]=result[t];
     end
   end
   bf_test();
   if(scenario==1)begin
    if(!fault||!cause[0])$fatal(1,"data-drop mutant not detected");
    $display("STATIC_REDUCE FAULT PASS scenario1 cause%h",cause);
   end else if(errors==0 && !fault)$display("STATIC_REDUCE PASS groups12 ranks8 quarterflits16 lanes16 checks%0d cycles%0d nativeLAT8",checks,cyc);
   else $fatal(1,"STATIC_REDUCE FAIL errors%0d cause%h",errors,cause);
   $finish;
  end
 end
endmodule
