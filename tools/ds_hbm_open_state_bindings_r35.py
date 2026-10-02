"""Join actual old open-group source payloads; no invented historical slots."""
import argparse,gzip,json
from pathlib import Path
from ds_hbm_source_inputs_r34 import sha

def bindings(native,records):
    import numpy as np
    opens={r['layer']:r for r in records if r['kind']==3};out={}
    for op in native['instructions']:
        for key,bs in op['provider_bindings'].items():
            for name,b in bs.items():
                if name!='open_group' or b['kind']!='explicit_auxiliary_provider':continue
                record=opens[b['layer']];spec=native['templates'][key]['providers'][name];path=Path(record['path'])
                if sha(path)!=record['file_sha256']:raise ValueError('retained open-group source image pin')
                a=np.load(path,mmap_mode='r',allow_pickle=False)
                if spec['dtype']!='F32' or list(a.shape)!=spec['shape']:raise ValueError('exact source open-group shape/type')
                if record['logical_positions']!=[b['position']-1]:raise ValueError('source open-group position identity')
                out[f"{op['pc']}/{key}/{name}"]=dict(path=str(path.resolve()),sha256=sha(path),shape=list(a.shape),dtype='F32',source_binding=b,generation=1,checkpoint_revision='dba1be0a40aa45a94ad051997016db3960a90277',scope='exact source entering old open group; no current slot invented')
    return out

def main():
    p=argparse.ArgumentParser()
    for n in ('native','images','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh bindings output')
    a.out.write_text(json.dumps(bindings(json.loads(gzip.decompress(a.native.read_bytes())),json.loads(a.images.read_bytes())),sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
