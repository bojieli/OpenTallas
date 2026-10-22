#!/usr/bin/env python3
"""Fleet-only bounded real L2 producer pair through current native components."""
import hashlib,json,shutil,subprocess,sys,struct
from pathlib import Path
root=Path.cwd();out=root.parent/'run_r3';out.mkdir(exist_ok=False);images=out/'images';images.mkdir()
for p in (root.parent/'vectors/f').iterdir():
 if p.is_file():shutil.copy2(p,images/p.name)
for p in (root.parent/'vectors/f2').iterdir():
 if p.is_file() and p.name.startswith('f_'):shutil.copy2(p,images/('f2'+p.name[1:]))
meta=[json.loads((root.parent/f'vectors/{n}/meta.json').read_text()) for n in ('f','f2')]
values=[v['bf16']<<16 for m in meta for k,v in sorted(m['rows'].items(),key=lambda kv:int(kv[0]))]
assert len(values)==8
(images/'expect_pair.hex').write_text(f'{sum(v<<(32*i) for i,v in enumerate(values)):064x}\n')
fx=Path('/srv/opentallas-scratch/claude/codex-tok-s81-layers/fixtures/L2')
b=(fx/'weights/kv_norm.bin').read_bytes();assert len(b)==1024
w=[v<<16 for v in struct.unpack('<512H',b)]
eps=struct.unpack('<I',struct.pack('<f',1e-20))[0]
gain=[eps<<96,0,0,0]+[sum(w[4*i+j]<<(32*j) for j in range(4)) for i in range(128)]
(images/'gain.hex').write_text(''.join(f'{v:032x}\n' for v in gain))
sys.path.insert(0,str(root/'tools/s81_dv'))
from layer_prog.kv_bank_contract import dispatch
gk_command=dispatch(7,0,0,1024,parameter_base=528,operand_base=896)
(images/'gk_command.hex').write_text(f'{gk_command:040x}\n')
base=json.loads((root.parent/'result.json').read_text())
src=[p for p in base['source_sha256'] if not '/test/' in p and p.endswith(('.sv','.v'))]
frame=(root/'tools/s81_dv/frame_bench.f').read_text().splitlines();incs=[s for s in frame if s.startswith('+')];src += [s for s in frame if s and not s.startswith('+')]
extra=['rtl/dsrom_sys/s81_dv/frame_lp/col_h9_l4_lp.sv','rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv','rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv','rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv','rtl/common/landed_parent/ot_pl_land.sv','rtl/common/landed_parent/ot_pl_land_n32.sv','rtl/common/landed_parent/ot_pl_land_rst_copy.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_tr.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ld.sv','rtl/dsrom_sys/s81_dv/slice/lp/ot_s81sl_capc5r.sv','rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv','rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v','tools/s81_dv/tb_cap_sukv.sv']
extra += ['rtl/dsrom_sys/s81_dv/land/dsfd_dvland.sv','rtl/hdc/v41x/ot_dsrom_su_hcpost.sv','rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv']
src=list(dict.fromkeys(src+extra));missing=[p for p in src if not (root/p).is_file()];assert not missing,missing
pins={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in src}
identity=dict(schema='opentallas.s81.native_producer_events.v1',record='run_identity',run_id='s81-l2-cap-carriage-sukv-20261021-r1',source_sha256=pins,native_clock_domain='bounded_common_phase_component_clock',native_command_epoch_edge=0,fixture_manifest_sha256=hashlib.sha256((fx/'manifest.sha256').read_bytes()).hexdigest(),physical_epoch_mapping=None,owner='L2.attn.kv_norm.sumsq',source_frames=['u_f_2L13','u_f_2R10'],source_slice='u_s_2N',target_slice='u_s_3N',source_rank=0,source_native_rows=[2,3],target_rows=[692,693],full_d512=False)
(out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n');(out/'sources.f').write_text('\n'.join(incs+src)+'\n')
obj=out/'obj';v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
cmd=[v,'--binary','--timing','-O1','-fno-dfg','--unroll-count','4','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','-Wno-lint','-Wno-style','-DSU_SMU_T','-DDSFD_PQ_STATIC_X2','-DDSFD_PQ_HAS_BF_X2','-DOT_S81SL_KV_TRANSPORT','--top-module','tb_cap_sukv','-Mdir',str(obj),'-f',str(out/'sources.f'),'-j','2','-CFLAGS','-O1']
(out/'argv.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (out/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
if r.returncode:sys.exit(r.returncode)
guard_dir=Path.home()/'.local/opentallas-tools/verilator-5.050/share/ot_nba_guard'
sys.path.insert(0,str(guard_dir));import verilator_nba_guard as G
guard=G.scan(str(obj));(out/'nba_guard.json').write_text(json.dumps(guard,indent=2)+'\n')
if guard['findings']:sys.exit(86)
identity['binary_sha256']=hashlib.sha256((obj/'Vtb_cap_sukv').read_bytes()).hexdigest()
identity['runtime_images_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in images.iterdir() if p.is_file()}
identity['actual_fixture_inputs_sha256']={name:hashlib.sha256((fx/name).read_bytes()).hexdigest() for name in ['weights/kv_norm.bin','weights/wkv.bin','weights/wkv.scale.bin','ops/attn.norm.scale.bin']}
identity['producer_mapping']={n:dict(frame=m['die_frame'],slice=m['slice'],rows={r:{k:v[k] for k in ('src','out_index')} for r,v in m['rows'].items()},fixture=m['fixture'],images=m['images']) for n,m in zip(('f','f2'),meta)}
identity['scoreboard_only_files']=['expect_pair.hex','meta.json','return_plan.json']
identity['reference_source_files_sha256']={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ['tools/hdc_golden_v41.py','tools/hdc_golden.py','tools/s81_dv/layer_prog/kv_bank_contract.py','tools/s81_dv/layer_prog/lower_vs.py']}
identity['argv']=cmd
(out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
checks={}
for mut in (0,1):
 with (out/f'run_mut{mut}.log').open('w') as f:r=subprocess.run([str(obj/'Vtb_cap_sukv'),f'+OT_ROM_DIR={images}',f'+MUT={mut}'],stdout=f,stderr=subprocess.STDOUT)
 text=(out/f'run_mut{mut}.log').read_text();print(mut,r.returncode,text[-1500:],flush=True)
 checks[str(mut)]=(r.returncode==0 and 'CAP_SUKV_PASS' in text) if mut==0 else (r.returncode!=0 and 'PAIR_MISMATCH' in text and 'CAP_SUKV_FAIL' in text)
 if mut==0:
  with (out/'events.jsonl').open('w') as f:
   f.write(json.dumps(identity)+'\n')
   for s in text.splitlines():
    if s.startswith('JSON '):f.write(s[5:]+'\n')
assert pins=={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in src}

(out/'result.json').write_text(json.dumps(dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,scope='Eight ordinary L2 WKV values; Four real D4 K2 lane landings; physical flight/absolute epoch open; no full arithmetic consumer or gain lease'),indent=2)+'\n')
sys.exit(0 if all(checks.values()) else 1)
