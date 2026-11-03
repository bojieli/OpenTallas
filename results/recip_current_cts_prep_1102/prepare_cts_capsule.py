from pathlib import Path
import hashlib,json,shutil
source=Path('/srv/opentallas-scratch2/claude/codex-recip-place-canary-prep-0810');out=Path('/srv/opentallas-scratch2/claude/codex-recip-cts-lifecycle-prep-1102r0');assert not out.exists();out.mkdir();k=out/'kit';k.mkdir();d=json.loads((source/'PLACE_EXPECTED.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel,want in d['expected'].items():
 p=source/'kit'/rel;assert sha(p)==want,rel;q=k/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
base='run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base';extra={}
for n in ['3_place.odb','3_place.sdc']:
 rel=base+'/'+n;shutil.copy2(source/'kit'/rel,k/rel);extra[rel]=sha(k/rel)
assert extra[base+'/3_place.odb']=='9ba70335e4f85dc5bd467e67629ab9a1db18143f8c319ea86656e531d3f9586f'
for n in ['pg_native_qualified_562.tcl','pg_native_8c9.so']:shutil.copy2(source/'kit'/n,k/n)
(out/'source/tools').mkdir(parents=True);shutil.copy2(k/'orfs_hold_mm.tcl',out/'source/tools/orfs_hold_mm.tcl')
result={'status':'SOURCE_ONLY_CTS_LIFECYCLE_PREP_NOT_RELEASED','source_case':str(source),'original_inputs':d['expected'],'actual_saved_PLACE_inputs':extra,'original94_unchanged':True,'OT_PG_STRICT':'Preserve original manual UNSET; no 1-to0 change','global_strict_CTS_admission':'UNCHANGED_UNSUPPORTED','KW_RESUME':'FULL unchanged / manual physical continuation','no_old_tree_or_model_transfer':True};(out/'CTS_SOURCE_INPUTS.json').write_text(json.dumps(result,indent=2)+'\n');(out/'.keep').write_text('Owned CURRENT RECIP CTS source-only PREP. No physical job released or launched. Preserve current saved PLACE and source inputs.\n');print(str(out))
