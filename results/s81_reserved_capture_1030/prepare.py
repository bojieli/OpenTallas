from pathlib import Path
import hashlib,json,re
p=Path(__file__).parent
source=(p/'original_t1.sv').read_text()
assert '.leafdn_i0({leafdn_i0[597], leafdn_i0[593:0]})' in source
# Actual wrapper's bound connection proves reserved inputs do not enter functional body.
assert source.count('leafdn_i0')==4, source.count('leafdn_i0')
insert='''    // PRIVATE CANDIDATE: capture exactly three reserved plan inputs, zero observable cycles.
    ot_dp_reserved_capture u_bin_reserved_leafdn_i0 (.clk(clk), .d(leafdn_i0[596:594]));
'''
module='''
(* keep_hierarchy = "yes" *) module ot_dp_reserved_capture(input wire clk, input wire [2:0] d);
    (* keep = "true", dont_touch = "true" *) reg [2:0] q;
    always @(posedge clk) q <= d;
endmodule
'''
pos=source.index('    s81p_ot_s81sl_kv_leaf__t1_bound ')
candidate=source[:pos]+insert+source[pos:]
candidate=candidate.replace('`default_nettype wire',module+'`default_nettype wire')
(p/'candidate_t1.sv').write_text(candidate)
(p/'reserved_capture.sv').write_text(module)
receipt={'private_candidate':True,'adopted':False,'port':'leafdn_i0','bits':[594,595,596],'epoch_bit':597,'functional_bound_data_bits':[0,593],'functional_body_connection_unchanged':True,'added_dff':3,'observable_added_cycles':0,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'remaining_failures':['t1 FT3 spare capture','current wrapper/source ABI qualification','native hard views/composition']}
(p/'candidate.json').write_text(json.dumps(receipt,indent=2)+'\n')
