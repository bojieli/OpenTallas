#!/usr/bin/env python3
"""Use the actual canonical fan-root as golden; seed an independent guard-bypass control."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
root=here.parents[6]
rtl=root/'rtl/qwen_sys/static_kv_die_20261017'
text=(rtl/'qkd_kv_ctl_nc32_face.sv').read_text()
a=text.index('module qkd_kv_es_fan_root2_b_nc32');b=text.index('endmodule',a)+len('endmodule')
ref=text[a:b]+'\n'
new=(rtl/'qkd_kv_es_fan_root2_b_nc32_bpin.sv').read_text()
needle='wire [NU-1:0] ubc = {NU{bw_p[0]}} & ub_guard_q;'
assert new.count(needle)==1
mut=new.replace('module qkd_kv_es_fan_root2_b_nc32_bpin #','module qkd_kv_es_fan_root2_b_nc32_bpin_mut #').replace(needle,'wire [NU-1:0] ubc = {NU{bw_p[0]}};')
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
for name,body in [('ref',ref),('new',new),('mut',mut)]: (out/(name+'.sv')).write_text(body)
