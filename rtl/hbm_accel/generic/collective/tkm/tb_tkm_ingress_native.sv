`timescale 1ns/1ps
module tb_tkm_ingress_native;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;reg rn=0,dv=0,dr=0,pop=0;reg[544:0]flit;reg[7:0]pe=0,consume=0;
 wire permit,fault,decoded,empty,landing;wire[1:0]early;wire[2719:0]heads;wire[31:0]masks;wire[7:0]epoch,occ,taken;wire[2:0]hn;
 reg[2719:0]cache;reg[7:0]base;reg[2:0]count;wire[7:0]offset=consume-base;
 integer checked=0,cycles=0;
 ot_hgi_coll_tkm_lane #(.MUT(MUT),.HEAD_SEAM(1))dut(.clk(clk),.rst_n(rn),.del_valid(dv),.del_reserve(dr),.del_flit(flit),
  .cfg_g(8'd1),.cfg_gbase(8'd0),.cfg_pf(16'd320),.ins_live(1'b1),.tau(83'd0),.sel_take(8'hff),.sel_pop(pop),.sel_epoch(pe),
  .del_permit(permit),.fault(fault),.early_valid(early),.decoded_v(decoded),.decoded_mask(),.head_e(),.head_m(),
  .heads_e(heads),.heads_m(masks),.head_epoch(epoch),.head_n(hn),.taken(taken),.occ(occ),.landing_v(landing),.fifo_empty(empty));
 always @(posedge clk)begin
  cache<=heads;base<=epoch;count<=hn;cycles=cycles+1;
  if(!rn)begin pop<=0;consume<=0;end else begin
   pop<=0;
   if(cycles>16&&offset<4&&offset<count)begin
    for(integer s=0;s<8;s=s+1)begin:check_entry
     reg[31:0]key,id_;reg[10:0]j_;reg nz;reg[84:0]expected;
     id_=32'(checked*8+s);nz=(s==0&&checked%3==0);key=nz?32'h80000000:(32'hbf000000|32'(checked*17+s));j_=11'(checked*8+s);
     expected={1'b0,1'b1,key,~id_,7'h7f,~j_,nz};
     if(cache[680*offset+85*s+:85]!==expected)$fatal(1,"INGRESS_NATIVE FAIL full85 packet=%0d slot=%0d",checked,s);
    end
    pe<=consume;pop<=1;consume<=consume+1'b1;checked=checked+1;
   end
   if(fault)$fatal(1,"INGRESS_NATIVE FAIL fault");
   if(checked==320)begin $display("INGRESS_NATIVE PASS full85entries=2560 packets=320 epoch_wrap=1 cycles=%0d",cycles);$finish;end
   if(cycles>5000)$fatal(1,"INGRESS_NATIVE FAIL timeout checked=%0d",checked);
  end
 end
 initial begin
  repeat(8)@(negedge clk);rn=1;repeat(8)@(negedge clk);
  for(integer f=0;f<320;f=f+1)begin
   while(!permit)@(negedge clk);
   flit=0;flit[544]=1;flit[512+:16]=16'(f);
   for(integer s=0;s<8;s=s+1)begin
    flit[32*s+:32]=(s==0&&f%3==0)?32'h80000000:(32'h3f000000|32'(f*17+s));flit[256+32*s+:32]=32'(f*8+s);
   end
   dv=1;dr=1;@(negedge clk);dv=0;dr=0;
   if(f%11==0)repeat(2)@(negedge clk);
  end
 end
endmodule
