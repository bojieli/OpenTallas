from pathlib import Path
import shutil
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');a=r/'QREL_exact_v1';b=r/'QREL_exact_v2';b.mkdir(exist_ok=False)
for n in ['ot_s81sl_xrt.sv','ot_rst_relay.sv','tb_exact_xrt.sv','source.json']:shutil.copyfile(a/n,b/n)
(b/'ref_xrt.sv').write_text((a/'ref_xrt.sv').read_text().replace('ref_ot_s81sl_xrt','ref_s81sl_xrt'))
(b/'.keep').write_text('criticalQREL currentXRT fixture-name retry; v1failurepreserved\n')
