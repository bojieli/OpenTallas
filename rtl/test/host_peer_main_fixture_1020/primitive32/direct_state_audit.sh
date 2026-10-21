#!/bin/bash
set -eu
mkdir -p audit
cat > audit/coupon.v <<'SV'
module coupon(input ck,rst,input d,output a,b,c,e);
DFFHQNx1_ASAP7_75t_R u_a(.CLK(ck),.D(d),.QN(a));
DFFHQNx1_ASAP7_75t_R u_b(.CLK(ck),.D(d),.QN(b));
DFFASRHQNx1_ASAP7_75t_R u_c(.CLK(ck),.D(d),.RESETN(rst),.SETN(1'b1),.QN(c));
DFFASRHQNx1_ASAP7_75t_R u_e(.CLK(ck),.D(d),.RESETN(rst),.SETN(1'b1),.QN(e));
endmodule
SV
for variant in async direct;do
 { echo 'read_verilog canonical_ASR_normalized.v canonical_DFF_normalized.v audit/coupon.v';echo 'hierarchy -top coupon; flatten; proc; opt_expr; opt_clean';echo "write_json audit/$variant.pre.json";[ "$variant" != async ] || echo async2sync;echo clk2fflogic;echo "write_json audit/$variant.post.json"; } > "audit/$variant.ys"
 docker run --rm -v "$PWD:/work" -w /work openroad/orfs:latest yosys -Q -T -s "audit/$variant.ys" > "audit/$variant.log" 2>&1
 done
