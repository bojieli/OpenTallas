from pathlib import Path
import re,json
P=Path(__file__).parent;src=(P/'inputs/phy_capture_optional_input.v').read_text();gold=src.replace('module qkd_hr_phy_adp #','module qkd_hr_phy_adp_gold_zero #').replace('CREDIT_RETURN_CAPTURE = 1','CREDIT_RETURN_CAPTURE = 0');(P/'phy_gold_zero.v').write_text(gold)
s=src.replace('module qkd_hr_phy_adp #','module qkd_hr_phy_adp_zero_m1 #').replace('CREDIT_RETURN_CAPTURE = 1','CREDIT_RETURN_CAPTURE = 0');s=s.replace('ot_sram_1r1w_512x128_m2_r2c2','ot_sram_1r1w_512x128_m1_r2c2').replace(".rr_addr(16'h0000)",".rr_addr(18'h00000)")
old='''  reg [3:0] \\u_slice.u_body.o_cred ;''';new='''  wire [3:0] \\u_slice.u_body.o_cred ;
  (* keep = 1 *) reg [3:0] hr_credit_base;
  (* keep = 1 *) reg hr_credit_capture_q;
  assign \\u_slice.u_body.o_cred = hr_credit_base + {3'b000, hr_credit_capture_q};''';assert s.count(old)==1;s=s.replace(old,new)
old='''  always @(posedge ck, negedge \\u_slice.u_body.rs )
    if (!\\u_slice.u_body.rs ) \\u_slice.u_body.o_cred  <= 4'h5;
    else \\u_slice.u_body.o_cred  <= _016_;''';new='''  // Zero-cycle state encoding: logical C = base + last captured return (mod16).
  // Post-edge C = (oldC-pop_rb)+current_r_cr, exactly the original update.
  always @(posedge ck, negedge \\u_slice.u_body.rs )
    if (!\\u_slice.u_body.rs ) begin hr_credit_base <= 4'h5; hr_credit_capture_q <= 1'b0; end
    else begin hr_credit_base <= _075_; hr_credit_capture_q <= r_cr[0]; end''';assert s.count(old)==1;s=s.replace(old,new)
(P/'phy_zero_m1.v').write_text(s);mut=s.replace('module qkd_hr_phy_adp_zero_m1 #','module qkd_hr_phy_adp_zero_m1_mut #').replace('hr_credit_capture_q <= r_cr[0];','hr_credit_capture_q <= ~r_cr[0];');(P/'phy_zero_m1_mut.v').write_text(mut)
json.dump({'status':'SOURCE_PREP_NOT_ADOPTED','original_return_capture':0,'macro_mux':1,'macro_cycles_added':0,'credit_cycles_added':0,'extra_credit_state_ff':1,'original_reset_counter':5,'encoded_reset_base':5,'encoded_reset_capture':0,'invariant':'logical_o_cred=(hr_credit_base+hr_credit_capture_q) mod16; base_next=logical_o_cred-pop_rb; capture_next=r_cr','port_scope':'r_cr has only its direct capture load after dead old expression cleanup; o_cred is internal, public outputs retain existing FFs','internal_macro_abi':'rr_addr16 zero->18 zero, rr_en0 disables repairs; mask allones; no public ABI change'},open(P/'zero_credit_recode.json','w'),indent=1)
