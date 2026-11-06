module decode_miter(input[31:0] vv,id,input[7:0]rk,f8,input h,input[1:0]si,input ok,output bad);
localparam EW=86,RANK_W=8;
    function automatic [31:0] native_okey(input [31:0] x);
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'h0 : x;
            native_okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
 function automatic [EW-1:0] native_dec(input [31:0] vv,input [31:0] id,input [7:0] rk,input [7:0] f8,input h,input [1:0] s_,input ok);
  begin
   native_dec={1'b0,1'b1,native_okey(vv),~id,~rk[RANK_W-1:0],~{f8,h,s_},(vv==32'h80000000)};
   if(vv==32'hffffffff||!ok)native_dec=0;
  end
 endfunction
  function automatic [85:0] ot_del_decode(input [31:0] vv,input [31:0] id,input [7:0] rk,input [7:0] f8,input h,input [1:0] si,input ok);
    reg [31:0] norm,ordered;
    begin
      norm=vv;
      ordered=norm[31]?~norm:(norm|32'h80000000);
      ot_del_decode={1'b0,1'b1,ordered,~id,~rk,~{f8,h,si},(vv==32'h80000000)};
      if(vv==32'hffffffff || !ok)ot_del_decode=86'd0;
    end
  endfunction
assign bad=|(native_dec(vv,id,rk,f8,h,si,ok)^ot_del_decode(vv,id,rk,f8,h,si,ok));
endmodule
