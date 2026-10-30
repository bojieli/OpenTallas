import subprocess,re,json,hashlib
from pathlib import Path
out=Path(__file__).resolve().parent
paths=['rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv']
receipts={}
for label,base in [('recipe','80e52b927345d6551be758d467b46792fe593c14:'),('native','e5b2ac1fc8d72396a7db4c0c73d63a65727184b6:physical/die_plan/hbm/bind/r18h5_bundle/')]:
 texts=[subprocess.check_output(['git','show',base+p]).decode() for p in paths]
 receipts[label]={p:hashlib.sha256(t.encode()).hexdigest() for p,t in zip(paths,texts)}
 names=set(re.findall(r'\bmodule\s+(\w+)', '\n'.join(texts)))
 s='\n'.join(texts)
 for n in sorted(names,key=len,reverse=True):s=re.sub(r'\b'+re.escape(n)+r'\b',label+'_'+n,s)
 (out/(label+'.sv')).write_text(s)
(out/'source_hashes.json').write_text(json.dumps(receipts,indent=1)+'\n')
