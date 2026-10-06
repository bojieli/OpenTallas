`timescale 1ns/1ps
module tb_registered_admission;
    reg clk=0; always #0.4165 clk=~clk;
    reg rst_n=0;
    reg [23:0] addr=0;
    reg re=1;
    reg [31:0] arrived=0;
    wire [31:0] gray=arrived^(arrived>>1);
    reg [191:0] bases=0,lens=0;
    reg [255:0] indices=0;
    reg [15:0] kinds=0;
    wire admit,ref_ok,kv_ok,ref_kv,fault,ref_fault;
    wire [31:0] consumed,ref_consumed;
    ot_qwen_hbmacc_gate_admission #(.OPT(3),.ADMISSION_PIPE(1)) dut(
        .clk(clk),.rst_n(rst_n),.int8_wrom_re(re),.int8_wrom_addr(addr),.me_clk_en(admit),
        .seg_base(bases),.seg_len(lens),.seg_sidx(indices),.seg_kind(kinds),.w_a_gray(gray),
        .me_ok(admit),.kv_ok(kv_ok),.w_c_gray(consumed),.hbm_fault(fault));
    ot_qwen_hbmacc_gate_f12 #(.OPT(3)) ref_gate(
        .clk(clk),.rst_n(rst_n),.int8_wrom_re(re),.int8_wrom_addr(addr),.me_clk_en(admit),
        .seg_base(bases),.seg_len(lens),.seg_sidx(indices),.seg_kind(kinds),.w_a_gray(gray),
        .me_ok(ref_ok),.kv_ok(ref_kv),.w_c_gray(ref_consumed),.hbm_fault(ref_fault));
    integer accepted=0,cycles=0,last_take=-100,epoch=0;
    reg previous_accept=0;
    // Every request is held until the actual pre-edge grant. The next request
    // alternates resident and arriving data; an old grant must never follow it.
    always @(posedge clk) if(rst_n) begin
        cycles=cycles+1;
        if(admit) begin
            if(!ref_ok) $fatal(1,"stale/early grant address=%0d arrived=%0d",addr,arrived);
            if(cycles-last_take<3) $fatal(1,"grant reused after advancing request");
            last_take=cycles; accepted=accepted+1;
            if(accepted%3==0) addr<=24'd1024+accepted;
            else addr<=accepted;
        end
        if(fault!==ref_fault || consumed!==ref_consumed || kv_ok!==ref_kv)
            $fatal(1,"retirement/visibility/source fault contract changed");
    end
    initial begin
        bases[23:0]=0; lens[23:0]=1024; indices[31:0]=0; kinds[1:0]=1;
        bases[47:24]=1024; lens[47:24]=1024; kinds[3:2]=2;
        repeat(5) @(negedge clk); rst_n=1;
        repeat(1000) begin
            @(negedge clk);
            if(cycles%7==0 && arrived<400) arrived=arrived+3;
        end
        if(accepted<100) $fatal(1,"no finite service under supplied arrivals");
        // Reset between SAMPLE/REDUCE and grant must cancel all permission.
        rst_n=0; @(negedge clk); addr=900; arrived=0;
        accepted=0;cycles=0;last_take=-100; rst_n=1;
        repeat(30) @(negedge clk);
        if(accepted!=0) $fatal(1,"reset leaked old grant");
        $display("PASS held request, resident/HBM stalls, accepted retirement, reset; II=3");
        $finish;
    end
endmodule
