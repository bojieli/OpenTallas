#!/usr/bin/env python3
"""Assemble fresh vCF1a inputs after vCF1 failed before synthesis.

The standalone preflight reads one complete VERILOG_FILES assignment; make's
+= append alone did not include the reset module for that reader.  No RTL or
physical constraint changes.  Preserve the failed vCF1 directory separately.
"""
from pathlib import Path
import sys,shutil,re,json
src=Path(__file__).resolve().parent/'kit_inputs';dst=Path(sys.argv[1]);assert not dst.exists(),dst
shutil.copytree(src,dst)
p=dst/'config.mk';s=p.read_text();name='/work/rtl/ot_hbm_face_rst_relay.sv';lines=[]
for line in s.splitlines():
 if re.match(r'^(?:override )?export VERILOG_FILES \+=',line):continue
 if re.match(r'^(?:override )?export VERILOG_FILES =',line)and name not in line:line+=' '+name
 lines.append(line)
p.write_text('\n'.join(lines)+'\n')
j=json.load(open(dst/'FORM_CANDIDATE.json'));j.update(form='f512_vCF1a',operational_repair='full VERILOG_FILES assignment includes existing reset relay for all readers; vCF1 failed RTL_LINT before synthesis');(dst/'FORM_CANDIDATE.json').write_text(json.dumps(j,indent=1)+'\n');(dst/'.keep').touch()
