// At most24 parent record mux bits per independently published select FF.
(* keep_hierarchy="yes" *) module qfd_sysface_select_local #(parameter integer W=24,ID=0)(input wire s,input wire[W-1:0]a,b,output wire[W-1:0]y);
 assign y=s?b:a;
endmodule
