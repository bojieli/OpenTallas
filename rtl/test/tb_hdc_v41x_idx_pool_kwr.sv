`timescale 1ns/1ps
module tb_hdc_v41x_idx_pool_kwr;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,su_go=0;
    reg [15:0] kd=32;
    reg [7:0] kv_we=0;
    reg [8*24-1:0] kv_waddr=0;
    reg [8*32-1:0] kv_wdata=0;
    wire w_v,fault;
    wire [3:0] w_stack_mask;
    wire [27:0] w_csec,w_ssec;
    wire [511:0] w_codes;
    wire [2:0] w_sslot;
    wire [31:0] w_scales,dbg_keys;
    ot_hdc_v41x_idx_pool_kwr dut(
        .clk(clk),.rst_n(rst_n),.cfg_ik_base(24'd0),.i_user_base_sec(28'd0),.su_go(su_go),
        .i_dst(2'd3),.i_obase(24'd0),.i_orow(24'd0),.i_nout(16'd1),.i_kdim(kd),
        .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .w_v(w_v),.w_rdy(1'b1),.w_stack_mask(w_stack_mask),.w_csec(w_csec),.w_codes(w_codes),
        .w_ssec(w_ssec),.w_sslot(w_sslot),.w_scales(w_scales),.fault(fault),.dbg_keys(dbg_keys));
    integer errors=0;
    task automatic run_case(input integer k);
        integer i,l;
        begin
            @(negedge clk);kd=k;su_go=1;
            @(negedge clk);su_go=0;
            for(i=0;i<k;i=i+8) begin
                kv_we=8'hff;
                for(l=0;l<8;l=l+1) begin
                    kv_waddr[l*24 +: 24]=16*(i+l);
                    kv_wdata[l*32 +: 32]=32'h3f80_0000;
                end
                @(negedge clk);
            end
            kv_we=0;
            wait(w_v);
            if(fault || w_stack_mask!=4'hf || w_csec!=28'd128 || w_ssec!=0 || w_sslot!=0)
                errors=errors+1;
            for(i=0;i<128;i=i+1)
                if(w_codes[4*i +: 4] != (i<k ? 4'h6 : 4'h0)) errors=errors+1;
            for(i=0;i<4;i=i+1)
                if(w_scales[8*i +: 8] != (32*i<k ? 8'h7d : 8'h00)) errors=errors+1;
            @(negedge clk);
        end
    endtask
    initial begin
        repeat(3) @(negedge clk);rst_n=1;
        run_case(32);run_case(128);
        if(dbg_keys!=2) errors=errors+1;
        $display("V41XPOOLKWR checked=2 errors=%0d keys=%0d",errors,dbg_keys);
        $finish;
    end
    initial begin #100000;$display("V41XPOOLKWR TIMEOUT");$finish;end
endmodule
