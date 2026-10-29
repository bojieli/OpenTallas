import pathlib,sys,json,pickle,collections
sys.path.insert(0,'/d');import lec
src=pathlib.Path('/d/input');out=pathlib.Path('/d/fresh');out.mkdir(exist_ok=True);log=[]
for name in ('gold.aliases.json',):
 if not (out/name).exists():(out/name).symlink_to(src/name)
L=lec.Lec(lec.read_aig(src/'gold.aig'),lec.read_map(src/'gold.map'),lec.read_aig(src/'gate.aig'),lec.read_map(src/'gate.map'))
try:
 lec.correspond(L,out,1000,log)
 p='ff:u_dut.u_g.u_tile.u_tile.u_logic.u_me.';guard=[[(p+'active',1)],[(p+'pend',1)]]
 hints=[['gold',p+f'nb_t[{i}]',['loaded',0,guard]] for i in range(7)]
 rec=lec.apply_hints(L,hints,out,1000,log)
 (out/'hints_result.json').write_text(json.dumps(rec))
 (out/'model.pkl').write_bytes(pickle.dumps(L));(out/'hyp.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in L.hyp.items()]))
 m,kind=L.build(with_compare=True,with_hyp=True);st=lec.prove(m,out,1000,log,tag='compare',single_cap=200)
 (out/'compare.json').write_text(json.dumps(st));print('COMPARE',collections.Counter(st.values()),flush=True)
finally:(out/'proof.log').write_text('\n'.join(log))
