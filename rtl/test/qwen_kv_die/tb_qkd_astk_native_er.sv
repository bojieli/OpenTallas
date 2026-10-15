`timescale 1ns/1ps
module tb_qkd_astk_native_er;
    parameter integer ROUTE_MUT=0,TAG_MUT=0,LATENCY_MUT=0,CONFLICT_MUT=0;
    reg ck=0,rst_n=0;always #1 ck=~ck;
    reg rv=0;reg [10:0] ra=0;
    reg [3399:0] so=0;
    wire [3399:0] aso;
    wire [5071:0] si;
    reg [4175:0] ri=0;
    wire ov,fault;wire [10:0] oa;wire [63:0] od;
    qkd_astk_native_er_service #(.ROUTE_MUT(ROUTE_MUT),.TAG_MUT(TAG_MUT),.LATENCY_MUT(LATENCY_MUT)) u_route
      (.ck(ck),.rst_n(rst_n),.read_v(rv),.read_addr(ra),.engine_so(so),.astk_so(aso),.astk_si(si),.engine_si(),
       .response_v(ov),.response_addr(oa),.response_data(od),.fault(fault));
    genvar e;
    generate for(e=0;e<8;e=e+1)begin:g_ep
        qkd_astk_ep u_ep(.ck(ck),.rst_n(rst_n),.sq({2'd0,3'(e)}),.so(aso[425*e+:425]),.si(si[634*e+:634]),
          .qi(572'd0),.xi(267'd0),.xo(),.zi(651'd0),.zo(),.ri(ri[522*e+:522]),.xa(),.xe(136'd0),.cr(1'b0),
          .ui(536'd0),.uo(),.di(536'd0),.do_(),.pi(263'd0),.po(),.ci(6'd0),.co(),
          .kui(4'd0),.kuo(),.kdi(4'd0),.kdo(),.tui(1'b0),.tuo(),.tdi(1'b0),.tdo(),.fi(1'b0),.fo());
    end endgenerate
    function automatic [63:0] value(input integer owner,input integer row,input integer slot);
        integer l;begin for(l=0;l<4;l=l+1)value[16*l+:16]=16'h8001 ^ 16'(owner*4093+row*113+slot*17+l*3);end
    endfunction
    function automatic [511:0] row_value(input integer owner,input integer row);
        integer j;begin for(j=0;j<8;j=j+1)row_value[64*j+:64]=value(owner,row,j);end
    endfunction
    integer cycles=0,start_cycle=0,requests=0,responses=0,errors=0;
    always @(posedge ck)if(rst_n && rv)begin
        if(requests==0)start_cycle=cycles;
        requests=requests+1;
    end
    always @(negedge ck)if(rst_n)begin
        cycles=cycles+1;
        if(ov)begin
            if(oa!==11'(responses) || cycles!=start_cycle+3+responses || od!==value(responses[5:3],2*(responses>>7)+((responses>>6)&1),responses&7))begin
                errors=errors+1;
                if(errors<6)$display("FAIL native_er response=%0d addr=%0d cycle=%0d expected_cycle=%0d got=%h expected=%h",responses,oa,cycles,start_cycle+3+responses,od,value(responses[5:3],2*(responses>>7)+((responses>>6)&1),responses&7));
            end
            responses=responses+1;
        end
    end
    integer row,owner;
    initial begin
        repeat(5)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
        // Exactly one real e-row write per edge, as on the actual return chain.
        // No ideal score/e array exists in this DUT or initializer.
        for(row=0;row<32;row=row+1)for(owner=0;owner<8;owner=owner+1)begin
            ri=0;
            ri[522*owner+:522]={row_value(owner,row),1'(row&1),3'(owner),4'(row>>1),1'b0,1'b1};
            @(negedge ck);
        end
        ri=0;repeat(8)@(negedge ck);
        for(integer a=0;a<2048;a=a+1)begin rv=1;ra=11'(a);@(negedge ck);end
        rv=0;repeat(8)@(negedge ck);
        if(CONFLICT_MUT)begin so[0]=1;@(negedge ck);so=0;repeat(2)@(negedge ck);end
        if(responses!=2048 || fault!=1'(CONFLICT_MUT))begin errors=errors+1;$display("FAIL count=%0d fault=%b",responses,fault);end
        if(errors==0)$display("PASS native_er actual_EP=8 score_macros=16 e_macros=32 requests=%0d responses=%0d ERL=3 conflict_fault=%b",requests,responses,fault);
        else $display("FAIL native_er errors=%0d",errors);
        $finish;
    end
endmodule
