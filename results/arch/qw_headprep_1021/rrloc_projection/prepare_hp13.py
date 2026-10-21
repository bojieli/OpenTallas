#!/usr/bin/env python3
"""Assemble a unique true-c_emb LP source candidate; no view or timing adoption.
Run in this git worktree; output is an isolated source tree, never a gate tree.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
BASE='d2c8e45a7'
HP='9add100c4'
HEAD_HASHES={'native32_1r_param.v':'44d54f850a0630849746de3cb907e132ec579b6155fbb10ef21fd5e20c44a9d7','native32_helpers.sv':'1e021ff33742ef24529373bfab456eeb95f90c693f597963cd8c2f368c3bec88'}
def blob(rev,path): return subprocess.check_output(['git','show',rev+':'+path])
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--head-dir',required=True);p.add_argument('--baseline-source',required=True);a=p.parse_args()
 out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 if any(out.iterdir()):raise SystemExit('fresh empty output directory required')
 records={}
 baseline=Path(a.baseline_source).resolve()
 # These are the exact symbolic inputs whose reversed HP projection was proven.
 for filename,digest in {'qfd_tt_ctlm_dv_lpf.sv':'a48be9addcb73bb1544c7b705d54e815df28a2f6885ecd404b7c3978ebfe1ef4','qfd_tt_ctlm_dv_lpf_parts.sv':'a61c5bce3cc751a0ee36043cf9d4ff92fcf1263d8f7012312fde1cd0ec5245a9'}.items():
  if sha((baseline/'rtl/qwen_dv'/filename).read_bytes())!=digest:raise SystemExit('actual RR symbolic input identity differs: '+filename)
 def put(path,data,origin):
  q=out/path;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data);records[path]=dict(sha256=sha(data),origin=origin)
 files=blob(BASE,'results/rtl/qw_tlprod_1020/bench10.f').decode().splitlines()
 deps=[]
 for f in files:
  if f.startswith(('rtl/qwen_dv/lp9d_np/','rtl/qwen_dv/qfd_tt_ctlm_dv_lpf')) or f=='tb_np10.sv' or f=='rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_static_hr.sv':continue
  source='results/rtl/qw_calr_1020/ctlm9c/'+f.split('/')[-1] if f.startswith('calr/') else f
  data=(baseline/source).read_bytes() if (baseline/source).is_file() else blob(BASE,source)
  put(f,data,'actual RR source snapshot:'+source if (baseline/source).is_file() else BASE+':'+source);deps.append(f)
 hp_paths=['rtl/qwen_dv/headprep13/qfd_tt_ctlm_dv_lpf_hp13.sv','rtl/qwen_dv/headprep13/qfd_tt_ctlm_dv_lpf_hp13_parts.sv']
 for f in hp_paths:
  data=blob(HP,f.replace('headprep13/','headprep/').replace('_hp13','_hp'))
  if f==hp_paths[0]:
   old=b'ot_qfd_tt_ctlm_static_hr #(.STAGE_ME((STAGE_ME != 0) ? 1 : 0)) u_hr'
   assert data.count(old)==1
   data=data.replace(old,b'ot_qfd_tt_ctlm_static_hr_safe32_native32_1r #(.STAGE_ME(1), .SEGCAL(1)) u_hr').replace(b', .ck_pm0(ck), .ck_pm1(ck)',b'')
  data=data.replace(b'_hp',b'_hp13')
  put(f,data,HP+':'+f+'; u_hr actual H16X3 source projection only' if f==hp_paths[0] else HP+':'+f)
 head_paths=[]
 for name in ['native32_1r_param.v','native32_helpers.sv']:
  data=(Path(a.head_dir)/name).read_bytes()
  if sha(data)!=HEAD_HASHES[name]:raise SystemExit('actual H16ZA source hash mismatch: '+name)
  path='rtl/qwen_dv/headprep13/h16za/'+name;put(path,data,'c0ad783cd generated3 actual H16X3; supplied immutable artifact');head_paths.append(path)
 extra='physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v'
 put(extra,blob(BASE,extra),BASE+':'+extra);deps.append(extra)
 for f in ['tools/landed_parent/lp.py','tools/landed_parent/endpoint_domains.py']:
  put(f,blob(BASE,f),BASE+':'+f)
 s=json.loads(blob(BASE,'tools/landed_parent/specs/qfd_tt_ctlm_dv_lpf_np.json'))
 s.update(top='qfd_tt_ctlm_dv_lpf_hp13',top_lp='qfd_tt_ctlm_dv_lpf_hp13_lp',sources=[hp_paths[0]],child_sources=deps+[hp_paths[1]]+head_paths,out_dir='rtl/qwen_dv/headprep13/lp',record_dir='results/arch/qw_headprep_1021/tt_lp_recipe/generated',landing_mcp=False,landing_reset_forest=False)
 s['why']='SOURCE CANDIDATE ONLY: exact safe11 minimal dependency assembly plus true c_emb bank export9add and actual H16X3 generated3. No old LP/view alias. All crossings single-cycle STA; physical qualification remains owed.'
 s['params']=json.loads(blob(HP,'results/arch/qw_headprep_1021/tt_emb_projection.json'))['params']
 s['params']['XPF_TRANSPORT_EDGES']=21 # explicit construction setting; no new-GEN age qualification
 s['_spec_path']='tools/landed_parent/specs/qfd_tt_ctlm_dv_lpf_hp13_rrloc.json'
 put(s['_spec_path'],(json.dumps(s,indent=2)+'\n').encode(),'unique source construction recipe; no adoption')
 (out/'source_manifest.json').write_text(json.dumps(dict(scope='SOURCE ASSEMBLY ONLY: exact RR symbolic baseline + trueGI export + H16ZA source; explicit21 is NOT measured selected new GEN; RRrole/RRloc native transformation still owed',base=BASE,hp=HP,H16_source='c0ad783cd generated3',files=records),indent=2)+'\n')
 (out/'source.f').write_text('\n'.join(deps+hp_paths+head_paths)+'\n')
 print(out)
if __name__=='__main__':main()
