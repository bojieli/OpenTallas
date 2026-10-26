#!/usr/bin/env python3
"""Cacheable bit-level mapping of the exact completed FEC census netlist.

No ABC/library map or timing claim. Heavy work must use fleet admission.
"""
import argparse,hashlib,json,pathlib,subprocess,time

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--netlist',required=True,type=pathlib.Path);ap.add_argument('--census-receipt',required=True,type=pathlib.Path);ap.add_argument('--out',required=True,type=pathlib.Path);ap.add_argument('--yosys',default=str(pathlib.Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'));a=ap.parse_args()
 net=a.netlist.resolve();receipt=a.census_receipt.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 parent=json.loads(receipt.read_text());input_hash=sha(net);assert input_hash==parent['netlist_sha256'],'Input netlist does not match completed source-pinned census'
 binding={'input_netlist_sha256':input_hash,'census_receipt_sha256':sha(receipt),'mapper_sha256':sha(pathlib.Path(__file__)),'top':parent['top'],'native_qualified':False,'physical_qualified':False,'library_mapped':False,'source_scope':parent['scope'],'source_sha256':parent.get('sources_sha256',parent.get('sha256'))}
 assert isinstance(binding['source_sha256'],dict) and binding['source_sha256'], 'Missing source binding'
 (out/'input_binding.json').write_text(json.dumps(binding,indent=2)+'\n')
 script=f'read_json {net}\nhierarchy -check -top {parent["top"]}\ntechmap\nopt\ncheck -assert\nstat\nwrite_json {out}/bit_netlist.json\n'
 (out/'map.ys').write_text(script);started=time.monotonic()
 with (out/'yosys.log').open('w') as log:cp=subprocess.run([a.yosys,'-s',str(out/'map.ys')],stdout=log,stderr=subprocess.STDOUT)
 result=dict(binding,elapsed_seconds=time.monotonic()-started,yosys_exit=cp.returncode,map_script_sha256=sha(out/'map.ys'),yosys_log_sha256=sha(out/'yosys.log'))
 assert sha(net)==input_hash and sha(receipt)==binding['census_receipt_sha256'],'Input binding changed during mapping'
 if not cp.returncode:result['bit_netlist_sha256']=sha(out/'bit_netlist.json');result['bit_netlist_bytes']=(out/'bit_netlist.json').stat().st_size
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return cp.returncode
if __name__=='__main__':raise SystemExit(main())
