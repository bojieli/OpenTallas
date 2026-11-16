`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[1501:0]ev[0:431];reg[1501:0]d=0;wire[1566:0]hw;wire[23:0]cid;wire[515:0]nd,sd;
qfd_dv_s8_tap_bounded tap(.ck(ck),.rst_n(rst_n),.sid(4'd0),.hr_q(d[452:0]),.xt_vcopies({6{d[453]}}),.xt_a(d[477:454]),.xt_d(d[1501:478]),.xt_bad(1'b0),.lq_bad(32'd0),.hw(hw),.cid(cid),.tap_fault());
qfd_dv_s5_xhead3 head(.ck(ck),.rst_n(rst_n),.cid(cid[5:0]),.fault_i(1'b0),.a_d(hw),.n_d(nd),.s_d(sd),.lq(512'd0),.lq_v(8'hff),.lq_bad(8'd0));
integer cy=0,go=-1,tag=-1,last=-1,n=0;
initial begin
 $readmemh("input.hex",ev);repeat(12)@(negedge ck);rst_n=1;
 for(cy=0;cy<432;cy++)begin
 @(negedge ck);d=ev[cy];@(posedge ck);
 if(nd[0])begin if(go>=0)$fatal(1,"multipleGO");go=cy;end
 if(nd[515])begin if(tag<0)tag=cy;last=cy;n++;end
 end
 $display("GO_TAG_RECEIVERS inputGO248 corridorGO%0d GOage%0d firstTAG%0d TAGage%0d lastTAG%0d count%0d",go,go-248,tag,tag-248,last,n);
 if(go<0||tag<0||n!=32)$fatal(1,"missing native events");$finish;
end
endmodule
