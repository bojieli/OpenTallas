set -e
R=/srv/opentallas-scratch2/claude/die-s81-85/compose1111
S=$R/s87/src; D=$R/repo/physical/die_plan/s81
cp $S/ftr/physical/die_plan/s81/delta_s81_ftregs0lm_1111.py $D/
cp $S/dead/physical/die_plan/s81/delta_dead_proof_1111.py $D/
cp $R/s87/apply_leaf_sidecars_1111.py $D/
DL=$S/dl/physical/die_plan/s81/cleanslate_1111/die_layout_s81
cp $DL/stage_s1_dielayout_1111.py $DL/stage_s1_pvso_f1r_1111.py $DL/delta_s1_svc_resite_only.json $R/s87/
cat > $D/dead_wrap_1111.py <<'PY'
"""DIE-S81-87: stage wrapper for delta_dead_proof_1111.py (in place) -> IN OUT REPORT. Runs with cwd = repo root."""
import shutil, subprocess, sys
inp, out, rep = sys.argv[1:4]
shutil.copyfile(inp, out)
r = subprocess.run([sys.executable, "-I", "physical/die_plan/s81/delta_dead_proof_1111.py", out], capture_output=True, text=True)
open(rep, "w").write(r.stdout + r.stderr)
sys.exit(r.returncode)
PY
cp $D/dead_wrap_1111.py $R/s87/
mk() { # name why script type_keys top_keys argv...
 python3 -I - "$@" <<'PY'
import json,sys
n,why,script,tk,topk=sys.argv[1:6]; argv=sys.argv[6:]
json.dump(dict(name=n,why=why,script=script,argv=argv,type_keys=json.loads(tk),top_keys=json.loads(topk)),open("/srv/opentallas-scratch2/claude/die-s81-85/compose1111/s87/stage_"+n+".json","w"),indent=1)
PY
}
mk a_leaf "CPL-S81-LEAF-2 289c9b5c + LEAF-3 3e38b28c (accepted COORD): types_after sidecars" physical/die_plan/s81/apply_leaf_sidecars_1111.py '["hard_cores","internal_stations","clock"]' '[]' '{in}' '{out}' '{report}' "$S/leaf2/physical/die_plan/s81/cleanslate_1111/cpl_s81_leaf,$S/leaf3/physical/die_plan/s81/cleanslate_1111/cpl_s81_leaf3"
mk f_ftregs "S81-GEOM-3 FTREGS0LM c1 470fc60a (accepted COORD)" physical/die_plan/s81/delta_s81_ftregs0lm_1111.py '["ft_slots","clock"]' '["clock.landing_network","ports"]' '{in}' '{out}' '{report}' --base-sha '{in_sha}'
mk d1_dielayout_svc "DIE-LAYOUT-S81 0526f88c33 svc ft re-site" "$R/repo/physical/die_plan/s81/stage_s1_dielayout_1111.py" '["ft_slots"]' '["partitions","die.channels"]' '{in}' '{out}' '{report}' "$R/s87/delta_s1_svc_resite_only.json"
mk d2_pvso_f1r "DIE-LAYOUT-S81 pvso F1 +57.24" "$R/repo/physical/die_plan/s81/stage_s1_pvso_f1r_1111.py" '["hard_cores","contents","clock","note"]' '[]' '{in}' '{out}' '{report}' 57.24
mk z_dead "S81-BIND-2 dead-input re-proof 2122a3c72d (last)" physical/die_plan/s81/dead_wrap_1111.py '["dead_inputs","note"]' '[]' '{in}' '{out}' '{report}'
cp $DL/stage_s1_dielayout_1111.py $DL/stage_s1_pvso_f1r_1111.py $D/
echo done
