`timescale 1ns/1ps
module tb_qwen_tp8_attn_vm_commit;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,start=0,rv=0,vr=0,cv=0;
    reg [15:0] epoch=16'h51,re=16'h51,ce=16'h51;
    reg [5:0] layer=3,rl=3,cl=3;
    reg [4:0] rb=0,cb=0; reg [511:0] rd=0;
    wire rr,vv,done,fault; wire [23:0] addr; wire [511:0] data;
    wire [4:0] beat; wire [15:0] ve; wire [5:0] vl,count;
    ot_qwen_tp8_attn_vm_commit dut(.clk(clk),.rst_n(rst_n),.start(start),.epoch(epoch),.layer(layer),
      .res_valid(rv),.res_ready(rr),.res_beat(rb),.res_data(rd),.res_epoch(re),.res_layer(rl),
      .vm_valid(vv),.vm_ready(vr),.vm_word_addr(addr),.vm_data(data),.vm_beat(beat),.vm_epoch(ve),.vm_layer(vl),
      .commit_valid(cv),.commit_beat(cb),.commit_epoch(ce),.commit_layer(cl),
      .done(done),.fault(fault),.committed_words(count));
    task tick; @(posedge clk); #1; endtask
    task check(input bit ok,input string why); if(!ok) $fatal(1,"COMMIT_FAIL %s",why); endtask
    integer b,neg; reg [511:0] expected;
    initial begin
      neg=0; if($value$plusargs("NEG=%d",neg)) begin end
      #12; rst_n=1; start=1; tick();start=0;
      for(b=0;b<32;b=b+1) begin
        rb=b; rd={16{32'h01234000+b}}; expected=rd; rv=1;
        #1; check(rr,"ordered result ready");tick();rv=0;
        rd=0; check(vv&&data==expected&&addr==3167+b&&ve==epoch&&vl==layer,"registered actual VM payload/address/tag");
        tick(); check(vv&&data==expected&&!done&&count==b,"VM request held until ready");
        vr=1; tick(); vr=0;
        check(!vv&&!done&&count==b&&!rr,"issue is not receiver commit");
        tick(); check(!done&&count==b,"delayed commit keeps barrier closed");
        cb=b; cv=1; if(neg==1&&b==31) ce=epoch+1;
        tick(); cv=0;
        if(neg==1&&b==31) begin check(fault&&!done&&count==31,"wrong epoch does not release barrier");
          $display("COMMIT_NEGATIVE_PASS wrong epoch rejected after31real commits");$finish;end
        check(!fault&&count==b+1,"exact committed word count");
      end
      check(done&&count==32,"all32 receiver commits release barrier");
      $display("COMMIT_PASS 32 exact registered payloads and delayed receiver commits"); $finish;
    end
endmodule
