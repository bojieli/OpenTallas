#!/usr/bin/env python3
"""Selected integration-only alpha-renaming; canonical Carson/c12 files untouched."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'rtl/hbm_accel/integrated_20261006/sfu_c12_selected'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--no-parent-list',action='store_true');a=ap.parse_args()
 sources=(ROOT/'physical/hbm_die_abstracts_20261006/compute/sources.f').read_text().splitlines()
 shared={'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv'}
 # No HC_POST instantiation or copied known-wrong HC arithmetic.
 sources=[p for p in sources if p not in shared and p not in {
  'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv','physical/hbm_die_abstracts_20261006/compute/ot_hbm_hc_quarter.sv'}]
 # Actual f12 add/multiply require canonical lzc32/mul24_rows helpers.
 helper='rtl/hdc/ot_hdc_fastfp.sv'
 names=[]
 for p in sources+[helper]:names+=re.findall(r'^\s*module\s+(\w+)',(ROOT/p).read_text(),re.M)
 assert len(names)==len(set(names))
 mapping={n:'ot_hbm_selected_c12__'+n for n in names}
 pattern=re.compile(r'\b('+'|'.join(map(re.escape,mapping))+r')\b')
 OUT.mkdir(exist_ok=True)
 exports=[];records={}
 # Preserve original framing module ABI/name; only child module reference is
 # alpha-renamed. There is exactly one framed module in the selected source list.
 sources+=['physical/hbm_die_abstracts_20261006/compute/ot_hbm_sfu_quarter_framed.sv',helper]
 for i,p in enumerate(sources):
  src=(ROOT/p).read_text();dst=pattern.sub(lambda m:mapping[m.group()],src)
  assert pattern.sub(lambda m:mapping[m.group()],src)==dst
  target=OUT/(str(i).zfill(2)+'_'+Path(p).name)
  target.write_text('// Integration-only c12 namespace export. Canonical source: '+p+'\n'+dst)
  exports.append(str(target.relative_to(ROOT)))
  records[str(target.relative_to(ROOT))]=dict(canonical=p,canonical_sha256=hashlib.sha256(src.encode()).hexdigest(),
    exported_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),transformation='module identifier alpha-renaming only')
 original=(ROOT/'physical/hbm_die_abstracts_20261006/memory_control/formatter_provider.files.f').read_text().splitlines()
 extra=sorted(shared)+exports+[
  'physical/hbm_die_abstracts_20261006/compute/ot_hbm_compute_frame1024.sv',
  'rtl/hbm_accel/collective/ot_hbm_accel_gu_metadata.sv',
  'rtl/hbm_accel/integrated_20261006/ot_hbm_integrated_stage_join.sv',
  'rtl/hbm_accel/integrated_20261006/ot_hbm_integrated_sfu_c12_stage.sv',
  'rtl/hbm_accel/integrated_20261006/ot_hbm_integrated_sfu_provider_join.sv']
 if not a.no_parent_list:(OUT.parent/'sfu_c12_selected_parent.files.f').write_text('\n'.join(dict.fromkeys(original+extra))+'\n')
 result=ROOT/'results/uarch/hbm_integrated_sfu_provider_join_20261006'
 (result/'namespace_export.json').write_text(json.dumps(dict(mapping=mapping,files=records,
   arithmetic_changes=0,new_module_instances=0,canonical_files_edited=False),indent=2)+'\n')
if __name__=='__main__':main()
