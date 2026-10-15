`timescale 1ns/1ps
// One bank slice owns ALL six rotation stages. Identity paths stay entirely
// inside this M5 leaf; only the six alternative inputs use die transport.
// Remote alternative s must arrive after Ds ENABLED engine edges. Local self,
// valid and rotation tag take the same Ds edges here, then one mux-register edge.
// me_in_e is the production engine enable ONE hclk early, as existing MEE glue.
module ot_qfd_vm_rotation_bank_t #(
    parameter integer W=128,
    parameter integer MUT=0,
    parameter integer D0=2,D1=2,D2=2,D3=2,D4=2,D5=2
)(
    input wire clk,rst_n,me_in_e,in_valid,
    input wire [5:0]in_rot,
    input wire [W-1:0]bank_in,
    input wire [W-1:0]rx0,rx1,rx2,rx3,rx4,rx5,
    output wire [W-1:0]tx0,tx1,tx2,tx3,tx4,tx5,bank_out,
    output wire out_valid,
    output wire [5:0]out_rot
);
    wire [W-1:0]data[0:6];wire [5:0]rot[0:6];wire valid[0:6];
    wire [W-1:0]remote[0:5];
    assign data[0]=bank_in;assign rot[0]=in_rot;assign valid[0]=in_valid;
    assign remote[0]=rx0;assign remote[1]=rx1;assign remote[2]=rx2;
    assign remote[3]=rx3;assign remote[4]=rx4;assign remote[5]=rx5;
    assign tx0=data[0];assign tx1=data[1];assign tx2=data[2];
    assign tx3=data[3];assign tx4=data[4];assign tx5=data[5];
    genvar s;
    generate for(s=0;s<6;s=s+1)begin:g_stage
        localparam integer D=(s==0)?D0:(s==1)?D1:(s==2)?D2:(s==3)?D3:(s==4)?D4:D5;
        localparam integer SEL=(s<3)?s+3:s-3;
        reg [W-1:0]self_pipe[0:D-1];
        reg [5:0]rot_pipe[0:D-1];reg[D-1:0]v_pipe;
        // Each kept local enable drives one word and its tag, rather than all
        // delayed words on this root. They sample the same early enable epoch.
        (* keep="true",dont_touch="true" *)reg[D:0]ce;
        integer k;
        always @(posedge clk)ce<={(D+1){me_in_e}};
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)v_pipe<=0;
            else begin
                if(ce[0])v_pipe[0]<=valid[s];
                for(k=1;k<D;k=k+1)if(ce[k])v_pipe[k]<=v_pipe[k-1];
            end
        end
        always @(posedge clk)begin
            if(ce[0])begin self_pipe[0]<=data[s];rot_pipe[0]<=rot[s];end
            for(k=1;k<D;k=k+1)if(ce[k])begin self_pipe[k]<=self_pipe[k-1];rot_pipe[k]<=rot_pipe[k-1];end
        end
        reg[W-1:0]q;reg[5:0]rq;reg vq;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)vq<=0;else if(ce[D])vq<=v_pipe[D-1];
        always @(posedge clk)if(ce[D])begin
            q<=(rot_pipe[D-1][SEL]^((MUT!=0)&&(s==0)))?remote[s]:self_pipe[D-1];rq<=rot_pipe[D-1];
        end
        assign data[s+1]=q;assign rot[s+1]=rq;assign valid[s+1]=vq;
    end endgenerate
    assign bank_out=data[6];assign out_rot=rot[6];assign out_valid=valid[6];
    initial if(D0<1||D1<1||D2<1||D3<1||D4<1||D5<1||
               (W+8)*(D0+D1+D2+D3+D4+D5+6)>15000)
        $fatal(1,"rotation bank leaf exceeds local root budget");
endmodule

// Minimum exact composition vehicle. Transport registers stand for the real
// die relay stations; they are outside each independently rooted bank slice.
module ot_qfd_vm_rotation_banked_vehicle #(
    parameter integer BANK_W=512,W=128,MUT=0,
    parameter integer D0=2,D1=3,D2=4,D3=2,D4=3,D5=4
)(
    input wire clk,rst_n,me_ce,me_in_e,in_valid,
    input wire[5:0]in_rot,
    input wire[64*BANK_W-1:0]in_data,
    output wire out_valid,
    output wire[5:0]out_rot,
    output wire[64*BANK_W-1:0]out_data
);
    wire[BANK_W*6-1:0]tx[0:63],rx[0:63];
    wire[63:0]vv;wire[64*6-1:0]rr;
    genvar b,l,s;
    generate for(b=0;b<64;b=b+1)begin:g_bank
        wire[BANK_W/W-1:0]sv;wire[(BANK_W/W)*6-1:0]sr;
        for(l=0;l<BANK_W/W;l=l+1)begin:g_slice
            ot_qfd_vm_rotation_bank_t #(.W(W),.MUT(MUT),.D0(D0),.D1(D1),.D2(D2),.D3(D3),.D4(D4),.D5(D5)) u_leaf(
                .clk(clk),.rst_n(rst_n),.me_in_e(me_in_e),.in_valid(in_valid),.in_rot(in_rot),.bank_in(in_data[b*BANK_W+l*W+:W]),
                .rx0(rx[b][0*BANK_W+l*W+:W]),.rx1(rx[b][1*BANK_W+l*W+:W]),.rx2(rx[b][2*BANK_W+l*W+:W]),
                .rx3(rx[b][3*BANK_W+l*W+:W]),.rx4(rx[b][4*BANK_W+l*W+:W]),.rx5(rx[b][5*BANK_W+l*W+:W]),
                .tx0(tx[b][0*BANK_W+l*W+:W]),.tx1(tx[b][1*BANK_W+l*W+:W]),.tx2(tx[b][2*BANK_W+l*W+:W]),
                .tx3(tx[b][3*BANK_W+l*W+:W]),.tx4(tx[b][4*BANK_W+l*W+:W]),.tx5(tx[b][5*BANK_W+l*W+:W]),
                .bank_out(out_data[b*BANK_W+l*W+:W]),.out_valid(sv[l]),.out_rot(sr[l*6+:6]));
        end
        assign vv[b]=sv[0];assign rr[b*6+:6]=sr[0+:6];
        for(s=0;s<6;s=s+1)begin:g_transport
            localparam integer SEL=(s<3)?s+3:s-3;
            localparam integer D=(s==0)?D0:(s==1)?D1:(s==2)?D2:(s==3)?D3:(s==4)?D4:D5;
            reg[BANK_W-1:0]pipe[0:D-1];integer k;
            always @(posedge clk)if(me_ce)begin
                pipe[0]<=tx[(b+(1<<SEL))%64][s*BANK_W+:BANK_W];
                for(k=1;k<D;k=k+1)pipe[k]<=pipe[k-1];
            end
            assign rx[b][s*BANK_W+:BANK_W]=pipe[D-1];
        end
    end endgenerate
    assign out_valid=vv[0];assign out_rot=rr[0+:6];
endmodule
