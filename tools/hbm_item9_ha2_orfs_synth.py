#!/usr/bin/env python3
"""Changed HA2 full16/PF384 synthesis only; retain objects for protected parent P&R."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
import run_abi3_physical as D
root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);assert out.is_absolute() and not out.exists()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()
r=json.loads((root/'results/rtl/hbm_item9_closure_20261005/HA2_cuts_exact_r1/result.json').read_text());assert r['verdict']=='PASS_CHANGED_HA2_FULL16_GOLDEN' and r['new_cycles']==0
sources=['rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv','rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce_runtime.sv','rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce_item9_cuts.sv','rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_adapter_item9_cuts.sv']
for f in sources:assert hashlib.sha256((root/f).read_bytes()).hexdigest()==r['source_sha256'][f]
block=dict(top='ot_ha2_tu_owner_adapter_item9_cuts',sources=sources,parameters=dict(CUTS=1,NC=8,NOG=8,PFMAX=384,LANES=16,BF16=1,INJ=2,NPT=8,LAT=7,SLOTREG=1),clock_port='clk',clock_uncertainty_ns=.06,clock_uncertainty_hold_ns=.025,false_path_from_ports=[],io_delay_fraction=.2)
view=D.VIEWS['asap7'];pnr={**view['pnr'],'corner_env':'WC'}
nickname='opentallas_item9_ha2cuts_full16_synth_r1';case=out/'work/orfs';case.mkdir(parents=True)
(case/'constraint.sdc').write_text(D.sdc_text(view,block,.833))
config=D.orfs_config_lines(nickname,block,'asap7',pnr,30,.55,memory_max_bits=None)
config += ['export ADDER_MAP_FILE =','export SYNTH_MEMORY_MAX_BITS = 273645'] # actual previous fullshape267501 FF plus6144 added FF; compiler shape guard, no resource cap
(case/'config.mk').write_text('\n'.join(config)+'\n')
record=dict(owner='Codex/Dirac item9',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),sources_sha256={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in sources},shape=block['parameters'],constraints=dict(period_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,clock_roots=['clk'],false_paths=False,external_IO_budget_is_not_measured_parent_delay=True),threads=16,admission_guard_GiB=64,admission_guard_unchanged=True,synthesis_only=True,actual_context_route_qualified=False,adopted=False)
(out/'launch.json').write_text(json.dumps(record,indent=2)+'\n')
target=f'/work/results/asap7/{nickname}/base/1_2_yosys.v'
command=['docker','run','--rm','-v',f'{root}:/src:ro','-v',f'{case}:/work','-w','/OpenROAD-flow-scripts/flow',D.ORFS_IMAGE,'bash','-lc',f"trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 {target}"]
with (out/'run.log').open('w') as log:rc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT).returncode
record['exit']=rc
record['artifacts']={str(p.relative_to(out)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in case.rglob('*') if p.is_file() and p.name in ('stat.txt','1_2_yosys.v','constraint.sdc','config.mk')}
(out/'result.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(rc)
