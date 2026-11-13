module inv(input wire clk, input wire rst_n, input wire fill_start, input wire stop, input wire [11:0] total);
  reg [11:0] ordinal; reg [12:0] ordinal8; reg filling;
  always @(posedge clk or negedge rst_n)
    if(!rst_n) begin filling<=0; ordinal<=0; ordinal8<=13'd8; end
    else begin
      if(fill_start) begin filling<=1; ordinal<=0; ordinal8<=13'd8; end
      if(filling&&!stop) begin
        if(ordinal8>=total) filling<=0;
        else begin ordinal<=ordinal8[11:0]; ordinal8<=ordinal8+13'd16; end
      end
    end
  initial begin ordinal=0; ordinal8=13'd8; filling=0; end
  always @* assert(ordinal8 == {1'b0,ordinal} + 13'd8);
endmodule
