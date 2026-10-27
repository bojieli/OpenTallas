import json,subprocess,math
from pathlib import Path
root=Path('/srv/opentallas-scratch2/claude/wt/codex-flow-2004')
p=root/'results/hold_pad_dispatch_1026/mesh3_count.json';d=json.loads(p.read_text());frag=json.loads(subprocess.check_output(['git','-C','/home/ubuntu/OpenTallas','show','b6b245b1d1:results/qc_clk_mesh3/hold_demand_fragment.json']));sl=json.loads(subprocess.check_output(['git','-C','/home/ubuntu/OpenTallas','show','32fa41d13d:results/qc_mp_region2/seam_landing.json']));bits={'|'.join(sorted((x['a'],x['b']))):x['bits_ab']+x['bits_ba'] for x in sl['seams']};pairs=frag['clock']['hold_demand']['pairs'];assert set(bits)==set(pairs)
rows=[]
for k,v in pairs.items():
 n=math.ceil((12.28+v)/(46.90*.95)-1e-9);rows.append(dict(pair=k,bits=bits[k],demand_ps=v,cells_per_bit=n,cells=bits[k]*n))
d.update(basis='UNCHECKED contract budget pending final revised QC plan and actual endpoint mapping; source hold fragment b6b245b1d1 + segmented seam bits32fa41d13d (QC peer confirmed same e482 plan). Hold12.28ps; HB4ff46.90*.95; sender12.5 cancels uncertainty half.',seam_bits_source='32fa41d13d:results/qc_mp_region2/seam_landing.json',pair_rows=rows,bits=sum(bits.values()),pair_cells=sum(x['cells'] for x in rows),pair_area_mm2=sum(x['cells'] for x in rows)*.1021/1e6,zero_bits_pairs=[k for k,v in bits.items() if not v]);d.pop('uncovered_pairs',None);p.write_text(json.dumps(d,indent=1)+'\n');print(json.dumps({k:v for k,v in d.items() if k not in ['pair_rows','type_port_rows','zero_bits_pairs']},indent=1))
