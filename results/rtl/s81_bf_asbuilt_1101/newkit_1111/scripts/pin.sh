D=/srv/opentallas-scratch2/claude/s81-bfasb-1111; cd /
python3 -I - <<'PY'
import json,hashlib
m=json.load(open('/srv/opentallas-scratch2/claude/s81-bfasb-1111/asbuilt_bf_measure_1111.json'))
for k,r in m.items():
    M=k.split('_asb')[0]; p=f'rtl/dsrom_sys/s81_dv/frame_lp/plan/{M}_l4_lp_plan_kit.sv'; pin=r['asbuilt_source_qualification']['source_sha256'][p]
    for name,root in (('new','/srv/opentallas-scratch2/claude/s81-bfasb-1111/root'),('a2_ts5','/srv/opentallas-scratch2/claude/tok-verify-1/a2/froot'),('root_old','/srv/opentallas-scratch2/claude/s81-bfasb-1111/root_old')):
        s=hashlib.sha256(open(f'{root}/{p}','rb').read()).hexdigest()
        print(k,name,'pin',pin[:12],'root',s[:12],'MATCH' if s==pin else 'REFUSE')
PY
cd $D/code/tools/s81_dv && for t in test_bf_source_measurement.py test_bf_cfg_census.py test_bf_nx_monitor.py test_bf_go_align.py; do python3 -I -c "import sys;sys.path[:0]=['$D/code/tools','$D/code/tools/s81_dv','$D/code/tools/s81_dv/layer_prog'];import runpy,unittest;sys.argv=['x'];runpy.run_path('$t',run_name='__main__')" > /tmp/bfasb_$t.log 2>&1; echo "$t rc=$? $(tail -n 1 /tmp/bfasb_$t.log)"; done
