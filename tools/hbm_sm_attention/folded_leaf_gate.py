#!/usr/bin/env python3
"""Minimal actual command-to-leaf folded publication vehicle; no full-SM claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sm_elem_bench as E

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument("--work",required=True)
a=ap.parse_args()
work=Path(a.work).resolve();work.mkdir(parents=True,exist_ok=True)
# The existing compiler owns bit positions. Distinct assertions exercise all
# values in command[131:124], including parity-independent folded publication.
for aa in range(8):
 for bb in range(8):
  w=E.cmd_word(mode=6,h128=1,fold=1,fold_a=aa,fold_b=bb,folded_publish=1)
  assert (w>>131)&1 and (w>>128)&7==aa and (w>>125)&7==bb and (w>>124)&1
cal,metadata=E.compile_folded_publication(240)
cal.write(work,500)
vl=os.environ.get("VERILATOR",os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
src=[s for s in E.SRC if not s.endswith("tb_hbm_smh_attn.sv")]
src += ["rtl/test/hbm_accel/sm_attn/tb_hbm_sm_folded_leaf.sv","rtl/hbm_accel/generic/collective/p2p/f32add.c"]
obj=work/"obj"
cmd=[vl,"--binary","--timing","-j","4","-O2","-Wno-fatal","-Wno-lint","-Wno-style","-Wno-TIMESCALEMOD","-Wno-MULTIDRIVEN","--unroll-count","128","--top-module","tb_hbm_sm_folded_leaf","-DOT_SMH_HIER","-DOT_SMH_FC_HIER","--Mdir",str(obj)]+[str(E.ROOT/s) for s in src]
with (work/"build.log").open("w") as f:
 result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
if result.returncode:raise SystemExit("build failed: "+str(work/"build.log"))
results=[]
for mutant in range(3):
 cmd=[str(obj/"Vtb_hbm_sm_folded_leaf"),"+CMD="+str(work/"cmd.hex"),"+mutant="+str(mutant)]
 result=subprocess.run(cmd,capture_output=True,text=True)
 output=result.stdout+result.stderr
 (work/("run"+str(mutant)+".log")).write_text(output)
 print(output,end="")
 expect="FOLDED_LEAF PASS" if mutant==0 else "FOLDED_LEAF MUTANT REJECTED"
 if result.returncode or expect not in output:raise SystemExit("gate failed mutant="+str(mutant))
 results.append(dict(mutant=mutant,verdict="PASS" if mutant==0 else "REJECTED",returncode=result.returncode))
receipt=dict(verdict="PASS",scope="one actual leaf, all 8 column straps and 4 row straps; declared BF16 row boundary seeds real native arithmetic and stack; actual frontend command124/fold131:125 -> XS -> fold -> scalar publication",full_SM_qualification=False,physical_qualification=False,calendar=metadata,results=results,source_sha256={s:hashlib.sha256((E.ROOT/s).read_bytes()).hexdigest() for s in src},compiler_sha256=hashlib.sha256(Path(E.__file__).read_bytes()).hexdigest(),binary_sha256=hashlib.sha256((obj/"Vtb_hbm_sm_folded_leaf").read_bytes()).hexdigest())
(work/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
