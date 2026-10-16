#!/usr/bin/env python3
"""Probe TT native launch/capture on a completed immutable CTS gate.
Uses placement parasitics, never qualifies a routed view. Heavy STA runs via
ot-run against the recorded gate directory; it never changes the saved ODB.
"""
import argparse,hashlib,json,shlex,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'hier_contract'))
import pinreg_audit as PA

def run(argv,**kw):return subprocess.run(argv,check=True,**kw)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('kit',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mem',type=int,default=4);a=ap.parse_args()
 gate=json.loads((a.kit/'gate_result.json').read_text());binding=gate['source_binding'];host=binding['remote_host'];remote=binding['remote_run'];kit=gate['kit'] if '/'in gate['kit'] else 'physical/ref_tile/'+gate['kit'];out=a.out;out.mkdir(parents=True,exist_ok=True)
 # The original gate's exact archived signoff SDC remains authoritative. This
 # prelude only reads its CTS ODB, propagated clocks, TT cells and placement RC.
 prelude=(HERE/'path_classes.tcl').read_text().split('proc kind')[0]
 tcl=prelude+'\nwrite_timing_model -library_name native_cts_probe_tt /work/native_probe_tt.lib\n';(out/'probe.tcl').write_text(tcl)
 script=remote+'/native_probe.tcl';run(['ssh',host,'cat > '+shlex.quote(script)],input=tcl,text=True)
 cmd=['ot-run','--mem',str(a.mem),'--threads','1','--dir',remote,'--','docker','run','--rm','-e','OT_GATE_SIGNOFF_SDC=/src/'+kit+'/signoff.sdc','-v',remote+'/src:/src:ro','-v',remote+'/routes/gate/work/orfs:/work','-v',script+':/probe.tcl:ro','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/probe.tcl']
 p=subprocess.run(cmd,capture_output=True,text=True);(out/'probe.log').write_text(p.stdout+p.stderr)
 if p.returncode or 'ot-run: RAN on ' not in p.stderr:raise RuntimeError('STA did not complete; see probe.log')
 for name,path in [('probe_tt.lib',remote+'/routes/gate/work/orfs/native_probe_tt.lib'),('insertion.json',remote+'/ck.json')]:run(['rsync','-a',host+':'+path,str(out/name)])
 lib=PA.parse_lib(out/'probe_tt.lib');refs=PA.clock_refs(lib,json.loads((out/'insertion.json').read_text()),'tt');metrics=PA.pin_metrics(lib,refs)
 launch=[(m['out'],n)for n,m in metrics.items()if m['dir']=='output'and m['out']is not None];capture=[(m['inp'],n)for n,m in metrics.items()if m['dir']=='input'and m['inp']is not None];comb=[n for n,m in metrics.items()if m['comb']and m['dir']in ('input','output')]
 result=dict(schema='opentallas.ref-tile.cts-native-probe.v1',scope='CTS placement RC diagnostic; NOT a routed native qualification',kit=kit,remote_host=host,remote_run=remote,gate_source_commit=binding.get('commit')or binding.get('start_commit'),gate_result_sha256=hashlib.sha256((a.kit/'gate_result.json').read_bytes()).hexdigest(),library_sha256=hashlib.sha256((out/'probe_tt.lib').read_bytes()).hexdigest(),insertion_sha256=hashlib.sha256((out/'insertion.json').read_bytes()).hexdigest(),probe_tcl_sha256=hashlib.sha256(tcl.encode()).hexdigest(),launch=dict(ps=max(launch)[0],pin=max(launch)[1])if launch else None,capture=dict(ps=max(capture)[0],pin=max(capture)[1])if capture else None,launch_over=sum(v>220 for v,n in launch),capture_over=sum(v>190 for v,n in capture),comb_pins=comb,clock_refs=refs)
 result['spread_ps']={k:v['bmax']-v['bmin']for k,v in refs.items()}
 result['measured_reference_coverage']=bool(refs)and all(v['src']=='insertion.json boundary mean'for v in refs.values())
 result['diagnostic_pass']=bool(launch and capture and refs)and result['measured_reference_coverage']and max(result['spread_ps'].values())<=80 and not(result['launch_over']or result['capture_over']or comb)
 (out/'native_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['diagnostic_pass']else 1
if __name__=='__main__':sys.exit(main())
