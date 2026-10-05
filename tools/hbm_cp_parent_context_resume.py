#!/usr/bin/env python3
"""Resume the sole CP context after a constraint-API correction; reuse its mapped netlist."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shlex
import shutil

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r1-root', type=Path, required=True)
    parser.add_argument('--retry-root', type=Path, required=True)
    parser.add_argument('--corrected-sdc', type=Path, required=True)
    parser.add_argument('--checkpoint', choices=['mapped','tapcell','pdn','gp-no-io','placed'], required=True)
    parser.add_argument('--checkpoint-sha256', required=True)
    parser.add_argument('--bind-inserted-cells', action='store_true',
                        help='Bind CTS and repair cells to Turing\'s retained finite fences before legalization')
    args = parser.parse_args()
    r1, retry = args.r1_root.resolve(), args.retry_root.resolve()
    assert retry.parent == r1, 'Retry must remain under the same context job'
    assert (r1/'terminal.exit').read_text().strip() == '1'
    record = json.loads((r1/'physical.json').read_text())
    assert 'STA-0410' in record['error'] and not record['flow_completed']
    for source in record['design']['sources']:
        assert sha(ROOT/source['path']) == source['sha256'], source['path']
    old = (r1/'work/orfs/constraint.sdc').read_text()
    new = args.corrected_sdc.read_text()
    expected = old.replace('set_clock_latency -early 90 ', 'set_clock_latency -min 90 ', 1)
    expected = expected.replace('set_clock_latency -late 100 ', 'set_clock_latency -max 100 ', 1)
    # Compare executable constraints, permitting comments/formatting only.
    def commands(text):
        return [' '.join(line.split()) for line in text.splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
    assert commands(new) == commands(expected), 'Retry changes more than the two network API options'
    assert 'set_clock_latency -source 0 [get_clocks core_clk]' in new
    original = list((r1/'work/orfs/results').rglob('1_2_yosys.v'))
    assert len(original) == 1
    rel = original[0].relative_to(r1/'work/orfs')
    mapped = retry/'work/orfs'/rel
    assert sha(mapped) == sha(original[0]), 'Copied mapped netlist changed'
    checkpoint_names={'mapped':'1_2_yosys.v','tapcell':'2_3_floorplan_tapcell.odb',
                      'pdn':'2_4_floorplan_pdn.odb','gp-no-io':'3_1_place_gp_skip_io.odb',
                      'placed':'3_place.odb'}
    checkpoint=mapped.parent/checkpoint_names[args.checkpoint]
    assert sha(checkpoint)==args.checkpoint_sha256, 'Retained checkpoint differs from the selected source artifact'
    limits={'mapped':(1,2),'tapcell':(2,3),'pdn':(2,4),'gp-no-io':(3,1),'placed':(3,99)}
    limit=limits[args.checkpoint]
    frozen={}
    for file in mapped.parent.iterdir():
        if args.checkpoint=='mapped' and file!=mapped:continue
        if file.suffix not in ('.odb','.sdc','.v') or 'error' in file.name.lower():continue
        parts=file.stem.split('_')
        if not parts[0].isdigit():continue
        stage=(int(parts[0]),int(parts[1]) if len(parts)>1 and parts[1].isdigit() else 99)
        if stage>limit:continue
        if file.suffix=='.sdc' and args.checkpoint!='mapped':
            text=file.read_text()
            assert 'set_clock_latency -early 90' not in text and 'set_clock_latency -late 100' not in text, file
        frozen[file]=sha(file)
    frozen[mapped]=sha(mapped)
    validation = (retry/'network_api_validation.log').read_text()
    assert 'OT_NETWORK_SDC_PARSE_PASS' in validation and '[ERROR' not in validation
    argv = record['runner']['argv'][1:]
    def replace_option(option, value):
        index = argv.index(option)
        argv[index+1] = str(value)
    replace_option('--sdc-append', args.corrected_sdc.resolve())
    replace_option('--keep-workdir', retry/'work')
    replace_option('--output', retry/'physical.json')
    receipt = dict(schema='hbm.cp.parent-context.mapped-resume.v1',
                   original_root=str(r1),original_physical_sha256=sha(r1/'physical.json'),
                   mapped_netlist_sha256=sha(mapped),corrected_sdc_sha256=sha(args.corrected_sdc),
                   hardware_sources=record['design']['sources'],same_context=True,
                   changed_network_API_only=True,source_phase_ps=0,
                   analytical_network_latency_ps=[90,100],setup_ps=60,hold_ps=25,
                   original_failure_preserved=True,synthesis_reused=False,
                   resume_checkpoint=str(checkpoint),resume_checkpoint_sha256=sha(checkpoint),
                   frozen_upstream_artifacts={str(p.relative_to(retry/'work/orfs')):h for p,h in frozen.items()})
    (retry/'resume.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if args.bind_inserted_cells:
        assert args.checkpoint == 'placed'
        model = json.loads((ROOT/'results/physical/hbm_cp_cts_allocation_20261005/model.json').read_text())
        hook = ROOT/model['hook']
        assert sha(hook) == model['hook_sha256']
        assert sha(checkpoint) == model['last_valid_placed_checkpoint_sha256']
        assert model['verification']['check_placement_PASS']
        shutil.copyfile(hook, retry/'work/orfs/cts_membership.tcl')
        # POST_CTS_TCL runs too late: inserted cells must join their fences before
        # both the clock-tree and timing-repair detailed-placement calls.
        patch = '''from pathlib import Path
import hashlib,json
p=Path('/OpenROAD-flow-scripts/flow/scripts/cts.tcl')
s=p.read_text()
needle='set result [catch { log_cmd detailed_placement } msg]'
assert s.count(needle)==2, 'Installed CTS legalization API changed'
print(json.dumps(dict(original_cts_sha256=hashlib.sha256(s.encode()).hexdigest(),membership_calls=2)))
p.write_text(s.replace(needle,'source /work/cts_membership.tcl\\n'+needle))
'''
        (retry/'work/orfs/bind_cts_membership.py').write_text(patch)
        receipt['inserted_cell_membership'] = dict(hook_sha256=sha(hook),
            model_sha256=sha(ROOT/'results/physical/hbm_cp_cts_allocation_20261005/model.json'),
            region_geometry_changed=False, padding_changed=False, timing_changed=False)
        (retry/'resume.json').write_text(json.dumps(receipt,indent=2)+'\n')
    import run_abi3_physical as driver
    original_run = driver.run
    reused = 0
    def run(command, **kwargs):
        nonlocal reused
        # Skip precisely the driver's initial mapped-netlist make target.
        # All floorplan/placement/CTS/route commands run unchanged.
        if (command[:3] == ['docker','run','--rm']
            and str('/work/'+str(rel)+' && chmod a+w /work/'+str(rel)) in command[-1]):
            assert reused == 0 and sha(mapped) == receipt['mapped_netlist_sha256']
            reused += 1
            receipt['synthesis_reused'] = True
            (retry/'resume.json').write_text(json.dumps(receipt,indent=2)+'\n')
            return subprocess.CompletedProcess(command,0,stdout='REUSED_R1_MAPPED_NETLIST '+sha(mapped)+'\n',stderr='')
        if command[:3] == ['docker','run','--rm'] and 'make DESIGN_CONFIG=/work/config.mk' in command[-1]:
            # Make must not re-map RTL due solely to copied-source/config timestamps.
            assert reused == 1
            command = list(command)
            keep=[]
            for file in frozen:keep.extend(['-o','/work/'+str(file.relative_to(retry/'work/orfs'))])
            command[-1] = command[-1].replace('make DESIGN_CONFIG=/work/config.mk',
                'make '+shlex.join(keep)+' DESIGN_CONFIG=/work/config.mk',1)
            if args.bind_inserted_cells:
                command[-1] = 'python3 /work/bind_cts_membership.py && '+command[-1]
        return original_run(command, **kwargs)
    driver.run = run
    rc = driver.main(argv)
    assert reused == 1, 'Mapped-netlist resume hook was not consumed exactly once'
    for file,digest in frozen.items():
        assert sha(file)==digest, 'Upstream stage replayed despite retained-checkpoint selection: '+str(file)
    return rc

if __name__ == '__main__':
    raise SystemExit(main())
