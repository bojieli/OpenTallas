"""Apply the measured QC tap-density proposal to the exact studied base types."""
import argparse,json,hashlib
from pathlib import Path

def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();p=json.loads(a.plan.read_text());patch=json.loads(Path(__file__).with_name('clock_patches.json').read_text())
 for tn,entry in patch.items():
  if digest(p['partition_types'][tn])!=entry['base_type_sha256']:raise ValueError(tn+': base type changed; review the measured-profile composition')
 for tn,entry in patch.items():p['partition_types'][tn]['clock']=entry['clock']
 a.out.write_text(json.dumps(p,separators=(', ',': '))+'\n');print(json.dumps({'changed_types':sorted(patch),'data_cycles':0,'source_windows_changed':False,'qualification':'planning estimate; native/reset/profile and CTS/signoff pending'}))
if __name__=='__main__':main()
