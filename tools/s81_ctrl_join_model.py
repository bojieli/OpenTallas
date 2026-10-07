"""Pinned, model-before-generator accounting for the S81 ctrl/service join."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TILE = '3f0455126'
BASE = 'bac833b4a'
PORTS = {'rq': 341, 'rk': 1, 'wd': 1, 'r_data': 256, 'r_tag': 17, 'r_beat': 4, 'rv': 1}


def read(ref, path):
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT)


def model():
    pins = {}
    def source(ref, path):
        data = read(ref, path)
        full = subprocess.check_output(['git', 'rev-parse', ref], cwd=ROOT, text=True).strip()
        pins[f'{full}:{path}'] = hashlib.sha256(data).hexdigest()
        return data
    records = {}
    for kind in ('ctrl', 'svc'):
        path = f'physical/s81_ph_views/ports/contract/dsfd_{kind}_pc/ports.json'
        records[kind] = json.loads(source(TILE, path))
    capacity = {}
    for kind, rec in records.items():
        selected = [pin for port in PORTS for pin in rec['ports'][port]['pins']]
        for port, width in PORTS.items():
            assert len(rec['ports'][port]['pins']) == width
        assert len(selected) == 621
        for p in selected:
            assert p[1] == 'M5' and 0 <= p[2] < p[4] <= rec['w_um']
            assert abs(((p[2]+p[4])/2-.012)/.048-round(((p[2]+p[4])/2-.012)/.048)) < 1e-6
        assert len({(p[1], p[2], p[4]) for p in selected}) == 621
        capacity[kind] = dict(face='N' if kind == 'ctrl' else 'S', width_um=rec['w_um'],
            height_um=rec['h_um'], registered_interface_pins=621,
            required_signal_tracks=621, two_track_pin_spacing_demand=1242, grid_pitch_um=.048,
            geometric_M5_track_sites=2522, occupied_pin_pitch_um=.096,
            interface_min_x_um=min(p[2] for p in selected), interface_max_x_um=max(p[4] for p in selected),
            physical_routing_capacity=None, note='2522 grid centres fit the outline; not a routed capacity or spare-pin authorization')
    for port in PORTS:
        for c, s in zip(records['ctrl']['ports'][port]['pins'], records['svc']['ports'][port]['pins']):
            assert c[1:3] == s[1:3] and c[4] == s[4]
    comp = json.loads(source(TILE, 'physical/s81_ph_views/svc/composition.json'))
    source(TILE, 'physical/s81_ph_views/ctrl/composition.json')
    source(TILE, 'rtl/dsrom_sys/s81_ph/dsfd_ctrl.sv')
    source(TILE, 'rtl/dsrom_sys/s81_ph/svc/dsfd_svc_pc.sv')
    source(TILE, 'rtl/dsrom_sys/s81_ph/ctrl/dsfd_ctrl_pc.sv')
    source(TILE, 'rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io_tiles.sv')
    source(BASE, 'rtl/common/ot_fwd_link_stage.sv')
    source('24f79a4b8', 'tools/s81_ph_boundary_bindings.py')
    source(BASE, 'tools/dsrom_s81_fulldie.py')
    source(BASE, 'tools/uarch_model.py')
    source(BASE, 'tools/dsrom_s81_unified_components.py')
    return dict(schema='opentallas.s81.ctrl_join_model.v1', source_sha256=pins,
        status='PIN_FIT_PASS_SERVICE_TOP_MISSING', default_enabled=False,
        PCs_per_stack=32, stacks=4, interface_bits_per_PC=621,
        per_stack_bits=dict(rd=8896, rq=10912, rk=32, wd=32),
        per_stack_bits_per_cycle=dict(ctrl_to_svc=8960, svc_to_ctrl=10912),
        per_stack_data_bytes_per_cycle=1024, per_die_interface_bits=79488,
        missing_v6_bits_per_stack=11008, missing_v6_bits_per_die=44032,
        endpoint_capacity=capacity, new_tile_pins=0, new_MACs=0, new_memories=0,
        added_muxes=0, added_demuxes=0, signal_fanout=1, new_flops=0,
        new_area_um2=0, added_cycles_from_wiring=0,
        inherited_service_register_cycles_each_way=1, inherited_credit_round_trip_cycles=2,
        inherited_price_source=comp['cost'],
        unified_token_model_explicitly_binds_this_link=False,
        exposed_token_delta_cycles=None,
        token_composition='Use actual exposed PC traversals * existing one-cycle service cut in each direction; overlap/credit waits unknown. Do not add a second register or claim a rate.',
        receiver_arrivals_ps=None, delay_budgets_ps=None, timing_closure=False,
        blockers=['Pinned tree has no executable dsfd_svc top or quadrant-to-PC composition; do not replace it with an empty slab.',
                  'Unified model has no explicit selected ctrl/service traversal binding; inherited composition cost is not measured per-token latency.',
                  'SS/FF die-context timing and routed channel capacity remain unmeasured.'])


if __name__ == '__main__':
    print(json.dumps(model(), indent=2, sort_keys=True))
