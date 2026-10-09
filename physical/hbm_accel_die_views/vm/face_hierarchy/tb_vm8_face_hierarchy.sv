`timescale 1ps/1fs
module tb_vm8_face_hierarchy;
reg [0:0] ck=0;
reg [0:0] rst=0;
reg [255:0] f_n_ctl=0;
reg [2255:0] f_n_row=0;
reg [2263:0] f_n_wr=0;
reg [2255:0] f_w_row=0;
reg [2263:0] f_w_wr=0;
wire [255:0] t_n_ctl;
wire [255:0] c_t_n_ctl;
wire [2255:0] t_n_row;
wire [2255:0] c_t_n_row;
wire [2263:0] t_n_wr;
wire [2263:0] c_t_n_wr;
wire [255:0] t_w_ctl;
wire [255:0] c_t_w_ctl;
wire [2255:0] t_w_row;
wire [2255:0] c_t_w_row;
wire [2263:0] t_w_wr;
wire [2263:0] c_t_w_wr;
reg [1077:0] s2n=0;
wire [3854:0] n2s;
wire [3854:0] c_n2s;
always #416.667 ck=~ck;
hfd_vm_se_n_f3_reference reference(.ck(ck),.rst(rst),.f_n_ctl(f_n_ctl),.f_n_row(f_n_row),.f_n_wr(f_n_wr),.f_w_row(f_w_row),.f_w_wr(f_w_wr),.t_n_ctl(t_n_ctl),.t_n_row(t_n_row),.t_n_wr(t_n_wr),.t_w_ctl(t_w_ctl),.t_w_row(t_w_row),.t_w_wr(t_w_wr),.s2n(s2n),.n2s(n2s));
hfd_vm_se_n_hier candidate(.ck(ck),.rst(rst),.f_n_ctl(f_n_ctl),.f_n_row(f_n_row),.f_n_wr(f_n_wr),.f_w_row(f_w_row),.f_w_wr(f_w_wr),.t_n_ctl(c_t_n_ctl),.t_n_row(c_t_n_row),.t_n_wr(c_t_n_wr),.t_w_ctl(c_t_w_ctl),.t_w_row(c_t_w_row),.t_w_wr(c_t_w_wr),.s2n(s2n),.n2s(c_n2s));
integer cycle=0,i,checks=0;
always @(negedge ck)begin
 cycle=cycle+1;
 if(cycle>10)begin if(t_n_ctl!==c_t_n_ctl)$fatal(1,"actual fullface mismatch t_n_ctl cycle%0d",cycle);checks=checks+1;end
 if(cycle>10)begin if(t_n_row!==c_t_n_row)$fatal(1,"actual fullface mismatch t_n_row cycle%0d",cycle);checks=checks+1;end
 if(cycle>10)begin if(t_n_wr!==c_t_n_wr)$fatal(1,"actual fullface mismatch t_n_wr cycle%0d",cycle);checks=checks+1;end
 if(cycle>10)begin if(t_w_ctl!==c_t_w_ctl)$fatal(1,"actual fullface mismatch t_w_ctl cycle%0d",cycle);checks=checks+1;end
 if(cycle>10)begin if(t_w_row!==c_t_w_row)$fatal(1,"actual fullface mismatch t_w_row cycle%0d",cycle);checks=checks+1;end
 if(cycle>10)begin if(t_w_wr!==c_t_w_wr)$fatal(1,"actual fullface mismatch t_w_wr cycle%0d",cycle);checks=checks+1;end
 if(cycle>10)begin if(n2s!==c_n2s)$fatal(1,"actual fullface mismatch n2s cycle%0d",cycle);checks=checks+1;end
 rst=cycle<5;
 for(i=0;i<256;i=i+1)f_n_ctl[i]=$urandom;
 for(i=0;i<2256;i=i+1)f_n_row[i]=$urandom;
 for(i=0;i<2264;i=i+1)f_n_wr[i]=$urandom;
 for(i=0;i<2256;i=i+1)f_w_row[i]=$urandom;
 for(i=0;i<2264;i=i+1)f_w_wr[i]=$urandom;
 for(i=0;i<1078;i=i+1)s2n[i]=$urandom;
 f_w_wr[0]=cycle>=8;
 f_w_wr[1]=cycle<264;
 f_w_wr[2]=((cycle-8)/128)&1;
 f_w_wr[9:3]=(cycle-8)%128;
 if(cycle>519)begin f_w_wr[0]=(cycle%3!=0);f_w_wr[1]=cycle[2];end
 if(cycle==750)begin $display("PASS_VM8_FACE_HIER cycles=%0d allfacechecks=%0d realmacros=12 reference6candidate6",cycle,checks);$finish;end
end
endmodule
