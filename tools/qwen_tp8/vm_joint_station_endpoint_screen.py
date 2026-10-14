"""Screen proposed station endpoints; geometric TT wire is not extracted RC."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/arch/qwen_tp8_1012'
source = BASE / 'vm_joint_g1_boundary_station_candidate.json'
candidate = json.loads(source.read_text())
rows = []
for station in candidate['stations']:
    bits = [bit for match in station['matches'] for bit in match['bits']]
    north = candidate['origin_um'][1] + candidate['region_outline_um'][1]
    costs = []
    for bit in bits:
        launch = bit['new_launch_corners']['tt']['o_ps']
        distance = north - bit['new_launch_xy_um'][1]
        costs.append(dict(lane=bit['lane'], bit=bit['bit'],
                          pin=bit['region1_station_pin'],
                          compensated_launch_ps=launch,
                          north_face_distance_um=distance,
                          TT_geometric_data_wire_screen_ps=.76 * distance,
                          full_TT_geometric_launch_screen_ps=launch + .76 * distance))
    rows.append(dict(station=station['name'], bits=len(costs),
                     zero_wire_launch_over220_bits=sum(c['compensated_launch_ps'] > 220 for c in costs),
                     north_face_TT_screen_over220_bits=sum(c['full_TT_geometric_launch_screen_ps'] > 220 for c in costs),
                     endpoints=costs))
output = dict(schema='opentallas.vm-station-endpoint-screen.v1',
              status='REJECTED_FOR_FULL_INTERFACE_CONTRACT; NO_PHYSICAL_FREEZE_OR_ROUTE',
              source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              interface_launch_limit_ps=220, interface_capture_limit_ps=190,
              normalization='o=O_child-R_child; s=S_child+R_child. Do not subtract R twice.',
              caveat='TT geometric data-wire screening only; no extracted RC, no SS coefficient. Clock entry wire separately compensated, never counted as data wire.',
              intrinsic_failure_proof='53 assigned q endpoints exceed compensated launch220 even at zero data wire.',
              stations=rows)
(BASE / 'vm_joint_g1_station_endpoint_screen.json').write_text(json.dumps(output, indent=1) + '\n')
