from pathlib import Path
import subprocess,json,hashlib
P=Path(__file__).resolve().parent;out=P/'proof';receipts=[]
for mode,src in [('nominal','current_native_ring_face.sv'),('mutant','current_native_ring_face_mutant.sv')]:
 stem='pure_'+mode;cmd=['iverilog','-g2012','-s','tb_ring_face_bridge','-o',str(out/(stem+'.vvp')),str(P/'prepared/native_pure.sv'),str(P/'prepared/physical_pure.sv'),str(P/src),str(P/'tb_ring_face_diagnose.sv')]
 r=subprocess.run(cmd,text=True,capture_output=True);(out/('build_'+stem+'.log')).write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError('compile failed '+mode)
 r=subprocess.run(['vvp',str(out/(stem+'.vvp'))],text=True,capture_output=True);log=r.stdout+r.stderr;(out/(stem+'.log')).write_text(log)
 passed=r.returncode==0 and 'RING_FACE_PASS edges1600' in log
 caught=r.returncode!=0 and 'RING_FACE_DIFF' in log
 if (mode=='nominal'and not passed)or(mode=='mutant'and not caught):raise RuntimeError('unexpected source proof outcome '+mode+' '+log)
 receipts.append({'mode':mode,'returncode':r.returncode,'result':'PASS'if passed else'CAUGHT','log':str(out/(stem+'.log')),'source_sha256':hashlib.sha256((P/src).read_bytes()).hexdigest()});print(mode,receipts[-1]['result'],flush=True)
(out/'pure_receipt.json').write_text(json.dumps({'scope':'strict finite fullcut proof against explicit2224FF CURRENTnative sourcecandidate, not whole-parent/calendar qualification','outputs':1345,'qid':[2,3],'edges':1600,'POR_assert_edges':66,'extra_valid_or_startup_masks':False,'repeated_reset':True,'XZ_stimulus':True,'profiles':'same exact native/physical profiles with only pure-function sensitivity fix','results':receipts},indent=2)+'\n')
