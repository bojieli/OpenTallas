`timescale 1ns/1ps
// Compare the real 16 hardened multiplier leaves with the native functional
// port, including all result addresses/masks, fault flags and argmax ordering.
module tb_qfd_slab_hard_port;
    parameter integer MUTANT=0;
    reg ck=0,rst_n=0,v=0;
    always #1 ck=~ck;
    reg [2047:0] data=0;
    reg [1023:0] scales=0;
    reg [112:0] pf=0;
    wire [3:0] we_h,we_r;
    wire [95:0] addr_h,addr_r;
    wire [63:0] mask_h,mask_r;
    wire [2047:0] data_h,data_r;
    wire [50:0] am_h,am_r;
    wire ov_h,ov_r,f_h,f_r;
    wire [2047:0] mutant_data = MUTANT ? {data[2047:32],32'd0} : data;
    ot_qwen_me_spport_w12 #(.W(16),.IL(8),.AW(24),.NW(18),.GT(3072),.SMIN(7),
        .PQ(4),.TREE_LAT(7),.SCALE_LAT(8),.BANDF(1),.TCUT(7),.HARD_MUL(1)) dut (
        .clk(ck),.ck_mul({16{ck}}),.rst_n(rst_n),.pt_id(16'd0),.lv_in(mutant_data),
        .a_v_e2(v),.a_f_e2(pf),.scale_q(scales),.o_we(we_h),.o_addr(addr_h),
        .o_mask(mask_h),.o_data(data_h),.o_ov(ov_h),.am(am_h),.fault(f_h));
    ot_qwen_me_spport_w12 #(.W(16),.IL(8),.AW(24),.NW(18),.GT(3072),.SMIN(7),
        .PQ(4),.TREE_LAT(7),.SCALE_LAT(7),.BANDF(1),.TCUT(7)) refp (
        .clk(ck),.ck_mul({16{ck}}),.rst_n(rst_n),.pt_id(16'd0),.lv_in(data),
        .a_v_e2(v),.a_f_e2(pf),.scale_q(scales),.o_we(we_r),.o_addr(addr_r),
        .o_mask(mask_r),.o_data(data_r),.o_ov(ov_r),.am(am_r),.fault(f_r));
    reg [2212:0] rq_previous;
    reg [50:0] am_previous;
    reg fault_previous;
    integer n,l,bad=0,words=0;
    wire [2212:0] rq_h={ov_h,we_h,addr_h,mask_h,data_h};
    wire [2212:0] rq_r={ov_r,we_r,addr_r,mask_r,data_r};
    initial begin
        repeat(16) @(negedge ck);
        rst_n=1;
        for(n=0;n<600;n=n+1) begin
            @(negedge ck);
            v=(n<560 && n%13!=0);
            pf={1'b1,1'b1,1'b0,1'b0,4'd7,24'(n*16),24'd512,19'(n%8),19'd0,19'd8192};
            for(l=0;l<64;l=l+1) begin
                data[32*l +:32]=32'h3f000000+32'((n*17+l*41)<<12);
                scales[16*l +:16]=16'h3f80+16'(l%7);
            end
            @(posedge ck); #0.1;
            if(n>40) begin
                if(rq_h[2212]!==rq_previous[2212]) bad=bad+1;
                if(ov_h) begin
                    words=words+1;
                    if(rq_h!==rq_previous) bad=bad+1;
                end
                if(am_h!==am_previous || f_h!==fault_previous) bad=bad+1;
            end
            rq_previous=rq_r;am_previous=am_r;fault_previous=f_r;
        end
        if(bad || words<400) $fatal(1,"SLAB_HARD_PORT_FAIL words=%0d bad=%0d",words,bad);
        $display("SLAB_HARD_PORT_PASS 64lanes 16realhardleaves words=%0d",words);$finish;
    end
endmodule
