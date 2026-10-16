module golden_skid #(parameter integer WIDTH=1,MUT=0)(
    input wire clk,rst_n,input wire in_v,output wire in_r,
    input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
    output wire [WIDTH-1:0]out_data
);
    reg head_valid,tail_valid;
    reg [WIDTH-1:0]head_data,tail_data;
    wire push=in_v&&in_r,pop=out_v&&out_r;
    assign in_r=!tail_valid;assign out_v=head_valid;assign out_data=head_data;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin head_valid<=0;tail_valid<=0;end
        else begin
            case({push,pop})
                2'b10:begin
                    if(!head_valid)begin head_data<=in_data;head_valid<=1;end
                    else begin tail_data<=in_data;tail_valid<=1;end
                end
                2'b01:begin
                    if(tail_valid)head_data<=tail_data;
                    head_valid<=tail_valid;tail_valid<=0;
                end
                2'b11:begin head_data<=in_data;head_valid<=1;tail_valid<=0;end
                default:;
            endcase
            // Checked negative control: illegally overwrite a stalled head.
            if(MUT!=0 && push && head_valid && !out_r)head_data<=in_data;
        end
    end
endmodule