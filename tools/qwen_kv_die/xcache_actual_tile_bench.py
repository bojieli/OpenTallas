#!/usr/bin/env python3
"""Immutable-source actualCEXT2/XLOCAL gate; run this command under ot-run."""
import argparse,hashlib,json,os,pathlib,shutil,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
PARENT_FILES=['rtl/hdc/'+n+'.sv' for n in ['ot_qwen_me_array_w12','ot_qwen_rom_tile_w12','ot_hdc_matvec','ot_hdc_fpu','ot_hdc_fp32_mul_pipe','ot_hdc_fastfp','ot_hdc_delay','ot_hdc_sfu','ot_hdc_fp32_add_lat','ot_hdc_fp32_add_lat_nr','ot_hdc_prefix','ot_qwen_w12_matvec','ot_qwen_w12_arith']]+['rtl/proto/ot_fp32_add_rne_pipe.sv','rtl/physical/ot_qwen_tile_lsl.sv','rtl/physical/ot_qwen_tile_node.sv','rtl/lib/ot_rst_relay.sv','rtl/physical/ot_qwen_tile_kids.sv','rtl/physical/ot_qwen_tile_ctl.sv']
LOCAL_FILES=['rtl/physical/ot_qwen_xcache_indexed.sv','rtl/test/qwen_kv_die/tb_qwen_xcache_actual_tile.sv']
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent-commit',required=True);p.add_argument('--workdir',type=pathlib.Path,required=True);p.add_argument('--prepare-only',action='store_true');p.add_argument('--native-tp8',action='store_true');a=p.parse_args()
 out=a.workdir.resolve();out.mkdir(parents=True,exist_ok=True);src=out/'src';src.mkdir(exist_ok=True)
 commit=subprocess.check_output(['git','rev-parse',a.parent_commit],cwd=ROOT,text=True).strip()
 manifest={'parent_commit':commit,'actual_tile_GT':3072 if a.native_tp8 else 6144,'NW':18,'CEXT':2,'ME_EXTRA':8,'local_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sources':{}}
 for f in PARENT_FILES+LOCAL_FILES:
  b=subprocess.check_output(['git','show',commit+':'+f],cwd=ROOT) if f in PARENT_FILES else (ROOT/f).read_bytes()
  dest=src/f;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b);manifest['sources'][f]=hashlib.sha256(b).hexdigest()
 if a.native_tp8:
  import sys
  sys.path.insert(0,str(ROOT/'tools'));import hdc_isa as I
  progpath='results/rtl/ref_tile/qfd_su_vreduce/native_profile_1013/candidate_tp8_layer0.hex'
  prog=subprocess.check_output(['git','show','14065c8c7:'+progpath],cwd=ROOT)
  sha=hashlib.sha256(prog).hexdigest()
  if sha!='120b42a583db68fb9faaa32d2076f1515d5c07e41787bf47533a1d230b4d1903':raise RuntimeError('candidate program provenance mismatch')
  fields=[('me_nout',18),('me_tiles',18),('me_k',18),('me_wsrc',1),('me_wbase',24),('me_ts',24),('me_ks',24),('me_js',24),('me_xbase',24),('me_xks',24),('me_xjs',24),('me_xcs',24),('me_jsh',3),('me_split',4),('me_wcs',24),('me_round',1),('me_obase',24),('me_ots',24),('me_ojs',24),('me_mmode',1),('me_oen',1),('me_amax',1),('me_rmax',1),('me_mbase',24)]
  words=prog.decode().splitlines();packed=[];profiles=[]
  for pc in [1,16,19,23]:
   f=I.decode(int(words[pc],16));w=0
   for name,bits in fields:
    value=f[name]
    if not 0<=value<1<<bits:raise RuntimeError('native field out of range')
    w=(w<<bits)|value
   packed.append(f'{w:095x}');profiles.append({'pc':pc,'fields':{n:f[n] for n,b in fields}})
  (src/'native_profiles.hex').write_text('\n'.join(packed)+'\n')
  (out/'candidate_program.hex').write_bytes(prog)
  manifest['program']={'commit':'14065c8c7','path':progpath,'sha256':sha,'status':'candidate_profile_only_not_checkpoint_or_token_qualification','profiles':profiles}
  manifest['defines']=['XCACHE_TP8']
 (out/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
 if a.prepare_only:return
 vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')
 for name,mut in [('positive',0),('row_mutant',1),('extra_XL_edge_mutant',2)]+([('raw_split_diagnostic',0)] if a.native_tp8 else []):
  cmd=[vlt,'--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_xcache_actual_tile','--Mdir',str(out/('obj_'+name)),f'-GMUT={mut}']+(['-GALL_SPLITS=1'] if name=='raw_split_diagnostic' else [])+(['-DXCACHE_TP8'] if a.native_tp8 else [])+PARENT_FILES+LOCAL_FILES
  with (out/(name+'_build.log')).open('w') as log:subprocess.run(cmd,cwd=src,stdout=log,stderr=subprocess.STDOUT,check=True)
  r=subprocess.run([str(out/('obj_'+name)/'Vtb_qwen_xcache_actual_tile')],cwd=src,capture_output=True,text=True)
  (out/(name+'.log')).write_text(r.stdout+r.stderr)
  if mut==0:
   if r.returncode or 'PASS actual CEXT2 tile' not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
   print(r.stdout,flush=True)
  elif r.returncode==0 or 'actual CEXT2 arithmetic mismatch' not in r.stdout+r.stderr:raise RuntimeError('mutant did not fail actual arithmetic: '+r.stdout+r.stderr)
  else:print('PASS rejected '+name,flush=True)
 print('PASS actualtile all gates',flush=True)
if __name__=='__main__':main()
