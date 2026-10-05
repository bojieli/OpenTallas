`timescale 1ns/1ps
module tb_hbm_w2_tag16_map;
    reg iv=1, ok=1, ib=1, rv=1, rb=1;
    reg [12:0] ir=0;
    reg [6:0] xa=0, a=0, b=16, dx=16;
    reg [11:0] rr=0;
    reg [31:0] oa=17, ob=29;
    wire [6:0] xo;
    wire ifault, ov, seg, alast, plast, rfault;
    wire [11:0] localrow;
    wire [31:0] operation;
    ot_hbm_accel_w2_tag16_map #(.ENABLE(1)) dut (
        .issue_v(iv),.issue_row_ok(ok),.issue_virtual_row(ir),.issue_xa_absolute(xa),
        .issue_pair_bound(ib),.issue_xb_a(a),.issue_xb_b(b),.issue_delta_x(dx),
        .issue_xa_out(xo),.issue_fault(ifault),.rsp_v(rv),.rsp_virtual_row(rr),
        .result_pair_bound(rb),.result_op_a(oa),.result_op_b(ob),.out_v(ov),
        .out_local_row(localrow),.out_operation(operation),.out_segment(seg),
        .out_a_last(alast),.out_pair_last(plast),.result_fault(rfault));
    wire [6:0] off_xa; wire off_v; wire [11:0] off_row;
    wire off_if,off_rf;
    ot_hbm_accel_w2_tag16_map off (
        .issue_v(iv),.issue_row_ok(ok),.issue_virtual_row(ir),.issue_xa_absolute(xa),
        .issue_pair_bound(ib),.issue_xb_a(a),.issue_xb_b(b),.issue_delta_x(dx),
        .issue_xa_out(off_xa),.issue_fault(off_if),.rsp_v(rv),.rsp_virtual_row(rr),
        .result_pair_bound(rb),.result_op_a(oa),.result_op_b(ob),.out_v(off_v),
        .out_local_row(off_row),.out_operation(),.out_segment(),
        .out_a_last(),.out_pair_last(),.result_fault(off_rf));
    integer base,row,g,t,checks=0;
    initial begin
        for (base=0;base<128;base=base+1) begin
            a=base; b=(base+16)%128; dx=b-a;
            for (row=0;row<4;row=row+1) begin
                ir=row; rr=row;
                for (g=0;g<2;g=g+1) for (t=0;t<8;t=t+1) begin
                    xa=(base+8*g+t)%128; #1;
                    if(ifault||rfault||!ov||localrow!=(row%2)||seg!=(row>=2)||
                       operation!=(row<2?17:29)||alast!=(row==1)||plast!=(row==3))
                        $fatal(1,"identity/valid mismatch");
                    if(xo!=((row<2?base:((base+16)%128))+8*g+t)%128)
                        $fatal(1,"x address mismatch");
                    if(off_xa!=xa||off_row!=rr||!off_v||off_if||off_rf)
                        $fatal(1,"defaultoff mismatch");
                    checks=checks+1;
                end
            end
        end
        // New issuing pair changes x context while old pair still responds:
        a=80; b=96; dx=16; xa=80; ir=2; rr=0; #1;
        if(xo!=96||operation!=17||localrow!=0) $fatal(1,"descriptor head alias");
        ib=0; #1; if(!ifault) $fatal(1,"unbound issue accepted");
        ib=1; dx=15; #1; if(!ifault) $fatal(1,"wrong delta accepted");
        dx=16; ir=4; #1; if(!ifault) $fatal(1,"issue bounds accepted");
        ok=0; #1; if(ifault) $fatal(1,"bubble fault");
        rb=0; #1; if(!rfault||ov) $fatal(1,"unbound result accepted");
        rb=1; rr=4; #1; if(!rfault||ov) $fatal(1,"result bounds accepted");
        rv=0; #1; if(rfault||ov) $fatal(1,"invalid result fault");
        $display("PASS W2_TAG16_MAP %0d address/identity checks; negative refusal checks",checks);
        $finish;
    end
endmodule
