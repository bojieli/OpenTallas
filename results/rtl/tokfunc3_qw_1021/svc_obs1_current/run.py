import pathlib,subprocess,json
r=pathlib.Path(__file__).resolve().parent;o=r.parent/'svc_current2';o.mkdir(exist_ok=True)
cs=[]
for n in ['s1','s2','m_hpseq','m_ret']:
 with (o/(n+'.log')).open('w') as f:p=subprocess.run(['bash','results/arch/sqc2_n59_1021/bench.sh',n,str(o/n)],cwd=r,stdout=f,stderr=subprocess.STDOUT)
 text=(o/(n+'.log')).read_text();expect=n.startswith('m_');good=p.returncode==(1 if expect else 0) and ('N59OBS_MUTANT_REJECTED' if expect else 'N59OBS_PASS') in text and 'build failed' not in text
 cs.append(dict(name=n,rc=p.returncode,ok=good));print(cs[-1],flush=True)
(o/'record.json').write_text(json.dumps(dict(identity=json.loads((r/'source_manifest.json').read_text()),cases=cs),indent=2)+'\n')
raise SystemExit(0 if all(c['ok'] for c in cs) else 1)
