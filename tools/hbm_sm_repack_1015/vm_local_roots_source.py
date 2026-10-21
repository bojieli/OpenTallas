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
# Literal per-quadrant physical identities; stable native masters remain frozen.
for q in range(4):
 p=D/'physical'/f'hfd_vms_bank_native_q{q}.sv';text=p.read_text()
 text=text.replace(f'module hfd_vms_bank_native_q{q}',f'module hfd_vms_bank_local_q{q}',1)
 assert text.count('input wire clk,')==1
 text=text.replace('input wire clk,','input wire clk_pin,clk_ctrl,clk_s1,clk_s2,clk_ecc,clk_out,clk_ma,clk_mb,clk_mc,',1)
 text=text.replace('ot_vms_bank_static_strap #(', 'ot_vms_bank_static_local_roots #(',1)
 assert text.count('.clk(clk)')==1
 text=text.replace('.clk(clk)', '.clk_local({clk_out,clk_ecc,clk_s2,clk_s1,clk_ctrl,clk_pin}),.clk_macro({clk_mc,clk_mb,clk_ma})',1)
 (D/'physical'/f'hfd_vms_bank_local_q{q}.sv').write_text(text)
text=(D/'ot_vms_bank_native_physical.sv').read_text().replace('module ot_vms_bank_native_physical','module ot_vms_bank_local_physical',1)
assert text.count('input wire clk, rst_n,')==1
text=text.replace('input wire clk, rst_n,','input wire [5:0] clk_local, input wire [2:0] clk_macro, input wire rst_n,',1)
text=text.replace("wire die_clk=MUT==5&&bid==7?1'b0:clk;", "wire[2:0]die_macro=MUT==5&&bid==7?(clk_macro&3'b110):clk_macro;")
for q in range(4):text=text.replace(f'hfd_vms_bank_native_q{q}',f'hfd_vms_bank_local_q{q}')
assert text.count('.clk(die_clk)')==4
text=text.replace('.clk(die_clk)', '.clk_pin(clk_local[0]),.clk_ctrl(clk_local[1]),.clk_s1(clk_local[2]),.clk_s2(clk_local[3]),.clk_ecc(clk_local[4]),.clk_out(clk_local[5]),.clk_ma(die_macro[0]),.clk_mb(die_macro[1]),.clk_mc(die_macro[2])')
text=text.replace('hfd_vms_bank_local_q3 u_bank','hfd_vms_bank_local_q2 u_bank')
(D/'ot_vms_bank_local_physical.sv').write_text(text)
