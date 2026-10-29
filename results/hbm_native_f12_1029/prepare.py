"""Stage the actual bundle wrapper golden and explicit native f12 candidates."""
from pathlib import Path
import hashlib,json,re,shutil,sys
W,O=map(Path,sys.argv[1:]);R=Path(__file__).parent;B=W/'physical/die_plan/hbm/bind/r18h5_bundle/rtl/hdc';N=W/'rtl/hbm_accel/generic/adapters/native_f12/ot_hdc_fastfp_lat_native_f12.sv'
O.mkdir(parents=True,exist_ok=True);(O/'rtl').mkdir(exist_ok=True)
old=(B/'ot_hdc_fastfp_lat.sv').read_text();new=N.read_text()
# Exact default-off resolution: only the two new explicit macro branches differ.
resolved=new[new.index('`timescale'):]
for flag in ('OT_HBM_NATIVE_F12_ADD4','OT_HBM_NATIVE_F12_MUL5'):
 resolved,n=re.subn(r'`ifdef '+flag+r'\n.*?`else\n(.*?)`endif\n',r'\1',resolved,flags=re.S)
 assert n==1
assert resolved==old,'default wrapper changed'
# The f12 arithmetic body is the canonical repository implementation. The
# bundle's existing prefix callee alias is the sole textual distinction.
f12=(B/'ot_hdc_fp32_f12.sv').read_text()
assert f12.replace('ot_hdc_ksadd_k__u1','ot_hdc_ksadd_k').replace('ot_hdc_inc_k__u1','ot_hdc_inc_k')==(W/'rtl/hdc/ot_hdc_fp32_f12.sv').read_text()
deps=['ot_hdc_fastfp.sv','ot_hdc_fp32_mul_lat.sv','ot_hdc_fp32_add_lat.sv','ot_hdc_prefix.sv','ot_hdc_fp32_f12.sv']
for n in deps:shutil.copy(B/n,O/'rtl'/n)
shutil.copy(N,O/'rtl'/N.name)
gold=re.sub(r'\b(ot_hdc_(?:qmul_lat|qadd_lat|kadd|kge|kinc))\b',r'\1_gold',old)
(O/'rtl/gold_fastfp_lat.sv').write_text(gold)
for n in ('profile_eq.sv','profile_eq.cpp','run.sh'):shutil.copy(R/n,O/n)
paths=[B/'ot_hdc_fastfp_lat.sv',N]+[B/n for n in deps]
receipt=dict(default_off_wrapper_byte_identical=True,bundle_f12_body_canonical_after_prefix_alias_normalization=True,files=[dict(path=str(p.relative_to(W)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in paths],profiles=dict(minimal_4_4_0=dict(MLAT=4,ALAT=4,WCOPY=0,defines=['OT_HBM_NATIVE_F12_ADD4'],added_cycles=0),candidate_5_4_1=dict(MLAT=5,ALAT=4,WCOPY=1,defines=['OT_HBM_NATIVE_F12_ADD4','OT_HBM_NATIVE_F12_MUL5'],added_cycles=dict(each_multiply=1,bank_write_visibility=1,each_add=0))),status='Source candidates only; actual hierarchy/profile/caller/token/physical gates required')
(O/'source_closure.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
