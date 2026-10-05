"""Additive WAVE controller wiring after the actual S81 capture installer.

Arch owns the stage caller: this helper never replaces C8 request/restore logic.
No array qualification or physical admission is implied by installing ports.
"""
from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / 'rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv'
CONTROLLER_SHA = '12843b3de997ca12acc76a36b7b11a29f174575b8d9bc6edc780effa4f108cbe'
ROLES = ('ot_chip_v41x_die_owner_safe_c8.sv', 'ot_v41_rt_die_l20_c8.sv')
PKG_DEFAULTS = dict(PKG_ID=0, MAXU=866, SOURCE=0, RESULT_PARTS=1,
                    SEND_HIDDEN=0, HID_DEST=0, SEND_RESULT=0, RES_DEST=0,
                    COMBINE_IN=0, ROW0=0, FWD_TOKEN=1)

COMMON_PORTS = '''
    // Actual whole-stage caller result; hold done/data until wf_stage_accepted is sampled high.
    // A fragment c8_retire_v is NOT whole-stage completion.
    input wire wf_stage_done,
    output wire wf_stage_accepted,
    input wire [20:0] wf_stage_next_token,
    input wire [31:0] wf_stage_next_val,
    output wire wf_request,
    output wire [20:0] wf_token,wf_pos,
    output wire [9:0] wf_user,
    output wire wf_busy,
    output wire [3:0] wf_pr_blk,
    input wire wf_pr_qk,
    output wire wf_issue,wf_reject,wf_squash,
'''


def _one(s, old, new):
    if s.count(old) != 1:
        raise ValueError('selected S81 hook changed: ' + old)
    return s.replace(old, new, 1)


def _connection(s, name, expression):
    pattern = r'\.' + re.escape(name) + r'\([^()]*\)'
    s, n = re.subn(pattern, lambda _: '.' + name + '(' + expression + ')', s)
    if n != 1:
        raise ValueError('selected top port changed: ' + name)
    return s


def controller_adapter(s):
    # Export the ACTUAL source acceptance, without duplicating state or its test.
    s = _one(s, 'module ot_rom_pkg_ctrl_wf #(', 'module ot_rom_pkg_ctrl_wf_s81 #(')
    s = _one(s, '    output wire               core_busy,',
             '    output wire               core_done_accepted,\n    output wire               core_busy,')
    line = '    wire job_done = running && core_done && tx_st == T_IDLE && !rd_inflight && (txq_n + 2 <= TXQ);'
    return _one(s, line, line + '\n    assign core_done_accepted = WAVE && job_done;')


def wire_die(s):
    s = _one(s, '    parameter integer PKG_ID   = 0,',
             '    parameter integer PKG_WAVE=0,\n    parameter integer PKG_WAVE_WIN=6,\n    parameter integer PKG_ID   = 0,')
    s = _one(s, ') (\n', ') (\n' + COMMON_PORTS)
    # Keep the entire canonical C8/capture/journal/VM path unchanged.
    s = _one(s, '    ot_rom_pkg_ctrl_x #(',
             '''    assign wf_request = PKG_WAVE && c_start;
    assign wf_token = c_token;
    assign wf_pos = c_pos;
    assign wf_user = c_user;
    assign wf_busy = PKG_WAVE && ctrl_busy;
    // Local mutable-state visibility comes from the actual selected journals.
    // Arch must additionally provide the full-stage/index-visible completion.
    wire wf_result_visible = c8_write_quiet && !c8_write_quarantine &&
                             !c8_write_fault && !coll_busy;
    ot_rom_pkg_ctrl_wf_s81 #(.WAVE(PKG_WAVE), .WIN(PKG_WAVE_WIN), ''')
    s = _one(s, ".core_done(host_mode ? 1'b0 : core_done)",
             ".core_done(PKG_WAVE ? (wf_stage_done && wf_result_visible) : (host_mode ? 1'b0 : core_done))")
    s = _one(s, '.core_next_token(core_next_token), .core_next_val(core_next_val)',
             '.core_next_token(PKG_WAVE ? wf_stage_next_token : core_next_token), .core_next_val(PKG_WAVE ? wf_stage_next_val : core_next_val)')
    s = _one(s, '.pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),',
             '.pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),\n        .core_done_accepted(wf_stage_accepted),\n        .pr_blk(wf_pr_blk), .pr_qk(PKG_WAVE && wf_pr_qk),\n        .wf_issue(wf_issue), .wf_reject(wf_reject), .wf_squash(wf_squash),')
    return s


def wire_top(s, die):
    params = '    parameter integer PKG_WAVE=0,\n    parameter integer PKG_WAVE_WIN=6,\n'
    params += ''.join('    parameter integer ' + k + '=' + str(v) + ',\n' for k, v in PKG_DEFAULTS.items())
    s = _one(s, '    parameter integer COLL_ACCEPTED_POP=0,', params + '    parameter integer COLL_ACCEPTED_POP=0,')
    # Existing die ports, prefixed at the wrapper. Fixed full-shape widths.
    names = ['cfg_users', 'cfg_prompt_len', 'cfg_gen_len', 'pr_re', 'pr_user',
             'pr_pos', 'pr_q', 'tok_valid', 'tok_user', 'tok_pos', 'tok_id',
             'users_done', 'rcfg_we', 'rcfg_dest', 'rcfg_mask']
    names += [link + '_' + tail for link in ('ucie', 'bl') for tail in
              ('tx_valid', 'tx_ready', 'tx_data', 'tx_last', 'rx_valid', 'rx_ready', 'rx_data', 'rx_last')]
    declarations = []
    for name in names:
        pattern = r'^    (?:input|output)\s+wire\s+.*?\b' + name + r'\s*,.*$'
        matches = re.findall(pattern, die, re.M)
        if len(matches) != 1:
            raise ValueError('die declaration changed: ' + name)
        decl = matches[0].split('//')[0].rstrip()
        decl = decl.replace('(FULL_SHAPE ? 10 : 8)', '10').replace('(FULL_SHAPE ? 21 : 16)', '21')
        decl = re.sub(r'\b' + name + r'\b', 'wf_' + name, decl)
        declarations.append(decl + '\n')
    s = _one(s, ') (\n', ') (\n' + COMMON_PORTS + ''.join(declarations))
    forwarded = '.PKG_WAVE(PKG_WAVE), .PKG_WAVE_WIN(PKG_WAVE_WIN), ' + ', '.join('.'+k+'('+k+')' for k in PKG_DEFAULTS) + ', '
    s = _one(s, 'ot_chip_v41x_die_owner_safe_c8 #(', 'ot_chip_v41x_die_owner_safe_c8 #(' + forwarded)
    s = _one(s, '.host_mode(1\'b1),', '.host_mode(1\'b1),\n' + ''.join('        .'+n+'('+n+'),\n' for n in
             ('wf_stage_done','wf_stage_accepted','wf_stage_next_token','wf_stage_next_val','wf_request','wf_token','wf_pos','wf_user','wf_busy','wf_pr_blk','wf_pr_qk','wf_issue','wf_reject','wf_squash')))
    for name in names:
        is_input = any(re.match(r'    input\s', d) and re.search(r'\bwf_'+name+r'\b', d) for d in declarations)
        if is_input:
            original = re.findall(r'\.'+name+r'\(([^()]*)\)', s)
            if len(original) != 1:
                raise ValueError('top input hook changed: ' + name)
            expr = 'PKG_WAVE ? wf_' + name + ' : ' + original[0]
        else:
            expr = 'wf_' + name
        s = _connection(s, name, expr)
    return s


def install(selected, output, *, enable=False, win=6):
    """Layer on system_sources.install(... capture/workspace/accepted_pop=True).

    Caller joins wf_request to the existing C8 context offer; host_mode stays 1.
    core_user registers on the request edge: sample wf_user after that edge.
    Hold wf_stage_done and result data until wf_stage_accepted at the edge; TX backpressure and
    actual local visibility may defer consumption. Squash/reissue must invalidate
    downstream speculative contexts and K/V/index visibility by source identity.
    Neither local quiet nor a C8 fragment retire proves full-stage completion.
    """
    if type(enable) is not bool or type(win) is not int or not 1 <= win <= 15:
        raise ValueError('enable must be bool and win an integer 1..15')
    parameters = selected.get('parameters', {})
    for key in ('S81_CAPTURE', 'S81_HOST_WORKSPACE', 'COLL_ACCEPTED_POP', 'C8_CONTEXT', 'C8_PUBLICATION'):
        if parameters.get(key) != 1:
            raise ValueError('actual selected source requires ' + key + '=1')
    if selected.get('head_candidate_selected', False):
        raise ValueError('rejected head candidate must stay off')
    paths = [Path(p).resolve() for p in selected['sources']]
    output = Path(output).resolve()
    if any(output == p.parent or output in p.parents for p in paths):
        raise ValueError('output must be disjoint from selected source inputs')
    if hashlib.sha256(CONTROLLER.read_bytes()).hexdigest() != CONTROLLER_SHA:
        raise ValueError('qualified WAVE controller pin changed')
    originals = {}
    pins = selected.get('source_sha256', {})
    for p in paths:
        b = p.read_bytes()
        if str(p) not in pins or hashlib.sha256(b).hexdigest() != pins[str(p)]:
            raise ValueError('selected source pin missing/changed: ' + str(p))
        originals[p] = b
    roles = {}
    for role in ROLES:
        matches = [p for p in paths if p.name == role]
        if len(matches) != 1:
            raise ValueError('missing/ambiguous selected role: ' + role)
        roles[role] = matches[0]
    die = originals[roles[ROLES[0]]].decode()
    changed = {roles[ROLES[0]]: wire_die(die),
               roles[ROLES[1]]: wire_top(originals[roles[ROLES[1]]].decode(), die)}
    destinations = {p: output/'native'/p.name for p in changed}
    adapter = output/'native/ot_rom_pkg_ctrl_wf_s81.sv'
    adapter_text = controller_adapter(CONTROLLER.read_text())
    if adapter.exists() and adapter.read_text() != adapter_text:
        raise FileExistsError('immutable controller adapter differs: ' + str(adapter))
    # Preflight all outputs before creating any file. Existing outputs immutable.
    for p, dest in destinations.items():
        if dest.exists() and dest.read_text() != changed[p]:
            raise FileExistsError('immutable output differs: ' + str(dest))
    if any(p.read_bytes() != b for p, b in originals.items()):
        raise ValueError('source changed during installation')
    for p, dest in destinations.items():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_text(changed[p])
    adapter.parent.mkdir(parents=True, exist_ok=True)
    if not adapter.exists():
        adapter.write_text(adapter_text)
    sources = [destinations.get(p, p) for p in paths]
    sources.append(adapter)
    result = dict(selected)
    result.update(sources=sources,
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  parameters=dict(parameters, PKG_WAVE=int(enable), PKG_WAVE_WIN=win),
                  verilator_args=list(selected.get('verilator_args', [])) +
                                 ['-GPKG_WAVE='+str(int(enable)), '-GPKG_WAVE_WIN='+str(win)],
                  wavefront_request_to_C8_bound=False, whole_stage_result_source_required=True,
                  wavefront_controller_sha256=CONTROLLER_SHA, wavefront_added_state_bits=0,
                  wavefront_added_pipeline_cycles=0, physical_admission=False,
                  measured_system_result=False)
    return result
