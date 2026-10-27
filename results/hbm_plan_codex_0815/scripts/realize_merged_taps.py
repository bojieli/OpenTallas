"""Carry source-verified preserved bit ports into real clock-tap consumers. Never infer a bus collapse."""
import json,sys,pathlib,hashlib
pd=pathlib.Path(sys.argv[1]);d=json.load(open(pd/'die_plan.json'));entries=json.load(open(pd/'clock_entries.json'));rows=[]
for tn,t in d['partition_types'].items():
 for hc in t.get('hard_cores',[]):
  if hc.get('module') not in ('ot_hbm_idx_score_hcol_h0','ot_hbm_idx_score_hcol_h1'):continue
  ci=hc['inst'];e=entries.get(tn,{}).get(ci)
  assert e and e.get('merged_clock_ports')==['clk_pair[0]','clk_pair[1]'],(tn,ci,e)
  tab=json.load(open(pd/hc['pins_file']));tab=tab.get('pins',tab) if isinstance(tab,dict) else tab
  def name(p):return p.get('name') or f"{p['bus']}[{p.get('bit',0)}]"
  assert set(e['merged_clock_ports'])<=set(map(name,tab)),(tn,ci,'actual pin missing')
  taps=[p for p in t.get('clock',{}).get('taps',[]) if p.get('kind')=='core' and (p['name']==ci or p['name'].startswith(ci+'.'))]
  assert len(taps)==1,(tn,ci,len(taps))
  tp=taps[0];old=tp.get('merged_clock_ports');assert old in (None,e['merged_clock_ports'])
  tp['merged_clock_ports']=list(e['merged_clock_ports']);tp['note']=tp.get('note','')+' | source ef994fe77: both actual clk_pair bits share one833ps root; explicit afdd0a5e6 physical adapter coverage'
  rows.append(dict(type=tn,inst=ci,tap=tp['name'],merged_clock_ports=tp['merged_clock_ports']))
(pd/'die_plan.json').write_text(json.dumps(d,indent=1)+'\n');(pd/'merged_taps_report.json').write_text(json.dumps(dict(types=len({r['type'] for r in rows}),taps=len(rows),rows=rows,physical_coverage='PENDING actual selected LEF+Lib; source-only metadata cannot qualify physical kit'),indent=1)+'\n')
print('explicit merged taps',len(rows),'types',len({r['type'] for r in rows}))
