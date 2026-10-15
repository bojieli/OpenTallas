#!/usr/bin/env python3
"""Build actual Nk/Nl physical contracts from the die port assignment and routed child manifest."""
import argparse,copy,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--pins',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--lsl-view',required=True);a=ap.parse_args()
r=Path(__file__).resolve().parents[2]
base=json.loads((r/'physical/ref_tile/qfd_tile_nk_r5/spec.json').read_text())
manifest=json.loads(a.manifest.read_text())
for master,data in manifest['masters'].items():
 pins=json.loads((a.pins/(master+'.json')).read_text())
 assert pins['overlapping_pin_pairs']==0
 assert [pins['outline']['w'],pins['outline']['h']]==data['outline'], 'physical outline and die pin assignment differ'
 for port,rec in pins['ports'].items():
  if not any(port in v for v in pins['pins'].values()): pins['pins'].setdefault(rec['face'],[]).append(port)
 name=master+'_native';dest=r/'physical/ref_tile'/name;dest.mkdir(parents=True,exist_ok=True)
 children=[];hard={}
 for port,ch in data['children'].items():
  view=a.lsl_view if port.startswith('ck_lsl') else ch['view']
  legacy=next(x for x in base['children'] if x['inst']=='u_tile.'+ch['child_instance'].replace('.genblk4.','.').removeprefix('u_tile.u_tile.'))
  children.append(dict(view=view,count=1,inst=ch['child_instance'],at=ch['origin'],orient=legacy['orient']))
  hard[port]=ch['child_instance']+'/clk'
 sources=[x for x in base['sources'] if 'hard/ot_qwen_tile_lsl/' not in x]
 sources.append('rtl/physical/bb/ot_qwen_tile_lsl_fp1_bb.v')
 sources.append('rtl/physical/qfd_tile_nk_slot.sv')
 s=dict(name=name,top=master,kind='cluster',clock='hybrid_entries',clock_port='ck',clock_ports=['ck']+list(hard),clock_cts_roots=['ck'],required_hybrid_roots=dict(standard_cell_cts=['ck'],hard_child_entry=hard),sources=sources,defines=['OT_QWEN_LSL_FP1'],params={},children=children,macros=[],outline=pins['outline'],pins=pins['pins'],pin_ranges=pins['pin_ranges'],io_tcl='physical/ref_tile/'+name+'/assigned_pins.tcl',reset_ports=['rst_n'],child_lattice_um=0.216,layer_cap='M7',recipe=2,keep_pin_regs=True,pin_reg_split=True,inhold=True,outhold=True,io_flop_at_pins=dict(cols=8),route=dict(pd=0.5,threads=8,peak_ram_gb=24,hold_margin_ns=0.03,macro_halo_um=5.4),refglob='*',inter=[],structural_change='Actual production GT3072 die-name parent, registered faces, independent clock entry for each CLOSED rpair/LSL/node; native LSL reset/fault pins; no hidden global child clock. Compiler reset and fault visibility add one child edge.',job=dict(owner='Codex:q_compute_elem',branch='codex/q-compute-native-parents-1014',tag='n1',purpose='Source-exact native tile parent with real hardened production children',benches_from='tools/ref_tile/specs_qtile_r5/qfd_tile_nk_r5_benches.json',extra_paths=['rtl/test/tb_qfd_tile_nk_slot.sv','rtl/test/tb_qfd_tile_nl_slot.sv'],views_to='physical/ref_tile/'+name+'/views',record_to='results/rtl/ref_tile/'+name))
 top='tb_'+master+'_slot'
 benches=[]
 for mutant in [False,True]:
  variant='mutant' if mutant else 'exact'
  define='-DOT_QFD_TILE_'+master.removeprefix('qfd_tile_').upper()+'_MUT' if mutant else ''
  cmd='mkdir -p {RUN}/bench && iverilog -g2012 '+define+' -s '+top+' -o {RUN}/bench/'+master+'_'+variant+' rtl/test/'+top+'.sv rtl/physical/qfd_tile_nk_slot.sv rtl/physical/ot_qwen_rom_tile_nk.sv && vvp {RUN}/bench/'+master+'_'+variant
  bench=dict(name='native_face_'+variant,cmd=cmd,expect='fail' if mutant else 'pass',threads=1,peak_ram_gb=1,needs=['iverilog'])
  bench['fail_regex' if mutant else 'pass_regex']=('^FAIL ' if mutant else '^PASS ')+master+'_slot checks=4000'
  benches.append(bench)
 s['job']['benches']=benches
 (dest/'assigned_pins.tcl').write_text((a.pins/(master+'.tcl')).read_text())
 out=r/'tools/ref_tile/specs_q_compute_native'/(name+'.json');out.write_text(json.dumps(s,indent=2)+'\n');print(out)
