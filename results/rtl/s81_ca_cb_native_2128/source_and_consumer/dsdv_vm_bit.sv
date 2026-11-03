`timescale 1ps/1ps
module dsdv_vm_bit #(parameter integer ID=0)(input wire ck,rn,d,output wire q);
    (* keep *)reg r;
    always @(posedge ck or negedge rn)if(!rn)r<=0;else r<=d;
    assign q=r;
endmodule
