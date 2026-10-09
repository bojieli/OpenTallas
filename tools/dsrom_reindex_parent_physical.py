#!/usr/bin/env python3
"""Minimum fullshape production control/list/finite-consumer physical run."""
import argparse,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CTS_VARIANTS={'compact':(20,40,50),'medium':(30,50,60),'wide':(40,60,80)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--exact',type=Path,required=True)
 p.add_argument('--split-counters',action='store_true');p.add_argument('--ctl-x1',type=float,help='CLAUDE s81-blocks: control fence right edge um (default 308.124)');p.add_argument('--io-margin',action='store_true',help='margin-first register-to-register top, route at 770 ps, sign off at 833.333 ps');p.add_argument('--mapped-route',type=Path);p.add_argument('--cts-variant',choices=CTS_VARIANTS);a=p.parse_args()
 if bool(a.mapped_route)!=bool(a.cts_variant):raise SystemExit('mapped reuse and distinct CTS variant required together')
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise SystemExit('clean pinned source required')
 exact=json.loads(a.exact.read_text())
 if exact['status']!='pass' or not exact.get('backpressure',{}).get('pass_'):raise SystemExit('actual production exact and finite drain gates required')
 if bool(exact.get('split_counters',False))!=a.split_counters:raise SystemExit('exact counter partition mismatch')
 if bool(exact.get('io_margin',False))!=a.io_margin:raise SystemExit('exact boundary mismatch')
 pre='rtl/dsrom_sys/reindex_parent/'
 src=[pre+n for n in ['ot_dsrom_reindex_parent_physctx.sv','ot_dsrom_reindex_parent_control.sv','ot_dsrom_reindex_kgctl_parent.sv','ot_dsrom_reindex_list_macro.sv','ot_dsrom_reindex_request_cut.sv','ot_dsrom_reindex_drain_queue.sv']+(['ot_dsrom_reindex_io_margin.sv'] if a.io_margin else [])]
 for f in src:
  if f.endswith('physctx.sv'):continue
  if exact['source_sha256'].get(f)!=hashlib.sha256((ROOT/f).read_bytes()).hexdigest():raise SystemExit('exact source mismatch: '+f)
 macro='ot_sram_1r1w_512x128_m4_r2c2'
 src+=['physical/asap7_memory_macros/'+macro+'/'+macro+'_bb.v']
 pins=src+['tools/run_abi3_physical.py','tools/orfs_allcorner_spef.py','tools/dsrom_reindex_parent_physical.py','physical/common/ot_macro_track_snap.tcl','physical/dsrom_reindex_parent/place.tcl','physical/dsrom_reindex_parent/regions.tcl','tools/dsrom_reindex_parent_model.py']
 reuse=None
 if a.mapped_route:
  pins.append('tools/dsrom_reindex_parent_fanout.py')
  baseline=json.loads((a.mapped_route/'source.json').read_text())
  for f in src+['tools/run_abi3_physical.py','tools/orfs_allcorner_spef.py','physical/dsrom_reindex_parent/place.tcl','physical/dsrom_reindex_parent/regions.tcl']:
   if sha(ROOT/f)!=baseline['sha256'][f]:raise SystemExit('mapped source/flow mismatch: '+f)
  if baseline['exact_record_sha256']!=sha(a.exact):raise SystemExit('different exact receipt')
  base=a.mapped_route/'work/orfs/results/asap7/opentallas_ot_dsrom_reindex_parent_physctx_asap7_reindex_parent/base'
  mapped=base/'1_2_yosys.v'
  if not (base/'1_synth.odb').is_file() or not mapped.is_file():raise SystemExit('completed normalized mapped checkpoint required; never duplicate synthesis')
  text=mapped.read_text()
  if len(re.findall(r'(?m)^\s*\\?ot_sram_1r1w_512x128_m4_r2c2\s+\S+\s*\(',text))!=16:raise SystemExit('mapped macro inventory is not sixteen')
  reuse=dict(route_source_sha256=sha(a.mapped_route/'source.json'),source_commit=baseline['commit'],mapped_sha256=sha(mapped),
             CTS_variant=a.cts_variant,CTS_parameters=CTS_VARIANTS[a.cts_variant],added_cycles=0,
             geometry_and_standardcell_cap_unchanged=True,parent_qualified=False,
             basis='Existing modeled fullshape control/list geometry; only clock clustering changes. Reuse actual mapped attributes/connectivity without ABC or RTL replay.')
 a.out.mkdir(parents=True,exist_ok=False)
 if reuse:
  case=a.out/'work/orfs';case.mkdir(parents=True)
  shutil.copy2(mapped,case/'r9_mapped.v')
  if sha(case/'r9_mapped.v')!=reuse['mapped_sha256']:raise SystemExit('mapped file changed during copy')
  (a.out/'mapped_reuse.json').write_text(json.dumps(reuse,indent=2)+'\n')
 (a.out/'source.json').write_text(json.dumps(dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pins},exact_record_sha256=hashlib.sha256(a.exact.read_bytes()).hexdigest(),scope='Actual production control, list SRAM/capture, request slots and four-entry drain header; key data store outside scope; all interfaces timed; fixed control cap37452.2um2'),indent=2)+'\n')
 cmd=[sys.executable,str(ROOT/'tools/run_abi3_physical.py'),'--view','asap7','--top','ot_dsrom_reindex_parent_physctx_margin' if a.io_margin else 'ot_dsrom_reindex_parent_physctx']
 for f in src:cmd+=['--source',f]
 if a.split_counters:cmd+=['--param','SPLIT_COUNTERS=1']
 cmd+=['--clock-period-ns','0.770' if a.io_margin else '0.833333','--clock-uncertainty-ns','0.060','--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC','--hold-corners','WC,BC','--stages','pnr','--hold-margin-ns','0.008','--max-transition-ns','library','--slew-margin-percent','20','--max-fanout','32','--io-delay-fraction','0.2','--die-area','0','0','728.384','460.964','--core-area','2.052','2.160','726.324','458.910','--macro-view',macro+'=physical/asap7_memory_macros/'+macro,'--macro-place-halo','2','2','--orfs-var','PLACE_DENSITY_LB_ADDON=','--step-tcl','POST_MACRO_PLACE=physical/dsrom_reindex_parent/place.tcl','--step-tcl','POST_PDN=physical/dsrom_reindex_parent/regions.tcl','--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited','--nickname-tag','reindex_parent',*(['--orfs-var',f'REINDEX_CTL_X1={a.ctl_x1}'] if a.ctl_x1 else []),'--keep-workdir',str(a.out.resolve()/'work'),'--output',str(a.out.resolve()/'physical.json')]
 if a.io_margin:cmd+=['--orfs-var','SYNTH_ARGS=-noshare','--nickname-tag','reindex_parent_margin']
 env=os.environ.copy();env['OT_ORFS_NUM_CORES']='16';env['PLACE_DENSITY_LB_ADDON']=''
 if reuse:
  cmd+=['--orfs-var','SYNTH_NETLIST_FILES=/work/r9_mapped.v']
  for key,value in zip(('CTS_CLUSTER_SIZE','CTS_CLUSTER_DIAMETER','CTS_BUF_DISTANCE'),CTS_VARIANTS[a.cts_variant]):cmd+=['--orfs-var',key+'='+str(value)]
 with (a.out/'route.log').open('w') as log:r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
 (a.out/'exit').write_text(str(r.returncode)+'\n')
 raise SystemExit(r.returncode)
if __name__=='__main__':main()
