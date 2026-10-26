#!/usr/bin/env python3
"""Exact source-bound requested pins for three HC partition prototypes.
Tcl is a data list, not a PG/pin audit bypass. Actual track placement is exported by owner.
"""
import csv,json
from pathlib import Path
from hbm_system_graph import module
BASE=Path('/home/ubuntu/wt/hc-physical-1015/rtl/hbm_accel/generic/peers/static_hc')
OUT=Path(__file__).resolve().parents[1]/'results/arch/hbm_system_geometry_1015/physical_assignments'
CONFIG={
 'HC_weight_quarter_exact_source':dict(top='ot_hgi_hc_weight_quarter_static',size=[204.336,194.4],FF=1059,macros=[dict(instance=f'slot[{i}].u_weight',origin_um=[55.296,y],size_um=[94.824,41.04],orientation='MY') for i,y in enumerate([23.76,100.44])],faces={'W':['weight_ap'],'N':['expected_bank_id','expected_quarter_id','read_v','read_slot','read_row','rst_n','clk'],'E':['weight_data','write_done','read_valid','fault']},counts={'W':278,'N':16,'E':259},clock=['N',102.144],latency='ap sample n→writecommit n+1; macroread n→raw n+1→output n+2→MACcapture n+3 (TML3)'),
 'HC_residual_half_exact_source':dict(top='ot_hgi_hc_residual_half_static',size=[273.456,194.4],FF=783,macros=[dict(instance='u_residual',origin_um=[55.296,43.2],size_um=[174.744,70.47],orientation='MY')],faces={'W':['write_v','write_word','write_data'],'N':['read_v','read_word','rst_n','clk'],'E':['residual_data','read_valid','fault']},counts={'W':267,'N':13,'E':258},clock=['N',136.704],latency='NEW+1 residualwriteedge sample n→commit n+1; macroread n→raw n+1→output n+2→MACcapture n+3. Actual sourceproof/compilerwrite calendar must retain addededge.'),
 'HC_control_exact_source':dict(top='ot_hgi_hc_bank_control_static',size=[129.6,86.4],FF=461,macros=[],faces={'W':['clk','rst_n','d_v','d_ss','d_nv','d_wa','d_xa','f_in','lane_fault','memory_fault'],'E':['o_v','o_ss','o_nv','o_wa','o_xa','f_out'],'N':['w_read_v','x_read_v','w_read_addr','x_read_addr'],'S':['lane_valid','lane_ss','lane_go']},counts={'W':53,'E':41,'N':34,'S':65},clock=['W',43.2],latency='actual source NC8/ML3 bounded stage-control pipeline; no addededge from placement')}
def generate(name,c):
 src=BASE/(c['top']+'.sv');m=module(src,c['top']);counts={f:sum(m['ports'][p]['bits']for p in ports)for f,ports in c['faces'].items()};assert counts==c['counts'],(name,counts)
 rows=[];width,height=c['size']
 for face,ports in c['faces'].items():
  names=[]
  for port in ports:
   bits=m['ports'][port]['bits'];names += [port] if bits==1 else [f'{port}[{i}]'for i in range(bits)]
  data_names=[n for n in names if n!='clk']
  for pin in names:
   if pin=='clk':along=c['clock'][1]
   else:
    k=data_names.index(pin);pitch=.192 if face in ['W','E'] and name!='HC_control_exact_source' else .864
    edge=height if face in ['W','E'] else width
    along=(edge-pitch*(len(data_names)-1))/2+pitch*k
   if name=='HC_weight_quarter_exact_source' and pin=='read_row[0]':along=102.600
   xy=[0 if face=='W' else width,along] if face in ['W','E'] else [along,0 if face=='S' else height]
   rows.append(dict(port_bit=pin,face=face,layer='M4'if face in ['W','E']else'M5',requested_x_um=round(xy[0],6),requested_y_um=round(xy[1],6)))
 # Tech-preview check only: actual ODB PG/track audit remains authoritative.
 preview={}
 for face in c['faces']:
  snapped=[]
  for r in rows:
   if r['face']!=face:continue
   value=r['requested_y_um'] if face in ['W','E'] else r['requested_x_um']
   site=.012+.048*round((value-.012)/.048)
   assert abs(site-value)<=.024+1e-9,(name,r)
   snapped.append((site,r['port_bit']))
  snapped.sort()
  for a,b in zip(snapped,snapped[1:]):assert b[0]-a[0]>=.096-1e-9,(name,face,a,b)
  preview[face]={'track_pitch_um':.048,'track_offset_um':.012,'minimum_nearest_site_spacing_um':round(min((b[0]-a[0] for a,b in zip(snapped,snapped[1:])),default=0),6),'actual_ODB_readback_required':True}
 with (OUT/(name+'.tsv')).open('w')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
 tcl=['# Source-bound REQUESTED pins only. Read actual outline/tracks/PG before placement.',f'# sourceSHA256 {m["source_sha256"]}',f'set hbm_geometry_requested_outline {{{width} {height}}}','set hbm_geometry_requires_actual_outline_track_PG_readback 1','set hbm_geometry_pin_requests {']
 tcl += ['  {'+' '.join(str(r[k])for k in ['port_bit','face','layer','requested_x_um','requested_y_um'])+'}'for r in rows];tcl.append('}')
 (OUT/(name+'_pins.tcl')).write_text('\n'.join(tcl)+'\n')
 d=dict(status='SOURCE_BOUND_INDEPENDENT_PROTOTYPE_SOURCE_PROOF_PASS_PHYSICAL_PENDING',source_commit='473756fb3',source=str(src),source_sha256=m['source_sha256'],master=c['top'],actual_ports=m['ports'],outline_um=c['size'],exact_requested=True,permitted_platform_snap='record actual dimensions and rederive edge pin coordinates; requested pins are not actual coordinates',orientation='R0',face_bits=counts,literal_bits=sum(counts.values()),source_proc_opt_FF=c['FF'],mapped_FF=None,macro_clock_pins=len(c['macros']),source_clock_endpoints=c['FF']+len(c['macros']),roots=1,clock_period_ps=833.333333,macros=c['macros'],minimum_core_macro_channel_um=20,latency=c['latency'],requested_pins=rows,nearest_track_collision_preflight=preview,actual_pin_rectangles=None,above_pin_keepout_required=True,cut_limit=.60,adoption_allowed=False,whole_engine_minimum_roots=92,root_count_scope='88bankMAC/memory/control roots +4globals; excludes commonPC/prefetch HBM domain partitions and fullnativejoin',whole_engine_arithmetic_SRAMs=80,whole_engine_composition_qualified=False,remaining=['actual source-specific mappedclock census','exact fixedFF/macro halo/PG/track readback','nativephi-R/spread/slew/setup/hold','actual route DRC0','MACsum exact ETMmax406.491um','globalAP/control/response wiring andcalendar'])
 (OUT/(name+'.json')).write_text(json.dumps(d,indent=2)+'\n');return name,counts,m['source_sha256']
if __name__=='__main__':
 for name,c in CONFIG.items():print(generate(name,c))
