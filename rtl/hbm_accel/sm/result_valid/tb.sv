module tb;
  reg [7:0] v, f;
  wire rv, fe, legacy_rv, legacy_fe;
  reg expected_rv, expected_fe;
  integer vi, fi, checks=0;
  ot_hbm_accel_smh_result_valid #(.NC(8),.ENABLE(1)) dut(v,f,rv,fe);
  ot_hbm_accel_smh_result_valid #(.NC(8),.ENABLE(0)) legacy(v,f,legacy_rv,legacy_fe);
  initial begin
    for (vi=0;vi<256;vi=vi+1) begin
      for (fi=0;fi<256;fi=fi+1) begin
        v=vi;f=fi;#1;
        expected_rv=(vi==255);
        expected_fe=(((vi & fi)!=0) || ((vi!=0)&&(vi!=255)));
        if(rv!==expected_rv || fe!==expected_fe) $fatal(1,"QUALIFY_FAIL valid=%h fault=%h got=%b/%b expected=%b/%b",v,f,rv,fe,expected_rv,expected_fe);
        if(legacy_rv!==v[0] || legacy_fe!==(|f)) $fatal(1,"LEGACY_FAIL");
        checks=checks+1;
      end
    end
    $display("SM_RESULT_VALID_PASS checks=%0d stale_fault_vectors=255 partial_valid_vectors=254 NC=8",checks);
    $finish;
  end
endmodule
