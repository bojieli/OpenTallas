#!/usr/bin/env python3
"""One job/process keeps original fullshape TB fixed image capacities unchanged."""
import argparse,importlib.util,sys,json,hashlib
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 path=a.root/'tools/rtl_hdc_v41x_attn_campaign.py';sys.path.insert(0,str(path.parent));sp=importlib.util.spec_from_file_location('campaign',path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
 rng=np.random.default_rng(20260929);cases=[]
 for name,t,window,kind in [('window128',128,128,'coarse'),('mixed640',640,128,'coarse'),('mixed640wide',640,128,'wide'),('tail129',129,128,'coarse')]:
  job=m.random_job(rng,16,512,t,window,kind);counts,stats=m.write_jobs(a.out/name,[job],16,512,32)
  assert counts['NJOB']<=2 and counts['NKV']<=1280 and counts['NP']<=320 and counts['NSC']<=1280 and counts['NPV']<=1024
  cases.append(dict(name=name,rows=t,window_rows=window,counts=counts,expected=stats,images={x.name:sha(x) for x in sorted((a.out/name).glob('*.hex'))}))
 record=dict(scope='Synthetic golden inputs at actual H16 D512 TD32 NL4 T640. No checkpoint, HBM or softmax execution claim.',seed=20260929,parameters=dict(H=16,D=512,TD=32,NL=4,TROWS=640),golden_sources={str(x.relative_to(a.root)):sha(x) for x in [path,a.root/'tools/hdc_golden_v41.py']},cases=cases)
 (a.out/'manifest.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps([(c['name'],c['counts']) for c in cases]))
if __name__=='__main__':main()
