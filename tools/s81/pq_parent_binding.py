#!/usr/bin/env python3
"""Source-bound production PQ sizing and explicit full-die candidate reservation.

Historical screen views never qualify this native partition. All emitted objects
are opt-in candidates; no selected generator defaults or headline are changed.
"""
import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(mapping, stage_map, expected_hash):
    """Count actual emitter words, interning only byte-identical stream bodies.

    Cache ignores only ROM base/word count and tensor identity: native_stream
    reads neither ROM addresses nor payload. Region/pair/order/stride stay exact.
    Both output rounding modes share stream words; PHROM rounding stays external.
    """
    from dsrom_s81_target_field_controls import native_stream
    if digest(mapping) != expected_hash:
        raise ValueError('mapping source hash mismatch')
    stages = json.loads(Path(stage_map).read_text())
    rows = {}
    cache = {}
    emitter_hash = None
    with gzip.open(mapping, 'rt') as f:
        for line in f:
            m = json.loads(line)
            s = m['stage']
            v = rows.setdefault(s, dict(KMAX=0, phase_count=0, bodies=set(), words=0))
            v['KMAX'] = max(v['KMAX'], m['K'])
            v['phase_count'] += 1
            key = (m['format'], m['K'], tuple(map(tuple, m['segments'])),
                   tuple(tuple(p[:5]) for p in m['plans']))
            if key not in cache:
                _, beats, emitter_hash = native_stream(m)
                body = b''.join(x.to_bytes(6, 'little') for x in beats)
                cache[key] = body
            body = cache[key]
            if body not in v['bodies']:
                v['bodies'].add(body)
                v['words'] += len(body) // 6
    result = []
    for s, v in sorted(rows.items()):
        phw = stages['PHW_required_by_stage'][s]
        if v['phase_count'] > 1 << phw:
            raise ValueError('phase count exceeds released mapping PHW')
        saw = max(1, (v['words'] - 1).bit_length())
        if saw > 16 or v['KMAX'] >= 8192:
            raise ValueError('native PHROM K13 or SBASE16 encoding exceeded')
        kmax = math.ceil(v['KMAX'] / 128) * 128
        # Actual source bb[2*KMAX]16, qb[2*KMAX/32]256, eb[...]10.
        state = 2*kmax*16 + 2*(kmax//32)*266
        result.append(dict(stage=s, PHW=phw, SAW=saw, KMAX=kmax,
            mapped_KMAX=v['KMAX'], phase_count=v['phase_count'],
            distinct_stream_bodies=len(v['bodies']), stream_words=v['words'],
            stream_capacity_words=1 << saw, operand_storage_bits=state,
            phase_ROM_logical_bits=(2 << phw)*64,
            stream_ROM_logical_bits=(1 << saw)*48,
            ROM_4096x72_macros=2*math.ceil((1 << phw)/4096)+math.ceil((1 << saw)/4096)))
    return dict(schema='opentallas.s81.pq-production-inventory.v1',
        mapping_sha256=expected_hash, stage_map_sha256=digest(stage_map),
        native_emitter_sha256=emitter_hash, stages=result,
        cache_patterns=len(cache), replicas_per_TP_die=1, regions_per_replica=128,
        ROM_ECC=False, mutable_storage_protection_required=True,
        stream_interning='Exact full48-bit byte strings; PHROM base relocation required, no arithmetic change',
        physical_adopted=False)


def native_ports(phw, saw, r=128, vaw=19, vrd=64):
    """Production partition exports one packed broadcast, not duplicate aliases."""
    groups = {
        'clock_reset': [('clk', 'input', 1), ('rst_n', 'input', 1)],
        'issuer': [('go','input',1),('i_ph','input',phw),('i_np','input',3),
                   *[(p,'input',vaw) for p in ('i_xbase','i_xps','i_obase','i_ops')],
                   ('i_fmt','input',2),('ready','output',1),('idle','output',1)],
        'VM_read': [('x_re','output',1),('x_addr','output',vaw),('x_q','input',vrd*32)],
        'VM_write': [('w_we','output',r),('w_addr','output',r*vaw),('w_data','output',r*32)],
        'field_return': [(p,'input',r*w) for p,w in
                         [('r_v',1),('r_row',16),('r_pos',3),('r_fp32',32),('r_bf16',16),('r_e',1)]],
        'field_broadcast': [('f_bus','output',1624+phw)],
        'fault_status': [('f_fault','input',1),('fault','output',1),('phase_cycles','output',32),
                         ('ev_go','output',1),('ev_end','output',1),('ev_tag','output',2)],
        'phase_ROM': [('rom_pa0','output',phw+1),('rom_pa1','output',phw+1),
                      ('rom_pq0','input',64),('rom_pq1','input',64)],
        'stream_ROM': [('rom_sa','output',saw),('rom_sq','input',48)]}
    return {p:dict(direction=d, bits=w, owner=g) for g, ps in groups.items() for p,d,w in ps}


def wrapper(parameters):
    ports = native_ports(parameters['PHW'], parameters['SAW'])
    declarations = [f"    {v['direction']} wire " +
                    (f"[{v['bits']-1}:0] " if v['bits']>1 else '')+p
                    for p,v in ports.items()]
    aliases = ('f_cfg_go f_cfg_ph f_cfg_np f_go f_go_bf f_go_tag f_xs_v f_xs_p f_xs_b '
               'f_xs_sv f_xs_q0 f_xs_e0 f_xs_q1 f_xs_e1 f_xs_pos f_xb_pos f_xb_v f_xb_b '
               'f_xb_sv f_xb_u f_xb_d').split()
    params = dict(PHW=parameters['PHW'], SAW=parameters['SAW'], KMAX=parameters['KMAX'],
                  R=128, VAW=19, VRD=64, PQ=1)
    return ('// Candidate native partition. Compile pinned native source with OT_PQ_ROM_PORTS.\n'
            '// External ROMs require real two-cycle macro adapters; no screen memory or quantiser stub.\n'
            'module ot_s81_pq_native_partition (\n'+',\n'.join(declarations)+'\n);\n'
            '  ot_v41_spine_pqc_w17w10 #( '+', '.join(f'.{k}({v})' for k,v in params.items())+' ) u_sp (\n'
            +',\n'.join('    .'+p+'('+p+')' for p in ports)+',\n'
            +',\n'.join('    .'+p+'()' for p in aliases)+'\n  );\nendmodule\n')


def def_pins(record, units=1000):
    """Import actual DEF signal pins; require explicitly supplied DEF units."""
    text = ''.join(record['pins'])
    pins = {}
    for block in re.split(r'\n\s*- ', '\n'+text)[1:]:
        if '+ USE POWER' in block or '+ USE GROUND' in block:
            continue
        name = block.split()[0].replace('\\', '')
        loc = re.search(r'\+ (?:PLACED|FIXED) \(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)', block)
        direction = re.search(r'\+ DIRECTION (\w+)', block)
        layer = re.search(r'\+ LAYER (\w+)', block)
        if not loc or not direction or not layer:
            raise ValueError('incomplete physical signal pin: '+name)
        pins[name] = dict(x_um=int(loc[1])/units,y_um=int(loc[2])/units,
                          direction=direction[1], layer=layer[1], orient=loc[3])
    return pins


def pin_contract(pins, ports):
    """Fail closed on any missing, extra or wrong-direction functional bit."""
    expected = {}
    for p, spec in ports.items():
        names = [p] if spec['bits'] == 1 else [f'{p}[{i}]' for i in range(spec['bits'])]
        expected.update({n: spec['direction'].upper() for n in names})
    missing = sorted(set(expected)-set(pins))
    extra = sorted(set(pins)-set(expected))
    wrong = sorted(n for n in set(expected)&set(pins) if expected[n] != pins[n]['direction'])
    return dict(PASS=not(missing or extra or wrong), missing=missing, extra=extra,
                wrong_direction=wrong, expected_bits=len(expected), actual_bits=len(pins))


def boundary_contract(phw=9):
    return dict(replicas_per_TP_die=1, regions=128,
        owner_by_port={p:v['owner'] for p,v in native_ports(phw,11).items()},
        old_parent=dict(broadcast_bits=564, raw_return_bits_per_region=68),
        production=dict(broadcast_bits=1624+phw, post_root_return_bits_per_region=69,
                        VM_read_bits_per_cycle=2048, VM_write_bits_per_cycle=128*52),
        required_functions=[
            '128 source-native ot_v41_ret_root instances: raw66-bit tree -> rounded69-bit return',
            'PHW9 config phase plus actual PQ tags and full BF1024-bit broadcast',
            'Actual protected VM read and 128 write-port arbitration/ownership',
            'Immutable PHROM/stream ROM macro adapters at actual two-cycle capture timing',
            'Source-matched registered stations and finite producer/consumer flow control'],
        old_broadcast_is_drop_in=False, old_return_is_drop_in=False,
        return_root_added_cycles='Use actual parent root placement; do not double count existing root stages',
        measured_composed_token_latency=None, physical_adopted=False)


def reservation(m, xy, size=550.368, corridor=100):
    """Explicit parent reservation; fail on occupied slots or retained channels.

    Adding a candidate does not give an unknown production cell area a fit PASS.
    Every generated parent instance and named routing reservation participates.
    """
    import dsrom_s81_fulldie as F
    x,y=xy
    rect=(x-corridor,y-corridor,x+size+corridor,y+size+corridor)
    def overlap(a,b): return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
    if rect[0]<0 or rect[1]<0 or rect[2]>F.DIE[0] or rect[3]>F.DIE[1]:
        raise ValueError('candidate and pin corridor outside die')
    hits=[it.name for it in m['insts'] if overlap(rect,it.box())]
    hits += [r['name'] for r in m['regions'] if r['kind'] in ('channel','soft_child_reservation') and overlap(rect,r['rect'])]
    if hits: raise ValueError('PQ reservation collides with '+','.join(hits[:12]))
    it=F.Inst('sp_pqc','ot_s81_pq_native_partition',x,y,size,size,
              kind='pq_candidate',region='pq_candidate',domain='stream_1p2')
    m['insts'].append(it)
    m['regions'].append(dict(name='pq_pin_corridor',kind='channel',rect=list(rect)))
    return dict(instance=it.d(),pin_corridor_um=list(rect),corridor_width_um=corridor,
        screen_only_area_um2=148012,station_area_um2=5173.261,
        production_mapped_area_um2=None, production_fit_qualified=False,
        clock=dict(period_ps=833.3333333333334,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
                   root='stream_1p2',actual_clock_arrival_required=True),
        routing=dict(final_pin_segment_max_um=100,nominal_register_hop_um=215,
                     source_bound_pin_geometry_required=True,capacity_qualified=False),
        adoption=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mapping',type=Path,required=True)
    ap.add_argument('--stage-map',type=Path,required=True)
    ap.add_argument('--sha256',required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    result=inventory(a.mapping,a.stage_map,a.sha256)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(stages=len(result['stages']),cache_patterns=result['cache_patterns'],
        PHW=max(s['PHW'] for s in result['stages']), SAW=max(s['SAW'] for s in result['stages']),
        KMAX=max(s['KMAX'] for s in result['stages']))))


if __name__=='__main__': main()
