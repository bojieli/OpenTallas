`timescale 1ns/1ps
module syscal32_case #(parameter NE=32, AW=$clog2(NE), MUT=0)(output reg done);
  localparam G=NE/16,NB=(NE+31)/32;
  reg ck=0;always #5 ck=~ck;
  reg rn=0,cw=0,st=0,sg=0,ht=0;
  reg [AW:0] ca=0;reg [31:0] cd=0;
  wire av,bv,ar,br,af,bf;
  wire [2:0] ap,bp;wire [3:0] ak,bk;wire [4:0] ab,bb;
  integer checks=0,events=0,passid=0;
  ot_qwen_d2d_cal #(.NE(NE)) gold(.ck(ck),.rst_n(rn),.cfg_we(cw),.cfg_addr(ca),.cfg_data(cd),
    .start(st),.start_seg(sg),.halt(ht),.ev_v(av),.ev_port(ap),.ev_kind(ak),.ev_beat(ab),.running(ar),.fault(af));
  ot_qwen_d2d_cal_sysface32 #(.NE(NE),.MUT(MUT)) dut(.ck(ck),.rst_n({(3+2*G){rn}}),
    .cfg_we(cw),.cfg_addr(ca),.cfg_data_k({NB{cd}}),.cfg_seg_k({(3*G+1){cd[AW-1:0]}}),
    .start_k({(6+2*G){st}}),.halt_k({(6+2*G){ht}}),.seg_k({(4+G){sg}}),
    .ev_v(bv),.ev_port(bp),.ev_kind(bk),.ev_beat(bb),.running(br),.fault(bf));
  always @(posedge ck) begin
    #1;
    if(rn) begin
      checks=checks+1;if(av)events=events+1;
      if({av,ap,ak,ab,ar,af}!=={bv,bp,bk,bb,br,bf})
        $fatal(1,"SYSCAL32_MISMATCH NE=%0d MUT=%0d case=%0d check=%0d gold=%h dut=%h",NE,MUT,passid,checks,{av,ap,ak,ab,ar,af},{bv,bp,bk,bb,br,bf});
    end
  end
  task tick;begin @(negedge ck);end endtask
  task reset;begin rn=0;cw=0;st=0;ht=0;repeat(3)tick();rn=1;repeat(2)tick();end endtask
  task write(input [AW:0] a,input [31:0] d);begin ca=a;cd=d;cw=1;tick();cw=0;end endtask
  task image(input integer mode);
    integer i,dt,rp,bt;reg [31:0] w;
    begin
      for(i=0;i<NE;i=i+1) begin
        dt=(mode==0)?1:1+((i*7+mode)%5);rp=(mode==0)?0:((i+mode)%4);bt=i%16;
        w=(dt<<18)|((i==NE-1)?(1<<17):0)|((i%8)<<14)|(((i+mode)%16)<<10)|(bt<<5)|rp;
        write(i,w);
      end
      write(1<<AW,NE/2);repeat(2)tick();
    end
  endtask
  task play(input integer seg,input integer n);
    begin sg=seg;st=1;tick();st=0;repeat(n)tick();end
  endtask
  integer mode;
  initial begin
    done=0;reset();
    for(mode=0;mode<6;mode=mode+1) begin
      passid=mode;image(mode);play(0,NE*12);play(1,NE*12);
      // Halt/start priority and restart while running, with exact held outputs.
      sg=0;st=1;tick();st=0;tick();st=1;tick();st=0;ht=1;tick();ht=0;
      // Illegal programming while running is ignored and sticky-faulted.
      play(1,1);write(3,32'h12345678);ht=1;st=1;tick();ht=0;st=0;reset();
    end
    passid=7;image(1);
    // Last-entry segment wraps pointer; last stops without consuming wrapped word.
    write(1<<AW,NE-1);repeat(2)tick();play(1,30);
    // cfg_recent start conflict and dt-zero / burst-overrun faults.
    reset();image(0);write(0,32'h0000001f);st=1;tick();st=0;repeat(8)tick();ht=1;tick();ht=0;
    reset();write(0,(1<<18)|(1<<17)|(31<<5)|2);repeat(2)tick();play(0,10);
    $display("SYSCAL32_CASE_PASS NE=%0d MUT=%0d checks=%0d events=%0d",NE,MUT,checks,events);done=1;
  end
endmodule
module tb_qwen_syscal32 #(parameter MUT=0);
  wire a,b,c;
  syscal32_case #(.NE(16),.MUT(MUT)) t16(a);
  syscal32_case #(.NE(32),.MUT(MUT)) t32(b);
  syscal32_case #(.NE(64),.MUT(MUT)) t64(c);
  initial begin wait(a&&b&&c);$display("SYSCAL32_PASS");$finish;end
  initial begin #2000000;$fatal(1,"SYSCAL32_TIMEOUT");end
endmodule
