#!/usr/bin/env python3
"""Local event/timer and actual-node valid path gate; full arithmetic is separate."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
dr=pathlib.Path('rtl/physical/ot_qwen_tile_local_drain.sv');nd=pathlib.Path('rtl/physical/ot_qwen_tile_node_lifetime.sv')
cases={'drain_positive':(dr,'tb_qwen_tile_local_drain',None),'drain_early':(dr,'tb_qwen_tile_local_drain',("6'd48","6'd47")),'node_positive':(nd,'tb_qwen_tile_node_lifetime',None),'node_latest_offer':(nd,'tb_qwen_tile_node_lifetime',('node_produced_tuple<=metadata[7]','node_produced_tuple<={node_context,node_version,node_sequence}')),'node_no_seal':(nd,'tb_qwen_tile_node_lifetime',('identity_valid&&sealed&&outstanding','identity_valid&&outstanding')),'node_early':(nd,'tb_qwen_tile_node_lifetime',('if(valid[7])','if(valid[6])'))}
records={}
with tempfile.TemporaryDirectory(prefix='qwen-lifetime-') as tmp:
 for name,(src,top,mutation) in cases.items():
  content=src.read_text()
  if mutation:assert mutation[0] in content;content=content.replace(*mutation)
  path=pathlib.Path(tmp)/f'{name}.sv';path.write_text(content);exe=path.with_suffix('.vvp');files=[str(path),f'rtl/test/qwen_kv_die/{top}.sv']
  if name.startswith('node_'):files+=['rtl/physical/ot_qwen_tile_node.sv','rtl/hdc/ot_hdc_delay.sv','rtl/lib/ot_rst_relay.sv']
  build=subprocess.run(['iverilog','-g2012','-s',top,'-o',str(exe),*files],capture_output=True,text=True);assert build.returncode==0,build.stderr
  run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(a.out/f'{name}.log').write_text(run.stdout+run.stderr)
  records[name]={'exit':run.returncode,'source_sha256':hashlib.sha256(content.encode()).hexdigest()};assert (run.returncode==0)==name.endswith('positive'),name
(a.out/'record.json').write_text(json.dumps({'status':'UNIT_TIMER_AND_ACTUAL_FIXED_NODE_VALID_METADATA_GATES_NOT_FULL_NATIVE_ARITHMETIC_OR_PHYSICAL','cases':records,'sources':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [dr,nd,pathlib.Path('rtl/physical/ot_qwen_tile_node.sv')]}},indent=2)+'\n')
