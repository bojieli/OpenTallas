`timescale 1ns/1ps
module tb_split_seq_shape;
parameter integer GROUPS=1;
parameter integer BAD_TAG=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0;
reg[3:0] c_v=0;reg[2111:0]c_d=0;wire[3:0]c_cr;
wire a_start, q_valid, kv_v, fault;wire[5:0]q_beat;wire[511:0]q_data;wire[1:0]kv_vg;wire[1023:0]kv_data;
wire[2:0]u_v;wire[1583:0]u_d;
reg[2:0]u_cr=0;reg kv_cr=0;reg ov=0;reg og=0;reg[5:0]ob=0;reg[511:0]od=0;
integer starts=0, qn=0, kn=0, rn=0, errors=0,cyc=0, k,v,g,h,tag,layer;
reg[511:0]expected;
ot_qkvd_kv_seq_split_candidate #(.HEAD_GROUPS(GROUPS)) dut(.clk(clk),.rst_n(rst_n),.c_v(c_v),.c_d(c_d),.c_cr(c_cr),
 .u_v(u_v),.u_d(u_d),.u_cr(u_cr),.a_start(a_start),.a_q_valid(q_valid),.a_q_beat(q_beat),.a_q_data(q_data),
 .a_out_valid(ov),.a_out_g(og),.a_out_beat(ob),.a_out_data(od),.a_hub_fault(1'b0),.a_stk_fault(4'b0),.m_fault(4'b0),
 .d2d_fault(1'b0),.d2d_cause(5'b0),.kvw_v(kv_v),.kvw_vg(kv_vg),.kvw_d(kv_data),.kvw_cr(kv_cr),
 .fault(fault),.emb_req_cr(1'b0),.emb_q_v(1'b0),.emb_q_d(528'b0),.hc_v(1'b0),.hc_d(528'b0),.tok_cr(1'b0));
always @(negedge clk) if(rst_n)begin
 cyc=cyc+1;u_cr=0;kv_cr=0;
 if(a_start)starts=starts+1;
 if(q_valid)begin if(q_beat!==qn%(16*GROUPS) || q_data!=={16{32'(qn%(16*GROUPS)+100)}})errors=errors+1;qn=qn+1;end
 if(kv_v)begin
   tag=GROUPS==1 ? ((kn%(2*GROUPS))*4) : ((kn%(2*GROUPS))*2);
   if(kv_vg!==(tag>>1) || kv_data!=={{16{32'(tag+2)}},{16{32'(tag+1)}}})errors=errors+1;
   kn=kn+1;kv_cr=1;
 end
 if(u_v[0])begin
   if(u_d[511:0]!=={16{32'(rn%(32*GROUPS)+200)}} || u_d[517:512]!==6'(rn%32) || u_d[518]!==1'((rn%(32*GROUPS))/32))errors=errors+1;
   rn=rn+1;u_cr[0]=1;
 end
 if(fault)begin errors=errors+1;$display("SHAPE_FAIL stickyfault");$finish;end
end
task send(input integer cls,input[15:0]t,input[511:0]d);
begin @(posedge clk);#1;c_v=4'b1<<cls;c_d[cls*528+:528]={t,d};@(posedge clk);#1;c_v=0;end endtask
initial begin
 repeat(5)@(posedge clk);#1;rst_n=1;repeat(5)@(posedge clk);
 for(layer=0;layer<2;layer=layer+1)begin
   send(0,16'h1000,512'(4));
   for(v=0;v<2;v=v+1)for(g=0;g<GROUPS;g=g+1)for(h=0;h<2;h=h+1)begin
     tag=v*4+g*2+h;send(2,16'(BAD_TAG&&h==1 ? tag^1:tag),{16{32'(tag+1)}});
   end
   repeat(12)@(posedge clk);
   if(starts!=layer+1)begin $display("SHAPE_FAIL group%0d expectedstart%0d actual%0d",GROUPS,layer+1,starts);$finish;end
   for(k=0;k<16*GROUPS;k=k+1)send(1,16'(k),{16{32'(k+100)}});
   repeat(8)@(posedge clk);
   for(k=0;k<32*GROUPS;k=k+1)begin
     @(posedge clk);#1;ov=1;og=k/32;ob=k%32;od={16{32'(k+200)}};
   end
   @(posedge clk);#1;ov=0;repeat(12)@(posedge clk);
 end
 if(errors==0 && qn==32*GROUPS && kn==4*GROUPS && rn==64*GROUPS)$display("SHAPE_PASS groups=%0d Q=%0d KVrows=%0d RES=%0d cycles=%0d",GROUPS,qn,kn,rn,cyc);
 else $display("SHAPE_FAIL groups=%0d errors=%0d Q=%0d KVrows=%0d RES=%0d",GROUPS,errors,qn,kn,rn);
 $finish;
end
endmodule
