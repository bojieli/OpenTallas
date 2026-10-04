"""Exercise the actual emitted safety expressions without rebuilding 64 SMs."""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'rtl/model/qwen_hbm_matrix_tc_safety_20261003'

def test_actual_sourcebook_keeps_engine_and_driver_identity():
    base = ROOT / 'rtl/model/qwen_hbm_matrix_tc_factory_20261003'
    old = json.loads((base / 'ports.json').read_text())
    new = json.loads((OUT / 'ports.json').read_text())
    assert old['pins'] == new['pins']
    assert old['inventory'] == new['inventory']
    assert (OUT / 'pin_driver.cpp').read_bytes() == (base / 'pin_driver.cpp').read_bytes()
    for path in (OUT / 'sources.f').read_text().splitlines():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == new['source_sha256'][path]
    assert not new['physical_qualified'] and not new['token_qualified']

def test_each_actual_scratch_fault_and_outstanding_client_blocks_safe_retirement(tmp_path):
    if not shutil.which('iverilog'):
        pytest.skip('Icarus not installed')
    source = (OUT / 'ot_gpu_qwen_hbm_integrated_scratch.sv').read_text()
    drain = re.search(r'assign local_shared_router_drained=([^;]+);', source).group(1)
    fault = re.search(r'\.endpoint_fault\(([^\n]+)\),', source).group(1)
    # These are the expressions taken from the selected generated full-system source.
    tb = f'''module tb;
reg kv_shared_drained=1;
reg [63:0] scratch_drained='1,scratch_fault=0;
reg kv_endpoint_fault=0,rfcohort_tuple_mismatch=0,state_fault=0;
reg issuer_session_fault=0,local_fault=0,state_rpc_fault=0;
reg [63:0] rfdrain_fault=0,rfjoin_fault=0,issuer_fault=0,source_owner_fault=0;
wire drained={drain};
wire fault={fault};
initial begin
 #1; if (!drained || fault) $fatal;
 for(integer i=0;i<64;i=i+1) begin
  scratch_drained=~(64'b1<<i); #1; if(drained) $fatal;
  scratch_drained='1; scratch_fault=64'b1<<i; #1; if(!fault) $fatal;
  scratch_fault=0;
 end
 kv_shared_drained=0; #1; if(drained) $fatal;
 kv_endpoint_fault=1; #1; if(!fault) $fatal;
 $display("PASS all64 scratch drain/fault joins"); $finish;
end
endmodule
'''
    path=tmp_path/'tb.sv'; path.write_text(tb)
    subprocess.run(['iverilog','-g2012','-o',str(tmp_path/'sim'),str(path)],check=True,capture_output=True)
    result=subprocess.run(['vvp',str(tmp_path/'sim')],check=True,capture_output=True,text=True)
    assert 'PASS all64' in result.stdout
