"""Additive clock-only VM bank candidate; no cycle or arithmetic changes."""
import hashlib,json,pathlib,re
R=pathlib.Path(__file__).resolve().parents[2]
D=R/'rtl/hbm_accel/generic/vm/static'
src=D/'ot_vms_bank_static_strap.sv';s=src.read_text()
s=s.replace('module ot_vms_bank_static_strap #(', 'module ot_vms_bank_static_local_roots #(',1)
assert s.count('input wire clk, rst_n,')==1
s=s.replace('input wire clk, rst_n,','input wire [5:0] clk_local, input wire [2:0] clk_macro, input wire rst_n,',1)
# Concrete always blocks, in source order: release/identity, input payload/valid,
# slot capture/valid, S1 control/payload, S2 control/payload, macro capture+ECC,
# and response/status. The immutable source guards this semantic assignment.
roots=[1,1,0,0,1,1,2,2,3,3,4,4,5,5]
assert len(re.findall(r'posedge clk\b',s))==len(roots)
itr=iter(roots);s=re.sub(r'posedge clk\b',lambda m:f'posedge clk_local[{next(itr)}]',s)
for i,inst in enumerate(['u_a','u_b','u_c']):
 a=inst+' (.clk(clk)';assert s.count(a)==1;s=s.replace(a,inst+f' (.clk(clk_macro[{i}])',1)
a='ce_pipe(.clk(clk)';assert s.count(a)==1;s=s.replace(a,'ce_pipe(.clk(clk_local[5])',1)
assert not re.search(r'posedge clk\b|\.clk\(clk\)',s)
p=D/'ot_vms_bank_static_local_roots.sv';p.write_text('// Generated additive local-root candidate; original strap source unchanged.\n'+s)
x=dict(schema='opentallas.vm_local_roots_source.v1',source=str(src.relative_to(R)),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),generated=str(p.relative_to(R)),generated_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),always_block_root_order=roots,local_roots=['input_payload_valid','slot_strap_reset','S1_decode_egress','S2_macro_pin_registers','macro_capture_ECC_pipeline','response_status'],direct_macro_entries={'clk_macro[0]':'u_a/clk','clk_macro[1]':'u_b/clk','clk_macro[2]':'u_c/clk'},data_edges_added=0,scope='Candidate only; direct9clockentries require actual die delivery phi-R, local placement, CTS and TT/FF/DRC/native proof. Stable native quadrant master source is unchanged.')
(p.parent/'native_abi_1016/local_roots_manifest.json').write_text(json.dumps(x,indent=2)+'\n')
print(json.dumps(x,indent=2))
