`timescale 1ns/1ps
module tb_qwen_spine_lane;
    parameter integer NEG=0, OSTN=0;   // OSTN: the lane's pin stations (y +1, fault +2 against the reference tree)
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    reg [1535:0] d=0;
    reg [13:0] sel=0,tv=0;
    wire [1535:0] mutated;
    assign mutated=NEG ? {d[1535:96],d[63:32],d[95:64],d[31:0]} : d;
    wire [1535:0] y,ref_y0;
    wire fault,ref_fault0;
    ot_qwen_spine_lane #(.OSTN(OSTN)) dut(clk,rst_n,mutated,sel,tv,y,fault);
    reg [1535:0] ry1; reg rf1, rf2;
    always @(posedge clk) ry1 <= ref_y0;
    always @(posedge clk or negedge rst_n) if(!rst_n) begin rf1<=0; rf2<=0; end else begin rf1<=ref_fault0; rf2<=rf1; end
    wire [1535:0] ref_y = OSTN ? ry1 : ref_y0;
    wire ref_fault = OSTN ? rf2 : ref_fault0;
    ot_qwen_me_sptree_w12 #(.GT(6144),.SMIN(7),.TCUT(7),.TREE_LAT(7),.TINREG(1))
        ref_lane(clk,rst_n,d,sel,tv,ref_y0,ref_fault0);
    function automatic [31:0] fp;
        input integer value;
        integer k,j;
        reg [31:0] mant;
        begin
            k=0; for(j=0;j<30;j=j+1) if(value >= (1<<j)) k=j;
            mant=(value-(1<<k)) << (23-k);
            fp=value==0 ? 0 : ((127+k)<<23)|mant;
        end
    endfunction
    integer values[0:47], next_values[0:47];
    integer split,p,lv,cyc,txn,checks=0;
    task tick;
        begin @(posedge clk); #1; end
    endtask
    task compare;
        begin
            if(y !== ref_y || fault !== ref_fault) begin
                $display("FAIL spine exact cycle mismatch checks=%0d",checks); $fatal(1);
            end
            checks=checks+1;
        end
    endtask
    initial begin
        repeat(3) tick(); @(negedge clk); rst_n=1;
        // Full 48-position independent integer oracle. Values/sums are exact FP32 integers.
        for(txn=0;txn<21;txn=txn+1) begin
            split=7+(txn%7);
            @(negedge clk);
            for(p=0;p<48;p=p+1) begin values[p]=p+1+txn; d[p*32+:32]=fp(values[p]); end
            sel=0;tv=0;
            for(lv=8;lv<=12;lv=lv+1) begin sel[lv]=(split>=lv); tv[lv]=(split>=lv); end
            for(lv=8;lv<=12;lv=lv+1) begin
                for(p=0;p<48;p=p+1) next_values[p]=values[p];
                if(split>=lv) for(p=0;p<(6144>>lv);p=p+1)
                    next_values[p]=values[2*p]+values[2*p+1];
                for(p=0;p<48;p=p+1) values[p]=next_values[p];
            end
            repeat(55) tick();
            compare();
            if(fault) begin $display("FAIL spine finite fault"); $fatal(1); end
            for(p=0;p<48;p=p+1) if(y[p*32+:32] !== fp(values[p])) begin
                $display("FAIL spine position split=%0d p=%0d got=%h want=%h",split,p,y[p*32+:32],fp(values[p])); $fatal(1);
            end
        end
        // Sustained pipeline activity with independent control/data transitions and reset.
        for(cyc=0;cyc<160;cyc=cyc+1) begin
            @(negedge clk);
            for(p=0;p<48;p=p+1) d[p*32+:32]=$random;
            sel=$random; tv=$random;
            tick(); compare();
        end
        @(negedge clk); rst_n=0; tv=0;
        repeat(3) tick(); compare();
        if(fault) begin $display("FAIL spine reset fault"); $fatal(1); end
        $display("PASS spine full_shape=48 checks=%0d splits=7 independent_oracle=21",checks);
        $finish;
    end
endmodule
