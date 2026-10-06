#!/usr/bin/env python3
"""Changed HA2 full16/PF384 synthesis only; retain objects for protected parent P&R."""
import hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
import run_abi3_physical as D


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def prepare_mapped_route(src, binding, out, utilization):
    """Reuse the terminal adapter map; never route the enclosing queue array."""
    repo = Path(__file__).resolve().parents[1]
    terminal = src / 'result.json'
    if not terminal.is_file():
        raise SystemExit('Mapping still active: preserve ABC; no route prepared')
    r = json.loads(terminal.read_text())
    assert r['exit'] == 0 and r['synthesis_only']
    assert r['shape'] == dict(CUTS=1, NC=8, NOG=8, PFMAX=384, LANES=16,
                            BF16=1, INJ=2, NPT=8, LAT=7, SLOTREG=1)
    gate = json.loads((repo / 'results/rtl/hbm_item9_closure_20261005/HA2_cuts_exact_r2/result.json').read_text())
    assert gate['verdict'] == 'PASS_CHANGED_HA2_FULL16_GOLDEN' and gate['new_cycles'] == 0
    for f, h in r['sources_sha256'].items():
        assert digest(repo / f) == h == gate['source_sha256'][f], f
    mapped, = src.glob('work/orfs/results/asap7/*/base/1_2_yosys.v')
    mh = digest(mapped)
    assert mh == r['artifacts'][str(mapped.relative_to(src))]['sha256']
    b = json.loads(binding.read_text())
    assert b['top'] == 'ot_ha2_tu_owner_adapter_item9_cuts'
    assert b['source_mapped_sha256'] == mh
    assert b['clock_period_ps'] == 833 and b['setup_uncertainty_ps'] == 60 and b['hold_uncertainty_ps'] == 25
    assert b['clock_roots'] == ['clk']  # literal adapter ABI, not TU's pclk alias
    for field in ('producer_tuples', 'receiver_tuples', 'clock_pin_tuples',
                  'reset_pin_tuples', 'corridor_segments', 'route_memory_inventory_basis'):
        assert b[field], field
    # Synthesis's 64 GiB inventory is not a measured P&R peak. Kant must
    # supply the route inventory before using the unchanged host guard.
    assert b['route_memory_owner'] == 'Kant'
    assert isinstance(b['route_memory_guard_GiB'], (int, float)) and b['route_memory_guard_GiB'] > 0
    assert b['canonical_r14_geometry_used'] is False
    assert b['PG_and_clock_tracks_excluded_from_capacity'] is True
    sdc, pins = (Path(b[k]['path']) for k in ('SDC', 'pins_Tcl'))
    assert digest(sdc) == b['SDC']['sha256'] and digest(pins) == b['pins_Tcl']['sha256']
    text = sdc.read_text()
    assert not re.search(r'\b(set_false_path|set_multicycle_path|set_disable_timing)\b', text)
    assert all(k in text for k in ('create_clock', 'set_input_delay', 'set_output_delay', 'set_load'))
    assert utilization in (55, 60) and out.is_absolute() and not out.exists()
    # The full-capacity changed adapter is the minimum unit. No TU queues,
    # switch, full die, or second synthesis is included in this continuation.
    work = out / 'work/orfs'; work.mkdir(parents=True)
    shutil.copy2(mapped, work / 'mapped.v')
    shutil.copy2(sdc, work / 'constraint.sdc'); shutil.copy2(pins, work / 'pins.tcl')
    prefixes = ('export DESIGN_NICKNAME', 'export CORE_UTILIZATION', 'export PLACE_DENSITY',
                'export DIE_AREA', 'export CORE_AREA', 'export SYNTH_NETLIST_FILES',
                'export FOOTPRINT_TCL', 'export VERILOG_FILES', 'export CORNERS',
                'export WC_LIB_FILES', 'export BC_LIB_FILES')
    config = [x for x in (src / 'work/orfs/config.mk').read_text().splitlines()
              if not x.startswith(prefixes)]
    config += ['export DESIGN_NICKNAME = opentallas_item9_ha2cuts_mapped_u' + str(utilization),
               'export VERILOG_FILES = /work/mapped.v',
               'export SYNTH_NETLIST_FILES = /work/mapped.v',
               'export FOOTPRINT_TCL = /work/pins.tcl',
               'export CORE_UTILIZATION = ' + str(utilization),
               'export PLACE_DENSITY = ' + str(utilization / 100),
               'export DIE_AREA = ' + ' '.join(map(str, b['die_bbox_um'])),
               'export CORE_AREA = ' + ' '.join(map(str, b['core_bbox_um']))]
    config += D.corner_lib_lines(['WC', 'BC'], None)
    (work / 'config.mk').write_text('\n'.join(config) + '\n')
    record = dict(phase='PREPARED_NOT_ADMITTED', source_synth=r, source_bound_binding=b,
                  mapped_sha256=mh, exact_gate_reused=True, new_cycles=0,
                  full_protected_parent_included=False, physical_signoff=False, adopted=False,
                  NUM_CORES=16, memory_guard_GiB=b['route_memory_guard_GiB'], guard_unchanged=True,
                  utilization_percent=utilization, driver_sha256=digest(Path(__file__)),
                  work_sha256={f: digest(work / f) for f in ('mapped.v', 'config.mk', 'constraint.sdc', 'pins.tcl')})
    (out / 'launch.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


def route_admitted(out):
    """Called only inside the host's unchanged guard; refuse lost CPU fit."""
    from hbm_item9_context32_route import cpu_fit, routed_reports
    assert Path('/srv/opentallas-scratch/admit.sh').is_file()
    if not cpu_fit(16):
        raise SystemExit(75)
    r = json.loads((out / 'launch.json').read_text())
    assert r['phase'] == 'PREPARED_NOT_ADMITTED' and digest(Path(__file__)) == r['driver_sha256']
    work = out / 'work/orfs'
    for f, h in r['work_sha256'].items():
        assert digest(work / f) == h
    image = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', D.ORFS_IMAGE], text=True).strip()
    (out / 'image_id.txt').write_text(image + '\n')
    repo = Path(__file__).resolve().parents[1]
    (out / 'postadmission.json').write_text(json.dumps(dict(load=os.getloadavg(),
        CPUs=os.cpu_count(), meminfo=Path('/proc/meminfo').read_text(),
        disk_free_bytes=shutil.disk_usage(out).free)) + '\n')
    command = ['docker', 'run', '--rm', '-v', f'{repo}:/src:ro', '-v', f'{work}:/work', image,
               'bash', '-lc', 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '
               'python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && '
               'cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/work/config.mk '
               'WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 finish']
    (out / 'command.json').write_text(json.dumps(command) + '\n')
    with (out / 'run.log').open('w') as log:
        rc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
    r.update(phase='FLOW_TERMINAL', exit=rc)
    if rc == 0:
        reports = routed_reports(work)
        r['routed_corner_reports'] = reports
        r['adapter_timing_closed'] = len(reports) == 2 and all(
            x['exit'] == 0 and x['metrics']['CLOCK_COUNT'] == '1' and
            all(float(x['metrics'][k]) >= 0 for k in ('SETUP', 'HOLD')) for x in reports)
    (out / 'result.json').write_text(json.dumps(r, indent=2) + '\n')
    raise SystemExit(rc)


if sys.argv[1:2] == ['--prepare-mapped-route']:
    prepare_mapped_route(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), int(sys.argv[5]))
    raise SystemExit(0)
if sys.argv[1:2] == ['--route-admitted']:
    route_admitted(Path(sys.argv[2]))

root=Path(__file__).resolve().parents[1];out=Path(sys.argv[1]);assert out.is_absolute() and not out.exists()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()
r=json.loads((root/'results/rtl/hbm_item9_closure_20261005/HA2_cuts_exact_r2/result.json').read_text());assert r['verdict']=='PASS_CHANGED_HA2_FULL16_GOLDEN' and r['new_cycles']==0
sources=['rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv','rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce_runtime.sv','rtl/hbm_accel/ha2_ar/ot_ha2_owner_reduce_item9_cuts.sv','rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_adapter_item9_cuts.sv']
for f in sources:assert hashlib.sha256((root/f).read_bytes()).hexdigest()==r['source_sha256'][f]
block=dict(top='ot_ha2_tu_owner_adapter_item9_cuts',sources=sources,parameters=dict(CUTS=1,NC=8,NOG=8,PFMAX=384,LANES=16,BF16=1,INJ=2,NPT=8,LAT=7,SLOTREG=1),clock_port='clk',clock_uncertainty_ns=.06,clock_uncertainty_hold_ns=.025,false_path_from_ports=[],io_delay_fraction=.2)
view=D.VIEWS['asap7'];pnr={**view['pnr'],'corner_env':'WC'}
nickname='opentallas_item9_'+out.name.replace('-','_');case=out/'work/orfs';case.mkdir(parents=True)
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
