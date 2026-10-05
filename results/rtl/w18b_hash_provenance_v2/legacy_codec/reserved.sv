module tb; wire [511:0] r; wire ok; ot_chip_v41x_kv_enc #(.CODEC(1)) e(.v(1024'd0),.rec(r),.ok(ok)); endmodule
