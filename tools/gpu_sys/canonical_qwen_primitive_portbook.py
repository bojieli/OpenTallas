"""Generate actual controller pin book from its Verilog header, no arithmetic."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MODULE='rtl/gpu/native/ot_gpu_native_primitive_controller.sv'
SOURCES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_sfu.sv','rtl/hdc/v41/ot_hdc_fdiv.sv','rtl/hdc/v41/ot_hdc_fsqrt.sv','rtl/proto/ot_fp32_add_rne_pipe.sv','rtl/proto/ot_fp32_mul_rne_pipe.sv','rtl/abi3/ot_a3_format_pkg.sv','rtl/gpu_sys/ot_gpu_simt_lane.sv','rtl/experimental/qwen_native_fp32_20261003/ot_qwen_native_fp32_lanes.sv','rtl/gpu/native/ot_gpu_native_conversion.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_native_bits.sv','rtl/hbm_accel/native_movement/ot_hbm_native_movement.sv',MODULE]
def generate():
 s=(ROOT/MODULE).read_text();header=s[s.index(')(\n')+3:s.index('\n);')]
 header=re.sub(r'//[^\n]*','',header);ports={};direction=None;bits=None
 for part in header.split(','):
  part=part.strip();m=re.fullmatch(r'(input|output)\s+(?:wire|reg)\s*(?:\[(\d+):0\]\s*)?(\w+)',part)
  if m:direction=m[1];bits=int(m[2])+1 if m[2] else 1;name=m[3]
  else:
   assert re.fullmatch(r'\w+',part),repr(part)
   name=part
  assert name not in ports;ports[name]=dict(direction=direction,bits=bits)
 return dict(schema='opentallas.native.owned_rf.portbook.v1',module='ot_gpu_native_primitive_controller',default_enabled=False,
  ports=ports,sources=SOURCES,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
  clock='same enclosing source clock; constructor must never SET/EDGE/reset/GO',
  RF_contract='four<=128-element operands in fullyowned page-aligned512B apertures, types little-endian F32/U32/I64/U8; output fullyowned512B pages; real read mirrors equal; ACKslot9/owner46 match; provider retains all source/result leases through RPC reverse',
  descriptor_contract='programSHAab3fe; immutable descriptor.mem and pc_templates.mem from released source; GLOBAL6 exact; unsupported external services excluded by EXTERNAL_OPCODE_MASK=0; movement extension requires source-compiled ROM rows/masks and captured map; no synthetic recipe nodes',
  authority_contract='actual held physical root/PC/shape/aperture observations; no host grant fabrication; post-all-pageACK visibility tuple239/owner55; published lease retirement is provider responsibility',
  external_contract='GLOBAL6 services17..25 or38..39 only if actual mask enables; captures fulltuple/owner/PC/sequence/beat on valid-ready; holds response until accepted; same enclosing clock; no new protected data buffers',
  acceptance_status='implementation+leaf protocol pending; not full1737 arithmetic/token or physical qualification')
if __name__=='__main__':
 out=ROOT/'results/uarch/qwen_native_primitive_control_20261003/ports.json'
 out.write_text(json.dumps(generate(),sort_keys=True,indent=2)+'\n');print(out)
