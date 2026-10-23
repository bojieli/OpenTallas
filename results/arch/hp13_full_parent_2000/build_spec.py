from pathlib import Path
import json,re,hashlib
r=Path('/home/ubuntu/wt/codex-qk-hp13-parent-2000')
template=json.load(open('/home/ubuntu/wt/codex-qk-hroot-sp6-physical-2000/physical/ref_tile/qkd_hr_ingest_eng_sp6a/spec.json'))
audit=json.load(open('/home/ubuntu/wt/codex-qk-hp13-audit-2000/results/arch/hp13_corepub39_1021/DATA_CLOCK_OWNERS.json'))
base='rtl/qwen_dv/headprep13/'
shared=[base+'corepub39/qfd_hp13_corepub39.sv',base+'native32/qfd_tt_ctlm_dv_hp13_rrloc_helpers.sv',base+'h16za/native32_1r_param.v',base+'h16za/native32_helpers.sv','rtl/qwen_dv/qfd_tt_ctlm_dv_wtn.sv']
mac=[]
for rel,prefix,root in [(audit[0]['rtl'],'','ck_core'),(shared[2],'u_hr.','ck_hr')]:
 for line in (r/rel).read_text().splitlines():
  s=re.sub(r'^\(\*.*?\*\)\s*','',line)
  m=re.match(r'(ot_(?:sram|rom)_\w+)\s+(?:#\(.*?\)\s+)?(\\[^\s]+|\w+)\s*\(',s)
  if m:
   typ,inst=m.groups();inst=inst.lstrip('\\');mac.append((typ,prefix+inst,root))
assert len(mac)==19,len(mac)
views=sorted({x[0]for x in mac});sources=shared+['physical/asap7_memory_macros/'+x+'/'+x+'_bb.v'for x in views]
for variant in [1,2]:
 j=json.loads(json.dumps(template));top=audit[variant-1]['master'];name='qfd_hp13_cpub39_full_'+('main'if variant==1 else'alt');j.update(name=name,top=top,sources=[audit[variant-1]['rtl']]+sources,clock_port='ck_core',clock_ports=['ck_core','ck_hr'],reset_ports=['rst_n'],outline={'w':907.2 if variant==1 else 993.6,'h':561.6 if variant==1 else 648.0})
 j['params']={};j.pop('slot_change_request',None);j['fill_reason']={'macro_bound':'19 authentic macros with channels and two actual source clock domains; source synthesis area estimate40000um2, actual utilization remains measured.'};j['route'].update(peak_ram_gb=96,period_ps=770,signoff_period_ps=833.333)
 domains={x:{'ratio':[1,1],'ports':[x],'inputs':[],'outputs':[]}for x in ['ck_core','ck_hr']}
 for p,v in audit[variant-1]['ports'].items():
  if v['status']=='PROVEN' and len(v.get('clock_ports',[]))==1:
   domains[v['clock_ports'][0]]['inputs'if p in audit[variant-1]['input_captures']else'outputs'].append(p)
 domains['ck_core']['inputs']+=['rst_n','dh_user'];j['clock_entry_domains']={'core':domains['ck_core'],'hr':domains['ck_hr']};j['clock_data_paths']='related_same_frequency'
 j['soft_root_macro_masters']=views;j['soft_root_macro_bindings']={inst:{'master':typ,'clock_pin':'clk','root':clk}for typ,inst,clk in mac}
 j['macros']=[];large=[x for x in mac if '64x512'in x[0]];others=sorted([x for x in mac if x not in large],key=lambda x:(0 if 'rom_4096x266' in x[0] else 1 if 'rom_'in x[0] else 2,x[1]))
 for k,(typ,inst,clk)in enumerate(large):j['macros'].append({'view':'physical/asap7_memory_macros/'+typ,'count':1,'inst':inst,'at':[216+216*(k%3),43.2+129.6*(k//3)],'orient':'R0'})
 for k,(typ,inst,clk)in enumerate(others):
  # Bottom strip: dedicated channels for each ROM and narrow SRAM.
  x=172.8+(151.2*k if k<5 else 86.4*(k-5));y=432.0 if k<5 else 518.4
  j['macros'].append({'view':'physical/asap7_memory_macros/'+typ,'count':1,'inst':inst,'at':[round(x,3),round(y,3)],'orient':'R0'})
 # use a taller MAIN to fit the second bottom strip with genuine channels
 j['outline']={'w':864.0,'h':561.6}
 ports=re.findall(r'^(?:input|output) wire \[[^\]]+\] (\w+);',(r/audit[variant-1]['rtl']).read_text(),re.M)
 j['pins']={s:[]for s in ['N','S','E','W']}
 for k,p in enumerate(ports):j['pins'][['W','E','S','N'][k%4]].append(p)
 j['pin_regs']={'enable':False,'reason':'Exact native full parent retains all source capture/publication registers; no added edge or source rewrite.'}
 j['reset_landing']={'enable':False,'reason':'Preserve exact source reset forests; full-parent reset release and removal remain measured obligations, no source-edge inference.'}
 j['structural_change']='First actual full dual-clock cpub39 parent, including complete H16ZA source and nineteen authentic memory macros. No borrowed hard child or tiny-bank view.'
 j['safe_design_checklist']={'1_pins':'Exact source native boundaries; full-face distribution, no extra edge. Actual pin register census required.','2_reach':'Macro channels >=20um; full physical reach measured, no die transport credit.','3_fanout':'Native-first strict census required for complete composed parent.','4_depth':'Unchanged source math and833.333ps target; measured CTS timing required.','5_storage':'19 actual SRAM/ROM macros, no inferred replacement.','6_floorplan':'Lattice placements, continuous west216um band, >=20um channels.','7_clock':'Two real source roots ck_core/ck_hr, same PLL intended1:1/phase0, measured qualification open.','8_schedule':'Variant1/2 retain exact publisher stages; all existing source ages unchanged, actual routed ages required.'}
 j['job']={'owner':'CODEX-QK-2000','branch':'codex/qk-hp13-parent-2000','tag':'hpfull'+str(variant),'purpose':'Full source-bound HP13 native-first physical qualification; not a die result','extra_paths':['results/arch/hp13_corepub39_1021'],'benches':[]}
 d=r/'physical/ref_tile'/name;d.mkdir(parents=True,exist_ok=True);(d/'spec.json').write_text(json.dumps(j,indent=2)+'\n')
print('Full parent:',len(mac),'memory macros, source files',len(sources)+1)
