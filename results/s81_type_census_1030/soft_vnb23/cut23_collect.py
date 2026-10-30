from pathlib import Path
import json,re,hashlib
r=Path('/srv/opentallas-scratch2/claude/codex-s81types-1030');out=[]
old={1:94717,3:138117,4:123432,5:88282}
for t in [1,3,4,5]:
 k=r/f'kv_cut23_t{t}';p=next(k.glob('run/reports/**/synth_stat.txt'));s=p.read_text();row=re.findall(r'^\s*(\d+)\s+\S+\s+\S+\s+\S+\s+cells$',s,re.M)[-1];ffs={m[2]:int(m[1]) for m in re.finditer(r'^\s*(\d+)\s+\S+\s+\S+\s+\S+\s+(DFF\S+)$',s,re.M)};macs={m[2]:int(m[1]) for m in re.finditer(r'^\s*(\d+)\s+\S+\s+\S+\s+\S+\s+(ot_sram\S+)$',s,re.M)}
 area=float(re.findall(r'Chip area for top module .*?: ([0-9.]+)',s)[-1]);ma=0.
 for m,n in macs.items():
  lib=k/'macros'/(m+'_tt.lib');a=float(re.search(r'\barea\s*:\s*([0-9.eE+-]+)',lib.read_text())[1]);ma+=n*a
 out.append(dict(type=f'ot_s81sl_kv_leaf__t{t}',mapped_total=int(row),mapped_total_24cut=old[t],measured_VNb_soft_delta=int(row)-old[t],flops=sum(ffs.values()),flop_types=ffs,real_sram_instances=macs,real_sram_total=sum(macs.values()),reported_chip_area_um2=area,real_sram_area_um2=ma,standard_cell_area_um2=area-ma,cycles_added=0,retained_soft=['VN_b','VQ'],expected_abstract_children=23,scope='MAPPED_CENSUS_ONLY; native old-source frozencanonical sameas24cut; no physical macro/clock/ABI adoption',report_sha256=hashlib.sha256(s.encode()).hexdigest()))
j=dict(rows=out,source='Same original frozen canonical/native configs; ONLY removed *ot_s81sl_vn_b from24cut SYNTH_BLACKBOXES. New postmaps include realVNb SRAM, not behavioralflattened storage.',next='Real23childviews and4SRAM parent packing+58177..sourceclockloadcomposition; reservedinputs+FTspareFACE fixes; fullparent594/597 ABI stillheld',adopted=False)
(r/'cut23_results.json').write_text(json.dumps(j,indent=1)+'\n');print(json.dumps(j,indent=1))
