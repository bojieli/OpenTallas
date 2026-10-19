// q3h C_B16 bench helpers: the op's ib and the TDM x line of (op, local column, station index)
`ifndef Q3H_CB16_TBDEFS
`define Q3H_CB16_TBDEFS
`define Q3H_IB(o) {{47{8'((o) * 37 + 8'h3C)}}, 3'((o) + 1)}
`define Q3H_LINE(o, c, s) ({8'(o), 8'(c), 8'(s), 8'hA5, 32'h0F1E_2D3C} ^ {16'h0, 8'((o) * 13 + (c) * 7 + (s) * 3), 40'h0})
`endif
