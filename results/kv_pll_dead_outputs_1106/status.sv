module status(input refclk,por_n,output locked);
qkd_pll_analog_model u_pll(.refclk(refclk),.por_n(por_n),.locked(locked));
endmodule
