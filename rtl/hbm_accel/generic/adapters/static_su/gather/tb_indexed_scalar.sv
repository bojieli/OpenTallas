`timescale 1ns/1ps
module tb_indexed_scalar;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,preload=0,readback=0;
 reg[23:0]ix=0,base=0,limit=0,dst=0;
 wire[543:0]rq;wire[8991:0]wq;
 wire[8223:0]raw_rr,rr;wire busy,done,fault;
 reg[8991:0]dq=0;reg[543:0]verify_rq=0;
 wire[575:0]status;
 ot_hbm_su_indexed_scalar #(.MUT_INDEX(MUT==1),.MUT_ADDRESS(MUT==2),.MUT_PHASE(MUT==3))dut(
 .clk(clk),.rst_n(rst_n),.start(start),.index_word(ix),.score_base(base),.score_limit(limit),.dest_word(dst),.dyn_mul(24'd1),
 .rr(rr),.rq(rq),.wq(wq),.busy(busy),.done(done),.fault(fault));
 // Actual static register-only tap transport: read n+6 bank output, three
 // return flops, engine sampling at n+11 from its registered request pin.
 reg[8223:0]ret[0:2];reg[8991:0]wr[0:3];integer s;
 always @(posedge clk)begin
  ret[0]<=raw_rr;ret[1]<=ret[0];ret[2]<=ret[1];
  wr[0]<=wq;for(s=1;s<4;s=s+1)wr[s]<=wr[s-1];
 end
 assign rr=ret[2];
 for(genvar q=0;q<4;q=q+1)begin:gq
  localparam RG=q<2?3:5,WG=q<2?1:3;
  for(genvar b=0;b<8;b=b+1)begin:gb
   localparam I=q*8+b;
   wire[RG*257-1:0]brr;
   wire[16:0]brq=readback?verify_rq[I*17+:17]:rq[I*17+:17];
   ot_vms_bank_static #(.RG(RG),.WG(WG))bank(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(q)),
   .rslot_v(1'b1),.rslot(0),.wslot_v(1'b1),.wslot(preload?WG+4:0),
   .rq({{(RG-1)*17{1'b0}},brq}),.rr(brr),.wq({{(WG-1)*281{1'b0}},wr[3][I*281+:281]}),.wq_done(),
   .dq(dq[I*281+:281]),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),
   .eg(),.pq(285'd0),.pr(),.status(status[I*18+:18]));
   assign raw_rr[I*257+:257]=brr[256:0];
  end
 end
 integer c,i,j,errors=0,checks=0,cyc=0,start_c,first_cycles=0;
 integer sel,score,idxadr,destadr,bank;
 reg[255:0]data,expected;
 always @(posedge clk)cyc=cyc+1;
 function automatic integer bankof(input integer adr);bankof=((adr>>16)&3)*8+((adr>>3)&7);endfunction
 task automatic load_sector(input integer adr,input[255:0]payload);
  begin
   @(negedge clk);dq=0;dq[bankof(adr)*281+:281]={1'b1,16'(adr>>3),payload,8'hff};
   @(negedge clk);dq=0;repeat(12)@(negedge clk);
  end
 endtask
 initial begin
  repeat(8)@(negedge clk);rst_n=1;preload=1;
  // Six canonical scalar routes plus32 structural routes spanning all SID/bank.
  for(c=0;c<38;c=c+1)begin
   if(c<6)begin
    base=87360;limit=87744;idxadr=88512+c;destadr=88576+c;
    case(c)0:sel=7;1:sel=1;2:sel=383;3:sel=64;4:sel=128;default:sel=3;endcase
   end else begin
    base=0;limit=262144;sel=((c-6)/8)*65536+((c-6)%8)*8+2;
    idxadr=90000+c;destadr=120000+c;
   end
   score=base+sel;ix=idxadr;dst=destadr;
   // Score sectors have distinct perword values; golden derives from score
   // address independently of the engine's read result.
   for(j=0;j<8;j=j+1)data[j*32+:32]=32'h3e800000+32'((score/8)*8+j);
   load_sector(score,data);
   data={8{32'hdeadbeef}};data[(idxadr%8)*32+:32]=32'(sel);load_sector(idxadr,data);
   expected={8{32'h6f55aa33}};load_sector(destadr,expected);
   preload=0;repeat(10)@(negedge clk);
   start=1;start_c=cyc;@(negedge clk);start=0;
   wait(done);@(negedge clk);
   if(c==0)first_cycles=cyc-start_c;
   if(cyc-start_c!=first_cycles)begin errors=errors+1;$display("variable schedule");end
   repeat(12)@(negedge clk);readback=1;verify_rq=0;
   bank=bankof(destadr);verify_rq[bank*17+:17]={1'b1,16'(destadr>>3)};
   @(negedge clk);verify_rq=0;
   repeat(6)@(negedge clk);
   expected[(destadr%8)*32+:32]=32'h3e800000+32'(score);
   checks=checks+8;
   if(raw_rr[bank*257+256]!==1'b1||raw_rr[bank*257+:256]!==expected)begin
    if(errors<4)$display("ERR case%0d score%0d valid%b got%h expected%h",c,score,raw_rr[bank*257+256],raw_rr[bank*257+:256],expected);errors=errors+1;
   end
   if(fault!==0||status!==0)begin if(errors<4)$display("FAULT case%0d engine%b banks%h",c,fault,status);errors=errors+1;end
   readback=0;repeat(12)@(negedge clk);preload=1;
  end
  if(errors)$fatal(1,"GATHER_NATIVE FAIL checks=%0d errors=%0d",checks,errors);
  $display("GATHER_NATIVE PASS checks=%0d canonical_routes=6 structural_routes=32 banks=32 SRAMs=96 fixed_cycles=%0d",checks,first_cycles);$finish;
 end
endmodule
