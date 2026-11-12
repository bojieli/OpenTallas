module miter #(parameter integer W=277)(input wire clk,rst_n,in_v,out_r,input wire[W-1:0]in_data);
 wire gr,gv,dr,dv,ghv,gtv,dhv,dtv;wire[W-1:0]go,do_,ghd,gtd,dhd,dtd;
 skid_gold #(.WIDTH(W)) g(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_r(gr),.in_data(in_data),.out_v(gv),.out_r(out_r),.out_data(go),.d_hv(ghv),.d_tv(gtv),.d_hd(ghd),.d_td(gtd));
 skid_gate #(.WIDTH(W)) d(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_r(dr),.in_data(in_data),.out_v(dv),.out_r(out_r),.out_data(do_),.d_hv(dhv),.d_tv(dtv),.d_hd(dhd),.d_td(dtd));
 always @* begin
  assert(gr==dr); assert(gv==dv); assert(!gv||go==do_);
  assert(ghv==dhv); assert(gtv==dtv); assert(!ghv||ghd==dhd); assert(!gtv||gtd==dtd);
 end
endmodule
