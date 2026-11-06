import importlib.util,json,re,sys,hashlib,argparse
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--source-sdc',type=Path,required=True);ap.add_argument('--abi',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source-sync',type=Path);args=ap.parse_args()
wt=Path(__file__).resolve().parents[4]
args.out.mkdir(parents=True,exist_ok=True)
p=wt/'physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py'
sp=importlib.util.spec_from_file_location('sdk',p);sdk=importlib.util.module_from_spec(sp);sp.loader.exec_module(sdk)
src=args.source_sdc.read_text();abi=json.loads(args.abi.read_text())
windows={};created=set()
for l in src.splitlines():
 m=re.fullmatch(r'create_clock -name \S+ -period [\d.]+ \[get_ports (?:\{([^}]+)\}|([^]\s]+))\]',l)
 if m:created.update((m[1] or m[2]).split())
 m=re.fullmatch(r'set_clock_latency -source -early -clock \S+ ([\d.\-]+) \[get_ports \{([^}]+)\}\]',l)
 if m:
  for n in m[2].split():
   assert n not in windows; windows[n]=-float(m[1])
for n in created:windows.setdefault(n,0.) # SDC create_clock with no source-latency command means exactly zero.
sync=json.loads(args.source_sync.read_text()) if args.source_sync else {'children':{}}
out={'source_constraint_sha256':hashlib.sha256(src.encode()).hexdigest(),'children':{}}
for child,ports in abi['children'].items():
 roots=[n for n,v in ports.items() if v['kind']=='clock'];w={n:windows[re.sub(r'\[0\]$','',ports[n]['source_root'])] for n in roots}
 landed=[n for n in roots if n.startswith('fclk_in_')]
 spec={'clock_port':roots[0],'tap_window_port_ps':w,'landed_clock_inputs':landed}
 mr={'roots':[{'base':n,'clock':sdk.root_clock_name(spec,n),'pins':[n]} for n in roots]}
 spec['source_sync_inputs']=sync['children'].get(child,{}).get('source_sync_inputs',{})
 inputs=sorted(spec['source_sync_inputs'])+['d']
 sr=sdk.source_sync_contract(spec,mr,inputs,833)
 rw=sdk.root_window_contract(spec,mr);rl=sdk.root_landed_contract(spec,mr)
 txt=sdk.root_landed_sdc(sdk.root_window_sdc(sdk.multi_root_sdc(sdk.sdc(833,250,47.5,[roots[0]],[],child),mr,833),rw),rl,mr,833)+sdk.source_sync_sdc(sr,mr)
 ctx=dict(period_ps=833,insertion_ps=250,insertion_tol_ps=47.5,clock_ports=roots,inputs=inputs,outputs=['q'],time_unit_ps=1.,io_floor_ps={p:166.6 for p in inputs+['q']},tap_window_port_ps=rw,tap_window_ps=min(rw.values()),tap_window_in_ps=max(rw.values()),landed_clock_inputs=rl)
 if sr:ctx.update(source_sync_inputs=sr,hold_in_min_ports_ps={p:r['min_ps'] for p,r in sr.items()})
 errors=sdk.sdc_lint.lint(txt,**ctx)
 assert not errors,errors[:8]
 # Real policy mutant: remove forwarded crossing max constraints, must fail closed.
 mutant='\n'.join(l for l in txt.splitlines() if not l.startswith('set_max_delay'))+'\n'
 assert sdk.sdc_lint.lint(mutant,**ctx),'missing half-cycle constraints escaped lint'
 mutant=txt.replace('set_clock_latency -source -early','set_clock_latency -source -late',1)
 assert sdk.sdc_lint.lint(mutant,**ctx),'lost early root frame escaped lint'
 try:sdk.root_window_contract({'tap_window_port_ps':{roots[0]:0}},mr)
 except SystemExit:pass
 else:raise AssertionError('missing root accepted')
 if sr:
  association=sdk.source_sync_sdc(sr,mr)
  first=next(l for l in association.splitlines() if l.startswith('set_input_delay -max'))
  import re as re_
  mutant=txt.replace(first,re_.sub(r'-clock \S+', '-clock vclk',first),1)
  assert sdk.sdc_lint.lint(mutant,**ctx),'forwarded input rebind escaped lint'
  replay=txt+'set_input_delay -min -47.5 -clock vclk $non_clk_in\n'+sdk.source_sync_sdc(sr,mr)
  assert not sdk.sdc_lint.lint(replay,**ctx),'runtime hold replay lost source frame'
 out['children'][child]={'tap_window_port_ps':w,'landed_clock_inputs':landed,'roots':len(roots),'source_sync_inputs':len(sr),'lint':'PASS','mutants':'missing crossing max, early-to-late, missing root all rejected','sdc_file':child+'.sdc'}
 (args.out/(child+'.sdc')).write_text(txt)
(args.out/'root_profile.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({c:{'roots':v['roots'],'landed':len(v['landed_clock_inputs']),'lint':v['lint']} for c,v in out['children'].items()}))
