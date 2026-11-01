module counter_induction #(parameter BAD=0)(input [15:0] age,input active,start,rst_n,mut4,output bad);
wire [31:0] MUT=mut4?4:0;
function [16:0] original(input [15:0] a,input act,input m4);
 original = ((m4?4:0)==4)?{1'b0,a}+17'd1:(act && a!=16'hffff)?{1'b0,a}+17'd2:{1'b0,a}+17'd1;
endfunction
wire [16:0] expected_current=original(age,active,mut4);
reg [15:0] age_after; reg active_after;
always @* begin
 age_after=age; active_after=active;
 if (!rst_n) begin age_after=0; active_after=0; end
 else if (start) begin age_after=0; active_after=1; end
 else if (active && age!=16'hffff) age_after=age+1'b1;
end
    // AHUB lookahead recurrence: parallel state, same edge_age value on every cycle.
    wire [16:0] edge_age_q = expected_current;
    reg [16:0] shadow_next;
    always @* begin
        shadow_next = edge_age_q;
        if (!rst_n) shadow_next = 17'd1;
        else if (start) shadow_next = (MUT == 4) ? 17'd1 : (BAD ? 17'd3 : 17'd2);
        else if (active && age != 16'hffff && ((MUT == 4) || age != 16'hfffe))
            shadow_next = edge_age_q + 17'd1;

    end
assign bad=shadow_next!=original(age_after,active_after,mut4);
endmodule
