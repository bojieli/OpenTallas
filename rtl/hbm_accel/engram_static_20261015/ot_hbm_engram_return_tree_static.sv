`timescale 1ps/1fs
// Opt-in structural return fabric, not an adopted performance/placement profile.
// Adjacent PC pairs capture locally. Registered balanced legs replace the long
// 32x256 combinational mux and any long combinational ready path. Physical pin
// incidence, actual <=500um segment placement and related-clock STA remain open.
// Each persistent PC head is sampled once/64 HBM edges, globally one head/2edges.
// All31 node clocks must be 1:1 same-phase HBM clocks with aligned reset release.
// A real finite downstream CDC must be sized/proved for this arrival envelope.
module ot_hbm_engram_return_tree_static #(
    parameter integer ONE_ROW=0,
    parameter integer MUT_DATA=0,MUT_RIGHT_SKEW=0
)(
    input wire[30:0]node_clk,input wire rst_n,
    input wire[31:0]kr_v,output wire[31:0]kr_rdy,
    input wire[543:0]kr_tag,input wire[127:0]kr_beat,input wire[8191:0]kr_data,
    output wire out_v,output wire[264:0]out_word,output wire fault
);
    wire[30:0]valid,errors;wire[264:0]word[0:30];
    assign out_v=valid[0];assign out_word=word[0] ^ (265'(MUT_DATA)<<256);assign fault=|errors;
    for(genvar leaf=0;leaf<16;leaf=leaf+1)begin:g_pair
        localparam integer N=15+leaf,P0=2*leaf,P1=2*leaf+1;
        reg[5:0]phase;reg v,sticky;reg[264:0]payload;
        wire s0=!phase[0] && phase[5:1]==5'(P0) && !sticky;
        wire s1=!phase[0] && phase[5:1]==5'(P1) && !sticky;
        wire take0=s0&&kr_v[P0],take1=s1&&kr_v[P1];
        wire bad0=take0&&(kr_tag[P0*17+9+:8]!=0 || kr_beat[P0*4+:4]!=0);
        wire bad1=take1&&(kr_tag[P1*17+9+:8]!=0 || kr_beat[P1*4+:4]!=0);
        assign kr_rdy[P0]=s0;assign kr_rdy[P1]=s1;
        assign valid[N]=v;assign word[N]=payload;assign errors[N]=sticky;
        always @(posedge node_clk[N] or negedge rst_n)begin
            if(!rst_n)begin phase<=0;v<=0;sticky<=0;end
            else begin
                phase<=phase+1'b1;v<=(take0||take1)&&!(bad0||bad1);
                if(take0)payload<={kr_tag[P0*17+:9],kr_data[P0*256+:256]};
                if(take1)payload<={kr_tag[P1*17+:9],kr_data[P1*256+:256]};
                if(bad0||bad1)sticky<=1;
            end
        end
    end
    for(genvar n=0;n<15;n=n+1)begin:g_reduce
        localparam integer DEPTH=$clog2(n+2)-1;
        // Candidate equal-leg register counts; not a substitute for actual pin/route incidence.
        localparam integer RELAY=(DEPTH==0)?(ONE_ROW?4:0):(DEPTH==1)?2:(DEPTH==2)?1:0;
        localparam integer LEFT=2*n+1,RIGHT=2*n+2;
        localparam integer RD=RELAY+((n==0&&MUT_RIGHT_SKEW)?1:0);
        wire lv,rv;wire[264:0]ld,rd;
        if(RELAY==0)begin:l_direct
            assign lv=valid[LEFT];assign ld=word[LEFT];
        end else begin:l_registered
            reg[RELAY-1:0]pv;reg[264:0]pd[0:RELAY-1];
            always @(posedge node_clk[n] or negedge rst_n)begin
                if(!rst_n)pv<=0;
                else begin
                    pv[0]<=valid[LEFT];if(valid[LEFT])pd[0]<=word[LEFT];
                    for(integer s=1;s<RELAY;s=s+1)begin pv[s]<=pv[s-1];if(pv[s-1])pd[s]<=pd[s-1];end
                end
            end
            assign lv=pv[RELAY-1];assign ld=pd[RELAY-1];
        end
        if(RD==0)begin:r_direct
            assign rv=valid[RIGHT];assign rd=word[RIGHT];
        end else begin:r_registered
            reg[RD-1:0]pv;reg[264:0]pd[0:RD-1];
            always @(posedge node_clk[n] or negedge rst_n)begin
                if(!rst_n)pv<=0;
                else begin
                    pv[0]<=valid[RIGHT];if(valid[RIGHT])pd[0]<=word[RIGHT];
                    for(integer s=1;s<RD;s=s+1)begin pv[s]<=pv[s-1];if(pv[s-1])pd[s]<=pd[s-1];end
                end
            end
            assign rv=pv[RD-1];assign rd=pd[RD-1];
        end
        reg v,sticky;reg[264:0]payload;
        assign valid[n]=v;assign word[n]=payload;assign errors[n]=sticky;
        always @(posedge node_clk[n] or negedge rst_n)begin
            if(!rst_n)begin v<=0;sticky<=0;end
            else begin
                v<=lv|rv;if(lv)payload<=ld;else if(rv)payload<=rd;
                if(lv&&rv)sticky<=1;
            end
        end
    end
endmodule
