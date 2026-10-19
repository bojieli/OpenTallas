#!/usr/bin/env python3
"""Probe TT native launch/capture on a completed immutable CTS gate.
Uses placement parasitics, never qualifies a routed view. Heavy STA runs via
ot-run against the recorded gate directory; it never changes the saved ODB.
--relative-to (owner 10-17 0dq): measure launch O - C / capture S + C and the
pin-flop arrival against the parent compensation / neighbour boundary C
(ps, tt=PS,ff=PS, or a neighbour view dir / insertion.json) instead of the
tile's own R; --from-dir re-scores a finished probe dir without STA.  The FF
pin-flop spread (ck.json ff.boundary) is reported and judged beside TT.
"""
import argparse,hashlib,json,re,shlex,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'hier_contract'))
import pinreg_audit as PA

# path_classes.tcl sources its helpers relative to [info script].  The probe runs as /probe.tcl inside the container, so
# that resolves to /<helper>.tcl, which is not mounted (S81-CAPRT / HKV-ERTAP 10-19: ORD error on cross_clock_paths.tcl),
# and older gate dirs may not stage the helper under /src at all.  Inline every such helper from this tools tree (the
# prelude itself is read from here too), and refuse a prelude that still depends on [info script].
SCRIPT_REL_SOURCE=re.compile(r'^[ \t]*source[ \t]+\[file join \[file dirname \[file normalize \[info script\]\]\] ([A-Za-z0-9_.-]+\.tcl)\][ \t]*$',re.M)
def inline_script_relative(tcl,base=HERE):
 def sub(m):
  f=Path(base)/m.group(1)
  if not f.is_file():raise FileNotFoundError(f'probe prelude sources {m.group(1)} next to path_classes.tcl, missing: {f}')
  return f'# --- inlined {m.group(1)} (cts_native_probe: the probe runs as /probe.tcl in the container)\n'+f.read_text().rstrip('\n')+f'\n# --- end {m.group(1)}'
 out=SCRIPT_REL_SOURCE.sub(sub,tcl)
 if 'info script' in out:raise RuntimeError('probe prelude still depends on [info script]: unsupported source form in path_classes.tcl')
 return out
def probe_tcl(base=HERE):
 prelude=(Path(base)/'path_classes.tcl').read_text().split('proc kind')[0]
 return inline_script_relative(prelude,base)+'\nwrite_timing_model -library_name native_cts_probe_tt /work/native_probe_tt.lib\n'

# Measured references: the CTS boundary mean, or (NATIVE-REF 10-18, pinreg_audit.clock_refs) the ck_insertion child_flop
# boundary mean, which ck_insertion records for every view with macro / hard-child clock pins (s81sl_cap_rt 10-19: one
# SRAM, child_flop boundary == boundary, and the probe called it unmeasured).  Lib midrange / neighbour refs are not.
MEASURED_SRCS=('insertion.json boundary mean','insertion.json child_flop boundary mean')
def measured_coverage(refs):return bool(refs)and all(v.get('src')in MEASURED_SRCS for v in refs.values())
def run(argv,**kw):return subprocess.run(argv,check=True,**kw)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('kit',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mem',type=int,default=4);ap.add_argument('--relative-to');ap.add_argument('--from-dir',action='store_true',help='reuse probe_tt.lib + insertion.json already in --out');a=ap.parse_args()
 comp=PA.compensation(a.relative_to)if a.relative_to else None
 gate=json.loads((a.kit/'gate_result.json').read_text());binding=gate['source_binding'];host=binding['remote_host'];remote=binding['remote_run'];kit=gate['kit'] if '/'in gate['kit'] else 'physical/ref_tile/'+gate['kit'];out=a.out;out.mkdir(parents=True,exist_ok=True)
 # The original gate's exact archived signoff SDC remains authoritative. This
 # prelude only reads its CTS ODB, propagated clocks, TT cells and placement RC.
 tcl=probe_tcl();(out/'probe.tcl').write_text(tcl)
 script=remote+'/native_probe.tcl'
 cmd=['ot-run','--mem',str(a.mem),'--threads','1','--hosts',host,'--dir',remote,'--','docker','run','--rm','-e','OT_GATE_SIGNOFF_SDC=/src/'+kit+'/signoff.sdc','-v',remote+'/src:/src:ro','-v',remote+'/routes/gate/work/orfs:/work','-v',script+':/probe.tcl:ro','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/probe.tcl']
 if not a.from_dir:
  run(['ssh',host,'cat > '+shlex.quote(script)],input=tcl,text=True)
  p=subprocess.run(cmd,capture_output=True,text=True);(out/'probe.log').write_text(p.stdout+p.stderr)
  if p.returncode or 'ot-run: RAN on ' not in p.stderr:raise RuntimeError('STA did not complete; see probe.log')
  for name,path in [('probe_tt.lib',remote+'/routes/gate/work/orfs/native_probe_tt.lib'),('insertion.json',remote+'/ck.json')]:run(['rsync','-a',host+':'+path,str(out/name)])
 ins=json.loads((out/'insertion.json').read_text());lib=PA.parse_lib(out/'probe_tt.lib');refs=PA.clock_refs(lib,ins,'tt')
 rel=None
 if comp and refs and comp.get('tt')is not None:rel=dict(tt=PA.boundary_match(refs,comp['tt']),src=comp['src']);refs=PA.relative_refs(refs,comp['tt'])
 metrics=PA.pin_metrics(lib,refs)
 launch=[(m['out'],n)for n,m in metrics.items()if m['dir']=='output'and m['out']is not None];capture=[(m['inp'],n)for n,m in metrics.items()if m['dir']=='input'and m['inp']is not None];comb=[n for n,m in metrics.items()if m['comb']and m['dir']in ('input','output')]
 result=dict(schema='opentallas.ref-tile.cts-native-probe.v1',scope='CTS placement RC diagnostic; NOT a routed native qualification',kit=kit,remote_host=host,remote_run=remote,gate_source_commit=binding.get('commit')or binding.get('start_commit'),gate_result_sha256=hashlib.sha256((a.kit/'gate_result.json').read_bytes()).hexdigest(),library_sha256=hashlib.sha256((out/'probe_tt.lib').read_bytes()).hexdigest(),insertion_sha256=hashlib.sha256((out/'insertion.json').read_bytes()).hexdigest(),probe_tcl_sha256=hashlib.sha256(tcl.encode()).hexdigest(),launch=dict(ps=max(launch)[0],pin=max(launch)[1])if launch else None,capture=dict(ps=max(capture)[0],pin=max(capture)[1])if capture else None,launch_over=sum(v>220 for v,n in launch),capture_over=sum(v>190 for v,n in capture),comb_pins=comb,clock_refs=refs)
 result['spread_ps']={k:v['bmax']-v['bmin']for k,v in refs.items()}
 result['measured_reference_coverage']=measured_coverage(refs)
 fb=[r.get('ff',{}).get('boundary')for r in[ins,*(ins.get('clock_measurements')or{}).values()]];fb=[b for b in fb if isinstance(b,dict)and b.get('min')is not None and b.get('max')is not None]
 result['ff_spread_ps']=round(max(float(b['max'])-float(b['min'])for b in fb),1)if fb else None
 if rel:
  if comp.get('ff')is not None and fb:lo,hi=min(float(b['min'])for b in fb)-comp['ff'],max(float(b['max'])for b in fb)-comp['ff'];rel['ff']=dict(rel_min_ps=round(lo,1),rel_max_ps=round(hi,1),mismatch_ps=round(max(abs(lo),abs(hi)),1),comp_ps=comp['ff'])
  result['relative']=rel
 match_ok=not rel or all(rel[c]['mismatch_ps']<=PA.NEIGHBOUR_SKEW_PS for c in('tt','ff')if c in rel)
 if comp and not rel:match_ok=False
 result['diagnostic_pass']=bool(launch and capture and refs)and result['measured_reference_coverage']and max(result['spread_ps'].values())<=80 and(result['ff_spread_ps']is None or result['ff_spread_ps']<=80)and match_ok and not(result['launch_over']or result['capture_over']or comb)
 (out/'native_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['diagnostic_pass']else 1
if __name__=='__main__':sys.exit(main())
