D=/srv/opentallas-scratch2/claude/s81-bfasb-1111; cd /
python3 -I - <<'PY'
import json
D='/srv/opentallas-scratch2/claude/s81-bfasb-1111'
out={}
for r in ('col_h9_asb_x','col_h9_asb_nx','col_h10_asb_x'):
    out.update(json.load(open(f'{D}/runs2/{r}/candidate_measurements.json')))
json.dump(out,open(f'{D}/asbuilt_bf_measure_1111_bound.json','w'),indent=1,sort_keys=True)
for k,v in out.items(): print(k,'pv',v['pv'],'corr',v['leaf_ret_corr'],'ret',v.get('ret_run'),v['asbuilt_source_qualification']['validated_ops'])
PY
M=$D/asbuilt_bf_measure_1111_bound.json
echo "== NEW root"; python3 -I $D/pyrun.py $D/qualify.py $M
echo "== OLD TS5 root (TOK-VERIFY-1 a2/froot)"; BFASB_ROOT=/srv/opentallas-scratch2/claude/tok-verify-1/a2/froot BFASB_SCHED=$D/sched_old python3 -I $D/pyrun.py $D/qualify.py $M
echo "== OLD root with old kit at the rtl path (own root_old)"; BFASB_ROOT=$D/root_old BFASB_SCHED=$D/sched_old python3 -I $D/pyrun.py $D/qualify.py $M
echo "== TOK-VERIFY-1 b3/froot as is (rtl plan path = stale base kit)"; BFASB_ROOT=/srv/opentallas-scratch2/claude/tok-verify-1/b3/froot python3 -I $D/pyrun.py $D/qualify.py $M
