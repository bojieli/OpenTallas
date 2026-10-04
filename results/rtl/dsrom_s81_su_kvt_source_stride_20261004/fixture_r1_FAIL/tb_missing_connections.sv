`timescale 1ns/1ps
module tb_s81_kvt_source_stride;
    reg clk=0, rst_n=0, ld=1;
    reg [23:0] ni=128, dim=0;
    reg [29:0] row=0;
    integer checks=0;
    ot_hdc_v41x_vec_lane #(.AW(30), .CW(24), .KIND(0), .LN(3), .KVT_SOURCE_STRIDE(1), .LEAF(0)) dynamic (
        
    );
    ot_hdc_v41x_vec_lane #(.AW(30), .CW(24), .KIND(0), .LN(3), .KVT_SOURCE_STRIDE(1), .LEAF(1)) captured (
        
    );
    ot_hdc_v41x_vec_lane #(.AW(30), .CW(24), .KIND(0), .LN(3), .KVT_SOURCE_STRIDE(0), .LEAF(0)) legacy (
        
    );
    task tick;
        begin #5; clk=1; #1; clk=0; #1; end
    endtask
    reg [29:0] want, oldwant, legacywant;
    integer i,j,k;
    integer rows[0:5];
    integer widths[0:2];
    initial begin
        rows[0]=0;rows[1]=15;rows[2]=16;rows[3]=31;
        rows[4]=262143;rows[5]=1048575;
        widths[0]=128;widths[1]=512;widths[2]=64;
        tick();rst_n=1;tick();ld=0;tick();tick();
        oldwant=captured.f_o;
        for (i=0;i<6;i=i+1) for (j=0;j<3;j=j+1) for (k=0;k<2;k=k+1) begin
            row=rows[i];ni=widths[j];dim=k ? widths[j]-1 : 0;
            want=64+((row>>4)<<(ni==128?11:13))+(dim<<4)+(row&15);
            legacywant=64+((row>>4)<<9)+(dim<<4)+(row&15);
            tick();
            if(dynamic.f_o!==want || legacy.f_o!==legacywant || captured.f_o!==oldwant)
                $fatal(1,"address/captured control mismatch row=%0d ni=%0d dim=%0d dynamic=%0d expected=%0d captured=%0d prior=%0d",row,ni,dim,dynamic.f_o,want,captured.f_o,oldwant);
            if(!dynamic.f_v || !legacy.f_v || !captured.f_v) $fatal(1,"liveness changed");
            oldwant=want;checks=checks+1;
        end
        tick(); if(captured.f_o!==oldwant) $fatal(1,"last captured address");
        $display("PASS %0d source KVT registered-address cases: D128, D512, SH13 compatibility; leaf and default-off",checks);
        $finish;
    end
endmodule
