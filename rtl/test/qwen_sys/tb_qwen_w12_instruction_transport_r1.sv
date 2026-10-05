`timescale 1ns/1ps
module tb_qwen_w12_instruction_transport_r1;
    reg clk=0; always #5 clk=~clk;
    reg por=0,warm=0,release_warm=0,drained=0,iv=0,br=0,cr=0,retire=0;
    reg [378:0] iw;
    wire ir,bv,bl,cv,fd,fault,debt; wire [189:0] bd; wire [378:0] cw;
    wire off_ir,off_cv; wire [378:0] off_cw;
    integer checks=0;
    ot_qwen_w12_instruction_transport_r1 #(.ENABLE_TWO_BEAT(1)) dut (
      .clk(clk),.cold_por_n(por),.warm_request(warm),.warm_release(release_warm),.all_copy_drained(drained),
      .in_valid(iv),.in_ready(ir),.in_word(iw),.beat_ready(br),.beat_valid(bv),.beat_last(bl),.beat_data(bd),
      .consumer_valid(cv),.consumer_ready(cr),.consumer_word(cw),.consumer_retire(retire),
      .warm_fence_done(fd),.fault(fault),.accepted_debt(debt));
    ot_qwen_w12_instruction_transport_r1 off_dut (
      .clk(clk),.cold_por_n(por),.warm_request(warm),.warm_release(release_warm),.all_copy_drained(drained),
      .in_valid(iv),.in_ready(off_ir),.in_word(iw),.beat_ready(br),.beat_valid(),.beat_last(),.beat_data(),
      .consumer_valid(off_cv),.consumer_ready(cr),.consumer_word(off_cw),.consumer_retire(retire),
      .warm_fence_done(),.fault(),.accepted_debt());
    task tick; begin @(posedge clk); #1; end endtask
    task check(input bit yes,input string what); begin checks=checks+1; if(!yes) $fatal(1,"%s",what); end endtask
    task boot; begin @(negedge clk);por=0;iv=0;br=0;cr=0;retire=0;warm=0;release_warm=0;drained=0;tick;@(negedge clk);por=1;tick;end endtask
    task accept(input [378:0] v);begin @(negedge clk);iw=v;iv=1;check(ir,"ready before accept");tick;@(negedge clk);iv=0;iw=~v;end endtask
    reg [378:0] wanted;
    reg [189:0] held;
    integer b;
    initial begin
      wanted={189'h13579,190'habcdef};boot;accept(wanted);
      held=bd;repeat(4)begin tick;check(bv&&!bl&&bd===held&&debt&&!ir,"held first beat");end
      @(negedge clk);warm=1;tick;check(debt&&!fd&&!ir,"warm retains accepted debt");
      @(negedge clk);warm=0;br=1;tick;check(bv&&bl,"second beat");
      @(negedge clk);br=0;repeat(3)begin tick;check(debt&&!fd&&!cv,"held second beat");end
      @(negedge clk);br=1;tick;check(cv&&cw===wanted&&!fd,"complete exact instruction only");
      @(negedge clk);br=0;repeat(3)begin tick;check(cv&&cw===wanted&&!fd,"consumer backpressure");end
      @(negedge clk);cr=1;tick;check(debt&&!cv&&!fd,"accept retains retirement debt");
      @(negedge clk);cr=0;drained=1;repeat(3)begin tick;check(debt&&!fd,"allcopies alone cannot retire accepted work");end
      @(negedge clk);retire=1;tick;check(!debt&&fd&&!fault,"exact retirement then warm fence");
      @(negedge clk);retire=0;release_warm=1;tick;check(ir&&!fd,"release warm fence");
      @(negedge clk);release_warm=0;retire=1;tick;check(fault,"duplicate retirement refused");
      boot;accept(wanted);@(negedge clk);release_warm=1;tick;check(fault&&debt,"premature reset release retains debt");
      boot;accept(wanted);@(negedge clk);dut.g_selected.q0[0]=~dut.g_selected.q0[0];br=1;
      tick;tick;check(cv&&cw===wanted&&!fault,"single mutable FIFO fault corrected");
      boot;accept(wanted);@(negedge clk);dut.g_selected.q0[0]=~dut.g_selected.q0[0];dut.g_selected.q0[1]=~dut.g_selected.q0[1];
      tick;check(fault&&debt&&!bv&&!cv,"double mutable FIFO fault refuses without debt discard");
      boot;accept(wanted);@(negedge clk);br=1;tick;
      @(negedge clk);br=0;dut.g_selected.assembly[0]=~dut.g_selected.assembly[0];dut.g_selected.assembly[1]=~dut.g_selected.assembly[1];
      tick;check(fault&&debt&&!bv&&!cv,"assembly fault cannot be laundered by second-beat encode");
      boot;accept(wanted);@(negedge clk);retire=1;tick;
      check(fault&&debt,"early retire retains accepted instruction");
      boot;accept(wanted);@(negedge clk);dut.g_selected.control[0]=~dut.g_selected.control[0];dut.g_selected.control[1]=~dut.g_selected.control[1];
      tick;tick;check(fault&&debt&&!ir&&!fd,"bad control decode preserves quarantine across re-encode");
      boot;accept(wanted);@(negedge clk);por=0;tick;check(!debt&&!cv,"cold reset invalidates interrupted instruction");
      boot;
      for(b=0;b<379;b=b+1) begin
        wanted=379'b1<<b;accept(wanted);
        @(negedge clk);br=1;tick;tick;
        check(cv&&cw===wanted&&!fault,"all packed bit positions survive the two-beat boundary");
        @(negedge clk);br=0;cr=1;tick;
        @(negedge clk);cr=0;retire=1;tick;
        @(negedge clk);retire=0;
      end
      @(negedge clk);iw={379{1'b1}};iv=1;cr=1;#1;
      check(off_ir&&off_cv&&off_cw===iw,"default-off exact combinational original path");
      $display("PASS_QWEN_W12_TWO_BEAT checks=%0d warm_debt_preserved=1",checks);$finish;
    end
endmodule
