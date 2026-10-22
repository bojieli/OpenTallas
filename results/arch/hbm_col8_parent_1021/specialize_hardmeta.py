#!/usr/bin/env python3
"""Consume fixed metadata parameter into the exact CLOSED physical master."""
from pathlib import Path
import hashlib,json
p=Path('rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_quarter_col8_control.sv')
meta=Path('rtl/hdc/v41x/ot_hidx_meta_sram146.sv');expected='e6546dff0e32e203f3a61bc7d2e755305d179f662daadda0dddcb19ede71d24f'
assert hashlib.sha256(meta.read_bytes()).hexdigest()==expected, 'metadata implementation differs from CLOSED source'
s=p.read_text();old='ot_hidx_meta_sram146 #(.D(146)) md(';new='ot_hidx_meta_sram146 md(';assert s.count(old)==1
out=Path('rtl/hdc/v41x/col8_parent_1021/quarter_control_hardmeta.v');out.write_text(s.replace(old,new))
r={'functional_source':str(p),'functional_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'physical_source':str(out),'physical_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'exact_transform':{'before':old,'after':new,'sites':1,'instances_after_elaboration':2},'master':'ot_hidx_meta_sram146','D':146,'closed_record':'06d0f5e44','closed_main':'6a5b95375','metadata_functional_sha256':expected,'ports':'Unchanged, including clk and clk_mem; both driven by clk_meta[e]. No data or clock/reset wiring changes.'}
Path('results/arch/hbm_col8_parent_1021/hardmeta_specialization.json').write_text(json.dumps(r,indent=2)+'\n')
