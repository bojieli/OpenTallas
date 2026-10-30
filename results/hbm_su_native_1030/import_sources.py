#!/usr/bin/env python3
"""Build recipes from the actual selected native module bodies, not shared-file guesses."""
import json,pathlib,hashlib,re
ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'physical/die_plan/hbm_arch_cores'
PACK=BASE/'native_1030'
M={'ot_hbm_su_static_pgslice_lg__lane_exp0_id':'ot_hnx_su_exp__rst3','ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691':'ot_hnx_su_exp__rst3','ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77':'ot_hnx_su_plain4__lid9_rst3','ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526':'ot_hnx_su_plain4__lid9_rst3'}
S=json.load(open(pathlib.Path(__file__).with_name('su_source_manifest.json')))
F=json.load(open(pathlib.Path(__file__).with_name('fused_source_manifest.json')))
assert S['manifest_defines']==F['manifest_defines']
all_rows={}
for manifest in (S,F):
 for root,rows in manifest['roots'].items():
  for name,row in rows.items():
   if name.startswith('ot_sram_'):continue
   if name in all_rows:assert all_rows[name]['exported_module_sha256']==row['exported_module_sha256'],name
   all_rows[name]=row
receipt=[]
for name,row in sorted(all_rows.items()):
 p=PACK/(name+'.sv');raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest()
 normalized=raw.decode();delta=None
 if name=='ot_hnx_fused_hub':
  original=pathlib.Path(__file__).with_name('native_hub_original.sv').read_bytes()
  assert hashlib.sha256(original).hexdigest()==row['exported_module_sha256']
  normalized=original.decode()
  needle="cd <= {112'd0, cs_r + 16'(cj)}"
  assert normalized.count(needle)==1
  target='reg [15:0] cs_r; reg [1:0] cj;'
  assert normalized.count(target)==1
  normalized=normalized.replace(target,target+"\n    wire [15:0] scrd_index = cs_r + {14'd0, cj};").replace(needle,"cd <= {112'd0, scrd_index}")
  assert h in (row['exported_module_sha256'],hashlib.sha256(normalized.encode()).hexdigest())
  p.write_text(normalized)
  delta='Existing exact-width YC1 normalization d4060d562: no state/cycle change; 262144 known +35 four-state cases.'
 else:
  assert h==row['exported_module_sha256'],(name,h,row['exported_module_sha256'])
 receipt.append(dict(module=name,native_source=row['source'],native_file_sha256=row['file_sha256'],native_module_body_sha256=row['module_sha256'],export_sha256=row['exported_module_sha256'],current_sha256=hashlib.sha256(normalized.encode()).hexdigest(),delta=delta))
# Hard memory models come from the normal qualified kit provider, never from this source pack.
for p in PACK.glob('ot_sram_*.sv'):p.unlink()
def files(manifest,top):return [('physical/die_plan/hbm_arch_cores/wrappers/ot_hbm_su_static_replicated_bank__native_zero.sv' if n=='ot_hbm_su_static_replicated_bank' else 'physical/die_plan/hbm_arch_cores/native_1030/'+n+'.sv') for n in sorted(manifest['roots'][top]) if not n.startswith('ot_sram_')]
rp=BASE/'recipes_b2.json';R=json.load(open(rp))
for physical,top in M.items():
 R[physical]=dict(top=top,files=files(S,top),defines=S['manifest_defines'],params={},macros=['ot_sram_1r1w_128x256_m1_r2c2'],source='SOURCE PREP ONLY: actual current native generated cut '+top+'; direct ABI adapter aliases only lane_lane_id to strap_lane_lane_id, retains cmd0_D/register/reset boundaries and all current parameters. New native pin table required; no legacy decoded-port compatibility claim. Mixed preferred provider WCOPY interface repaired by zero-only declared parameter + fail-closed nonzero guard; original provider body unchanged, receipt zero_wcopy_receipt.json.',synth_memory_max_bits=256*61 if top=='ot_hnx_su_exp__rst3' else 4096)
for physical,top in [('hnx_fused_lane','ot_hnx_fused_lane'),('ot_hnx_fused_tnode','ot_hnx_fused_tnode'),('ot_hnx_fused_hub_n4ext','ot_hnx_fused_hub_n4ext'),('ot_hnx_fused_host_program','ot_hnx_fused_host_program')]:
 rec=R[physical];rec['files']=files(F,top);rec['defines']=F['manifest_defines'];rec.pop('source_commit',None);rec.pop('read_at_commit',None)
 rec['source']='Actual b31t preferred used-module body snapshots + exact native defines; file/module hashes in results/hbm_su_native_1030/import_receipt.json. Hard memory library remains qualified separately. Hub only: existing d406 exact-width normalization, no RTL state/cycle change. Preserve original current native parameters.'
# QWDEC's previously checked14preferred files remain correct; use actual native preprocessing too.
R['ot_hgi_qw_dec']['defines']=F['manifest_defines']
rp.write_text(json.dumps(R,indent=1)+'\n')
for physical,top in M.items():
 source=(PACK/(top+'.sv')).read_text();head=source[source.index('(')+1:source.index(');')];ports=[]
 for d,a,name in re.findall(r'(input|output) wire \[(\d+):0\] (\w+)',head):ports.append((d,int(a)+1,name))
 assert len(ports)==(39 if top=='ot_hnx_su_exp__rst3' else 69)
 text='`timescale 1ns/1ps\n`default_nettype none\n// Actual current native cut ABI. SOURCE PREP only; no legacy decoded-port shim.\nmodule '+physical+'(\n'
 text+=',\n'.join(' '+d+' wire '+(f'[{w-1}:0] ' if w>1 else '')+('strap_lane_lane_id' if n=='lane_lane_id' else n) for d,w,n in ports)+'\n);\n'
 text+=' '+top+' u_native(\n'+',\n'.join('  .'+n+'('+('strap_lane_lane_id' if n=='lane_lane_id' else n)+')' for d,w,n in ports)+'\n );\nendmodule\n`default_nettype wire\n'
 (BASE/'wrappers'/(physical+'.sv')).write_text(text)
pathlib.Path(__file__).with_name('import_receipt.json').write_text(json.dumps(dict(status='CURRENT_NATIVE_SOURCE_ADAPTER_PREP_UNADOPTED',manifest_defines=F['manifest_defines'],modules=receipt),indent=2)+'\n')
print('PREP',len(all_rows),'actual selected modules;4native SU adapters;4FUSED recipes;QWDEC flags corrected')
