(* keep_hierarchy = "yes" *) module dsdv_idx_query_odd(input wire p,input wire[11:0]pw,output wire y);
assign y=p && pw<12'd64 && pw[0];
endmodule

(* keep_hierarchy = "yes" *) module dsdv_idx_query_even(input wire p,input wire[11:0]pw,output wire y);
assign y=p && pw<12'd64 && !pw[0];
endmodule
