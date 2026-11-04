// LEC model of the clock gate on both sides: the enable-to-clock function compared combinationally on every named clock net
module ot_hdc_cg (input wire clk, input wire en, output wire gclk);
    assign gclk = clk & en;
endmodule
