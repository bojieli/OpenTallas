module t (); wire n_diff, n_same; BLKA a (.o(n_diff), .p(n_same)); BLKB b (.i(n_diff), .j(n_same)); endmodule
