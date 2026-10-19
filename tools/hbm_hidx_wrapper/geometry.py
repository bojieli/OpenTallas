import json,re,math
from pathlib import Path
j=json.loads(Path('out/netlist.json').read_text());cells=j['modules']['hidx_coupon1']['cells'];lef=Path('canonical/cells.lef').read_text()
masters={}
for name,body in re.findall(r'MACRO\s+(\S+)\s+(.*?)END\s+\1\s',lef,re.S):
 z=re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',body)
 if z:masters[name]=[float(z[1]),float(z[2])]
used={c['type'] for c in cells.values() if c['type']!='$scopeinfo'}
assert used<=masters.keys(),used-masters.keys()
assert all(abs(masters[t][1]-.270)<1e-6 and abs(masters[t][0]/.054-round(masters[t][0]/.054))<1e-5 for t in used)
width=sum(masters[c['type']][0] for c in cells.values() if c['type']!='$scopeinfo')
area=width*.270;core=136.08;rows=504;band_rows=104;startrow=200
capacity=band_rows*core*.270;clock_area=95*masters['BUFx8_ASAP7_75t_R'][0]*.270
r=dict(scope='MODEL ONLY; no physical engine',die_um=[140.4,140.4],core_um=[2.16,2.16,138.24,138.24],legal_rows=rows,sites_per_row=2520,site_um=[.054,.270],all_rows_retained=True,band=dict(kind='ONE FULLWIDTH CONNECTED allocation; not FENCE or placement',row_first=startrow,row_count=band_rows,xlo=2.16,xhi=138.24,ylo=2.16+startrow*.270,yhi=2.16+(startrow+band_rows)*.270,capacity_um2=capacity,target_local_fill=.55),native_area_um2=json.loads(Path('out/native_summary.json').read_text())['area'],physical_lef_area_um2=area,cell_width_sum_um=width,whole_core_fill=area/core**2,band_fill_before_cts=area/capacity,analytical_clock_cells=95,analytical_clock_area_um2=clock_area,band_fill_with_clock_allowance=(area+clock_area)/capacity,additional_area_to_55pct_um2=capacity*.55-area-clock_area,actual_INT8_clock_reference_um2=75.86,band_fill_with_INT8_reference=(area+75.86)/capacity,additional_area_to_55pct_with_INT8_reference_um2=capacity*.55-area-75.86,root_selected_rows=104,native_master_dimensions_um={t:masters[t] for t in sorted(used)},pg=dict(birth_binding='a92 full-MTerm policy REQUIRED for every newly created native instance; no kit activation',terminals_before_cts=22290,rail_pitch_um=.270,rail_contact='legal-row/M1-contact MODEL only; actual terminal rectangles/vias/connectivity OPEN',actual_connected_terminals=None),placement=None,cts=None,route=None)
# Liberty statistical area and LEF footprint are separately retained; use real widths.
assert abs(json.loads(Path('out/native_summary.json').read_text())['area']-1651.18500)<1e-4
Path('out/geometry.json').write_text(json.dumps(r,indent=2)+'\n')
