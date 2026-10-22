`timescale 1ns/1ps
// Source boot-data publication comparison only; missing unrelated engines omitted.
module tb_sysface_cfg_copy;
reg ck=0;always #5 ck=~ck;
reg rst_n=0;reg[2:0]bs=0;reg db=0;reg[71:0]rw=0;integer i,n=0;
qfd_sys_face_ovl_lctx3 d(.ck(ck),.rst_n(rst_n));
initial begin force d.st=bs;force d.dq_boot=db;force d.rom_qr=rw;
repeat(5)@(negedge ck);rst_n=1;repeat(5)@(negedge ck);
for(i=0;i<160;i=i+1)begin bs=i%5;db=(i/5)%2;rw={4'(i%16),36'd0,32'(i*32'h9e3779b9)};@(negedge ck);end
rst_n=0;repeat(4)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
$display("PASS CFG_SOURCE_COPIES edges=%0d all28 independent publications equal actual original c_data source",n);$finish;end
always @(posedge ck)begin #1;n=n+1;
if(d.cd_t0!==d.c_data[31:0])$fatal(1,"CFG_COPY_DIFF cd_t0 edge%0d",n);
if(d.cd_t1!==d.c_data[31:0])$fatal(1,"CFG_COPY_DIFF cd_t1 edge%0d",n);
if(d.cs_t0!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t0 edge%0d",n);
if(d.cs_t1!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t1 edge%0d",n);
if(d.cs_t2!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t2 edge%0d",n);
if(d.cs_t3!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t3 edge%0d",n);
if(d.cs_t4!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t4 edge%0d",n);
if(d.cs_t5!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t5 edge%0d",n);
if(d.cs_t6!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t6 edge%0d",n);
if(d.cs_t7!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t7 edge%0d",n);
if(d.cs_t8!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t8 edge%0d",n);
if(d.cs_t9!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t9 edge%0d",n);
if(d.cs_t10!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t10 edge%0d",n);
if(d.cs_t11!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t11 edge%0d",n);
if(d.cs_t12!==d.c_data[5:0])$fatal(1,"CFG_COPY_DIFF cs_t12 edge%0d",n);
if(d.cd_l0!==d.c_data[31:0])$fatal(1,"CFG_COPY_DIFF cd_l0 edge%0d",n);
if(d.cs_l0!==d.c_data[4:0])$fatal(1,"CFG_COPY_DIFF cs_l0 edge%0d",n);
if(d.cs_l1!==d.c_data[4:0])$fatal(1,"CFG_COPY_DIFF cs_l1 edge%0d",n);
if(d.cs_l2!==d.c_data[4:0])$fatal(1,"CFG_COPY_DIFF cs_l2 edge%0d",n);
if(d.cs_l3!==d.c_data[4:0])$fatal(1,"CFG_COPY_DIFF cs_l3 edge%0d",n);
if(d.cs_l4!==d.c_data[4:0])$fatal(1,"CFG_COPY_DIFF cs_l4 edge%0d",n);
if(d.cs_l5!==d.c_data[4:0])$fatal(1,"CFG_COPY_DIFF cs_l5 edge%0d",n);
if(d.cs_l6!==d.c_data[4:0])$fatal(1,"CFG_COPY_DIFF cs_l6 edge%0d",n);
if(d.cd_e0!==d.c_data[31:0])$fatal(1,"CFG_COPY_DIFF cd_e0 edge%0d",n);
if(d.cs_e0!==d.c_data[3:0])$fatal(1,"CFG_COPY_DIFF cs_e0 edge%0d",n);
if(d.cs_e1!==d.c_data[3:0])$fatal(1,"CFG_COPY_DIFF cs_e1 edge%0d",n);
if(d.cs_e2!==d.c_data[3:0])$fatal(1,"CFG_COPY_DIFF cs_e2 edge%0d",n);
if(d.cs_e3!==d.c_data[3:0])$fatal(1,"CFG_COPY_DIFF cs_e3 edge%0d",n);
end
endmodule
