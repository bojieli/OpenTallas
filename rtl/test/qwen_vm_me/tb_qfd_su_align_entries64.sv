`timescale 1ns/1ps
module tb_qfd_su_align_entries64;
    parameter integer MUT=0;
    reg clk=0; always #0.5 clk=~clk;
    reg rst_n=0;
    reg [6143:0] vm_q;
    reg [4095:0] crom_q;
    reg [2047:0] emb_q;
    reg [63:0] emb_sel;
    reg [191:0] vm_mask;
    wire [6143:0] dut_v,ref_v,ref_new;
    wire [4095:0] dut_c,ref_c;
    wire [2047:0] dut_e,ref_e;
    wire [63:0] dut_s,ref_s;
    wire [191:0] ref_mask;
    reg [6143:0] ref_hold;
    wire [6143:0] fault_v=MUT==1?{vm_q[2047:0],vm_q[6143:2048]}:vm_q;
    ot_qfd_su_align_entries64 #(.ML(MUT==2?14:15)) dut(
        .clk_g0(clk), .clk_g1(clk), .clk_g2(clk), .clk_g3(clk), .clk_g4(clk), .clk_g5(clk), .clk_g6(clk), .clk_g7(clk), .clk_g8(clk), .clk_g9(clk), .clk_g10(clk), .clk_g11(clk), .clk_g12(clk), .clk_g13(clk), .clk_g14(clk), .clk_g15(clk),
        .rst_n(rst_n),.vm_q(fault_v),.crom_q(crom_q),.emb_q(emb_q),.emb_sel(emb_sel),.vm_mask(vm_mask),
        .vm_eff(dut_v),.crom_m(dut_c),.emb_m(dut_e),.emb_sel_m(dut_s));
    ot_hdc_delay #(.W(6144),.D(8)) r_vm(.clk(clk),.rst_n(rst_n),.d(vm_q),.q(ref_new));
    ot_hdc_delay #(.W(4096),.D(11)) r_cr(.clk(clk),.rst_n(rst_n),.d(crom_q),.q(ref_c));
    ot_hdc_delay #(.W(2112),.D(15)) r_em(.clk(clk),.rst_n(rst_n),.d({emb_sel,emb_q}),.q({ref_s,ref_e}));
    ot_hdc_delay #(.W(192),.D(15),.RESET(1)) r_mk(.clk(clk),.rst_n(rst_n),.d(vm_mask),.q(ref_mask));
    genvar j;
    generate for(j=0;j<192;j=j+1) begin:g_hold
        assign ref_v[j*32+:32]=ref_mask[j]?ref_new[j*32+:32]:ref_hold[j*32+:32];
    end endgenerate
    always @(posedge clk) ref_hold<=ref_v;
    integer n,k,checks=0,errors=0,resets=0;
    reg [31:0] seed=32'h12345;
    function [31:0] next_random;
        input [31:0] a;
        begin next_random=(a^32'h9e3779b9)*32'd1664525+32'd1013904223; end
    endfunction
    initial begin
        vm_q=0;crom_q=0;emb_q=0;emb_sel=0;vm_mask=0;
        for(n=0;n<3000;n=n+1) begin
            @(negedge clk);
            if(n%113==0) begin rst_n=0;resets=resets+1; end
            else if(n%113==3) rst_n=1;
            for(k=0;k<192;k=k+1) begin seed=next_random(seed);vm_q[k*32+:32]=seed;end
            for(k=0;k<128;k=k+1) begin seed=next_random(seed);crom_q[k*32+:32]=seed;end
            for(k=0;k<64;k=k+1) begin seed=next_random(seed);emb_q[k*32+:32]=seed;end
            seed=next_random(seed);emb_sel={seed,~seed};
            if(n<24) vm_mask={192{1'b1}};
            else begin
                for(k=0;k<6;k=k+1) begin seed=next_random(seed);vm_mask[k*32+:32]=seed;end
            end
            @(posedge clk);#0.01;
            if(n>=24) begin
                checks=checks+1;
                if(dut_v!==ref_v || dut_c!==ref_c || dut_e!==ref_e || dut_s!==ref_s) begin
                    errors=errors+1;
                    if(errors<3)$display("DIFF cycle=%0d vm=%0d crom=%0d emb=%0d select=%0d",n,dut_v!==ref_v,dut_c!==ref_c,dut_e!==ref_e,dut_s!==ref_s);
                end
            end
        end
        if(errors || checks!=2976 || resets!=27) $fatal(1,"FAIL alignment checks=%0d errors=%0d resets=%0d MUT=%0d",checks,errors,resets,MUT);
        $display("PASS alignment checks=%0d resets=%0d ML15 VL7 MC4 sixteen physical clock entries synchronously tested",checks,resets);$finish;
    end
endmodule
