module ICGx1_ASAP7_75t_R(input CLK, input ENA, input SE, output GCLK); assign GCLK = CLK & (ENA | SE); endmodule  // LEC-only functional stand-in (mutant run)
