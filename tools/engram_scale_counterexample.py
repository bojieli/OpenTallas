"""Bounded unchanged-RTL witness; all stimulus synthetic; no checkpoint IO."""
import ast,hashlib,json,re,subprocess,tempfile
from pathlib import Path
import numpy as np
PIN='ca863a38debfefb8968cacfb5beb2f8815a9cc2e'
OUT=Path('results/rtl/engram_eight_scale_counterexample_20261001')
TB=Path('rtl/test/tb_engram_eight_scale_counterexample.sv')
def read(p):return subprocess.check_output(['git','show',PIN+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 paths=['rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_gather.sv','tools/hdc_golden.py','tools/hdc_golden_v41.py','tools/hdc_v41_engram_shipped.py','tools/rtl_hdc_v41_engram_gather_campaign.py','results/rtl/hdc_v41_engram_gather_campaign.json']
 src={p:read(p) for p in paths};ns=dict(np=np,F=np.float32)
 segments={}
 for p,names in [('tools/hdc_golden.py',['bits','from_bits','to_bf16']),('tools/hdc_golden_v41.py',['_e4m3_table','decode_engram_rows'])]:
  tree=ast.parse(src[p]);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
  assert len(nodes)==len(names)
  for n in nodes:segments[p+':'+n.name]=sha(ast.get_source_segment(src[p].decode(),n).encode())
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned_synthetic_golden','exec'),ns)
 ns['E4M3']=ns['_e4m3_table']()
 scales=[127,128,126,129,125,130,124,131]
 codes=np.full((2,256),0x38,dtype=np.uint8);exps=np.array([scales,[127]*8],dtype=np.int32)-127
 golden=ns['decode_engram_rows'](codes,exps,[0,1]);g=(ns['bits'](golden)>>16).astype(np.uint16)
 expected=[int(g[0,b*32]) for b in range(8)]
 assert expected==[0x3f80,0x4000,0x3f00,0x4080,0x3e80,0x4100,0x3e00,0x4180]
 OUT.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='engram-scale-witness-') as temp:
  td=Path(temp);files=[]
  for p in paths[:2]:
   dest=td/Path(p).name;dest.write_bytes(src[p]);files.append(str(dest))
  cmd=['iverilog','-g2012','-s','tb_engram_eight_scale_counterexample','-o',str(td/'sim'),*files,str(TB)]
  c=subprocess.run(cmd,capture_output=True,text=True,timeout=30);(OUT/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stderr
  run=subprocess.run(['vvp',str(td/'sim')],capture_output=True,text=True,timeout=10);log=run.stdout+run.stderr;(OUT/'simulation.log').write_text(log);assert run.returncode==0,log
 writes=re.findall(r'WRITE column=(\d+) beat=(\d+) side_scale=(\d+) actual=([0-9a-f]+) golden=([0-9a-f]+)',log)
 assert len(writes)==16
 records=[]
 for col,beat,scale,actual,reported in writes:
  col=int(col);beat=int(beat);actual=int(actual,16);want=int(g[col,beat*32]);assert int(reported,16)==want
  records.append(dict(column=col,beat=beat,side_scale=int(scale),code='0x38',actual_BF16=f'{actual:04x}',golden_BF16=f'{want:04x}',matched=actual==want,lanes=32))
 assert sum(not r['matched'] for r in records)==7 and 'COUNTEREXAMPLE_CONFIRMED' in log
 result=dict(schema='opentallas.engram.eight-block-scale.unchanged-rtl-counterexample.v1',witness_verdict='PASS_COUNTEREXAMPLE_REPRODUCED',actual_checkpoint_codec_verdict='FAIL',source_commit=PIN,source_sha256={p:sha(b) for p,b in src.items()},golden_function_sha256=segments,bench_path=str(TB),bench_sha256=sha(TB.read_bytes()),runner_sha256=sha(Path(__file__).read_bytes()),simulator='iverilog/vvp',compile_command_template=['iverilog','-g2012','-s','tb_engram_eight_scale_counterexample','-o','<temp>/sim','<pinned shipped package>','<pinned unchanged gather>',str(TB)],compile_returncode=c.returncode,simulation_returncode=run.returncode,parameters=dict(NL=1,NC=2,LANES=32,BEATS=8,beat_bits=264),synthetic_only=True,checkpoint_payload_reads=0,direct_decoder=dict(code='0x38',scale127_BF16='3f80',scale128_BF16='4000',passed=True),writes=records,mismatched_BF16_elements=224,uniform_scale_control_elements=256,completion_verified=True,root_cause='scl bank latches side byte only on beat0; s1_s selects s1_scl forbeats1..7 despite differing perblock side bytes',old_campaign_scope='Existing row_bytes returns256codes and one scalar scale; old verdict retained unchanged and scoped to that synthetic one-scale-row contract.',required_baseline_codec='All8beats carry32E4M3codes plus the matching UE8M0 exponent for that block; decode each beat using its own side byte.',correction_requires='Ram full port/area/route budget admission before engine change; mandatory correctness, no optional1% gate',cycles_per_row=8,shipped24_column_response_beats_per_layer=192,corrected_SS_FF_timing_credit=False,engine_RTL_modified=False,place_and_route=False,admission_claim=False)
 (OUT/'witness.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 (OUT/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(OUT.iterdir()) if p.name!='SHA256SUMS'))
 print(json.dumps(dict(verdict=result['actual_checkpoint_codec_verdict'],mismatches=224,source_commit=PIN)))
if __name__=='__main__':main()
