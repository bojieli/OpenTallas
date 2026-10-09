#!/usr/bin/env python3
"""Prepare a NEW config-only checkpoint lineage; never alter the original run."""
import hashlib,json,pathlib,shutil,sys
old,out,src,w=map(pathlib.Path,sys.argv[1:])
assert old.resolve()!=out.resolve()
bases=list((old/'results/asap7').glob('*/base'));assert len(bases)==1
odb=bases[0]/'3_place.odb'; expected='7faacf15e72e118e151e0cee53082099d70d62019ba4f000a9c460951a72a439'
actual=hashlib.file_digest(odb.open('rb'),'sha256').hexdigest();assert actual==expected
assert not (bases[0]/'4_cts.odb').exists(), 'inventory changed; review checkpoint again'
assert not out.exists(), 'fresh destination required'
oldsrc=old.parents[3]/'src'
rtl=['rtl/physical/ot_qwen_die_io_xfifo.sv','rtl/physical/ot_qwen_die_cdc_ch.sv',
 'rtl/physical/ot_qwen_async_fifo_w.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv']
for path in rtl:
 assert (oldsrc/path).read_bytes()==(src/path).read_bytes(), 'RTL changed: '+path
shutil.copytree(old,out,copy_function=shutil.copy2)
# Existing clock/pin/physical topology is reused byte-for-byte; only the
# approved scoped Gray constraints and current flow hooks change at CTS.
config=out/'config.mk';text=config.read_text()
text=text.replace('OT_MM_FF_SDC = /src/physical/qwen_die_masters/signoff/qfd_io_xfifo_p2.sdc',
                  'OT_MM_FF_SDC = /src/physical/qwen_die_masters/signoff/qfd_io_xfifo_p2_gray.sdc')
config.write_text(text)
for n,f in enumerate(['cg_pushdown.tcl','clk_net_protect.tcl','link_budget_hook.tcl']):
 shutil.copy2(src/'physical/common_flow'/f,out/'hooks'/f'ot_cts_fix_{n}_{f}')
shutil.copy2(src/'physical/common_flow/link_budget_consistent.sdc',out/'hooks/link_budget_consistent.sdc')
hook=out/'hooks/pre_cts_ot_cts_fix.tcl'
with hook.open('a') as f:f.write('\nsource /src/physical/qwen_die_masters/signoff/qfd_io_xfifo_gray_cdc.tcl\n')
# Copytree preserves the completed objects; mutable unfinished logs belong to
# the new lineage only. The old failure remains preserved at its original path.
manifest={'original_orfs':str(old),'new_orfs':str(out),'checkpoint_sha256':actual,
 'resume_stage':'4_1_cts','rtl_source':'1d3c576bb','approved_overlay':'J6/I12',
 'old_failure_preserved':True,'source_commit':(src/'SOURCE_COMMIT').read_text().strip() if (src/'SOURCE_COMMIT').exists() else None}
(w/'checkpoint_import.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest))
