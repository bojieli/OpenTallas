`timescale 1ns/1ps
module tb_qwen_tp8_me_provider_dispatch;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, go=0, ws=0, contract_ok=0;
    reg ri=1, ai=1, rr=1, ar=1, rf=0, af=0;
    reg [15:0] rp=0, ap=0;
    wire rg, ag, ready, idle, fault, df; wire [15:0] progress;
    wire descriptor_native, accepted_native;
    wire legacy_ready, legacy_go, legacy_attn_go;
    ot_qwen_tp8_me_provider_dispatch legacy(
      .clk(clk),.rst_n(rst_n),.ctrl_go(go),.ctrl_wsrc(ws),
      .native_contract_ready(contract_ok),.rom_ready(rr),.rom_idle(ri),
      .rom_progress(rp),.rom_fault(rf),.attn_ready(ar),.attn_idle(ai),
      .attn_progress(ap),.attn_fault(af),.rom_go(legacy_go),.attn_go(legacy_attn_go),
      .ctrl_ready(legacy_ready),.ctrl_idle(),.ctrl_progress(),
      .ctrl_fault(),.dispatch_fault());
    ot_qwen_tp8_me_provider_dispatch #(.NATIVE_ATTENTION(1)) dut(
      .clk(clk),.rst_n(rst_n),.ctrl_go(go),.ctrl_wsrc(ws),
      .native_contract_ready(contract_ok),.rom_ready(rr),.rom_idle(ri),
      .rom_progress(rp),.rom_fault(rf),.attn_ready(ar),.attn_idle(ai),
      .attn_progress(ap),.attn_fault(af),.rom_go(rg),.attn_go(ag),
      .ctrl_ready(ready),.ctrl_idle(idle),.ctrl_progress(progress),
      .descriptor_native(descriptor_native),.accepted_provider_native(accepted_native),
      .ctrl_fault(fault),.dispatch_fault(df));
    task check(input bit ok,input string why);
      if (!ok) $fatal(1,"DISPATCH_FAIL %s",why);
    endtask
    initial begin
      #2; rst_n=0; #10; rst_n=1;
      ws=1; #1; check(!ready&&!ag&&!rg,"unbound native provider refused");
      ws=0; go=1; #1; check(rg&&!ag,"ROM accepted only by ROM");
      @(posedge clk); #1; go=0; ri=0; rp=7; ws=1; ap=31;
      #1; check(progress==7&&!ready&&!idle,"NEXT selector cannot steal in-flight ROM progress");
      check(descriptor_native&&!accepted_native,"NEXT wake metadata separate from accepted ROM");
      check(legacy_ready&&!legacy_attn_go,"default retains ROM ready even before idle");
      ri=1; contract_ok=1; go=1; #1; check(ag&&!rg,"native request suppresses ROM");
      @(posedge clk); #1; go=0; ai=0; ap=19; ws=0; rp=111;
      #1; check(progress==19&&!ready&&!idle,"NEXT ROM selector cannot retire native provider");
      check(!descriptor_native&&accepted_native,"accepted native metadata survives NEXT ROM");
      af=1; #1; check(fault,"native fault returned"); af=0;
      ai=1; #1; check(idle&&ready,"drained providers permit next request");
      rr=0; go=1; #1; check(!rg&&!ag,"unready request cannot leak");
      @(posedge clk); #1; go=0; check(df&&fault,"invalid controller issue observed");
      $display("DISPATCH_PASS actual routing/status/refusal observations"); $finish;
    end
endmodule
