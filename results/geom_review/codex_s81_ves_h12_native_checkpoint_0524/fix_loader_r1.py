from pathlib import Path
import json,hashlib,os
r=Path('/srv/opentallas-scratch2/claude/codex-ves-h12-prep-0524');k=r/'pass_m12_r1';b=k/'run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base'
(b/'INPUT_ROUTED').symlink_to('../../../../../baseline',target_is_directory=True)
assert (b/'INPUT_ROUTED/6_final.odb').resolve()==k/'baseline/6_final.odb'
f=k/'private_runtime_prepare.py';s=f.read_text();s=s.replace("replacement=b'load_design /work/baseline/6_final.odb 4_cts.sdc\\n'","replacement=b'load_design INPUT_ROUTED/6_final.odb 4_cts.sdc\\n'")
s=s.replace("target=scripts/'global_route.tcl';", "inp=Path('/work/run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base/INPUT_ROUTED/6_final.odb')\nif inp.resolve()!=Path('/work/baseline/6_final.odb') or not inp.is_file():raise SystemExit('OWN_IMMUTABLE_ROUTED_SYMLINK_REQUIRED')\ntarget=scripts/'global_route.tcl';")
f.write_text(s)
f=k/'run_grt_only.sh';s=f.read_text().replace('0524/pass_m12\n','0524/pass_m12_r1\n').replace('ves-h12-native-grt-0524','ves-h12-native-grt-r1-0524');s=s.replace('sha256sum -c FROZEN_INPUTS.sha256\ndocker run','test "$(realpath "$K/run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base/INPUT_ROUTED/6_final.odb")" = "$K/baseline/6_final.odb"\nsha256sum -c FROZEN_INPUTS.sha256\ndocker run',1);f.write_text(s)
p=json.loads((k/'PRD.json').read_text());p['source_route']=str(k/'baseline/6_final.odb');p['loader_reference']='INPUT_ROUTED/6_final.odb';(k/'PRD.json').write_text(json.dumps(p,indent=2))
(r/'INFRA_RETRY_R1.json').write_text(json.dumps({'failed_unit':'4116935-1793631377','failed_status':'EXIT2_BEFORE_DB_LOAD_PG_BEGIN_OR_REPAIR','reason':'load_design prepends RESULTS_DIR to absolute argument','first_package':'120229c838d1b063965e82a9b1a374c53324167133de9ae8804415cadc74cdd1','new_loader':'INPUT_ROUTED/6_final.odb','relative_link':str((b/'INPUT_ROUTED').readlink()),'resolved':str((b/'INPUT_ROUTED/6_final.odb').resolve()),'source_unchanged':hashlib.sha256((k/'baseline/6_final.odb').read_bytes()).hexdigest(),'modes_caps_guards_unchanged':True,'fresh_output_dir':str(k)},indent=2))
