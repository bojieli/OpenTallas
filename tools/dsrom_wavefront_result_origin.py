"""Add OLD pre-edge RESULT observation to already installed native WAVE ports.

RESULT carries user/position, not epoch. The source-owned accepted ledger must
resolve its retained generation/order. No controller scheduling or state edits.
"""
from pathlib import Path
import hashlib

ROLES = ('ot_chip_v41x_die_owner_safe_c8.sv', 'ot_v41_rt_die_l20_c8.sv', 'ot_rom_pkg_ctrl_wf_s81.sv')
PORTS = '''    // OLD registered RESULT processed at the upcoming edge, not current core user.
    output wire wf_result_v,
    output wire [9:0] wf_result_user,
    output wire [20:0] wf_result_pos,
    output wire wf_result_final,
'''


def _one(s, old, new):
    if s.count(old) != 1:
        raise ValueError('selected RESULT origin hook changed: ' + old)
    return s.replace(old, new, 1)


def controller(s):
    s = _one(s, 'module ot_rom_pkg_ctrl_wf_s81 #(', 'module ot_rom_pkg_ctrl_wf_s81_origin #(')
    s = _one(s, '    output wire               core_done_accepted,',
             '    output wire result_origin_valid,\n    output wire [USER_W-1:0] result_origin_user,\n    output wire [NW-1:0] result_origin_pos,\n    output wire result_origin_final,\n    output wire               core_done_accepted,')
    anchor = '    reg [31:0]   res_val;'
    return _one(s, anchor, anchor + '''
    assign result_origin_valid = WAVE && SOURCE && res_v;
    assign result_origin_user = res_u;
    assign result_origin_pos = res_p;
    assign result_origin_final = result_origin_valid && (red_n == RESULT_PARTS);
''')


def die(s):
    s = _one(s, ') (\n', ') (\n' + PORTS)
    s = _one(s, 'ot_rom_pkg_ctrl_wf_s81 #(', 'ot_rom_pkg_ctrl_wf_s81_origin #(')
    return _one(s, '        .core_done_accepted(wf_stage_accepted),',
                '''        .result_origin_valid(wf_result_v), .result_origin_user(wf_result_user),
        .result_origin_pos(wf_result_pos), .result_origin_final(wf_result_final),
        .core_done_accepted(wf_stage_accepted),''')


def top(s):
    s = _one(s, ') (\n', ') (\n' + PORTS)
    return _one(s, '        .wf_stage_accepted(wf_stage_accepted),',
                '''        .wf_result_v(wf_result_v), .wf_result_user(wf_result_user),
        .wf_result_pos(wf_result_pos), .wf_result_final(wf_result_final),
        .wf_stage_accepted(wf_stage_accepted),''')


def install(selected, output):
    """Layer after existing wavefront_install.install; do not duplicate it.

    Preserve inherited default-off parameters. Arch supplies non-consuming
    accepted-source lookup and owns all generation/result/cancel/fabric fences.
    No visibility/acceptance is inferred from this observational port bundle.
    """
    output = Path(output).resolve()
    paths = [Path(p).resolve() for p in selected['sources']]
    if any(output == p.parent or output in p.parents for p in paths):
        raise ValueError('output must be disjoint from selected native sources')
    originals = {}
    for p in paths:
        b = p.read_bytes()
        if hashlib.sha256(b).hexdigest() != selected['source_sha256'].get(str(p)):
            raise ValueError('selected source pin changed/missing: ' + str(p))
        originals[p] = b
    roles = {}
    for name in ROLES:
        candidates = [p for p in paths if p.name == name]
        if len(candidates) != 1:
            raise ValueError('missing/ambiguous selected WAVE role: ' + name)
        roles[name] = candidates[0]
    changed = {roles[n]: f(originals[roles[n]].decode()) for n, f in zip(ROLES, (die, top, controller))}
    dests = {p: output/'native'/('ot_rom_pkg_ctrl_wf_s81_origin.sv' if p.name == ROLES[2] else p.name) for p in changed}
    for p, dest in dests.items():
        if dest.exists() and dest.read_text() != changed[p]:
            raise FileExistsError('immutable output differs: ' + str(dest))
    if any(p.read_bytes() != b for p, b in originals.items()):
        raise ValueError('selected source changed during installation')
    for p, dest in dests.items():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists(): dest.write_text(changed[p])
    sources = [dests.get(p, p) for p in paths]
    result = dict(selected)
    result.update(sources=sources, source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  result_origin_preedge=True, result_origin_source='old res_v/res_u/res_p; actual final reduction compare',
                  result_origin_accepted_ledger_bound=False, result_origin_added_cycles=0,
                  result_origin_added_state_bits=0, physical_admission=False, measured_system_result=False)
    return result
