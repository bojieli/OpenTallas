module live(input refclk,por_n,output locked,clock_observable);
qkd_pll_analog_model u_pll(.refclk(refclk),.por_n(por_n),.locked(locked),.pll_c(clock_observable));
endmodule
