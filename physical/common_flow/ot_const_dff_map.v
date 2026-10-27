// Original positive-edge state only. ASAP7 QN is !D; invert D to retain Q=D.
module \$_DFF_P_ (D, C, Q);
input D, C;
output Q;
(* keep=1, dont_touch=1 *)
DFFHQNx2_ASAP7_75t_R _TECHMAP_REPLACE_ (.D(~D), .CLK(C), .QN(Q));
endmodule
