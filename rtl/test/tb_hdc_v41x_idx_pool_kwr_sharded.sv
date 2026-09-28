`timescale 1ns/1ps
module tb_hdc_v41x_idx_pool_kwr_sharded;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, su_go=0;
    reg [23:0] row=0;
    reg [7:0] kv_we=0;
    reg [8*24-1:0] kv_waddr=0;
    reg [8*32-1:0] kv_wdata=0;
    wire w_v, fault;
    wire [3:0] w_stack_mask;
    wire [27:0] w_csec,w_ssec;
    wire [511:0] w_codes;
    wire [2:0] w_sslot;
    wire [31:0] w_scales,dbg_keys;
    ot_hdc_v41x_idx_pool_kwr #(.SHARDED(1)) dut (
        .clk(clk),.rst_n(rst_n),.cfg_ik_base(24'd0),.su_go(su_go),
        .i_dst(2'd3),.i_obase(24'd0),.i_orow(row),.i_nout(16'd1),.i_kdim(16'd32),
        .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .w_v(w_v),.w_rdy(1'b1),.w_stack_mask(w_stack_mask),
        .w_csec(w_csec),.w_codes(w_codes),.w_ssec(w_ssec),
        .w_sslot(w_sslot),.w_scales(w_scales),.fault(fault),.dbg_keys(dbg_keys));
    integer errors=0;
    task automatic run_case(input integer r);
        integer i,l,local_row,base;
        begin
            local_row=((r>>6)<<4)|(r&15);
            base=(r>>4)*32*16+(r&15);
            @(negedge clk); row=r; su_go=1;
            @(negedge clk); su_go=0;
            for(i=0;i<32;i=i+8) begin
                kv_we=8'hff;
                for(l=0;l<8;l=l+1) begin
                    kv_waddr[l*24 +: 24]=base+16*(i+l);
                    kv_wdata[l*32 +: 32]=32'h3f80_0000;
                end
                @(negedge clk);
            end
            kv_we=0;
            wait(w_v);
            #1;
            if(fault || w_stack_mask !== (4'b0001 << ((r>>4)&3)) ||
                w_csec !== (1+(local_row>>6))*128+2*(local_row&63) ||
                w_ssec !== (local_row>>3) || w_sslot !== (local_row&7)) begin
                $display("BAD row=%0d mask=%h csec=%0d ssec=%0d slot=%0d",r,w_stack_mask,w_csec,w_ssec,w_sslot);
                errors=errors+1;
            end
            for(i=0;i<128;i=i+1)
                if(w_codes[4*i +: 4] !== (i<32 ? 4'h6 : 4'h0)) errors=errors+1;
            if(w_scales !== 32'h0000_007d) errors=errors+1;
            @(negedge clk);
        end
    endtask
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        run_case(0);run_case(7);run_case(15);run_case(16);
        run_case(31);run_case(32);run_case(47);run_case(48);
        run_case(63);run_case(64);run_case(127);run_case(1023);
        if(dbg_keys!=12) errors=errors+1;
        $display("V41XPOOLKWRSHARD checked=12 errors=%0d keys=%0d",errors,dbg_keys);
        if(errors) $fatal(1,"sharded writer mismatch");
        $finish;
    end
    initial begin #300000; $fatal(1,"V41XPOOLKWRSHARD TIMEOUT"); end
endmodule
