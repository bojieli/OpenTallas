#!/usr/bin/env python3
"""Build exact granted XS W-clock candidate; retain actual old signal boundary pins.
Exported routing-stub extension rectangles are not new placement pins. The
smallest perimeter rectangle is the actual pin; fresh routing rebuilds stubs.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
from child_lint import parse_lef
source=ROOT/'physical/ref_tile/smh_xs_ref_p45m'
grant_path=ROOT/'results/physical/hsm_takeover_0825/xs_w_clock_grant.json'
grant=json.loads(grant_path.read_text());lp=ROOT/grant['source_view'];raw=lp.read_bytes()
assert hashlib.sha256(raw).hexdigest()==grant['source_view_sha256']
lef=parse_lef(raw.decode());assert [lef['W'],lef['H']]==grant['outline_um']
tcl=[];count=0;extensions=0
for name,pin in lef['pins'].items():
 if pin.get('use') in ('POWER','GROUND'):continue
 boundary=[]
 for r in pin['rects']:
  ly,x0,y0,x1,y1=r
  if min(abs(x0),abs(y0),abs(x1-lef['W']),abs(y1-lef['H']))<1e-5:boundary.append(r)
 assert boundary,(name,pin)
 ly,x0,y0,x1,y1=min(boundary,key=lambda r:(r[3]-r[1])*(r[4]-r[2]))
 x=(x0+x1)/2;y=(y0+y1)/2;w=x1-x0;h=y1-y0
 extensions+=len(pin['rects'])-1
 if name=='clk':ly='M4';x=0;y=77.772;w=.084;h=.024
 elif abs(x0)<1e-5:x=0
 elif abs(x1-lef['W'])<1e-5:x=lef['W']
 elif abs(y0)<1e-5:y=0
 elif abs(y1-lef['H'])<1e-5:y=lef['H']
 tcl.append(f'place_pin -pin_name {{{name}}} -layer {ly} -location {{{x:.3f} {y:.3f}}} -pin_size {{{w:.3f} {h:.3f}}} -force_to_die_boundary')
 if name!='clk':count+=1
assert count==4542,count
pins=ROOT/'physical/ref_tile_specs/smh/smh_xs_wclk_1016_pins.tcl';pins.parent.mkdir(exist_ok=True,parents=True)
pins.write_text('# Exact actual old signal boundary pins; clock only changed by H-DIE9d111c95a.\n'+'\n'.join(tcl)+'\n')
s=json.loads((source/'spec.json').read_text())
s.update(name='smh_xs_wclk_1016',outline={'w':lef['W'],'h':lef['H']},recipe=3,io_tcl=str(pins.relative_to(ROOT)),pin_regs={'enable':False,'reason':'Unchanged closed XS RTL: source landing registers capture rl1,bk1,ohl1; XS memory/issue stages drive registered outputs, existing HDly hold delays retained. Exact die_window clock repin only; zero edges added and every actual non-clock signal boundary rectangle preserved.'},reroute_reason={'kind':'die_window','slot':'SM/RP4c/XS','source':str(grant_path.relative_to(ROOT)),'why_route':'149um raw clock stub/TT269.9ps slew exceeds120ps; W clock gives25.962um conservative stub'})
s['job'].update(owner='Codex H-SM physical',branch='codex/hsm-physical-0825',tag='wclk1',views_to='physical/ref_tile/smh_xs_wclk_1016/views',record_to='results/rtl/ref_tile/smh_xs_wclk_1016')
s['job'].pop('no_bench_reason',None)
defs=' '.join('--define '+x for x in s['defines'])
cmd='python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 1 --active 1 --rmax 4096 --smh '+defs+' --build-jobs 4'
s['job']['benches']=[{'name':'xs_in_smh_exact','cmd':cmd+' --out {RUN}/xs_exact.json --workdir {RUN}/xs_exact','expect':'pass','threads':4,'peak_ram_gb':16},{'name':'xs_source_data_mutant','cmd':cmd+' --mut-s1w --out {RUN}/xs_mutant.json --workdir {RUN}/xs_mutant','expect':'fail','threads':4,'peak_ram_gb':16}]
s['job']['extra_paths']=['tools/dshbm_sm_pq_seq.py','tools/dshbm_matched_sm_seq.py','tools/hdc_golden.py','tools/hdc_golden_v41.py','tools/rtl_gpu_sm_exact.py','rtl/test/tb_hbm_accel_sm_pq_seq.sv','rtl/hbm_accel/sm','rtl/hbm_accel/epilogue','rtl/gpu','rtl/hdc','rtl/lib','rtl/v41rom','rtl/proto','physical/asap7_memory_macros','physical/hbm_accel_macros']
s['job']['structural_change']='Actual XS clock N/M5 x122.748 -> W/M4 y77.772 under exact grant9d111c95a. All4542 non-clock signal boundary pins, actual302.4x157.68outline, RTL/macros unchanged. Parent raw stub149->25.962um; require fresh native slew/TT/FF/DRC. Parent pins move atomically only with actual qualified new XS; frozen d4 unchanged.'
p=ROOT/'physical/ref_tile/smh_xs_wclk_1016';p.mkdir(exist_ok=True);(p/'spec.json').write_text(json.dumps(s,indent=2)+'\n')
receipt={'source_lef_sha256':hashlib.sha256(raw).hexdigest(),'boundary_pins_preserved':count,'nonplacement_export_stub_rectangles':extensions,'pinfile_sha256':hashlib.sha256(pins.read_bytes()).hexdigest(),'actual_outline_um':[lef['W'],lef['H']],'clock_only_change':grant['clock_grant'],'scope':'candidate input geometry only, no route/native qualification'}
(ROOT/'results/physical/hsm_takeover_0825/xs_wclock_generation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
