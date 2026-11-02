"""Emit opt-in native clock pose/ownership data; never changes a kit or dispatches CAD.

Runtime is exact_native_clock.tcl. A model is geometry PREP, not native CTS or
PG qualification. Every original typed clock endpoint must be named once.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, math
from pathlib import Path


def load(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw)


def word(value):
    value = str(value)
    if '\n' in value or '\r' in value or '\x00' in value:
        raise ValueError('native identity contains a control character')
    return '"' + ''.join('\\' + c if c in '\\"$[]' else c for c in value) + '"'


def record(values):
    return '[list ' + ' '.join(word(v) for v in values) + ']'


def emit(model, source_map, outline_model, model_sha256=None):
    model_sha256 = model_sha256 or hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()
    if model.get('status') != 'DISABLED_NATIVE_INTERNAL_CLOCK_GEOMETRY_PREP':
        raise ValueError('requires a disabled native clock geometry model')
    if 'full BUFx24 Y output metal' not in model.get('radius_metric', ''):
        raise ValueError('requires actual buffer-output pin metric, not centre anchors')
    sinks, roots = model['sinks'], model['roots']
    if len(sinks) != len(source_map) or not roots:
        raise ValueError('incomplete native clock inventory')
    if model['outline_um'] != outline_model['outline_um']:
        raise ValueError('outline mismatch')
    counts = model['native_sinks']
    if counts['total'] != len(sinks) or counts['FF'] + counts['SRAM'] != len(sinks):
        raise ValueError('typed inventory count mismatch')
    budget = model['budget_ps']
    if budget['TT'] != 250 or budget['FF'] != 202.5:
        raise ValueError('native 250/202.5 budget changed')
    owner, names, root_rows = {}, set(), []
    for j, root in enumerate(roots):
        if root['reserved_master'] != 'BUFx24_ASAP7_75t_R':
            raise ValueError('unqualified native root master')
        box = root['reservation_um']
        if len(box) != 4 or any(not math.isfinite(v) for v in box):
            raise ValueError('invalid root rectangle')
        if abs(box[2]-box[0]-1.62) > 1e-8 or abs(box[3]-box[1]-.27) > 1e-8:
            raise ValueError('root body size mismatch')
        w,h=model['outline_um']
        if not (4.32 <= box[0] < box[2] <= w-4.32 and 4.32 <= box[1] < box[3] <= h-4.32):
            raise ValueError('root body outside native core frame')
        if any(abs(v/p-round(v/p))>1e-7 for v,p in ((box[0],2.16),(box[1],.27))):
            raise ValueError('root body lower-left outside native planned row grid')
        ids = root['sink_indices']
        if not ids or len(ids) != root['sink_count'] or len(ids) > 1500:
            raise ValueError('empty/count-mismatched/overloaded planned local root')
        x,y=root['xy_um']
        if abs(x-(box[0]+box[2])/2)>1e-8 or abs(y-(box[1]+box[3])/2)>1e-8:
            raise ValueError('root centre and body disagree')
        for i in ids:
            if i in owner or not 0 <= i < len(sinks):
                raise ValueError('duplicate or invalid sink ownership')
            owner[i] = j
            p=sinks[i]['rect_um']
            if len(p)!=4 or any(not math.isfinite(v) for v in p):
                raise ValueError('invalid native clock pin rectangle')
            actual=max(abs(p[a]-(x+dx))+abs(p[b]-(y+dy))
                       for a in (0,2) for b in (1,3)
                       for dx in (-.5,.792) for dy in (-.108,.108))
            if actual > 220 + 1e-6:
                raise ValueError('actual output-to-clock pin radius exceeds 220')
        reservation_name = root.get('name',f'regional_{j}')
        root_rows.append(record([f'ot_exact_native_clk_{j}', root['reserved_master'], *box, model_sha256+':'+reservation_name]))
    if set(owner) != set(range(len(sinks))):
        raise ValueError('unassigned native clock sink')
    sink_rows=[];normalized_names=set()
    norm=lambda s:s.replace('\\','').strip()
    for i,(sink,source) in enumerate(zip(sinks,source_map)):
        if (norm(source['instance']),source['kind'],source['pin']) != (sink['instance'],sink['kind'],sink['pin']):
            raise ValueError('actual typed source identity mismatch')
        if source['source_clock_port'] != 'clk' or source['actual_net'] != 'clk':
            raise ValueError('multiple or aliased source clocks')
        key=(source['instance'],source['pin'])
        normalized=(norm(source['instance']),source['pin'])
        if key in names or normalized in normalized_names:
            raise ValueError('duplicate actual native pin identity')
        names.add(key);normalized_names.add(normalized)
        sink_rows.append(record([source['instance'],source['master'],source['pin'],source['kind'],owner[i],*sink['rect_um']]))
    actual_sram_names={norm(s['instance']):s['instance'] for s in source_map if s['kind']=='SRAM'}
    if set(actual_sram_names) != {norm(m['name']) for m in outline_model['macros']}:
        raise ValueError('macro geometry/source identity mismatch')
    macros=[record([actual_sram_names[norm(m['name'])],*m['rect_um']]) for m in outline_model['macros']]
    if len(macros) != counts['SRAM']:
        raise ValueError('actual SRAM count mismatch')
    def rows(name,values):
        sep = ' ' + chr(92) + chr(10) + '  '
        return f'\nset ::ot_enc_{name} [list' + sep + sep.join(values) + ']\n'
    # No source, clock connection, kit generation, or CAD call is emitted.
    return ('# Generated exact native clock PREP data. Loading this file mutates no ODB.\n'
            'set ::ot_enc_schema "opentallas.exact_native_clock.prep.v1"\n'
            f'set ::ot_enc_model_sha256 {word(model_sha256)}\n'
            f'set ::ot_enc_outline {record(model["outline_um"])}\n'
            f'set ::ot_enc_expected_ff {counts["FF"]}\n'
            f'set ::ot_enc_expected_sram {counts["SRAM"]}\n'
            f'set ::ot_enc_root_island {record(model["entry_island_um"])}\n'
            'set ::ot_enc_entries [list ' + ' '.join(record([name,*entry['rect_um']]) for name,entry in model['entry'].items()) + ']\n'
            'set ::ot_enc_radius_um 220\n'
            'set ::ot_enc_tt_ps 250\nset ::ot_enc_ff_ps 202.5\n'
            + rows('roots',root_rows)+rows('sinks',sink_rows)+rows('macros',macros))


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--clock-model',required=True);a.add_argument('--source-map',required=True)
    a.add_argument('--outline-model',required=True);a.add_argument('--out',required=True)
    n=a.parse_args()
    raw=Path(n.clock_model).read_bytes()
    if raw[:2]==b'\x1f\x8b':raw=gzip.decompress(raw)
    result=emit(load(n.clock_model),load(n.source_map),load(n.outline_model),hashlib.sha256(raw).hexdigest())
    Path(n.out).write_text(result)
    print(json.dumps(dict(status='DISABLED_EXACT_NATIVE_CLOCK_CONSUMER_DATA_PREP',sha256=hashlib.sha256(result.encode()).hexdigest(),out=n.out)))


if __name__=='__main__':main()
