`timescale 1ns/1fs
module tb_owned_root_positional;
 // All12 legacy positional arguments retain their original meanings.
 ot_hbm_hc_root_static #(20480,32'h46a00000,0,0,1,0,7,2,0,7,8,6) legacy();
 initial begin
  if(legacy.NOUT!=24||legacy.WROW0!=0||legacy.OROW0!=0||legacy.QB!=7||legacy.NVQ!=8||legacy.QWW!=6)
   $fatal(1,"legacy positional parameter ABI changed");
  $display("OWNED_ROOT_LEGACY_POSITIONAL_ABI_PASS");$finish;
 end
endmodule
