#!/usr/bin/env python3
"""Copy exact NL + NK banked parent sources and the deterministic real via-map masks for ot-run (r13 NL helper)."""
from pathlib import Path
import argparse,json,hashlib,random,shutil
root=Path(__file__).resolve().parents[2]
a=argparse.ArgumentParser();a.add_argument('out',type=Path);out=a.parse_args().out
out.mkdir(parents=True,exist_ok=False)
s=json.loads((root/'tools/ref_tile/specs_q_compute_native/qfd_tile_nk_native.json').read_text())['sources']
remove={'rtl/physical/bb/ot_qwen_tile_rpair_bb.v','rtl/physical/bb/ot_qwen_tile_node_bb.v','rtl/physical/bb/ot_qwen_tile_lsl_fp1_bb.v','physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v'}
s=[p for p in s if p not in remove]
s+=['rtl/qwen_sys/tile_parent_banked_20261015/'+p for p in ['ot_qwen_w12_issue_banked_v1.sv','ot_qwen_w12_matvec_part_banked_v1.sv','ot_qwen_rom_tile_logic_banked_v1.sv','qfd_tile_nk_banked_v1.sv','qfd_tile_nk_staged_reference.sv']]
s+=['rtl/qwen_sys/tile_parent_nl_banked_20261015/'+p for p in ['ot_qwen_rom_tile_logic_nl_banked_v1.sv','qfd_tile_nl_banked_v1.sv','qfd_tile_nl_banked_v2.sv','qfd_tile_nl_staged_reference.sv']]
s+=['rtl/qwen_sys/tile_glue_banks_20261015/ot_qwen_tx198.sv','rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_face_masters.sv','rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_w514.sv','rtl/qwen_sys/head_staging_20261015/qkh_packet_masters.sv','rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv','rtl/lib/ot_rst_relay.sv','rtl/physical/ot_qwen_tile_rpair.sv','rtl/physical/ot_qwen_tile_node.sv','rtl/physical/ot_qwen_tile_lsl_fp1.sv','physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v']
tbs=['physical/qwen_tile_glue_banks_1015/tb_parent_nl_banked.sv','physical/qwen_tile_glue_banks_1015/tb_parent_banked_fault.sv','physical/qwen_tile_glue_banks_1015/tb_parent_nl_banked_v2.sv']
s=list(dict.fromkeys(s));hashes={}
for p in s+tbs:
 dst=out/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/p,dst);hashes[p]=hashlib.sha256(dst.read_bytes()).hexdigest()
(out/'sim_sources.list').write_text('\n'.join(s)+'\n')
shutil.copyfile(root/'physical/qwen_tile_glue_banks_1015/run_parent_bench_nl.sh',out/'run_parent_bench_nl.sh')
r=random.Random(198);(out/'masks').mkdir()
for b in range(5):
 for c in range(2):
  p=out/f'masks/qtile_t0_b{b}_c{c}.viamap.hex';p.write_text(''.join(f'{r.getrandbits(2128):0532x}\n'for _ in range(512)));hashes[str(p.relative_to(out))]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'source_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
print(f'Prepared {len(s)} real RTL sources + 2 benches, 10 real ROM via masks')
