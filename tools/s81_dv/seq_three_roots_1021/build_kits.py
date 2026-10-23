from pathlib import Path
import json,copy
root=Path('.')
record=json.loads(Path('results/arch/codex_seq_three_roots_1021/dsdv_seq_host_c_r3_lp_record.json').read_text())
old=Path('tools/s81_dv/seq_region_1021/r2a_fences.tcl').read_text()
tail=old[old.index('proc lpf_seq'):old.index('foreach r {lk_0')]
tail=tail.replace('(?:lk|mid)','(?:lk|sq|vc)')
base=json.loads(Path('physical/ref_tile/dsdv_seq_host_r2a/spec.json').read_text())
for suffix,extra in [('a',0),('b',43.2)]:
 name='dsdv_seq_host_r3'+suffix;s=copy.deepcopy(base)
 s['name']=name;s['top']='dsdv_seq_host_c_r3_lp';s['sources']=[x.replace('/r2/','/r3/').replace('_r2','_r3') for x in s['sources']]
 s['outline']={'w':475.2+extra,'h':1339.2+extra,'exact':True}
 s['children'][1]['at']=[86.4,691.2+extra];s['children'][2]['at']=[86.4,1080+extra]
 s['clock_ports']=['ck_lk','ck_sq','ck_vc'];s['reset_ports']=['rst_n_lk','rst_n_sq','rst_n_vc']
 s['pins']['E']=[x for x in s['pins']['E'] if x not in ['ck_mid','rst_n_mid']]+['ck_sq','rst_n_sq','ck_vc','rst_n_vc']
 s['pin_ranges'].pop('ck_mid');s['pin_ranges'].pop('rst_n_mid')
 for r,y in [('sq',604.8+extra),('vc',972+extra)]:
  s['pin_ranges']['ck_'+r]=[y,y+6.48];s['pin_ranges']['rst_n_'+r]=[y+10.8,y+17.28]
 s['clock_entry_domains']['sq']={'ratio':[1,1],'ports':['ck_sq'],'inputs':['rst_n_sq'],'outputs':[]}
 s['clock_entry_domains']['vc']=s['clock_entry_domains'].pop('mid');s['clock_entry_domains']['vc']['ports']=['ck_vc'];s['clock_entry_domains']['vc']['inputs'][0]='rst_n_vc'
 s['landed_record']='results/arch/codex_seq_three_roots_1021/dsdv_seq_host_c_r3_lp_record.json'
 s['child_centre_tap']={'children':['u_l0','u_l1','u_l2'],'why':'The actual r2 roots failed child versus soft boundary checks. Insert real per-root clock buffer chains using exact CLOSED child TT/FF/SS boundary ranges, retaining actual clock measurements and the unchanged 80 ps gate.'}
 s['structural_change']='Three real child roots, 21 D2/E1 seams and four-stage regional resets. New SQ/VC command and return landings add four feedback edges. Each root owns local landing cells in a source-pinned placement band, with canonical physical child-centre clock taps. No child RTL or timing-limit change. Full programme proof required before physical gate.'
 j=s['job'];j['branch']='codex/s81-seq-three-roots-2308';j['tag']=name;j['views_to']='physical/ref_tile/'+name+'/views';j['record_to']='results/rtl/ref_tile/'+name
 j['extra_paths']=[x.replace('seq_region_1021','seq_three_roots_1021') for x in j['extra_paths']]
 for bench in j['benches']:
  for k,v in list(bench.items()):
   if isinstance(v,str):bench[k]=v.replace('seq_region_1021','seq_three_roots_1021')
 fence='tools/s81_dv/seq_three_roots_1021/r3'+suffix+'_fences.tcl';s['pin_hook_before_flops']=[fence]
 Path('tools/s81_dv/seq_three_roots_1021/'+name+'.json').write_text(json.dumps(s,indent=2)+'\n')
 bands={'lk':(507.6,550.8),'sq':(594+extra,680.4+extra),'vc':(950.4+extra,1036.8+extra)}
 members={r:[] for r in bands};own={}
 for seam in record['landings']:
  for side,reg in [('w',seam['src_region']),('r',seam['dst_region'])]:members[reg].append('u_lpl_'+seam['name']+'_'+side)
 lines=['# Actual source-owned landing bands; release exclusive regions before DPL/CTS.','set ::lpf_blk [ord::get_db_block]','set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]','array set ::lpf_g {}','array set ::lpf_n {}','array set ::lpf_c {}'];groups=[]
 for reg,hs in members.items():
  y0,y1=bands[reg];rows=(len(hs)+3)//4
  for ix,h in enumerate(hs):
   g=reg+'_'+str(ix);groups.append(g);own[h]=g;x0=54+(ix%4)*91.8;yy=y0+(ix//4)*(y1-y0)/rows
   box=[x0,yy,x0+91.8,yy+(y1-y0)/rows]
   lines += [f'set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_{g}"]','odb::dbBox_create $::lpf_r '+' '.join(f'[expr {{round({v:.6f}*$::lpf_dbu)}}]' for v in box),f'set ::lpf_g({g}) [odb::dbGroup_create $::lpf_r "lp_fence_grp_{g}"]']
  g=reg+'_rst';groups.append(g)
  lines += [f'set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_{g}"]','odb::dbBox_create $::lpf_r '+' '.join(f'[expr {{round({v:.6f}*$::lpf_dbu)}}]' for v in [432,y0,464.4+extra,y1]),f'set ::lpf_g({g}) [odb::dbGroup_create $::lpf_r "lp_fence_grp_{g}"]']
  for h in [f'u_lpr_{reg}_p']+[f'u_lpr_{reg}_c{i}' for i in range(8 if reg == 'sq' else 4)]+[f'u_lprc_u_l{list(bands).index(reg)}']:own[h]=g
 lines+=['array set ::lpf_own {'+' '.join(f'{k} {v}' for k,v in own.items())+'}',tail,'foreach r {'+' '.join(groups)+'} {','  if {![info exists ::lpf_n($r)] || $::lpf_n($r) < 1} { error "LP_FENCE: region $r got no landing cells" }','  if {![info exists ::lpf_c($r)]} { set ::lpf_c($r) 0 }','  puts "LP_FENCE $r cells=$::lpf_n($r) read_cone=$::lpf_c($r)"','}']
 Path(fence).write_text('\n'.join(lines)+'\n')
