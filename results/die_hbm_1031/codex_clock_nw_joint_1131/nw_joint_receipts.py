from pathlib import Path
import json
import re
import math
r = Path(__file__).resolve().parent
base = json.loads((r/'joint_NW_base_nodes.json').read_text())
old_root = Path('/srv/opentallas-scratch/claude/wt/codex-hbm-clock-sparse/results/die_hbm_1031/codex_clock_feed_probes/measured')
receipts = {}
for variant, source, inverted in [('A','b2654',False), ('B','r2645_0',True)]:
    directory = r / f'joint_NW_{variant}'
    drc = int(re.findall(r'Number of violations = (\d+)', (directory/'route.log').read_text())[-1])
    assert drc == 0
    receipt = dict(verdict='LOCAL_ACTUAL_FEED_PREFIX_PASS', drc=drc, source=source,
                   physical_root='R/A', root_proxy_removed=True, boundary_basis='Saved-route source-A rise/fall slew and phase calibrated against original measured old cut; newly loaded source-Y never fitted', corners={},
                   scope='Real source/fanout and actual R/P1/P2 shared prefix. Whole mesh/native endpoint/current-tap G4 held.')
    for corner in ['TT','FF']:
        old = {f[1]+'/'+f[0]:list(map(float,f[2:]))
               for line in (old_root/f'NW_{variant}'/f'old_arr_{corner}.txt').read_text().splitlines()
               if (f:=line.split())}
        new = {f[0]:list(map(float,f[1:]))
               for line in (directory/f'joint_arr_calibrated_{corner}.txt').read_text().splitlines()
               if (f:=line.split())}
        calibration = json.loads((old_root/f'NW_{variant}'/f'calibration_{corner}.json').read_text())
        assert abs(new[f'ck_{source}/A'][2]-calibration['target_A_rise_slew_ps']) < .1
        source_base = base[corner][source]
        old_output = old[f'ck_{source}/Y']
        ri, fi = (3,0) if inverted else (0,3)
        nodes = {}
        for pin in ['R/A','R/Y','P1/Y','P2/Y','N255/A']:
            values = new[pin]
            nodes[pin] = dict(rise_late_ps=source_base['node_late_ps']+values[0]-old_output[ri],
                              rise_early_ps=source_base['node_early_ps']+values[1]-old_output[ri+1],
                              fall_late_ps=source_base['node_fall_late_ps']+values[3]-old_output[fi],
                              fall_early_ps=source_base['node_fall_early_ps']+values[4]-old_output[fi+1],
                              rise_slew_ps=values[2], fall_slew_ps=values[5])
        assert all(math.isfinite(value) for node in nodes.values() for value in node.values())
        receipt['corners'][corner] = dict(nodes=nodes, source_A_rise_slew_ps=new[f'ck_{source}/A'][2],
                                          source_boundary_match_ps=.1,
                                          P2_delta_vs_old_B_ps=nodes['P2/Y']['rise_late_ps']-base[corner]['NW_hub/P2']['node_late_ps'])
    receipts[variant] = receipt
(r/'joint_NW_receipts.json').write_text(json.dumps(receipts,indent=2))
for variant, receipt in receipts.items():
    print(variant, {corner:dict(P2=data['nodes']['P2/Y']['rise_late_ps'], delta_vs_old_B=data['P2_delta_vs_old_B_ps'])
                    for corner,data in receipt['corners'].items()})
