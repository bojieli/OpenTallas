#!/usr/bin/env python3
"""Emit the CTL_PRE integration lockstep and ownership mutant.

The old input is the actual flat vE RTL directory; the new source is this repo.
The vehicle supplies legal 80-beat loads and a closed-SEQ token-response boundary.
It checks every HSF output against vE, CTL_PRE=0 separately, complete first replay,
matching retirement overlapping the second START, FIFO tag identity/pop and reset.
This complements the seq_fan and static_issue mechanism proofs. It is not a
full-child protocol proof, physical LEC, or compiler/PIN-cycle adoption.
Run emitted run.sh only through plain ot-run on an eligible remote host.
"""
from pathlib import Path
import argparse, re, shutil
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--old-rtl",type=Path,required=True)
p.add_argument("--sram-model",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
p.add_argument("--partial",action="store_true",help="exercise optional partial capture at the same +1 PIN latency")
a=p.parse_args()
repo=Path(__file__).resolve().parents[2]
files={
 "ot_dsrom_mtp_seq.sv":"rtl/dsrom_sys/mtp",
 "dsfd_mtp_tops.sv":"rtl/dsrom_sys/mtp",
 "ot_s81hd_ctl_hsf0_static.sv":"rtl/dsrom_sys/s81_head",
 "ot_s81hd_static_issue.sv":"rtl/dsrom_sys/s81_head",
 "ot_s81hd_util.sv":"rtl/dsrom_sys/s81_head",
 "ot_s81hd_best64.sv":"rtl/dsrom_sys/s81_head",
 "ot_s81hd_lsc_parts.sv":"rtl/dsrom_sys/s81_head",
 "ot_s81hd_beat_link.sv":"rtl/dsrom_sys/s81_head",
 "ot_s81hd_mesh_ep_core.sv":"rtl/dsrom_sys/s81_head",
 "ot_link_crc32.sv":"rtl/link",
 "ot_link_credit_rx_b64.sv":"rtl/common",
 "ot_link_credit_tx_rc.sv":"rtl/common",
 "ot_dsrom_mtp_link_pair.sv":"rtl/dsrom_sys/mtp",
 "ot_rst_relay_tree3.sv":"rtl/lib",
}
old="".join((a.old_rtl/f).read_text()+"\n" for f in files)
new="".join((repo/d/f).read_text()+"\n" for f,d in files.items())
names=sorted(set(re.findall(r"^\s*(?:\(\*[^)]*\*\)\s*)?module\s+(\w+)",old,re.M)),key=len,reverse=True)
pattern=re.compile(r"\b("+"|".join(map(re.escape,names))+r")\b")
a.out.mkdir(parents=True,exist_ok=False)
(a.out/"old.v").write_text(pattern.sub(lambda m:m[1]+"_O",old))
(a.out/"new.v").write_text(new)
needle="else op_q1 <= ri_v && ri_q[3:1] == K_XB && rt_q[31] &&"
assert new.count(needle)==1
mut=new.replace(needle,"else op_q1 <= ri_v && ri_q[3:1] == K_XB && rt_q[31] || 1'b0 &&",1)
(a.out/"mut_op.v").write_text(mut)
tb=Path(__file__).with_name("head_ctl_pre_start_tb.sv").read_text()
tb=tb.replace('mism=mism+1;if(mism<5)$display("MISMATCH cycle %0d",cyc);','$fatal(1,"MISMATCH cycle %0d",cyc);')
tb=tb.replace('mism=mism+1;if(mism<5)$display("OP_INVARIANT cycle %0d",cyc);','$fatal(1,"OP_INVARIANT cycle %0d",cyc);')
if a.partial:
 tb=tb.replace(".SRAM_RAW_CAPTURE(1),.CTL_PRE(1)",".SRAM_RAW_CAPTURE(0),.SRAM_PARTIAL_CAPTURE(1),.CTL_PRE(1)")
tb=tb.replace("default_off=PASS","CTL_PRE_off=PASS")
(a.out/"tb.sv").write_text(tb)
shutil.copyfile(a.sram_model,a.out/"sram.v")
(a.out/"run.sh").write_text("""#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for k in positive mutant; do
 f=new.v; [ "$k" = positive ] || f=mut_op.v
 iverilog -g2012 -DNEWMOD=ot_s81hd_ctl_hsf0_static -s tb_hsf -o sim_$k old.v "$f" sram.v tb.sv >build_$k.log 2>&1
 if vvp sim_$k >run_$k.log 2>&1; then
  [ "$k" = positive ] || { echo MUTANT_SURVIVED;exit 1; }
  grep -q HSF_START_PASS run_$k.log
 else
  [ "$k" = mutant ] || { cat run_$k.log;exit 1; }
  grep -qE 'FATAL|OP_INVARIANT|MISMATCH' run_$k.log
 fi
 tail -4 run_$k.log
done
""")
print(a.out)
