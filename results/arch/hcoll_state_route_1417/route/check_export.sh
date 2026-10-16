set -euo pipefail
r=/srv/opentallas-scratch/claude/ref_gate/hcoll_ring_state_capture_1417-20261015-142729
cd "$r/src"
test "$(docker image inspect --format '{{.Id}}' openroad/orfs:latest)" = sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
python3 - "$r" <<'PY'
import pathlib,subprocess,sys,json
r=pathlib.Path(sys.argv[1]); s=r/'src'; k=s/'physical/ref_tile/hcoll_ring_state_capture_1417'; v=r/'views/ot_hgi_coll_pring_static_state_capture_lane'; c=json.load(open(r/'corner_sta.json'))
a=[sys.executable,'tools/tt_views/view_export.py','--orfs-dir',str(r/'routes/gate/work/orfs'),'--name','ot_hgi_coll_pring_static_state_capture_lane','--out',str(v),'--interface-sdc',str(k/'signoff.sdc'),'--post-sdc',str(k/'signoff.sdc'),'--post-sdc',str(s/'physical/common_flow/io_ref_routed.sdc'),'--corners','ff,tt','--expect-tt',str(c['setup_tt']['worst_slack_ps']),'--expect-ff',str(c['hold_ff']['worst_slack_ps']),'--require-check','--signal-max-layer','M5','--pg-max-layer','M5','--signal-audit-tcl',str(s/'tools/ref_tile/signal_layer_audit.tcl')]
subprocess.run(a,check=True)
subprocess.run([sys.executable,'tools/hier_contract/abstract_pin_stub.py',str(v/'ot_hgi_coll_pring_static_state_capture_lane.lef'),str(v/'ot_hgi_coll_pring_static_state_capture_lane.lef')],check=True)
sys.path.insert(0,str(s/'tools/hier_contract'));import child_lint, native_pin_audit as N
l=child_lint.lint(str(v/'ot_hgi_coll_pring_static_state_capture_lane.lef'),str(v));(v/'child_lint.json').write_text(json.dumps(l,indent=1)+'\n');assert l['verdict']=='PASS',l
a=N.audit_one((str(s),'ot_hgi_coll_pring_static_state_capture_lane',str(v)));a['scope']='Component-only CLOSED under TTsetup>=0/FFhold>=0/DRC0; SS sensitivity only; parent not adopted; +1edge all state interactions';(r/'native_pin_audit.json').write_text(json.dumps(a,indent=1)+'\n');assert a['pass'] and a['inputs']==164 and a['outputs']==128,a
print(json.dumps(a))
PY
