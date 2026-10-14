#!/usr/bin/env python3
"""Prepare immutable real cached-parent/RPS0 gate sources for ot-run."""
import argparse,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/qwen_kv_die'))
from xcache_actual_tile_bench import PARENT_FILES
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent-commit',required=True);p.add_argument('--workdir',type=pathlib.Path,required=True);p.add_argument('--context-mailbox',action='store_true');p.add_argument('--split-cache',action='store_true');a=p.parse_args()
if a.context_mailbox and a.split_cache:p.error('select one parent harness mode')
out=a.workdir.resolve();src=out/'src';src.mkdir(parents=True,exist_ok=True)
parent=PARENT_FILES+['rtl/physical/ot_qwen_rom_tile_nkt.sv','rtl/physical/ot_qwen_tile_rpair.sv']
parent+=['rtl/physical/ot_qwen_tile_tp8_cached_split.sv','rtl/physical/ot_qwen_xcache_split32.sv'] if a.split_cache else ['rtl/physical/ot_qwen_tile_tp8_cached.sv','rtl/physical/ot_qwen_xcache_indexed.sv']
local=['rtl/test/qwen_kv_die/tb_qwen_xcache_split_parent.sv'] if a.split_cache else ['rtl/test/qwen_kv_die/tb_qwen_xcache_parent.sv'] if not a.context_mailbox else ['rtl/test/qwen_kv_die/tb_qwen_xcontext_parent.sv','rtl/physical/ot_qwen_xcontext_protocol.sv']
commit=subprocess.check_output(['git','rev-parse',a.parent_commit],cwd=ROOT,text=True).strip()
manifest={'parent_commit':commit,'actual_tile_GT':3072,'NW':18,'CEXT':2,'ME_EXTRA':8,'physical_claim':False,'sources':{}}
for f in parent+local:
 b=subprocess.check_output(['git','show',commit+':'+f],cwd=ROOT) if f in parent else (ROOT/f).read_bytes()
 q=src/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);manifest['sources'][f]=hashlib.sha256(b).hexdigest()
old=json.loads((ROOT/'results/rtl/qwen_xcache_actual_tile_1013/native/provenance.json').read_text())
manifest['program']=old['program']
progpath=old['program']['path'];prog=subprocess.check_output(['git','show','14065c8c7:'+progpath],cwd=ROOT)
if hashlib.sha256(prog).hexdigest()!=old['program']['sha256']:raise RuntimeError('candidate profile hash mismatch')
# Same exact program fields as the canonical actual-tile gate.
fields=[('me_nout',18),('me_tiles',18),('me_k',18),('me_wsrc',1),('me_wbase',24),('me_ts',24),('me_ks',24),('me_js',24),('me_xbase',24),('me_xks',24),('me_xjs',24),('me_xcs',24),('me_jsh',3),('me_split',4),('me_wcs',24),('me_round',1),('me_obase',24),('me_ots',24),('me_ojs',24),('me_mmode',1),('me_oen',1),('me_amax',1),('me_rmax',1),('me_mbase',24)]
packed=[]
for profile in old['program']['profiles']:
 w=0
 for name,bits in fields:w=(w<<bits)|profile['fields'][name]
 packed.append(f'{w:095x}')
(src/'native_profiles.hex').write_text('\n'.join(packed)+'\n');(out/'candidate_program.hex').write_bytes(prog)
(out/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
