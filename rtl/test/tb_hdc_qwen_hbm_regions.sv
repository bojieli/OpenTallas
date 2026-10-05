`timescale 1ns/1ps
module tb_hdc_qwen_hbm_regions;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, bind_region=0;
    reg [5:0] layer=0;
    reg [8:0] user_id=0;
    wire valid, fault;
    wire [31:0] layer_code_base, layer_scale_base, qk_norm_base,
        post_tp_base, packed_kv_base, head_code_base, head_scale_base,
        head_norm_base, embed_code_base, embed_scale_base;
    ot_hdc_qwen_hbm_regions dut (.*);
    initial begin
        repeat(2) @(negedge clk); rst_n=1; bind_region=1;
        @(negedge clk); bind_region=0;
        #1;
        if (!valid || fault || layer_code_base!==0 ||
            layer_scale_base!==119439360 || packed_kv_base!==139054720 ||
            embed_code_base!==119597312)
            $fatal(1,"user0/layer0 sector binding failed");
        user_id=282; layer=35; bind_region=1;
        @(negedge clk); bind_region=0;
        #1;
        if (!valid || fault || layer_code_base!==106659840 ||
            layer_scale_base!==119493120 || qk_norm_base!==119521920 ||
            post_tp_base!==119594240 || packed_kv_base!==2809515648 ||
            packed_kv_base+262144>2812500000)
            $fatal(1,"last legal user/layer binding failed code=%0d scale=%0d kv=%0d",
                layer_code_base,layer_scale_base,packed_kv_base);
        user_id=283; bind_region=1;
        @(negedge clk); bind_region=0;
        #1;
        if (valid || !fault) $fatal(1,"over-capacity user did not fault closed");
        $display("PASS Qwen HBM regions 36 layers 283 users 32-bit sectors");
        $finish;
    end
endmodule
