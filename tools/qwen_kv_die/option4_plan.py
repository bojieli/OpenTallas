#!/usr/bin/env python3
"""Source-pinned option-4 integration sizing; no change to released die recipes.

This checks the COLLECT port map against the actual master boundaries before
building a die. A geometry fit alone does not authorize physical adoption.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def ports(path, module):
    text = re.sub(r'//[^\n]*', '', path.read_text())
    match = re.search(r'module\s+' + module + r'\b.*?\);', text, re.S)
    if not match:
        raise ValueError(module)
    return set(re.findall(r'(?:input|output)\s+(?:wire|reg)?\s*(?:\[[^\]]*\])?\s*(\w+)', match.group()))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan():
    source = ROOT / 'results/arch/qwen_kv_die_20261009/rom_r22k_insts.json'
    raw = json.loads(source.read_text())
    instances = [dict(name=i[0], master=i[1], kind=i[2], x=i[3], y=i[4], w=i[5], h=i[6]) for i in raw['insts']]
    by = {i['name']: i for i in instances}
    tt, sq, su = (by[n] for n in ('sp_tree_top', 'sp_constants_sequencer', 'sp_su64_sfu'))
    slot = dict(tt)
    removed = ['sp_tree_top', 'sp_constants_sequencer']
    kept = [i for i in instances if i['name'] not in removed]
    proposed = [dict(name='tt_ctlm', master='qfd_tt_ctlm_a', kind='candidate', x=tt['x'], y=tt['y'], w=777.6, h=1814.4)]
    for u in range(4):
        proposed.append(dict(name=f'tt_up4_{u}', master='qfd_tt_up4_b', kind='candidate', x=tt['x'],
                             y=tt['y'] + 1814.4 + 2.16 + u * (388.8 + 2.16), w=345.6, h=388.8))
    east = by['sp_port_tiles_2_f1']
    # Leave one 2.16-um frame row below the port slab; the proposed COLLECT
    # y=11604..12122 overlaps this slab, whose S boundary is 12115.44 um.
    proposed.append(dict(name='seq_su', master='qfd_seq_su_boundary', kind='candidate', x=east['x'],
                         y=round(east['y'] - 518.4 - 2.16, 3), w=518.4, h=518.4))
    proposed.append(dict(name='sp_crom', master='qfd_crom_g_a', kind='candidate', x=sq['x'], y=sq['y'], w=777.6, h=1000.0))
    overlaps = []
    for i, a in enumerate(kept + proposed):
        for b in (kept + proposed)[i + 1:]:
            if min(a['x'] + a['w'], b['x'] + b['w']) > max(a['x'], b['x']) + .03 and min(a['y'] + a['h'], b['y'] + b['h']) > max(a['y'], b['y']) + .03:
                overlaps.append([a['name'], b['name']])
    seq_file = ROOT / 'rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su.sv'
    seq_ports = ports(seq_file, 'ot_qfd_seq_su')
    # Required die outputs; direction is explicit because an x_oacc input
    # cannot serve as the SU accepted-operation-count output.
    outputs = {'su_snapshot': {'x_sacc': 24, 'x_sidle': 1, 'x_sprog': 16, 'x_srows': 16},
               'me_layer_start': {'me_start': 1, 'me_token': 18, 'me_pos': 18, 'me_prog_base': 12}}
    missing = {group: [name for name in ps if name not in seq_ports] for group, ps in outputs.items()}
    upper_file = ROOT / 'physical/qwen_die_masters/cfg/qfd_tt_up4_b.env'
    ctl_file = ROOT / 'physical/qwen_die_masters/cfg/qfd_tt_ctlm_a.env'
    cbuf_file = ROOT / 'physical/qwen_die_masters/cfg/qfd_su_cbuf_g_a.env'
    seq_new = proposed[5]
    ctl = proposed[0]
    # Lower bounds only: using the facing S and W boundaries, before relay
    # placement, output/input pin offsets, CTS, lockups and channel detours.
    pin_dist = abs(seq_new['x'] - (ctl['x'] + ctl['w'] / 2)) + abs(seq_new['y'] + seq_new['h'] / 2 - ctl['y'])
    return dict(schema='opentallas.qwen.option4-integration-sizing.v1',
                scope='candidate sizing from rounded committed rectangles and interface audit; not a routed closure or complete electrical die',
                sources={str(p.relative_to(ROOT)): sha(p) for p in (source, seq_file, upper_file, ctl_file, cbuf_file)},
                die_um=raw['die'], old_tree_slot=slot, removed=removed, candidates=proposed,
                geometry_overlaps=overlaps, geometry_ok=not overlaps,
                model=dict(clock_hz=1200000000, macs_per_cycle_delta=0, replicas={'ctlm': 1, 'up4': 4, 'seq_su': 1, 'cbuf_g': 8},
                           added_seq_output_bits=sum(sum(ps.values()) for ps in outputs.values()),
                           required_endpoint_accepted_count_bits=24, output_pipeline_cycles=1,
                           output_pipeline_flops=106, snapshot_bits_per_cycle={'su_to_me':57, 'me_to_su':92},
                           snapshot_pin_distance_lower_bound_um=round(pin_dist, 2),
                           snapshot_relay_cycles_lower_bound=max(0, math.ceil(pin_dist / 430.56) - 1),
                           assumption='Lower bound is not a priced token gain; actual relay chains and exact component latency are required.'),
                old_to_new_ports=dict(si='removed; ME controller inside ctlm', so='removed; ME snapshot92bits to seq_su',
                                     md='removed; END carried by ME snapshot',
                                     c='ctlm t_sel/t_tv, port issue and per-band scale slices',
                                     f='ctlm per-band p_am/p_fault/tr_fault slices', lc='ctlm selects',
                                     bw='four tiles: lane4u+j -> pw[32*(4*b+j)+:32]; same band valid to all four',
                                     lf='all six band faults to every upper tile',
                                     ty='tile u, word k,j -> lane4u+j; valid/use from tile0',
                                     mx='ctlm -> VM', xd='ctlm -> VM', xr='VM -> ctlm', ld='VM -> ctlm'),
                missing_seq_outputs=missing,
                blockers=[
                    'Released seq_su omits the SU snapshot and per-layer ME start outputs. Successor is required.',
                    'SU acceptance counter must be captured at actual endpoint acceptance and align with idle/progress; controller issue count is insufficient.',
                    'up4 closed view has LNK=0/CR=1/DLY=1; die band-word relays must be discovered before matching DLY=CLNK+2+LNK-CR.',
                    'ctlm module does not expose die LNK/CLNK parameters; successor must match composed band-control latency.',
                    'Eight 194.4-um cbuf groups span 1555.2 um, exceeding the 777.58-um SU width; VM abuts the SU N face. New constant-store geometry and SU pin plan required.',
                    'seq_su east slot is adjusted below the port slab to avoid a 7-um overlap in the handoff coordinates.',
                    'Master abstractions must bind real RTL slices and pass hub routing-layer and pin-access checks before adoption.'
                ], ready_to_build_die=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = plan()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('geometry_ok','geometry_overlaps','missing_seq_outputs','ready_to_build_die')}))


if __name__ == '__main__':
    main()
