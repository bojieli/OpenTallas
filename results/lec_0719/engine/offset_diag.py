import pathlib,json
import lec_crypto as lec
p=pathlib.Path('eng_bound')
L=lec.Lec(lec.read_aig(p/'gold.aig'),lec.read_map(p/'gold.map'),lec.read_aig(p/'gate.aig'),lec.read_map(p/'gate.map'))
for title,src in [('gold',L.gp),('gate',L.tp)]:
 for k in src:
  if 'q_off' in k or '.g_roff[' in k:print(title,k,'state',src[k],'D',(L.gc if title=='gold' else L.tc).get(k))
log=[];lec.renamed(L,log);print('renamed',log)
for sd,k,h in json.load(open('eng_boundproof/hyp_final.json')):
 if 'q_off' in k or '.g_roff[' in k:print('hyp',sd,k,h)
