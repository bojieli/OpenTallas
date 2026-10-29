import pathlib,sys,json,collections,pickle,tarfile,importlib.util,argparse,hashlib
parser=argparse.ArgumentParser();parser.add_argument('--out',type=pathlib.Path,required=True);args=parser.parse_args()
HERE=pathlib.Path(__file__).resolve().parent;receipt=json.loads((HERE/'gq_retained_receipt.json').read_text())
archive=HERE/receipt['inputs'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['inputs_sha256']
out=args.out.resolve();out.mkdir(parents=True,exist_ok=True);inputs=out/'inputs';inputs.mkdir(exist_ok=True)
with tarfile.open(archive) as tar:tar.extractall(inputs,filter='data')
sys.path.insert(0,str(inputs/'tool'));import lec
src=inputs/'new';old=inputs/'old' 
L=lec.Lec(lec.read_aig(src/'gold.aig'),lec.read_map(src/'gold.map'),lec.read_aig(src/'gate.aig'),lec.read_map(src/'gate.map'))
log=[]
lec.normalize_gold_elements(L,lec.slang_elements(src/'gold.aliases.json'),log)
for fn in (lec.json_alias_keys,lec.slang_element_keys,lec.alias_arrays):fn(L,log,work=src)
for fn in (lec.relayout,lec.renamed,lec.replica_proposals,lec.merged_proposals,lec.register_alias_proposals,lec.fsm_proposals):fn(L,log)
L.hyp.clear();dropped=[]
for sd,k,h in json.loads((old/'hyp.json').read_text()):
 valid=(k in L.gp and k in L.tp) if sd=='both' else k in (L.gp if sd=='gold' else L.tp)
 if h[0]=='eq':valid=valid and h[2] in (L.gp if h[1]=='gold' else L.tp)
 if valid:L.hyp[sd,k]=tuple(h)
 else:dropped.append([sd,k,h])
added=[]
for k in L.gp:
 if k.startswith('ff:') and ('fp4' in k or '.u_d27f.' in k):
  sd='both' if k in L.tp else 'gold';L.hyp[sd,k]=('const',0);added.append([sd,k])
print('retained',len(L.hyp),'dropped',len(dropped),'format-constants',added,flush=True)
(out/'dropped.json').write_text(json.dumps(dropped));(out/'model.pkl').write_bytes(pickle.dumps(L))
for tag,cmp in [('joint',False),('compare',True)]:
 m,_=L.build(with_compare=cmp,with_hyp=True);st=lec.prove(m,out,1000,log,tag=tag,single_cap=100)
 (out/(tag+'.json')).write_text(json.dumps(st));(out/'proof.log').write_text('\n'.join(log));print(tag,collections.Counter(st.values()),flush=True)
 if tag=='joint' and any(v!='proved' for v in st.values()):break
