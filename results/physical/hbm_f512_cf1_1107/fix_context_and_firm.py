#!/usr/bin/env python3
"""Fresh vCF1b: restore generated SDC context and avoid tiny GPL regions."""
from pathlib import Path
import json,shutil,re,sys
here=Path(__file__).resolve().parent;dst=Path(sys.argv[1]);assert not dst.exists();shutil.copytree(here/'kit_inputs',dst)
s=(dst/'config.mk').read_text();name='/work/rtl/ot_hbm_face_rst_relay.sv';ls=[]
for l in s.splitlines():
 if re.match(r'^(?:override )?export VERILOG_FILES \+=',l):continue
 if re.match(r'^(?:override )?export VERILOG_FILES =',l)and name not in l:l+=' '+name
 ls.append(l)
(dst/'config.mk').write_text('\n'.join(ls)+'\n')
# This JSON is generated input to lint_kit_files, not just a past gate verdict.
shutil.copy2(here/'base_sdc_lint_context.json',dst/'sdc_lint.json')
shutil.copy2(here/'input_relay_firm.tcl',dst/'input_relay_firm.tcl')
p=dst/'face_flops.tcl';p.write_text(p.read_text().replace('source /work/input_relay_guide.tcl','source /work/input_relay_firm.tcl'))
p=dst/'face_flops_release.tcl';p.write_text(p.read_text().replace('source /work/input_relay_guide_release.tcl','# No GPL regions; the normal face release ledger includes all mid-relays.'))
j=json.load(open(dst/'FORM_CANDIDATE.json'));j.update(form='f512_vCF1b',operational_repair='complete filelist and original byte-exact generated SDC context',placement_repair='existing ff_put_near FIRM/site ledger replaces one-FF inclusive regions after independent class pilot GPL NaN');(dst/'FORM_CANDIDATE.json').write_text(json.dumps(j,indent=1)+'\n');(dst/'.keep').touch()
