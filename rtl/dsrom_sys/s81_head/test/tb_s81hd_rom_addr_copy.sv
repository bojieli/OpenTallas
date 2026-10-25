`timescale 1ns/1ps
module tb;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, go=0;
    reg go_r=0,run=0;reg [13:0] a=0;
    wire [13:0] next_a=a+14'd1;
    wire [11:0] r0,r1;
    ot_s81hd_rom_addr_copy #(.BANK(0)) u0(clk,rst_n,go_r,run,next_a[12:1],r0);
    ot_s81hd_rom_addr_copy #(.BANK(1)) u1(clk,rst_n,go_r,run,next_a[12:1],r1);
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin go_r<=0;run<=0;a<=0;end
        else begin
            go_r<=go;
            if(go_r)begin run<=1;a<=0;end
            else if(run)begin a<=a+14'd1;if(a==8247)run<=0;end
        end
    integer i,errors=0;
    initial begin
        repeat(4)@(negedge clk);rst_n=1;
        for(i=0;i<40000;i=i+1)begin
            @(negedge clk);
            if(r0!==a[12:1]||r1!==a[12:1])begin
                errors=errors+1;
                if(errors<3)$display("ADDR_DIFF cycle=%0d golden=%h r0=%h r1=%h",i,a[12:1],r0,r1);
            end
            // Complete production-length scans, repeated go, idle, and reset during a scan.
            go=(i==1||i==9000||i==9003||i==19000||i==31000);
            if(i==24000)rst_n=0;
            if(i==24004)rst_n=1;
        end
        if(errors)$fatal(1,"ADDR_COPY_FAIL errors=%0d",errors);
        $display("ADDR_COPY_PASS checks=80000 cycles_added=0");$finish;
    end
endmodule
