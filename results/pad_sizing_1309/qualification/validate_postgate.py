import json,pathlib,sys,math
p=pathlib.Path(sys.argv[1]);out={}
for c in ('tt','ff'):
 f=p/f'qualification_gate_{c}.json';x=json.loads(f.read_text())
 groups=[s.split('\t') for s in (p/f'qualification_gate_{c}.groups.tsv').read_text().splitlines() if s and not s.startswith('#')][1:]
 assert len(groups)==54 and sum(int(s[2]) for s in groups)==x['pinreg_n']==1133
 assert x['verdict']=='FAIL' and x['group_spread_ps']>20 and x['dev_ps']<20
 assert all(math.isfinite(v) for v in x.values() if isinstance(v,(int,float)))
 assert x['hold_census_status']==('MEASURED' if c=='ff' else 'NOT_RUN')
 if c=='ff':assert x['hold_census_n']==0 and x['hold_census_margin_n']==0
 out[c]=dict(pinreg_n=x['pinreg_n'],groups=len(groups),mean_ps=x['pinreg_mean_ps'],group_spread_ps=x['group_spread_ps'],design_verdict=x['verdict'],census_status=x['hold_census_status'],census_n=x['hold_census_n'])
print(json.dumps(dict(validation='PASS',corners=out),indent=1))
