`timescale 1ns/1ps
module tb_d2d_calendar_prefetch;
  reg ck=0; always #0.5 ck=~ck;
  reg rst_n=0,cfg_we=0,start=0,seg=0;
  reg [2:0] addr=0; reg [31:0] data=0;
  wire ev,running,fault;wire[2:0]port;wire[3:0]kind;wire[4:0]beat;
  integer errs=0,n=0,age;
  ot_qwen_d2d_cal #(.NE(4),.AW(2)) dut(.ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(addr),.cfg_data(data),
    .start(start),.start_seg(seg),.halt(1'b0),.ev_v(ev),.ev_port(port),.ev_kind(kind),.ev_beat(beat),.running(running),.fault(fault));
  task write_word(input[2:0]a,input[31:0]d);
    begin @(negedge ck);cfg_we=1;addr=a;data=d;@(negedge ck);cfg_we=0;end
  endtask
  task run_segment(input bit which);
    begin
      @(negedge ck);start=1;seg=which;@(negedge ck);start=0;
      for(age=1;age<=9;age=age+1)begin
        @(posedge ck);#0.01;
        if(ev)begin
          n=n+1;
          if(which)begin if(age!=6||port!=2||kind!=7||beat!=4)errs=errs+1;end
          else if(age<2||age>4||port!=3||kind!=5||beat!=age+1)errs=errs+1;
        end else if(which ? age==6 : (age>=2&&age<=4))errs=errs+1;
        if(fault)errs=errs+1;
      end
    end
  endtask
  initial begin
    repeat(3)@(negedge ck);rst_n=1;
    write_word(0,(2<<18)|(1<<17)|(3<<14)|(5<<10)|(3<<5)|2);
    write_word(1,(6<<18)|(1<<17)|(2<<14)|(7<<10)|(4<<5));
    write_word(4,1);repeat(3)@(negedge ck);
    run_segment(0);run_segment(1);
    if(n!=4)errs=errs+1;
    // A start on the first edge after the last config write fails immediately.
    @(negedge ck);cfg_we=1;addr=4;data=1;
    @(negedge ck);cfg_we=0;start=1;
    @(posedge ck);#0.01;if(!fault)errs=errs+1;
    $display("calendar first-entry prefetch: events=%0d errors=%0d settle_fault=%b",n,errs,fault);
    if(errs==0)$display("CAL_PREFETCH_PASS");else $fatal(1,"CAL_PREFETCH_FAIL");
    $finish;
  end
  initial begin #100;$fatal(1,"CAL_PREFETCH_TIMEOUT");end
endmodule
