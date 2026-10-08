import pathlib,hashlib,json,sys
R=pathlib.Path('/home/ubuntu/OpenTallas');O=pathlib.Path('/tmp/qwen-vm-composed-calendar-20261007');sys.path.insert(0,str(R/'tools'))
import qwen_rom_rt_core_emit_w12 as E
import qwen_rom_verify_core_emit_w12 as V
from hdc_isa import decode
base=E.emit(E.CORE.read_text());target=V.emit(E.CORE.read_text())
def cut(s):return s[s.index('    wire unit_ready'):s.index("    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin kvd_v")]
assert cut(base)==cut(target)
prog=(R/'results/rtl/qwen_rom_finite_vm_schedule_20261005/inputs/L20_program.hex').read_text().splitlines();controls=[]
for pc in [19,20,25]:
 d=decode(int(prog[pc],16));sels={k:v for k,v in d.items()if k.startswith('me_d_')or k in ['su_d_nin','a_d','b_d','c_d','d_d']};assert not any(sels.values());assert (int(prog[pc],16)>>900)&7==0
 controls.append(dict(pc=pc,dynamic_selectors=sels,pos_off=0))
files=['rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_vprm_stream4.sv','rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv','tools/qwen_rom_rt_vprm_w12.py','tools/qwen_rom_verify_core_emit_w12.py','tools/qwen_rom_rt_core_emit_w12.py','rtl/hdc/ot_hdc_core_vector_weight.sv','tools/qwen_hbm_finite_vm_bind.py','rtl/hbm_accel/qwen/finite_vm_20261005/ot_qwen_finite_vm_adapter.sv','rtl/hbm_accel/qwen/finite_vm_20261005/ot_qwen_checked_vm_bank.sv']
d=dict(scope='Corrected target source-context audit; previous baseline component evidence preserved.',target_top=files[0],target_sequencer='ot_qwen_tp_seq_w12_vp ENABLE_ARP=1 NTOK=8; VWA parameterized',target_emitter='qwen_rom_verify_core_emit_w12, VPOS=1',historical_pinned_top='results/rtl/qwen_rom_finite_vm_schedule_20261005/inputs/top.sv baseline ot_qwen_tp_seq_w12 VWA8',dispatch_fetch_end_slice_byte_identical=True,dispatch_slice_sha256=hashlib.sha256(cut(base).encode()).hexdigest(),selected_static_controls=controls,source_sha256={f:hashlib.sha256((R/f).read_bytes()).hexdigest()for f in files})
(O/'target_context.json').write_text(json.dumps(d,indent=2)+'\n');print('PASS target dispatch exact; static selectors zero')
