"""Explicit, default-off control-reset pipeline for a bound hard partition.

Only ot_dp_st.rst_n epoch-control pins are eligible. Native hard-core reset,
PMA, data, epoch-input and START connections are preserved byte-for-byte.
The caller must publish the emitted tree through bound_reset_contract.
"""
import copy
import math
import re
import reset_consumers as RC
import reset_tree as RT

class ControlResetError(ValueError):
    pass

def apply(text, declaration, *, type_name, hard, outline, blocked_boxes=()):
    if not declaration:
        return text, None, None
    if not hard or not isinstance(declaration, dict):
        raise ControlResetError('control pipeline requires an explicit hard-type declaration')
    tree = copy.deepcopy(declaration.get('tree'))
    if not isinstance(tree, dict) or tree.get('type') != type_name:
        raise ControlResetError('control pipeline needs its matching explicit tree')
    if tree.get('entry') != 'relayed' or tree.get('sync_stages') != 2:
        raise ControlResetError('only an already synchronous delivered reset is supported')
    if any(tree.get(k) for k in ('start', 'lock', 'outs', 'core_resets', 'relay_driver', 'relay_lockup')):
        raise ControlResetError('control pipeline cannot alter START, native reset, or output reset contracts')
    if declaration.get('delivered_reset_net') != 'arst_n':
        raise ControlResetError('delivered reset must be the bound arst_n input')
    contract = declaration.get('cycle_contract', {})
    release = RT.release_clocks(tree)
    if (contract.get('extra_reset_cycles') != release or contract.get('steady_data_cycles') != 0
            or not isinstance(contract.get('start_guard_cycles'), int)
            or contract['start_guard_cycles'] < release + 1
            or not contract.get('source_witness')):
        raise ControlResetError('explicit reset delay, zero data delay and witnessed START guard are required')
    calls = RC._calls(text)
    if 'u_rst_in' in calls or re.search(r'\b(?:rst_root_n|rst_n_t\d+)\b', text):
        raise ControlResetError('existing reset tree cannot be silently replaced')
    if not re.search(r'\bwire\s+rst_n\s*=\s*arst_n\s*;', text):
        raise ControlResetError('expected delivered-reset alias missing')
    rows = tree.get('relays', [])
    taps = tree.get('taps', [])
    reach = tree.get('reach_um')
    if not rows or not taps or not isinstance(reach, (int, float)) or not 0 < reach <= 450:
        raise ControlResetError('explicit bounded reset topology and taps are required')
    def xy(point):
        if (not isinstance(point, (list, tuple)) or len(point) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in point)
                or not all(0 <= v <= extent for v, extent in zip(point, outline))):
            raise ControlResetError('reset placement outside outline')
        if any(box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3] for box in blocked_boxes):
            raise ControlResetError('reset placement overlaps a hard macro')
        return point
    root = xy(tree.get('root'))
    nodes = {'rst_root_n': (0, root)}
    names = set()
    pending = list(rows)
    while pending:
        progressed = False
        for row in pending[:]:
            q, d, name = row.get('q'), row.get('d'), row.get('name')
            if not all(isinstance(v, str) and re.fullmatch(r'[A-Za-z_]\w*', v) for v in (q,d,name)):
                raise ControlResetError('invalid reset node identifier')
            if q in nodes or name in names or name in calls:
                raise ControlResetError('duplicate reset node/instance')
            if d not in nodes:
                continue
            dep, prior = nodes[d]; point = xy(row.get('xy'))
            if row.get('depth') != dep + 1 or sum(abs(a-b) for a,b in zip(point, prior)) > reach:
                raise ControlResetError('reset depth or registered hop differs from declaration')
            nodes[q] = (dep + 1, point); names.add(name); pending.remove(row); progressed = True
        if not progressed:
            raise ControlResetError('missing or cyclic reset predecessor')
    for i, tap in enumerate(taps):
        if nodes.get(f'rst_n_t{i}') != (tree['depth'], xy(tap)):
            raise ControlResetError('tap coordinate or equal release depth differs')
    selected = declaration.get('consumers')
    if not isinstance(selected, dict) or not selected:
        raise ControlResetError('explicit epoch-control consumer mapping is required')
    sites = declaration.get('consumer_sites', {})
    if set(sites) != set(selected):
        raise ControlResetError('every selected epoch-control needs its explicit actual placement site')
    patches = []
    for name, tap in selected.items():
        call = calls.get(name)
        if not call or call['module'] != 'ot_dp_st':
            raise ControlResetError(f'{name}: only generated ot_dp_st epoch-control is eligible')
        ports = call['ports']
        if ports.get('clk', ('',))[0] != 'clk' or ports.get('rst_n', ('',))[0] != 'rst_n':
            raise ControlResetError(f'{name}: clock or original control reset differs')
        if tap not in {f'rst_n_t{i}' for i in range(len(taps))}:
            raise ControlResetError(f'{name}: unpublished tap')
        site = xy(sites[name])
        if sum(abs(a-b) for a,b in zip(site, nodes[tap][1])) > reach:
            raise ControlResetError(f'{name}: final control-reset hop exceeds bound')
        _, lo, hi = ports['rst_n']; patches.append((lo, hi, tap))
    for lo, hi, tap in sorted(patches, reverse=True):
        text = text[:lo] + tap + text[hi:]
    marker = re.search(r'\bwire\s+rst_n\s*=\s*arst_n\s*;[^\n]*', text)
    insert = '\n' + '\n'.join(RT.rtl_lines(tree)) + '\n'
    text = text[:marker.end()] + insert + text[marker.end():]
    return text, tree, {'type':type_name, 'consumers':selected, **contract,
                        'native_reset_changed':False, 'data_or_epoch_input_changed':False}
