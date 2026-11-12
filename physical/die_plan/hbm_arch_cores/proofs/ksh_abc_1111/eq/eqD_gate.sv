(* keep_hierarchy, keep *) module ot_hbm_svc_skid_enh (input wire a, input wire b, output wire y); assign y = !a | b; endmodule
module skid_gate #(parameter integer WIDTH=1,SLW=32)(
    input wire clk,rst_n,input wire in_v,output wire in_r,
    input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
    output wire [WIDTH-1:0]out_data,output wire d_hv,d_tv,output wire [WIDTH-1:0]d_hd,d_td
);
    localparam integer NS=(WIDTH+SLW-1)/SLW;
    reg head_valid,tail_valid;
    reg [WIDTH-1:0]head_data,tail_data;
    wire push=in_v&&in_r,pop=out_v&&out_r;
    assign in_r=!tail_valid;assign out_v=head_valid;assign out_data=head_data;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin head_valid<=0;tail_valid<=0;end
        else begin
            case({push,pop})
                2'b10:begin
                    if(!head_valid)head_valid<=1;
                    else tail_valid<=1;
                end
                2'b01:begin
                    head_valid<=tail_valid;tail_valid<=0;
                end
                2'b11:begin head_valid<=1;tail_valid<=0;end
                default:;
            endcase
        end
    end
    for(genvar s=0;s<NS;s=s+1)begin:g_sl
        localparam integer LO=s*SLW,HI=(WIDTH-1<LO+SLW-1)?WIDTH-1:LO+SLW-1;
        wire en_h;
        ot_hbm_svc_skid_enh u_eh(.a(head_valid),.b(out_r),.y(en_h));
        always @(posedge clk)begin
`ifdef OT_KSH_MUT_D
            if(en_h)head_data[HI:LO]<=in_data[HI:LO];   // bench negative control: tail beat lost
`else
            if(en_h)head_data[HI:LO]<=tail_valid?tail_data[HI:LO]:in_data[HI:LO];
`endif
            if(!tail_valid)tail_data[HI:LO]<=in_data[HI:LO];
        end
    end
    assign d_hv=head_valid;assign d_tv=tail_valid;assign d_hd=head_data;assign d_td=tail_data;
endmodule