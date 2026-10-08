"""Library-only delay-cell screen for capture startup crossings; selects no depth."""
import gzip
import hashlib
import json
from pathlib import Path
import uarch_topk_station_SSFF_cell_model as lib

ROOT = Path(__file__).resolve().parents[1]
BASE = lib.BASE / 'inputs'
CELLS = ['BUFx2_ASAP7_75t_R', 'INVx1_ASAP7_75t_R', 'HB1xp67_ASAP7_75t_R', 'HB2xp67_ASAP7_75t_R', 'HB3xp67_ASAP7_75t_R', 'HB4xp67_ASAP7_75t_R']


def build():
    manifest = json.loads((lib.BASE / 'source_manifest.json').read_text())
    corners, pins = {}, {}
    for corner in ['SS', 'FF']:
        name = f'asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz'
        raw = (BASE / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != manifest[name]['sha256']:
            raise ValueError('Pinned library changed: ' + name)
        pins[str((BASE / name).relative_to(ROOT))] = digest
        text = gzip.decompress(raw).decode()
        corners[corner] = {n: lib.cell_facts(text, n) for n in CELLS}
    receiver_caps = {}
    for corner in ['SS', 'FF']:
        name = f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib'
        raw = (BASE / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != manifest[name]['sha256']:
            raise ValueError('Pinned receiver library changed: ' + name)
        pins[str((BASE / name).relative_to(ROOT))] = digest
        cell = lib.group(raw.decode(), 'cell', 'DFFHQNx1_ASAP7_75t_R')
        receiver_caps[corner] = lib.number(lib.group(cell, 'pin', 'D'), 'capacitance')
    rows = []
    for name in CELLS:
        ss, ff = corners['SS'][name], corners['FF'][name]
        tables = ff['delay_transition_tables']
        ff_min = min(v for k, t in tables.items() if k.startswith('cell_')
                     for row in t['values'] for v in row)
        load_floor = max(t['index2'][0] for k, t in tables.items() if k.startswith('cell_'))
        slew_floor = max(t['index1'][0] for k, t in tables.items() if k.startswith('cell_'))
        sweeps = []
        for slew in [20, 40, 80]:
            for load in [0.72, 1.44, 2.88]:
                vals = []
                for k, t in ss['delay_transition_tables'].items():
                    if not k.startswith('cell_'):
                        continue
                    if load < t['index2'][0]:
                        vals = []
                        break
                    cols = [i for i, x in enumerate(t['index2']) if x <= load]
                    rows_i = [i for i, x in enumerate(t['index1']) if x <= slew]
                    vals += [t['values'][i][j] for i in rows_i for j in cols]
                if vals:
                    # These ceilings are existing table indices; no extrapolation.
                    sweeps.append(dict(slew_ceiling_ps=slew, load_ceiling_fF=load,
                                       ss_cell_delay_upper_ps=max(vals)))
        rows.append(dict(master=name, area_um2=ss['area_um2'],
                         input_cap_fF={c: corners[c][name]['input_cap_fF']['A'] for c in corners},
                         ff_table_min_ps=ff_min,
                         ff_min_valid_only_with=dict(slew_at_least_ps=slew_floor,
                                                    load_at_least_fF=load_floor,
                                                    max_slew_ps=320,
                                                    load_not_above_characterized_max=True),
                         ss_sweeps=sweeps,
                         polarity='inverting: only even-length chains preserve logic' if name.startswith('INV') else 'noninverting'))
    wire_record = ROOT / 'results/uarch/topk_station_SSFF_cell_model_20261002/model_r3.json'
    wire = json.loads(wire_record.read_text())['wire_load']
    pins[str(wire_record.relative_to(ROOT))] = hashlib.sha256(wire_record.read_bytes()).hexdigest()
    return dict(schema='opentallas.s81.capture_startup_delay_screen.v1',
                status='LIBRARY_SCREEN_NO_DEPTH_SELECTED_NO_CLOSURE', source_sha256=pins,
                measured=dict(worst_ff_ps=-11.11, ff_gain_needed_ps=26.11,
                              worst_ss_ps=40.84, ss_spend_above_acceptance_ps=25.84,
                              note='Worst SS/FF are different roots. Endpoint-joined slacks needed.'),
                architecture=dict(cdc_instances=17, state_bits_per_direction=2, candidate_wires=68,
                                  incremental_cycles=0, arithmetic_change=False,
                                  cell_count='68 * depth only if all state arcs treated; prefer measured endpoint subset',
                                  area='sum actual selected cell counts * cell area; routing not yet measured'),
                cells=rows, receiver_D_cap_fF=receiver_caps,
                routing=dict(layer_cap_fF_per_um=wire['RC_capacitance_fF_per_um'],
                             layer_resistance_kohm_per_um=wire['RC_resistance_kohm_per_um'],
                             bound_formula='length <= (load_ceiling - receiver_cap - via/coupling_cap)/max_wire_cap_per_um',
                             minimum_delay='No wire delay credited to hold; require actual characterized load and slew floor.',
                             limitations='RC template excludes coupling/via capacitance. Fresh extracted STA required.'),
                decision='Do not select depth from aggregate slack. Join SS and FF for each startup endpoint, then propagate slew/load across candidate chain and verify routed fresh STA.')


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
