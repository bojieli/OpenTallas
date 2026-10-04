module leaf(input clk,input [63:0] din,output reg [71:0] q);
reg [63:0] d;
  function automatic [71:0] encode64(input [63:0] data);
    reg [71:0] c; integer p, k, j;
    begin
      c='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin c[p-1]=data[j]; j=j+1; end
      for (k=0;k<7;k=k+1)
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0 && p!=(1<<k)) c[(1<<k)-1]=c[(1<<k)-1]^c[p-1];
      c[71]=^c[70:0]; encode64=c;
    end
  endfunction
always @(posedge clk) begin d<=din;q<=encode64(d);end
endmodule
