// HBM-REFORM-B9 kshare RE-FORM (11-05, two strikes on kshare4ct/kshare4ct2): same ports, edges and behaviour as the
// kshare4c pointer skid, but the control is replicated per SL-bit data slice (keep), so every entry write enable and every
// out_data select drives at most SL flops / mux bits (the 277-bit u_d push enable was the -9.98 ps TT path, fanout 277).
// The master copy drives in_r / out_v only.
module ot_hbm_svc_pin_skid2 #(parameter integer WIDTH=1,MUT=0,SL=64)(
    input wire clk,rst_n,input wire in_v,output wire in_r,
    input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
    output wire [WIDTH-1:0]out_data
);
    localparam integer NS=(WIDTH+SL-1)/SL;
    reg [1:0]cnt;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)cnt<=2'd0;
        else cnt<=cnt+{1'b0,in_v&&cnt!=2'd2}-{1'b0,cnt!=2'd0&&out_r};
    assign in_r=cnt!=2'd2;assign out_v=cnt!=2'd0;
    genvar s;
    generate for(s=0;s<NS;s=s+1)begin:g_sl
        localparam integer LO=s*SL;
        localparam integer W=(LO+SL>WIDTH)?(WIDTH-LO):SL;
        (* keep *) reg [1:0]cnt_k;(* keep *) reg wp_k,rp_k;
        reg [W-1:0]e0,e1;
        wire push=in_v&&cnt_k!=2'd2,pop=cnt_k!=2'd0&&out_r;
        assign out_data[LO+:W]=rp_k?e1:e0;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin cnt_k<=2'd0;wp_k<=1'b0;rp_k<=1'b0;end
            else begin
                cnt_k<=cnt_k+{1'b0,push}-{1'b0,pop};
                if(push)wp_k<=!wp_k;
                if(pop)rp_k<=!rp_k;
            end
        always @(posedge clk)begin
            if(push&&!wp_k)e0<=in_data[LO+:W];
            if(push&&wp_k)e1<=in_data[LO+:W];
            // Checked negative control: illegally overwrite a stalled head.
            if(MUT!=0&&push&&cnt_k!=2'd0&&!out_r)begin if(rp_k)e1<=in_data[LO+:W];else e0<=in_data[LO+:W];end
        end
    end endgenerate
endmodule
