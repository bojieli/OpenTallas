from pathlib import Path
import importlib.util,json,random,subprocess
root=Path('/srv/opentallas/repos/boole-scan-edt-0ba7b2ac3')
job=Path('/srv/opentallas-scratch/jobs/boole-scan-edt-codec-component-20261005-r3')
spec=importlib.util.spec_from_file_location('edt',root/'tools/dft/edt_pattern_encode.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
results=[]
for chains,channels in [(32,4)]:
 rng=random.Random(1754+chains)
 words=[rng.randrange(1<<channels) for _ in range(16)]
 expected=m.decompress(words,chains,channels)
 encoded=m.encode(expected,channels)
 assert encoded['encodable'] and encoded['care_mismatches']==0
 actual=m.decompress(encoded['words'],chains,channels)
 assert actual==expected
 # Real sparse care cube: care first eight chain bits per edge, not filled fabrication.
 sparse=[[b if c<8 else None for c,b in enumerate(row)] for row in expected]
 assert m.encode(sparse,channels)['encodable']
 unsat=[[None]*chains];unsat[0][0]=0;unsat[0][channels]=1
 assert not m.encode(unsat,channels)['encodable']
 good=[[0]*chains];one=[[0]*chains];one[0][0]=1
 alias=[[0]*chains];alias[0][0]=alias[0][channels]=1
 assert m.response_check(good,one,channels)['compact_detected']
 assert m.response_check(good,alias,channels)['lost_detection']
 x=[[0]*chains];x[0][0]=None
 assert m.compact(x,channels)[0][0] is None
 cube={'chains':chains,'channels':channels,'load':expected,'good_response':good,'fault_responses':{'single':one}}
 inp=job/f'cube{chains}.json';out=job/f'encoded{chains}.json';inp.write_text(json.dumps(cube))
 subprocess.run(['python3',str(root/'tools/dft/edt_pattern_encode.py'),'--input',str(inp),'--output',str(out)],check=True)
 assert json.loads(out.read_text())['coverage_status']=='PASS_SUPPLIED_RESPONSE_SET'
 cube['load']=unsat;inp=job/f'unsat{chains}.json';inp.write_text(json.dumps(cube))
 p=subprocess.run(['python3',str(root/'tools/dft/edt_pattern_encode.py'),'--input',str(inp),'--output',str(job/f'unsat_result{chains}.json')])
 assert p.returncode==1
 cube['load']=expected;cube['fault_responses']={'alias':alias};inp=job/f'alias{chains}.json';inp.write_text(json.dumps(cube))
 p=subprocess.run(['python3',str(root/'tools/dft/edt_pattern_encode.py'),'--input',str(inp),'--output',str(job/f'alias_result{chains}.json')])
 assert p.returncode==1
 tb=['module tb; reg clk=0; always #5 clk=~clk;',f'reg rst_n=0,pattern_reset=0,scan_en=0; reg [{channels-1}:0] edt_in=0; reg [{chains-1}:0] chain_out=0;',f'wire [{chains-1}:0] chain_in,off_in; wire [{channels-1}:0] edt_out,off_out;',f'ot_scan_edt8to1 #(.ENABLE(1),.CHAIN_COUNT({chains}),.CHANNELS({channels})) dut(.*);',f'ot_scan_edt8to1 #(.CHAIN_COUNT({chains}),.CHANNELS({channels})) disabled(.clk(clk),.rst_n(rst_n),.pattern_reset(pattern_reset),.scan_en(scan_en),.edt_in(edt_in),.chain_out(chain_out),.chain_in(off_in),.edt_out(off_out));','initial begin @(negedge clk); rst_n=1; pattern_reset=1; scan_en=1; chain_out=1; #1; if(chain_in!==0 || edt_out!==1) $fatal(1,"reset erased old response"); @(negedge clk); pattern_reset=0;']
 for t,(w,row) in enumerate(zip(encoded['words'],actual)):
  bits=sum(b<<c for c,b in enumerate(row))
  tb += [f'edt_in={channels}\'h{w:x}; chain_out={chains}\'h1; #1; if(chain_in !== {chains}\'h{bits:x} || edt_out !== {channels}\'h1 || off_in !== 0 || off_out !== 0) $fatal(1,"cycle{t}"); @(negedge clk);']
 tb += ['scan_en=0; #1; if(chain_in!==0 || edt_out!==0) $fatal(1,"disable"); repeat(3) @(negedge clk); scan_en=1; pattern_reset=1; @(negedge clk); pattern_reset=0; edt_in=0; #1; if(chain_in!==0) $fatal(1,"pattern reset");',f'chain_out=0; chain_out[0]=1\'bx; #1; if(edt_out[0]!==1\'bx) $fatal(1,"X erased");',f'$display("PASS_EDT_CODEC chains{chains} channels{channels}"); $finish; end endmodule']
 path=job/f'tb{chains}.sv';path.write_text('\n'.join(tb)+'\n')
 exe=job/f'sim{chains}';subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(root/'rtl/dft/ot_scan_edt8to1.sv'),str(path)],check=True)
 subprocess.run(['vvp',str(exe)],check=True)
 results.append({'chains':chains,'channels':channels,'channel_ratio':chains/channels,'cases':'RTL decompression/compaction/defaultoff/disabled/reset/X; GF2 dense-valid/sparsecare/replay/UNSAT/alias; actual CLI pass/fail','status':'PASS_COMPONENT_ONLY'})
(job/'result.json').write_text(json.dumps({'source':'0ba7b2ac3','status':'PASS_COMPONENT_ONLY','partitions':results,'integrated_atpg':'UNVALIDATED','corrected_chain_binding':'PENDING_CONFUCIUS','physical':'UNVALIDATED'},indent=2)+'\n')
