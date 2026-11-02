"""Read-only external child graph attachment; does not edit the active kit or run STA."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/codex-parent-hold-export/tools/die_plan')
import child_clock_join as J
R=Path('/srv/opentallas-scratch2/claude/codex-hist-attachment-1634');R.mkdir(exist_ok=True)
K=Path('/srv/opentallas-scratch2/claude/codex-s81-hist-parent-1101/parent_alias1613/kits/dsdv_bksel_q_signed_source')
V=Path('/srv/opentallas-scratch2/claude/codex-hist-clock-witness-1101/views/ot_s81ph_native_sel_hist_bank')
B=Path('/srv/opentallas-scratch2/claude/codex-s81-hist-parent-1101/hist1131/ot_s81ph_native_sel_hist_bank_hrB20/run/results/asap7/kl_ot_s81ph_native_sel_hist_bank_hrB20/base')
QP=Path('/srv/opentallas-scratch2/claude/codex-parent-hold-export/child_clock_hist_final1131.json')
Q=json.loads(QP.read_text());MP=Path(Q['boundary_maps']['artifact']);M=json.loads(MP.read_text());W=json.loads((V/'child_clock_witness.json').read_text())
N=K/'run/results/asap7/kl_dsdv_bksel_q_signed_source/base/1_synth.v'
libs={c:K/'macros'/f'ot_s81ph_native_sel_hist_bank_{c}.lib' for c in ('tt','ff')}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Q['status']=='QUALIFIED_NATIVE_GRAPH'
assert sha(MP)==Q['boundary_maps']['artifact_sha256']
assert json.loads((V/'provenance.json').read_text())['child_clock_witness']['sha256']==sha(V/'child_clock_witness.json')
# Reuse the exact qualified join helper and parse each immutable native/parent netlist only once.
original=J.D.read_verilog;cache={}
def memo(path):
 key=str(Path(path));
 if key not in cache:cache[key]=original(path)
 return cache[key]
J.D.read_verilog=memo
instances=[f'u_q.u_s.u_{part}.g_bank[{i}].u_bank' for part in ('hc','hf') for i in range(8)]
joins=[J.join_parent(Q,N,'dsdv_bksel_q',inst,'ck',libs,B) for inst in instances]
assert all(row['status']=='PASS' for row in joins),joins
files={c:{p:dict(path=str(V/p),sha256=h,present=(V/p).is_file()) for p,h in W['corners'][c]['files'].items()} for c in ('tt','ff')}
assert all(row['present'] for corner in files.values() for row in corner.values())
packet=dict(schema='opentallas.external_child_graph_attachment.PREP.v1',status='READY_SELECTED_INPUT_ATTACHMENT_NOT_STA',active_kit=str(K),parent_top='dsdv_bksel_q',parent_netlist=dict(path=str(N),sha256=sha(N)),actual_selected_libraries={c:dict(path=str(p),sha256=sha(p)) for c,p in libs.items()},child_qualification=dict(path=str(QP),sha256=sha(QP),status=Q['status']),boundary_maps=dict(path=str(MP),sha256=sha(MP),inputs=len(M['maps']['inputs']),outputs=len(M['maps']['outputs']),boundary_registers=M['boundary_registers']),full_native_graph=dict(view=str(V),manifest=str(V/'child_clock_witness.json'),sha256=sha(V/'child_clock_witness.json'),native_base=str(B),native=Q['graph_identity']['native'],corners=Q['graph_identity']['corners'],all_manifest_files=files),instances=joins,child_root_pin='clk',parent_structural_clock_net='ck',timing_clock_source_root_edge='NOT_RUN_NO_PROPAGATED_PARENT_PATHS',actual_parent_STA_consumption='NOT_RUN',parent_source_equivalence='NOT_ASSERTED_OFFICIAL_PARENT_PROOF_IN_PROGRESS',parent_coverage='UNEXPANDED_CHILD_ETM',mutation='NONE_ACTIVE_KIT_UNTOUCHED',required_next=['actual normal parent PLACE and independent LOOK','stage/pass external registry to future inactive STA scope, not current active kit','normal parent consumed-library receipts matching exact selected TT/FF hashes','actual original-STD per-bit parent paths/clock/source/edge witnesses','qualified endpoint/pair composition with per-port maps; no aggregate or CPPR credit'])
(R/'attachment.json').write_text(json.dumps(packet,indent=2)+'\n')
print(json.dumps(dict(path=str(R/'attachment.json'),instances=len(joins),all_structural_joins='PASS',parent_netlist_sha256=sha(N),graph_sha256=packet['full_native_graph']['sha256'],graph_counts=Q['graph_identity']['corners'],parent_coverage=packet['parent_coverage'],active_kit_mutation='NONE'),indent=1))
