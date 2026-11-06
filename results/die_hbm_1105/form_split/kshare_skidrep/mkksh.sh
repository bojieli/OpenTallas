#!/usr/bin/env bash
# HBM-REFORM-B9: kshare skid-replication form kit from the kshare4c kit (kit files only; run outputs left behind)
set -eu
S=/srv/opentallas-scratch3/claude/die-hbm-66/forms/kshare4c/ot_hbm_svc_vm_kshare_splitstrap__v8e478a_d5b635a85881
D=/srv/opentallas-scratch2/claude/hbm-reform-b9/ksh/ot_hbm_svc_vm_kshare_splitstrap__v8e478a_d5b635a85881
B=/srv/opentallas-scratch2/claude/hbm-reform-b9/ksh/bench
test ! -e $D
mkdir -p $D
cd $S
for f in * .kw_inputs.json; do
  [ -f "$f" ] || continue
  # kit files are group-writable; run outputs (logs, json receipts, placed.csv) are not
  [ -n "$(find "$f" -maxdepth 0 -perm -g+w)" ] || continue
  case "$f" in run_finish.log|lec.py.routed) continue;; esac
  cp -p "$f" $D/
done
cp -rp rtl reset_contract $D/; mkdir -p $D/face_shell_work
python3 -I - $D/rtl/ot_hbm_svc_pc_ctrl_leaf.sv $B/skid_new.sv <<'P'
import sys,re
f,n=sys.argv[1],sys.argv[2]; s=open(f).read(); new=open(n).read()
i=s.index("module ot_hbm_svc_pin_skid2"); j=s.index("endmodule",i)+len("endmodule")
# keep the comment block above the module; replace module text
s=s[:i]+new[new.index("module ot_hbm_svc_pin_skid2"):].rstrip()[:-len("endmodule")]+"endmodule"+s[j:]
s=s.replace("module ot_hbm_svc_pin_skid2","// HBM-REFORM-B9 kshare RE-FORM 11-05: control replicated per 64-bit data slice (see skid_new.sv in the lane bench)\nmodule ot_hbm_svc_pin_skid2",1)
open(f,"w").write(s)
P
cat > $D/FORM_SKIDREP.json <<J
{"form": "kshare skid control replication (RE-FORM after two strikes kshare4ct / kshare4ct2)", "by": "HBM-FORM-SPLIT-6+REFORM-B9",
 "ruling": "COORD 14:21 11-05 RE-FORM; lane estimate: 158k logic cells (951k incl 773k fill), util 0.10 -> no split, fanout form fix",
 "change": "ot_hbm_svc_pin_skid2: cnt/wp/rp replicated per 64-bit slice (keep); enables and out_data selects drive <=64 bits; ports/edges unchanged",
 "proof": "skid lock-step old vs new 200k cycles W=277/286/340/5 PASS, MUT cross FAIL (epyc4 hbm-reform-b9/ksh/bench)",
 "source_kit": "epyc4:$S", "pin_cycles": "none added (kshare4c FORM_PINCYCLES unchanged)"}
J
du -sh $D; ls $D | wc -l
