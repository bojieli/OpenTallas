#!/usr/bin/env python3
"""Actual TT library map of completed scalar FEC; no retiming or physical claim."""
import argparse,hashlib,json,pathlib,subprocess,time

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--bits',type=pathlib.Path,required=True);ap.add_argument('--bit-receipt',type=pathlib.Path,required=True);ap.add_argument('--graph',type=pathlib.Path,required=True);ap.add_argument('--libs',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--yosys',default=str(pathlib.Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'));a=ap.parse_args()
 net=a.bits.resolve();r=a.bit_receipt.resolve();graph=a.graph.resolve();libs=sorted(a.libs.resolve().glob('*.lib'));out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 parent=json.loads(r.read_text());g=json.loads(graph.read_text());nh=sha(net);assert nh==parent['bit_netlist_sha256']==g['input_sha256'];assert g['combinational_scalar_cells']>0 and g['total_flop_bits']>0
 assert len(libs)==5 and all('RVT_TT' in p.name and 'FAKE' not in p.name for p in libs)
 seq=[p for p in libs if '_SEQ_' in p.name];assert len(seq)==1
 bind={'scope':'ACTUAL_STANDALONE_SCALAR_FEC_TT_LIBRARY_MAP_NO_PHYSICAL_CLAIM','input_scalar_sha256':nh,'parent_receipt_sha256':sha(r),'bit_graph_sha256':sha(graph),'mapper_sha256':sha(pathlib.Path(__file__)),'libraries_sha256':{p.name:sha(p) for p in libs},'library_image_id':(a.libs/'IMAGE_ID').read_text().strip(),'top':parent['top'],'clock_target_ps_for_abc':885,'retiming':False,'native_qualified':False,'physical_qualified':False}
 (out/'binding.json').write_text(json.dumps(bind,indent=2)+'\n');args=' '.join('-liberty '+str(p) for p in libs)
 script=f'read_json {net}\nhierarchy -check -top {parent["top"]}\ndfflibmap -liberty {seq[0]}\nabc {args} -D 885\nclean\ncheck -assert\nstat {args}\nwrite_verilog -noattr -noexpr {out}/mapped.v\nwrite_json {out}/mapped.json\n'
 (out/'map.ys').write_text(script);start=time.monotonic()
 with (out/'yosys.log').open('w') as f:cp=subprocess.run([a.yosys,'-s',str(out/'map.ys')],stdout=f,stderr=subprocess.STDOUT)
 result=dict(bind,yosys_exit=cp.returncode,elapsed_seconds=time.monotonic()-start,log_sha256=sha(out/'yosys.log'),script_sha256=sha(out/'map.ys'))
 assert sha(net)==nh and sha(graph)==bind['bit_graph_sha256']
 if cp.returncode==0:
  result['mapped_verilog_sha256']=sha(out/'mapped.v');result['mapped_json_sha256']=sha(out/'mapped.json')
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return cp.returncode
if __name__=='__main__':raise SystemExit(main())
