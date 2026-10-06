#!/usr/bin/env python3
"""Prepare/run one source-faithful tileW repair from retained CTS.

One explicit native macro OBS GCell (default OFF), no regional hard boxes,
no power-grid reduction and no capacity above the original allocated route.
Only successful GRT permits the existing detailed-route + SS/FF continuation.
"""
import argparse,ast,collections,hashlib,json,math,os,re,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
IMAGE='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def model(macros,cells):
    # Execute the actual unified-model definitions; avoid unrelated sparse-WT
    # import-time dataset dependencies. There is no private sizing model.
    source=(ROOT/'tools/uarch_model.py').read_text();tree=ast.parse(source);ns={'math':math}
    for name in ['hbm_smh_local_grt_price','hbm_smh_macro_band_price']:
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        exec(ast.get_source_segment(source,node),ns)
    return ns['hbm_smh_macro_band_price'](macros,cells)
def prepare(out,report,topology,cells):
    out.mkdir(parents=True,exist_ok=False)
    j=json.loads(topology.read_text());m=model(j['macros'],cells)
    raw=report.read_text();rows=[]
    for c in raw.split('violation type: ')[1:]:
        cap,u,ov=map(int,re.search(r'capacity:(\d+) usage:(\d+) congestion:(\d+)',c).groups())
        assert u-cap==ov
        rows.append(dict(capacity=cap,usage=u,overflow=ov))
    eps=[e for n in j['nets'].values() for e in n['endpoints'] if 'inst' in e]
    static_masks=[]
    for name,n in j['nets'].items():
        if any(e.get('macro') and e['pin'].startswith('w_mask_in') for e in n['endpoints']):
            static_masks.append(dict(net=name,endpoints=n['endpoints']))
    cause=dict(verdict='REAL_GRT_CONGESTION_WITH_OWN_ALL_LAYER_KEEP_OUT_REGRESSION',
        API_or_termination_failure=False,original_overflow=83,overflow=sum(r['overflow'] for r in rows),
        regions=len(rows),zero_capacity_regions=sum(r['capacity']==0 for r in rows),
        zero_capacity_overflow=sum(r['overflow'] for r in rows if r['capacity']==0),
        implicated_nets=len(j['nets']),implicated_endpoint_occurrences=len(eps),
        endpoint_occurrences_in_keepouts=sum(bool(e['inside_keepout']) for e in eps),
        endpoint_master_counts_in_keepouts=collections.Counter(e['master'] for e in eps if e['inside_keepout']),
        actual_static_mask_nets=static_masks,
        PG_region_box=j['PG_region_box'],PG_shape_counts=j['PG_region_counts'],
        DB_grid_capacity_semantics='Nominal layer capacity; DB usage includes blockages (GlobalRouter.cpp updateDbCongestionFromGuides). Not usable-track credit.',
        report_sha256=sha(report),topology_sha256=sha(topology),
        repair='Remove only own all-layer boxes; native one-GCell directional M2/M3/M4 SRAM OBS bands, preserve M5/M6 escape and ALL PG demand',
        baseline_closure_required=True,adopted=False)
    (out/'cause.json').write_text(json.dumps(cause,indent=2)+'\n')
    (out/'model_before_route.json').write_text(json.dumps(m,indent=2)+'\n')
    (out/'congestion.rpt').write_bytes(report.read_bytes())
    t=['# Explicit opt-in; native macro bands only. No invented capacity or PG credit.',
       'if {$::env(ROUTING_LAYER_ADJUSTMENT) != 0.25} {error "Original25percent layer reservation required"}',
       'set n 0',
       'foreach i [[ord::get_db_block] getInsts] {if {[[$i getMaster] isBlock]} {incr n}}',
       'if {$n != 8} {error "Wrong retained full tile macro inventory"}',
       'set_macro_extension '+str(cells),
       'puts "OT_NATIVE_MACRO_BAND cells='+str(cells)+' gcell_um=0.57 macros=8 lower_OBS_layers=M2,M3,M4 PG_unchanged=1 M5_M6_escape=1"']
    (out/'macro_bands.tcl').write_text('\n'.join(t)+'\n')
    return m

def run(old,w,src,recipe):
    import sys;sys.path.insert(0,'/srv/opentallas-scratch');import admit_core
    w.mkdir(parents=True,exist_ok=False)
    receipt=json.loads((old/'source_checkpoint_pin.json').read_text())
    for f,h in receipt['source_sha256'].items():assert sha(src/f)==h,f
    base=next((old/'results/asap7').glob('*/base'));dest=w/base.relative_to(old);dest.mkdir(parents=True)
    for name in ['4_cts.odb','4_cts.sdc']:
        key=str((base/name).relative_to(old));assert sha(base/name)==receipt['checkpoint_sha256'][key]
        shutil.copy2(base/name,dest/name)
    for name in ['constraint.sdc','pins.tcl','macros.tcl','geometry.json']:shutil.copy2(old/name,w/name)
    for name in ['macro_bands.tcl','model_before_route.json','cause.json']:shutil.copy2(recipe/name,w/name)
    config=(old/'config.original.mk').read_text()
    # Replace only this owner's PRE_GRT hook. All actual allocation, PG and
    # electrical/clock/uncertainty settings remain byte-faithful.
    config='\n'.join(l for l in config.splitlines() if not l.startswith('export PRE_GLOBAL_ROUTE_TCL'))+'\nexport PRE_GLOBAL_ROUTE_TCL = /work/macro_bands.tcl\n'
    (w/'config.original.mk').write_bytes((old/'config.original.mk').read_bytes());(w/'config.mk').write_text(config)
    original={str(p.relative_to(w)):sha(p) for p in [dest/'4_cts.odb',dest/'4_cts.sdc',w/'constraint.sdc',w/'pins.tcl',w/'macros.tcl']}
    (w/'source_checkpoint_pin.json').write_text(json.dumps(dict(original_source_pin=receipt['original_source_pin'],source_sha256=receipt['source_sha256'],
      checkpoint_sha256=original,driver_sha256=sha(__file__),model_sha256=sha(w/'model_before_route.json'),
      image=IMAGE,synthesis=False,placement=False,CTS=False,PG_rebuilt=False,clock_policy='833ps SS60FF25 and real SRAM timing unchanged; full contextual closure mandatory'),indent=2)+'\n')
    while True:
        load=os.getloadavg();avail=admit_core._avail();disk=shutil.disk_usage(w).free
        # Reuse actual measured8.55GiB GRT/24GiB whole-tile reservation and
        # measured4GiB outputs +267MB CTS inventory. Admission only, no caps.
        if load[0]<128 and disk>2*4*2**30+300*2**20 and admit_core.try_admit(24*2**30):break
        time.sleep(10)
    (w/'admission.json').write_text(json.dumps(dict(load=load,MemAvailable=avail,disk_free=disk,need_GiB=24,cores=24,
       execution_caps=None,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())),indent=2)+'\n')
    name='codex-smh-native-band-r3-tileW'
    cmd=['docker','run','--rm','--name',name,'-v',str(src)+':/src:ro','-v',str(w)+':/work','-w','/OpenROAD-flow-scripts/flow',IMAGE,'bash','-lc',
      'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=24 do-5_1_grt']
    (w/'command.json').write_text(json.dumps(cmd,indent=2)+'\n');(w/'status').write_text('LIVE_NATIVE_MACRO_BAND_GRT_FROM_RETAINED_CTS\n')
    ceiling=json.loads((w/'model_before_route.json').read_text())['original_resource_ceiling'];checked=False;invalid=None
    with (w/'flow.log').open('w') as f:
        q=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT)
        while True:
            text=(w/'flow.log').read_text();tables=re.findall(r'\[INFO GRT-0053\].*?\n\n',text,re.S)
            if tables:
                caps={k:int(cap) for k,cap in re.findall(r'^(M[2-6])\s+(?:Horizontal|Vertical)\s+\d+\s+(\d+)',tables[-1],re.M)}
                if len(caps)==5:
                    if any(caps[k]>ceiling[k] for k in caps):
                        invalid=dict(actual=caps,ceiling=ceiling,reason='Actual resources exceed original budget; own run terminated, not architecture FAIL')
                        (w/'invalid_capacity.json').write_text(json.dumps(invalid,indent=2)+'\n')
                        subprocess.run(['docker','kill',name],check=True);break
                    checked=True;(w/'capacity_guard.json').write_text(json.dumps(dict(actual=caps,ceiling=ceiling,pass_original_ceiling=True),indent=2)+'\n')
            if q.poll() is not None:break
            time.sleep(10)
        rc=q.wait()
    subprocess.run(['docker','run','--rm','-v',str(w)+':/work',IMAGE,'chmod','-R','a+rwX','/work'],check=True)
    intact=all(sha(w/p)==h for p,h in original.items());assert intact
    verdict='FAIL_INVALID_CAPACITY' if invalid else ('PASS_GRT' if rc==0 and checked else 'FAIL_GRT_OR_FLOW')
    if rc==0:assert checked and (dest/'5_1_grt.odb').is_file() and (dest/'5_1_grt.sdc').is_file()
    (w/'terminal.json').write_text(json.dumps(dict(rc=rc,verdict=verdict,checkpoint_unchanged=intact,capacity_guard_pass=checked and not invalid,
      scope='GRT only; final SS60 FF25 and all mandatory baseline classes pending',adopt=False),indent=2)+'\n')
    (w/'status').write_text('TERMINAL_GRT_RC='+str(rc)+'\n')
    return rc
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path);p.add_argument('--report',type=Path);p.add_argument('--topology',type=Path)
    p.add_argument('--macro-band-cells',type=int,default=0);p.add_argument('--run-from',type=Path);p.add_argument('--work',type=Path);p.add_argument('--source',type=Path);p.add_argument('--recipe',type=Path);a=p.parse_args()
    if a.prepare:prepare(a.prepare,a.report,a.topology,a.macro_band_cells)
    if a.run_from:raise SystemExit(run(a.run_from,a.work,a.source,a.recipe))
