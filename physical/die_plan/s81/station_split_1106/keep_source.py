import json,hashlib,shutil
from pathlib import Path
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--work-dir',type=Path,required=True);args=parser.parse_args()
b=args.work_dir
old=b/'attempt0_pruned';old.mkdir(exist_ok=True)
for n in ['selection.json','split.json','split.sv','split.log']:
 p=b/n
 if p.exists() and not (old/n).exists():shutil.copyfile(p,old/n)
source=json.load(open(b/'native_bound.json'));m=source['modules']['s81p_slice_station__t51'];changed=0
for cell in m['cells'].values():
 attrs=cell.setdefault('attributes',{})
 if attrs.get('keep')!='1':attrs['keep']='1';changed+=1
out=b/'kept_source.json';out.write_text(json.dumps(source)+chr(10))
link=b/'captured.json'
if link.is_symlink():link.unlink()
else:raise RuntimeError('captured input must be the known symlink')
link.symlink_to(out.name)
receipt={'schema':'opentallas.station_exact_cut_keep.v1','metadata_only':True,'data_reset_clock_changes':0,'cycles_added':0,'kept_cells':changed,'purpose':'Submod opt_clean otherwise removes unused native reset/tie cells; preserve exact state/source-root inventory during this cut and retain keep in emitted mapped RTL.','source_sha256':hashlib.sha256((b/'native_bound.json').read_bytes()).hexdigest(),'kept_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
(b/'keep_receipt.json').write_text(json.dumps(receipt,indent=2));print(receipt)
