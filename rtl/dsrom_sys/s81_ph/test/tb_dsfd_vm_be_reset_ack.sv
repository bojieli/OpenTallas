`timescale 1ns/1ps
module tb_dsfd_vm_be_reset_ack;
  reg ck=0, cks=0, en=1, ens=1, rn=0, rns=0;
  always #5 if(en) ck=~ck;
  always #4 if(ens) cks=~cks;
  wire a, as_;
  dsfd_vm_be_sl dut(.ck(ck),.cks(cks),.rn_in(rn),.rns_in(rns),
    .o_v(10'b0),.o_d(1280'b0),.o_f(4'b0),.o_o(3'b0),.f_vx(5'b0),.f_wex(5'b0),.f_mx(20'b0),
    .f_v5(1'b0),.f_we5(1'b0),.f_m5s(23'b0),.c_l0r(1'b0),.fe_flt(16'b0),.st_i(40'b0),
    .rst_ack(a),.rst_ack_s(as_));
  task automatic require_down;
    begin if(a!==0 || as_!==0) $fatal(1,"ACK before actual local reset release"); end
  endtask
  task automatic release_epoch;
    begin #43; require_down(); rn=1;rns=1; #160;
      if(a!==1 || as_!==1) $fatal(1,"Actual local reset/CDC rendezvous did not acknowledge");
    end
  endtask
  initial begin
    #1; rn=1;rns=1; #1; rn=0;rns=0;
    release_epoch();
    // A clock stopped throughout a complete reset pulse cannot acknowledge it.
    @(negedge ck);en=0; rn=0;rns=0;#2;require_down();#48;rn=1;rns=1;#40;
    if(a!==0) $fatal(1,"Stopped serial consumer acknowledged unsampled reset");
    en=1;#100;if(a!==0) $fatal(1,"Serial ACK falsely recovered from stale local reset states");
    rn=0;rns=0;release_epoch();
    // The stream clock is independently required, including real FIFO rendezvous.
    @(negedge cks);ens=0;rn=0;rns=0;#50;rn=1;rns=1;#80;
    if(as_!==0) $fatal(1,"Stopped stream consumer acknowledged unsampled reset");
    ens=1;#100;if(as_!==0) $fatal(1,"Stream ACK falsely recovered from stale local reset state");
    rn=0;rns=0;release_epoch();
    $display("BE_RESET_ACK_PASS: stopped serial/stream epochs blocked; complete sampled epochs acknowledged");$finish;
  end
  initial begin #2000;$fatal(1,"timeout");end
endmodule
