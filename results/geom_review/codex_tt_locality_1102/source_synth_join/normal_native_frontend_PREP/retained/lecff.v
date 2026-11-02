(* techmap_celltype = "$_DFF_P_ $_DFF_N_" *)
module _lec_ff (C, D, Q);
  parameter _TECHMAP_CELLTYPE_ = "";
  input C, D;
  output Q;
  (* keep *) wire \_TECHMAP_REPLACE_.lecq ;
  $dff #(.WIDTH(1), .CLK_POLARITY(_TECHMAP_CELLTYPE_ == "$_DFF_P_")) _TECHMAP_REPLACE_ (.CLK(C), .D(D), .Q(\_TECHMAP_REPLACE_.lecq ));
  assign Q = \_TECHMAP_REPLACE_.lecq ;
endmodule
