"""Rerun bounded packed-attention tests and bind separate current interface evidence."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 subprocess.run(['python3','-m','pytest','-q','tests/test_v41x_attn_desc_lifecycle.py::test_descriptor_lifecycle_replay_and_faults','tests/test_v41x_attn_packed_bypass.py::test_packed_bypass_qk_pv_handshake'],cwd=ROOT,check=True)
 subprocess.run(['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--lint-only','-Wno-fatal','-Wno-TIMESCALEMOD','-DV41X_ATTN_SERVICE_LINT_STUB','--top-module','ot_hdc_v41x_att_adapt','-GAW=30','-GNW=21','-GD=512','-GTROWS=640','-GNHMAX=16','-GPACKED_KV=1','rtl/hdc/v41x/ot_hdc_v41x_att_adapt.sv','rtl/test/ot_hdc_v41x_attn_service_lint_stub.sv'],cwd=ROOT,check=True,capture_output=True)
 from tools import rtl_chip_v41x_packed_die_boundary as b
 boundary=b.run()
 assert boundary['pass']
 bp=ROOT/'results/rtl/chip_v41x_packed_die_boundary.json'
 bp.write_text(json.dumps(boundary,indent=2,sort_keys=True)+'\n')
 for name in ('v41x_attn_desc_lifecycle','v41x_attn_packed_bypass'):
  p=ROOT/'results/rtl'/f'{name}.json';r=json.loads(p.read_text())
  for key in ('port_elaboration','die_port_elaboration','port_repin_note'):r.pop(key,None)
  if 'full_shape_stub_lint' in r:
   r.setdefault('historical_full_shape_stub_lint',r.pop('full_shape_stub_lint'))
   r['full_shape_stub_lint']={'status':'pass','scope':'current full-geometry adapter lint with interface-only engine stub; separate die headers in boundary record'}
  r['sources']={n:sha(ROOT/n) for n in r['sources']}
  r['current_integration_check']={'generator':'tools/refresh_v41_packed_integration_evidence.py','generator_sha256':sha(Path(__file__)),'boundary_record':str(bp.relative_to(ROOT)),'boundary_sha256':sha(bp),'scope':'standalone lifecycle/forwarding simulations plus separate header checks; no numerical engine or token claim'}
  p.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
