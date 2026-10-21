`timescale 1ns/1ps
module tb;
    parameter integer MUT=0, AW=4;
    reg wc=0,rc=0,wn=0,rn=0,wr=0,rd=0;
    reg[63:0] wd=0;
    wire gf,go,ge,df,dover,de;
    wire[AW:0] gw,gr,dw,dr;
    wire[63:0] gd,dd,local_valid;
    reg[63:0] gold_capture,dut_capture;reg gold_v=0,dut_v=0;
    integer errors=0,checks=0,write_cycles=0,read_cycles=0;
    reg[63:0] lfsr=64'h123456789abcdef1;
    always #5 wc=~wc;
    always #7 rc=~rc;
    ot_link_afifo #(.W(64),.AW(AW)) gold(
      .wclk(wc),.wrst_n(wn),.wr(wr),.wdata(wd),.wfull(gf),.wfreed(gw),.ovf(go),
      .rclk(rc),.rrst_n(rn),.rd(rd),.rempty(ge),.rdata(gd),.rcount(gr));
    qkc_afifo_bits_1021 #(.W(64),.AW(AW),.MUT_ROTATE(MUT)) dut(
      .wclk(wc),.wrst_n(wn),.wr(wr),.wdata(wd),.wfull(df),.wfreed(dw),.ovf(dover),
      .rclk(rc),.rrst_n(rn),.rd(rd),.rempty(de),.rdata(dd),.rd_valid(local_valid),.rcount(dr));
    always @(posedge rc)if(rd&&!ge)gold_capture<=gd;
    for(genvar b=0;b<64;b=b+1)begin:g_local_capture
      always @(posedge rc)if(rd&&local_valid[b])dut_capture[b]<=dd[b];
    end
    always @(posedge rc or negedge rn)
      if(!rn)begin gold_v<=0;dut_v<=0;end
      else begin gold_v<=rd&&!ge;dut_v<=rd&&!de;end
    task automatic check;
      if(wn&&rn)begin
        checks=checks+1;
        if(gold_v!==dut_v||(gold_v&&gold_capture!==dut_capture))errors=errors+1;
        if({gf,go,ge,gw,gr}!={df,dover,de,dw,dr})begin
          errors=errors+1;if(errors<4)$display("control mismatch t=%0t",$time);
        end
        if(!ge&&gd!==dd)begin
          errors=errors+1;if(errors<4)$display("head mismatch t=%0t gold=%h got=%h",$time,gd,dd);
        end
        // All pointer readiness matches in the equal-SYNC test. Coordinated
        // admission suppresses blocked writes before local ovf; the wrapper
        // preserves the original blocked-write fault on its public ovf.
        if(dut.full_b!=={64{df}}||dut.empty_b!=={64{de}}||(|dut.ovf_b)!==1'b0)errors=errors+1;
      end
    endtask
    always @(negedge wc)begin
      write_cycles=write_cycles+1;check();
      lfsr={lfsr[62:0],lfsr[63]^lfsr[62]^lfsr[60]^lfsr[59]};
      wd=lfsr;wr=wn&&(write_cycles%7!=0);
    end
    always @(negedge rc)begin
      read_cycles=read_cycles+1;check();rd=rn&&(read_cycles%5!=0);
    end
    initial begin
      #43;wn=1;#4;rn=1;
      #10000;wn=0;rn=0;wr=0;rd=0;
      #59;wn=1;rn=1;
      #10000;wn=0;rn=0;wr=0;rd=0;
      #43;wn=1;#4;rn=1;
      #10000;
      if(errors==0&&checks>1000)$display("CX_BITS PASS AW=%0d MUT=%0d checks=%0d cycles_w=%0d cycles_r=%0d delta_cycles=0",AW,MUT,checks,write_cycles,read_cycles);
      else $display("CX_BITS FAIL AW=%0d MUT=%0d errors=%0d checks=%0d",AW,MUT,errors,checks);
      if(errors!=0)$fatal(1,"CX_BITS mismatch");$finish;
    end
endmodule
