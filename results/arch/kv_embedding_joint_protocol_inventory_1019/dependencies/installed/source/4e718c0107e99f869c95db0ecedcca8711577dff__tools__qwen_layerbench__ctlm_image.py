#!/usr/bin/env python3
"""ctlm_image: compiler of the qfd_tt_ctlm_dv deployment image (PW0..1023 + DW0..7) from the static schedule (QLB-PROG 10-18,
layer-bench gap G-C3).

ONE image is installed per epoch (qfd_sys_face replays its config-ROM rows 0..1031 once, after the HOST BEGIN/AUTH) and
serves every stage of every token.  The image holds two programmes for two consumers inside qfd_tt_ctlm_dv:

  ME head (qfd_tt_ctlm_head_static, DENSE_IMAGE 1):
    PW 0 .. 16 n - 1     the n-instruction decode-layer ISA programme (1,024-b words, 16 PW each, beat b = bits 64b..)
    PW 976 .. 983        ME8 fixed-issue rows {last [46], unit [45:44], pc [43:32], cycle [31:0]} (ME ops + ENDs)
    PW 1004 .. 1015      four XPF188 arm records (3 PW each, zero padded)
    PW 1016 / 1017 / 1018  CAL1 (ME stop) / CALS {prog words, stage, su count, me count} / CAL2
    PW 1022 / 1023       XPFT (XPF stop) / footer {XPF1, fused native capability, stage, xpf count, 2'b10}
  slice-command calendar (qfd_dv_cmd_cal): PW base .. base + 2 nent - 1 (base >= 16 n, below 976), DW0 = CALD,
    DW1..4 = the four segments (stage 0, decode stages, LM head, BOOT), DW5..7 = 0.

Timing reference (every cycle in this file): edge 0 = the edge on which qfd_tt_ctlm_dv's dh pin register captures the
stage start (dh h_start).  Fixed RTL offsets (qfd_tt_ctlm_dv.sv / qfd_dv_cmd_cal.sv, confirmed by the unit bench
rtl/test/qwen_dv/tb_qfd_tt_ctlm_prog.sv, see PROG_CONSTANTS):
    cmd_cal segment start S = 1, entry k issues (cmd register load) on edge S + T_k;
    head fixed-issue cycle c  <->  edge HEAD0 + c;   XPF schedule cycle c  <->  edge XPF0 + c;
    die relays (compiled relay table): tt_ctlm.cmd -> dvs_W5.cmd_wi R_CMD, tt_ctlm.hr -> dvs_W5.hr_wi R_HR,
    dvs_W5.ss_wo / ag_wo -> tt_ctlm R_STATUS.
The STATIC SCHEDULE (the layer-bench compiled token path, results/rtl/qwen_layer_tput_1018/compiled_L1/d2d/
token_path_compiled.json.gz, layer L1 op windows) gives each programme operation its window; the compiler places every
SU / ME / END / collective / segment start on it, derives the status each consumer must see (the slices' SU / station
busy and progress, native59 idle) and checks every RTL rule of the three consumers (dense ME store seal, XPF loader +
static schedule seal, cmd_cal seal + fetch pipeline) fail-closed.  Nothing waits at run time: a missed cycle is a FAULT
in the RTL, and an image the RTL would reject is refused here.

NOT COMPILED HERE (G-C4, recorded in the output's 'not_compiled'): the DV slice lowering of the ISA programme -- the slice
PROG (SU word) image, the STN / ROOT / STREAM / PORTS / AMAX command fields (they need the DV row/slice ownership map and
the slice-local VM address map, which no committed tool defines), and the stage-0 / LM-head ME programmes (the head has
ONE fixed-issue calendar per image, armed only at programme base 0).

usage: ctlm_image.py --out DIR [--stage-me 1] [--program HEX --lowering JSON] [--token-path JSON.gz] [--relay JSON]
  -> DIR/program.memh (PW0..1023, DW0..7: the sys_face_image.py --program input), DIR/ctlm_image.json (plan, rows,
     calendar entries, expected events at the tt_ctlm pins and the W5 pins, status timeline, digest)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_qwen_fullshape_isa_w12 as ISA  # noqa: E402

DEF_PROGRAM = 'results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex'
DEF_LOWERING = 'results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/lowering.json'
DEF_TOKEN_PATH = 'results/rtl/qwen_layer_tput_1018/compiled_L1/d2d/token_path_compiled.json.gz'
DEF_RELAY = 'results/rtl/qwen_layer_tput_1018/compiled_L1/relay_schedule/compute_compiled.json'
DEF_SF_EVENTS = 'results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json'
NATIVE_TEMPLATE = 'results/rtl/qwen_q_export_1014/xpf/static/native380_template.json'
PW, DW = 1024, 8
SEED = 0x51484f5354505247

# RTL constants (edge offsets; see the module docstring).  PROG_CONSTANTS are confirmed by the unit bench (MUT 0 lands
# every event on these edges; its MUT 4 shifts the status one edge late and must FAIL).
PROG_CONSTANTS = dict(
    CAL_S=1,          # qfd_dv_cmd_cal samples `start` (dh_q h_start) one edge after the dh pin register
    HEAD0=3,          # dh_q -> st_h (+1) -> head u_is1 IS (+1) -> u_fixed_issue samples start (+1): cycle 0 after edge 3
    XPF0=3,           # dh_q -> st_h (+1) -> u_xpf_start_face (+1) -> u_xpf_schedule samples start (+1)
    FIRST_T=4,        # qfd_dv_cmd_cal: the first entry of a segment needs T_0 >= 4 (store read pipeline)
    LOC_EDGES=0,      # LOCAL SEG / EMB: the calendar's loc_seg / loc_emb register loads on the entry's issue edge
                      # (emb_start to the provider one register later)
    SEG_TO_HEAD=3,    # loc_seg -> st_h (+1) -> head u_is1 (+1) -> the controller accepts the segment start (+1)
    ISSUE_TO_ROM=2,   # head fixed issue edge -> hr ib go (hcmd -> relocate -> hr register)          [unit bench]
    ISSUE_TO_NAT=1,   # head fixed issue edge -> native_cmd go (ot_qfd_native_cmd_route, combinational) [unit bench]
    XPF_ARM_EDGE=2,   # XPF record arm cycle a -> hr xpf v on edge XPF0 + a + 2 (schedule xpf reg + hr reg)
    DEP=8,            # a status change at the tt_ctlm pins must precede the dependent ME issue edge by >= DEP edges
                      # (ag/ss pin register 1 + head IS 1 + XREG snapshot 1 + decode/NEXT 2, 3 edges of margin)
    SKIP=2,           # controller: edges per skipped other-unit (SU) instruction before the next ME op can issue
    CTRL_FIRST=8,     # controller: earliest head cycle of the first programme candidate after a start (FIFO fill)
    XPF_TAP=3,        # ot_qfd_xpf_static_schedule seal: first_write >= arm + ARM_TRANSPORT_EDGES + 3
    SU_LANES=96,      # priced: 12 DV slices x 8 SU lanes (rtl/qwen_dv/README.md)
    SU_LAT=24,        # priced: slice SU pipeline from the command at the W5 pin to the op's last write
)

ME_ROWS, XPF_N, CMD_CEIL = 8, 4, 976
HEAD_PLAN = 'results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/token_source_plan.json'
G_XPF_N = 3
SEG_STAGE0, SEG_DECODE, SEG_HEAD, SEG_BOOT = 0, 1, 2, 3


class CompileError(Exception):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ inputs
def load_programme(program: Path, lowering: Path):
    words = [int(w, 16) for w in program.read_text().split()]
    low = json.loads(lowering.read_text())
    if low.get('candidate_program_sha256') != sha(program):
        raise CompileError('lowering.json is not the lowering of this programme (candidate_program_sha256)')
    desc = [int(w, 16) for w in low['descriptor_hex']]
    ops = [ISA.decode_instruction(w) for w in words]
    if not 0 < len(words) < 60:
        raise CompileError('programme exceeds the 59-instruction ME store reservation')
    return words, desc, ops, low


def segments(ops, desc):
    """[(first_pc, end_pc, descriptor)] -- every segment ends with an END (unit 0), descriptors in order."""
    out, pc = [], 0
    for d in desc:
        dd = ISA.decode_descriptor(d, vm_addr_ext=True)
        if dd['program_base'] != pc:
            raise CompileError(f'descriptor base {dd["program_base"]} != next PC {pc}')
        end = next((p for p in range(pc, len(ops)) if ops[p]['unit'] == 0), None)
        if end is None:
            raise CompileError('segment without END')
        out.append(dict(first=pc, end=end, desc=dd))
        pc = end + 1
        if dd['kind'] == 0:
            break
    if pc != len(ops):
        raise CompileError('descriptors do not cover the programme')
    return out


def token_path_windows(path: Path, layer='L1'):
    tp = json.loads(gzip.open(path).read())
    nodes = {n['id'].split('.', 1)[1]: n for n in tp['nodes'] if n.get('group') == layer}
    t0 = nodes['rmsnorm1']['start']
    return {k: dict(start=n['start'] - t0, end=n['end'] - t0, cycles=n['cycles'], base=n.get('base_cycles'),
                    adders=n.get('adders', [])) for k, n in nodes.items()}, tp


def relay_edges(path: Path):
    r = json.loads(path.read_text())
    st = {b['id']: b['stages'] for b in r['buses']}
    need = {'R_CMD': 'tt_ctlm.cmd -> dvs_W5.cmd_wi', 'R_HR': 'tt_ctlm.hr -> dvs_W5.hr_wi',
            'R_SS': 'dvs_W5.ss_wo -> tt_ctlm.ss5', 'R_AG': 'dvs_W5.ag_wo -> tt_ctlm.ag5'}
    out = {}
    for k, bus in need.items():
        if bus not in st:
            raise CompileError(f'relay table lacks {bus}')
        out[k] = st[bus]
    out['digest'] = r.get('digest')
    return out


# ------------------------------------------------------------------------------------------------ the stage plan
# Programme operations -> token-path windows (decode layer).  The ISA programme (norm applied after the matvec) is
# pinned; each op takes the window of the token-path operation it implements.
PC_WINDOW = {
    0: 'rmsnorm1', 1: 'qkv', 2: 'qkv', 3: 'qknorm_rope', 4: 'qknorm_rope', 5: 'qknorm_rope', 6: 'qknorm_rope',
    7: 'qknorm_rope', 8: 'qknorm_rope', 9: 'qknorm_rope', 10: 'qknorm_rope', 11: 'attn_kv', 12: 'o_proj',
    13: 'o_proj', 14: 'attn_tail', 15: 'rmsnorm2', 16: 'gate_up', 17: 'gate_up', 18: 'gate_up', 19: 'gate_up',
    20: 'down', 21: 'down', 22: 'residual', 23: 'residual', 24: 'residual',
}
AR_WINDOW = {0: 'allreduce1', 1: 'allreduce2'}


def su_words(op):
    return max(1, (op['su_nin'] * max(op['su_nout'], 1) + 63) // 64)


def su_cycles(op, C):
    """priced DV slice SU time of one op: 12 slices x 8 lanes per edge plus the pipeline (SU_LAT)."""
    el = op['su_nin'] * max(op['su_nout'], 1)
    return C['SU_LAT'] + (el + C['SU_LANES'] - 1) // C['SU_LANES']


def plan_stage(ops, segs, win, C, R, lead, period, pc_window=None):
    """Static plan of one decode stage, in edges after edge 0 (dh h_start captured at tt_ctlm).

    SU op:   'at'   = edge its command is at the dvs_W5 cmd_wi pin (the slices' compiled issue).  The slice SU takes one
                      op at a time (qfd_dv_slice2: an SU go while the SU is not ready FAULTS), so SU ops are strictly
                      sequential in programme order: the next one arrives when the previous one's slice-side work ends.
                      Status at the tt_ctlm pins (R_SS relays + 1): busy over [at + R_SS + 1, done), progress = its
                      64-element words at 'done'.
    ME op:   'at'   = edge after which the head's fixed issue fires (head cycle at - HEAD0); station / native busy over
                      [at + 1, done).  Dependencies (barrier / chase) are met DEP edges before 'at' at the tt_ctlm pins;
                      the controller must have skipped every earlier SU op (SKIP edges each) after its (segment) start.
    END:     'at'   = head END edge; every earlier op done DEP edges before.  The collective (XC) of a non-terminal
                      segment is at the W5 pin at its AR window start (after the END); the next ME segment starts (LOCAL
                      SEG) when the AR window ends, and no SU op of that segment precedes its start.
    Windows: the token-path op each programme op implements (PC_WINDOW); SU ops of one window share it by words.
    """
    def wstart(name):
        return lead + int(win[name]['start'])

    def wlen(name):
        w = win[name]
        # the residual window carries a pre-DV adder (ROM split stations / issue relays) with no DV hardware: the DV
        # plan takes its base cycles (recorded in plan_notes)
        if name == 'residual' and w['base'] is not None:
            return int(w['base'])
        return int(w['cycles'])

    notes = ['residual window: base cycles %d (token path %d incl. the pre-DV ROM split-station adder)'
             % (wlen('residual'), int(win['residual']['cycles']))] if 'residual' in win else []
    PCW = PC_WINDOW if pc_window is None else pc_window
    groups = {}
    for pc in range(len(ops)):
        groups.setdefault(PCW[pc], []).append(pc)
    seg_of = {pc: k for k, sg in enumerate(segs) for pc in range(sg['first'], sg['end'] + 1)}
    plan, done_by_pc = [], {}
    t_su = 0                       # earliest next SU command at the W5 pin (previous SU op's slice-side end)
    su_done = me_done = 0          # latest completion at the tt_ctlm pins
    last_head = 0                  # last head fixed-issue edge (ME / END)
    ctrl_ready = 0                 # earliest edge the controller has the next candidate (start + skips)
    seg_start = {0: 0}
    k_seg = 0
    dep_me_issue = -(1 << 20)
    for pc, op in enumerate(ops):
        name = PCW[pc]
        k = seg_of[pc]
        if k != k_seg:             # a new ME segment: collective of the previous one, then LOCAL SEG
            prev = segs[k_seg]
            end = next(q for q in plan if q['pc'] == prev['end'] and q['kind'] == 'END')
            aw = AR_WINDOW[k_seg]
            at = max(wstart(aw), end['at'] + 1)
            done = max(wstart(aw) + int(win[aw]['cycles']), at + 16)
            plan.append(dict(pc=None, unit=None, kind='XC', at=at, done=done, words=prev['desc']['words'], mode=0,
                             tag=k_seg, window=aw, after_end=prev['end']))
            plan.append(dict(pc=segs[k]['first'], unit=None, kind='SEG', at=done, done=done, base=segs[k]['first'],
                             window=aw))
            seg_start[k] = done
            ctrl_ready = done + C['SEG_TO_HEAD'] + C['CTRL_FIRST']
            t_su = max(t_su, done + C['SEG_TO_HEAD'])
            k_seg = k
        unit = op['unit']
        if unit == 2:
            dur = su_cycles(op, C)
            at = max(wstart(name), t_su, dep_me_issue + R['R_CMD'] + 1)
            if op['barrier']:
                at = max(at, su_done - R['R_SS'] - 1, me_done)
            done = at + R['R_SS'] + 1 + dur
            plan.append(dict(pc=pc, unit=2, kind='SU', at=at, done=done, words=su_words(op), window=name))
            t_su = at + dur
            su_done = done
            ctrl_ready += C['SKIP']
        elif unit == 1:
            at = max(wstart(name), last_head + 1, ctrl_ready)
            if op['barrier']:
                at = max(at, su_done + C['DEP'], me_done + C['DEP'])
            if op['chase']:
                prev = max(p for p in range(pc) if ops[p]['unit'] == 2)
                at = max(at, done_by_pc[prev] + C['DEP'])
            done = max(wstart(name) + wlen(name), at + 16)
            plan.append(dict(pc=pc, unit=1, kind='NATIVE' if op['me_wsrc'] else 'ME', at=at, done=done, window=name))
            me_done = max(me_done, done)
            last_head = at
            if op['barrier'] or op['chase'] or op['wait_su']:
                dep_me_issue = at        # later SU commands must not reach the head's other-unit count before it
            ctrl_ready = at + 1
        else:
            at = max(su_done, me_done, last_head + 1, ctrl_ready) + C['DEP']
            plan.append(dict(pc=pc, unit=0, kind='END', at=at, done=at, window=name))
            last_head = at
        done_by_pc[pc] = plan[-1]['done']
    plan.sort(key=lambda p: (p['at'], p['kind'] != 'SEG'))
    # programme order of the SU commands (one SU queue) and of the head issues
    su = [p['pc'] for p in plan if p['kind'] == 'SU']
    head = [p['pc'] for p in plan if p['kind'] in ('ME', 'NATIVE', 'END')]
    if su != sorted(su) or head != sorted(head):
        raise CompileError('plan breaks programme order')
    stop = max(p['done'] for p in plan)
    if stop >= period - 8:
        raise CompileError(f'stage plan ends at {stop} >= the stage period {period} - 8')
    return plan, notes


# ------------------------------------------------------------------------------------------------ ME head image
def me_rows(plan, C, pc_off=0):
    rows = []
    for p in [q for q in plan if q['unit'] in (0, 1)]:
        cyc = p['at'] - C['HEAD0']
        if cyc < 2:
            raise CompileError('ME issue before the head calendar start-up (cycle >= 2)')
        rows.append(dict(pc=p['pc'] + pc_off, unit=p['unit'], cycle=cyc))
    rows.sort(key=lambda r: r['cycle'])
    for a, b in zip(rows, rows[1:]):
        if b['cycle'] <= a['cycle']:
            raise CompileError('two fixed issues on one edge')
    if len(rows) > ME_ROWS:
        raise CompileError(f'{len(rows)} ME/END issues > the ME8 calendar')
    if rows[-1]['unit'] != 0:
        raise CompileError('the ME calendar must end with the terminal END')
    for n, r in enumerate(rows):
        r['hex'] = f"{r['cycle'] | (r['pc'] << 32) | (r['unit'] << 44) | (int(n == len(rows) - 1) << 46):012x}"
    return rows


def native_capability(words, stage):
    native = [(pc, f) for pc, f in ((pc, ISA.decode_instruction(w)) for pc, w in enumerate(words))
              if f['unit'] == 1 and f['me_wsrc']]
    if not native:
        return False
    sys.path.insert(0, str(ROOT / 'tools'))
    from qwen_split.command_abi import pack_me
    tmpl = json.loads((ROOT / NATIVE_TEMPLATE).read_text())
    if len(native) != 1 or native[0][0] != 11 or not 1 <= stage <= 36:
        raise CompileError('native capability needs the sole PC11 layer dispatch')
    f = native[0][1]
    if any(v for k, v in f.items() if k.startswith('me_d_')) or pack_me(f) != int(tmpl['command_hex'], 16):
        raise CompileError('PC11 differs from the source-pinned native59 command')
    return True


def su_extent(op):
    """VM elements an SU op writes (dst 1 = VM): d_base + o * d_so + i * d_si."""
    if op['unit'] != 2 or op['dst'] != 1:
        return set()
    return {op['d_base'] + o * op['d_so'] + k * op['d_si'] for o in range(max(op['su_nout'], 1)) for k in range(op['su_nin'])}


def xpf_records(plan, ops, low):
    """XPF arms: each ROM matvec's x epoch (the column-head tap), armed before the producer of that epoch writes it.  The
    producer is the latest programme op (wrapping to the end of the programme: the next layer's qkv x is written by this
    stage's last SU op) whose writes cover the whole epoch; the native attention result (lowering fused_output) feeds the
    projection after it.  The native op itself takes q over the D2D path, not the tap: no record."""
    by_pc = {p['pc']: p for p in plan if p['pc'] is not None and p['kind'] != 'SEG'}
    nat = set(range(low['fused_output_element_base'], low['fused_output_element_base'] + low['fused_output_elements']))
    recs = []
    for cons, op in enumerate(ops):
        if op['unit'] != 1 or op['me_wsrc']:
            continue
        xb, xc, xk, sp, nk = op['me_xbase'], op['me_xcs'], op['me_xks'], op['me_split'], op['me_k']
        need = {xb + c * xc + k * xk for c in range(1 << sp) for k in range(nk)}
        prod = None
        for pc in list(range(cons - 1, -1, -1)) + list(range(len(ops) - 1, cons, -1)):
            p = ops[pc]
            if (p['unit'] == 1 and p['me_wsrc'] and need <= nat) or need <= su_extent(p):
                prod = pc
                break
        if prod is None:
            raise CompileError(f'no programme producer covers the x epoch of PC{cons}')
        recs.append(dict(consumer_pc=cons, producer_pc=prod, producer_unit=ops[prod]['unit'], xb=xb, xc=xc, xk=xk,
                         split=sp, nk=nk, round=op['me_round'], producer=by_pc[prod]))
    return recs


def xpf_pack(recs, stage, C, xpf_edges, ev):
    """ev: function (record) -> (issue_cycle_at_xpf, first_write_cycle_at_xpf)."""
    rows, used = [], set()
    for r in recs:
        issue_c, first_c = ev(r)
        arm = first_c - xpf_edges - C['XPF_TAP']
        while arm in used:
            arm -= 1
        if arm < 0:
            raise CompileError(f'XPF arm for PC{r["consumer_pc"]} before the stage start')
        used.add(arm)
        x72 = ((r['round'] & 1) << 71) | (r['nk'] << 53) | (r['split'] << 49) | (r['xk'] << 37) | (r['xc'] << 25) | \
              (r['xb'] << 1) | 1
        val = (first_c << 156) | (issue_c << 124) | (arm << 92) | (stage << 86) | (r['producer_unit'] << 84) | \
              (r['producer_pc'] << 72) | x72
        rows.append(dict(consumer_pc=r['consumer_pc'], producer_pc=r['producer_pc'], producer_unit=r['producer_unit'],
                         arm_cycle=arm, issue_cycle=issue_c, first_write_cycle=first_c, xpf72=f'{x72:018x}',
                         value=val))
    if not 1 <= len(rows) <= XPF_N:
        raise CompileError(f'{len(rows)} XPF records (the DV head has {XPF_N})')
    # ot_qfd_xpf_static_schedule seal: distinct producer ids / arm cycles, first >= arm + T + 3
    for i, a in enumerate(rows):
        if a['first_write_cycle'] < a['arm_cycle'] + xpf_edges + C['XPF_TAP']:
            raise CompileError('XPF first write too close to its arm')
        for b in rows[:i]:
            if (a['producer_pc'], a['producer_unit']) == (b['producer_pc'], b['producer_unit']) or a['arm_cycle'] == b['arm_cycle']:
                raise CompileError('XPF records collide (producer id or arm cycle)')
    return rows


# ------------------------------------------------------------------------------------------------ cmd_cal
def cmdw(go=1, kind=0, f=0, dst=15):
    return (go & 1) | ((kind & 7) << 1) | ((f & ((1 << 108) - 1)) << 4) | ((dst & 15) << 112)


def cal_entries(events, S, C):
    """events [(edge at the tt_ctlm.cmd output / local pulse source, cmd, label)] -> [(delta, cmd, label)]
    entry k issues on edge S + T_k (cmd register) = the event edge; LOCAL pulses come LOC_EDGES later (the caller
    already subtracted it).  Gaps > 4095 are spanned with NOP entries."""
    out, t_prev = [], 0
    for edge, cmd, label in sorted(events, key=lambda e: e[0]):
        T = edge - S
        if not out and T < C['FIRST_T']:
            raise CompileError(f'first calendar entry {label} at T {T} < {C["FIRST_T"]}')
        d = T - t_prev
        if d < 1:
            raise CompileError(f'two calendar entries on one edge ({label})')
        while d > 4095:
            out.append((4095, cmdw(0, 0, 0, 0), 'NOP'))
            d -= 4095
        out.append((d, cmd, label))
        t_prev = T
    return out


def is_tload(c):
    return (c >> 112) == 14 and (c & 1) and (c >> 1) & 7 == 3


def cal_model(entries, S):
    """cycle model of qfd_dv_cmd_cal fetch / FIFO / issue (RTL qfd_dv_cmd_cal.sv): returns the issue edges or raises."""
    n = len(entries)
    times, t = [], 0
    tl_at = set()
    for d, c, _ in entries:
        t += d
        times.append(t)
        if is_tload(c):
            tl_at.add(t)
    f_rem, fifo, infl, rce, rd_v, rd_n, r_n_q = n, [], 0, False, False, 0, 0
    fetched = 0
    tcount = 1
    issued, edge = [], S
    pending = []            # entries in flight: list of lists (read groups)
    rce_n = 0
    for _ in range(1 << 20):
        edge += 1
        # combinational values before this edge
        hv = bool(fifo)
        fire = hv and tcount == fifo[0]
        late = hv and tcount > fifo[0]
        if late:
            raise CompileError(f'cmd_cal late: entry at T {fifo[0]} not fetched in time (tcount {tcount})')
        f_n = min(4, f_rem)
        # QLB-C4b: a TLOAD entry's block read takes the store read port -> no fetch decision on its issue edge
        tl_fire = fire and tl_at is not None and fifo[0] in tl_at
        can_read = f_rem != 0 and len(fifo) + infl + 4 <= 8 and not tl_fire
        # register updates
        push = []
        if rd_v:
            push = times[fetched:fetched + rd_n]
            fetched += rd_n
        new_infl = infl + (f_n if can_read else 0) - (rd_n if rd_v else 0)
        rd_v, rd_n = rce, r_n_q
        rce, r_n_q = can_read, f_n
        if can_read:
            f_rem -= f_n
        infl = new_infl
        if fire:
            issued.append(edge)
            fifo.pop(0)
        fifo += push
        tcount += 1
        if len(issued) == n:
            return issued
    raise CompileError('cmd_cal model did not finish')


# ------------------------------------------------------------------------------------------------ QLB-C4b TLOAD
TL_SPACING = 2          # TLOAD entries >= 2 edges apart (the block read suppresses that edge's fetch decision)
TL_OUT_EDGES = 2        # issue edge -> tl register (qfd_dv_cmd_cal: read decision, macro read, tl load)
TL_SRC = 0xE            # stream src field of a tt_ctlm table word


def cmd_tload(row, kind, dst, eaddr, src=TL_SRC, tag=0):
    """LOCAL kind 3 TLOAD entry (qfd_dv_cmd_cal.sv ENTRY KINDS): [9:4] row, [12:10] kind, [16:13] dst, [20:17] src,
    [44:21] eaddr, [72:45] tag"""
    if not (0 <= row < 61 and kind in (1, 2, 3) and 0 <= dst < 16 and 0 <= eaddr < 1 << 24 and 0 <= tag < 1 << 28):
        raise CompileError('TLOAD field out of range')
    return cmdw(1, 3, row | (kind << 6) | (dst << 9) | (src << 13) | (eaddr << 17) | (tag << 41), 14)


def tl_word(kind, dst, eaddr, payload, src=TL_SRC, tag=0):
    """the 1,088-b stream word the TLOAD entry leaves on tt_ctlm.tl (= dv_lower.stream_table_word)"""
    ctl = (1 << 63) | (kind << 60) | (dst << 56) | (src << 52) | (eaddr << 28) | tag
    return (ctl << 1024) | payload


def table_words(dv_lower=True):
    """the slice table words the die must load: dv_lower.py PROG streams (kind 3) -> [(kind, dst, eaddr, payload)]"""
    sys.path.insert(0, str(ROOT / 'tools' / 'qwen_layerbench'))
    import dv_lower as DL
    lw = DL.lower()
    out = []
    for s in sorted(lw['prog_stream'], key=int):
        for w in lw['prog_stream'][s]:
            out.append((3, int(s), int(w['eaddr']), int(w['payload'], 16)))
    return out, lw


def tload_gap(R, margin=4):
    """SETID issue -> first TLOAD issue (edges).  Slice j takes its id from cmd_q one edge after SETID lands (W5 at
    k0 + R_CMD + 1, then 2 edges a hop) and taps a table word in sw_q (W5 at k1 + TL_OUT_EDGES + R_ST + 1, then 2 edges
    a hop: the same hop cost), so k1 - k0 >= R_CMD - R_ST - 1 + 1; margin edges on top (fail-closed: a word that
    overtakes SETID is taken by no slice or the wrong one, and the bench / die run sees the missing table)."""
    return max(TL_SPACING, R['R_CMD'] - R['R_ST'] + margin)


def cal_image(segs_entries, base, meta_rows):
    """segs_entries {seg: [(delta, cmd, label)]} -> (pw {addr: word}, dw[8], desc {seg: (first, count)})"""
    ents, desc = [], {}
    for s in (SEG_BOOT, SEG_STAGE0, SEG_DECODE, SEG_HEAD):
        while len(ents) % 4:
            ents.append((1, 0, 'PAD'))
        e = segs_entries.get(s, [])
        desc[s] = (len(ents) if e else 0, len(e))
        ents += e
    nent = len(ents)
    if base % 8 or base < 16 * meta_rows or base + 2 * nent > CMD_CEIL or nent == 0:
        raise CompileError(f'cmd_cal image does not fit: base {base} nent {nent} (programme rows {meta_rows})')
    pw = {}
    for k, (d, c, _) in enumerate(ents):
        if not 0 <= d < 4096:
            raise CompileError('delta out of range')
        w = (d << 116) | c
        pw[base + 2 * k] = w & ((1 << 64) - 1)
        pw[base + 2 * k + 1] = w >> 64
    dw = [0] * 8
    dw[0] = (0x43414C44 << 32) | (base << 16) | nent
    for s in range(4):
        f, n = desc[s]
        dw[1 + s] = (f << 16) | n
    return pw, dw, desc, ents


def digest(words):
    d = SEED
    for i, w in enumerate(words):
        d = ((d << 7) | (d >> 57)) & ((1 << 64) - 1)
        d ^= w ^ (i if i < PW else (1 << 10) | (i - PW))
    return d


# ------------------------------------------------------------------------------------------------ LM head (QLB-C4b)
def lm_head_programme(plan_path: Path):
    """The DV (TP8) LM-head ME programme: final RMSNorm (sum of squares, rsqrt, gain apply -> VM 8192, the head
    profile's three SU ops) -> ONE AMAX matvec over the die's head rows (head_geometry: rows, tiles a round, rounds;
    the profile's chunk-0 matvec fields with the DV geometry: no chunking, the 25-round DV schedule streams them) -> END.
    Source: token_source_plan head_geometry + head_profiles[0] (the die-0 ISA profile)."""
    p = json.loads(plan_path.read_text())
    geo, prof = p['head_geometry'], p['head_profiles'][0]
    pw = [int(h, 16) for h in prof['program_hex']]
    ops = [ISA.decode_instruction(w) for w in pw]
    if [o['unit'] for o in ops[:4]] != [2, 2, 2, 1] or not ops[3]['me_amax'] or ops[-1]['unit'] != 0:
        raise CompileError('head profile is not norm (3 SU) + AMAX matvec ... END')
    me = dict(ops[3])
    me.update(me_nout=geo['rows'], me_tiles=geo['tiles_per_round'], me_wbase=0, me_wcs=0, me_obase=0, me_row0=0,
              me_amc=0)
    if (geo['rows'] + geo['tiles_per_round'] * geo['rounds'] - 1) // (geo['tiles_per_round'] * geo['rounds']) > 128:
        raise CompileError('head rows exceed tiles x rounds x 128')
    fields = [ops[0], ops[1], ops[2], me, ops[-1]]
    words = [ISA.encode_instruction(f) for f in fields]
    for w, f in zip(words, fields):
        g = ISA.decode_instruction(w)
        if any(g[k] != f[k] for k in f):
            raise CompileError('head instruction does not round-trip')
    return words, [ISA.decode_instruction(w) for w in words], dict(geometry=geo, profile=prof['schema'],
                                                                     profile_die=prof['die'])


def compile_head(a, C, R, dec_words, stage, xpf_edges):
    """stage LAST_STAGE: the calendar's head segment starts the LM-head ME programme with a LOCAL SEG at its base
    (= the decode words) on edge E_SEG; every head event is planned on that start (the SEG edge plays edge 0: the
    segment start reaches the head calendar and the G XPF schedule SEG_TO_HEAD = HEAD0 = XPF0 edges later)."""
    if C['SEG_TO_HEAD'] != C['HEAD0'] or C['XPF0'] != C['HEAD0']:
        raise CompileError('segment start offsets differ from the stage start offsets')
    words, ops, src = lm_head_programme(ROOT / a.head_plan)
    B = len(dec_words)
    tp = json.loads(gzip.open(ROOT / a.token_path).read())
    hn = next(n for n in tp['nodes'] if n['id'] == 'head.lm_head')
    win = {'lm_head': dict(start=0, end=int(hn['cycles']), cycles=int(hn['cycles']), base=hn.get('base_cycles'),
                           adders=[])}
    lead = C['CAL_S'] + C['FIRST_T'] + R['R_CMD'] + a.lead_margin
    period = int(hn['cycles']) + lead + 2 * C['DEP'] + 32
    segs = [dict(first=0, end=len(ops) - 1, desc=None)]
    plan, notes = plan_stage(ops, segs, win, C, R, lead, period, pc_window={pc: 'lm_head' for pc in range(len(ops))})
    e_seg = C['CAL_S'] + C['FIRST_T']
    ev = [(e_seg, cmdw(1, 2, B, 14), f'SEG base {B}')]
    for p in plan:
        if p['kind'] == 'SU':
            ev.append((e_seg + p['at'] - R['R_CMD'], cmdw(1, 1, B + p['pc'], 15), f'SU PC{B + p["pc"]}'))
        elif p['kind'] not in ('ME', 'END'):
            raise CompileError(f'head plan op {p["kind"]} not supported')
    cal = cal_entries(ev, C['CAL_S'], C)
    if cal_model(cal, C['CAL_S']) != [C['CAL_S'] + t for t in _acc(cal)]:
        raise CompileError('cmd_cal model: head issue edges differ from the compiled entry times')
    rows = me_rows(plan, C, pc_off=B)
    stop = rows[-1]['cycle']

    def xpf_ev(r):
        pp = r['producer']
        if pp['unit'] == 1:
            raise CompileError('head XPF producer must be an SU op')
        return (pp['at'] - R['R_CMD']) + 3 - C['XPF0'] - 1, pp['at'] + a.su_first_write - C['XPF0'] - 1
    recs = xpf_records(plan, ops, dict(fused_output_element_base=0, fused_output_elements=0))
    for r in recs:
        r['consumer_pc'] += B
        r['producer_pc'] += B
    xrows = xpf_pack(recs, stage, C, xpf_edges, xpf_ev)
    if len(xrows) > G_XPF_N:
        raise CompileError(f'{len(xrows)} head XPF records > {G_XPF_N}')
    xstop = max(stop + C['HEAD0'] - C['XPF0'], max(r['issue_cycle'] for r in xrows) + 1,
                max(r['first_write_cycle'] for r in xrows) + 1)
    sh = lambda e: e_seg + e
    exp = dict(
        cmd_at_tt_ctlm=[dict(edge=C['CAL_S'] + t, cmd=f'{c:029x}', label=l) for t, (d, c, l) in zip(_acc(cal), cal)
                        if l != 'NOP' and (c >> 112) != 14],
        local_at_tt_ctlm=[dict(edge=C['CAL_S'] + t + C['LOC_EDGES'], kind='SEG', base=(c >> 4) & 0xFFF, label=l)
                          for t, (d, c, l) in zip(_acc(cal), cal) if (c >> 112) == 14],
        me_issue=[dict(head_cycle=r['cycle'], edge=sh(r['cycle'] + C['HEAD0']), pc=r['pc'], unit=r['unit']) for r in rows],
        xpf_arm_at_tt_ctlm=[dict(edge=sh(C['XPF0'] + r['arm_cycle'] + C['XPF_ARM_EDGE']), xpf72=r['xpf72'],
                                 consumer_pc=r['consumer_pc']) for r in xrows])
    exp['rom_go_at_tt_ctlm'] = [dict(edge=e['edge'] + C['ISSUE_TO_ROM'], pc=e['pc']) for e in exp['me_issue'] if e['unit'] == 1]
    status = [dict(s, edge=sh(s['edge'])) for s in status_timeline(plan, R, C)]
    return dict(base=B, words=words, ops_source=src, seg_edge=e_seg, period_check=period, plan=plan, plan_notes=notes,
                rows=rows, stop_cycle=stop, xpf_rows=xrows, xpf_stop=xstop, expected=exp, status=status,
                programme_hex=[f'{w:0256x}' for w in words], cal=cal)


def check_head_image(image, head, stage, xpf_edges):
    """seal rules of ot_qwen_fixed_issue_seg_pw (G rows / CALG / CALB) and qfd_dv_xpf_seg_loader, on the emitted words"""
    pw = image[:PW]
    if head is None:
        assert all(pw[k] == 0 for k in range(984, 1004))
        return
    gd, gs = pw[993], pw[992]
    cnt, base = (gd >> 24) & 15, gd & 0xFFF
    assert gd >> 32 == 0x43414C42 and (gd >> 28) & 15 == 0 and (gd >> 12) & 0xFFF == 0 and base and 0 < cnt <= 8
    assert gs >> 32 == 0x43414C47 and gs & 0xFFFFFFFF
    for k in range(8):
        r = pw[984 + k]
        if k < cnt:
            assert r >> 47 == 0 and ((r >> 46) & 1) == int(k == cnt - 1) and not (r >> 45) & 1
        else:
            assert r == 0
    pad, n = False, 0
    for k in range(3):
        v = pw[994 + 3 * k] | (pw[995 + 3 * k] << 64) | (pw[996 + 3 * k] << 128)
        assert pw[996 + 3 * k] >> 60 == 0
        if v == 0:
            pad = True
            continue
        assert not pad and v & 1 and (v >> 86) & 63 == stage and (v >> 84) & 3 != 0
        assert (v >> 156) >= ((v >> 92) & 0xFFFFFFFF) + xpf_edges + 3
        n += 1
    assert n >= 1 and pw[1003] >> 32 == 0x58505447 and pw[1003] & 0xFFFFFFFF


# ------------------------------------------------------------------------------------------------ main compile
plan_meta = {}


def compile_image(a):
    C = dict(PROG_CONSTANTS)
    words, desc, ops, low = load_programme(ROOT / a.program, ROOT / a.lowering)
    segs = segments(ops, desc)
    win, tp = token_path_windows(ROOT / a.token_path)
    R = relay_edges(ROOT / a.relay)
    R['source'] = 'relay table (hop count)'
    if a.lane_ages:
        la = json.loads((ROOT / a.lane_ages).read_text())
        for k in ('R_CMD', 'R_HR', 'R_SS', 'R_AG'):
            R[k] = la[k]
        if 'R_ST' in la:
            R['R_ST'] = la['R_ST']              # QLB-C4b: tt_ctlm.tl -> dvs_W5.st_wi
        R['source'] = f'{a.lane_ages} (measured lane ages; the die exports no land plan)'
    plan_meta.update(R)
    stage = a.stage
    # the T calendar's STAGE events (class 0, arg [5:0] = stage): every decode stage must fit its own window
    sfe = json.loads((ROOT / a.sys_face_events).read_text())
    starts = sorted((c, arg & 63) for c, k, arg in sfe['T'] if k == 0)
    gaps = [b[0] - a_[0] for a_, b in zip(starts, starts[1:]) if 1 <= a_[1] <= 36]
    period = min(gaps) if a.period is None else a.period
    a.period = period
    # plan: the first SU command must be at the W5 pin no earlier than S + FIRST_T + R_CMD
    lead = C['CAL_S'] + C['FIRST_T'] + R['R_CMD'] + a.lead_margin
    plan, notes = plan_stage(ops, segs, win, C, R, lead, a.period)

    # ---------------- cmd_cal events (edges at the tt_ctlm.cmd output = W5 pin edge - R_CMD; local = pulse - LOC)
    ev = []
    for p in plan:
        if p['kind'] == 'SU':
            op = ops[p['pc']]
            ev.append((p['at'] - R['R_CMD'], cmdw(1, 1, p['pc'], 15), f'SU PC{p["pc"]}'))
        elif p['kind'] == 'XC':
            f = (0 << 0) | (p['mode'] << 2) | ((p['words'] & 0xFFFF) << 3) | ((p['tag'] & 0xFFFFFFFF) << 19)
            ev.append((p['at'] - R['R_CMD'], cmdw(1, 0, f, 15), f'XC tag {p["tag"]} words {p["words"]}'))
        elif p['kind'] == 'SEG':
            # the head must accept the segment start SEG_TO_HEAD edges after the pulse, before its first ME candidate
            ev.append((p['at'] - C['LOC_EDGES'], cmdw(1, 2, p['base'] << 0, 14), f'SEG base {p["base"]}'))
    decode = cal_entries(ev, C['CAL_S'], C)
    boot_ev = [(C['CAL_S'] + C['FIRST_T'], cmdw(1, 7, 0, 15), 'SETID 0')]
    tl_tab, tl_rec = [], None
    if a.tload:
        tl_tab, _ = table_words()
        R.setdefault('R_ST', R['R_HR'])
        gap = tload_gap(R)
        t1 = C['CAL_S'] + C['FIRST_T'] + gap
        # rows are assigned after the entry count is known (blocks sit above the entry area); placeholders first
        for i, (k_, d_, e_, _) in enumerate(tl_tab):
            boot_ev.append((t1 + TL_SPACING * i, cmd_tload(0, k_, d_, e_), f'TLOAD k{k_} s{d_} e{e_}'))
        tl_rec = dict(gap=gap, spacing=TL_SPACING, out_edges=TL_OUT_EDGES, R_CMD=R['R_CMD'], R_ST=R['R_ST'],
                      R_ST_source='lane ages R_ST' if a.lane_ages and 'R_ST' in json.loads((ROOT / a.lane_ages).read_text())
                      else 'assumed = R_HR (same tt_ctlm -> W5 route; check on the GEN die: dvw_st_wi lane)')
    boot = cal_entries(boot_ev, C['CAL_S'], C)
    stage0 = cal_entries([(C['CAL_S'] + C['FIRST_T'], cmdw(1, 1, 0, 14), 'EMB')], C['CAL_S'], C)
    # SEG / EMB: cmd field [15:4] = base for SEG (loc_base = hc[15:4]); cmdw shifts f by 4
    issue = cal_model(decode, C['CAL_S'])
    want = [C['CAL_S'] + t for t in _acc(decode)]
    if issue != want:
        raise CompileError('cmd_cal model issue edges differ from the compiled entry times')
    rows = me_rows(plan, C)
    stop_cycle = rows[-1]['cycle']

    # ---------------- XPF records
    xpf_edges = a.xpf_transport_edges if a.xpf_transport_edges is not None else 1 + R['R_HR']

    def xpf_ev(r):
        # the XPF schedule evaluates edge E with cycle E - XPF0 - 1 (cycle 0 is loaded on edge XPF0)
        pp = r['producer']
        if pp['unit'] == 1:      # ME issue (issue_v high after edge 'at') -> actual_me_observe -> monitor face (+1)
            eval_edge = pp['at'] + 1 + a.me_observe_edges + 1
            first_edge = pp['done'] - 16       # the native result's first landed word (plan: 16 before its done)
        else:                    # SU: cmd_cal register (edge e) -> su_obs (+1) -> monitor face (+1) -> evaluated e + 3
            eval_edge = (pp['at'] - R['R_CMD']) + 3
            first_edge = pp['at'] + a.su_first_write
        return eval_edge - C['XPF0'] - 1, first_edge - C['XPF0'] - 1
    recs = xpf_records(plan, ops, low)
    xrows = xpf_pack(recs, stage, C, xpf_edges, xpf_ev)
    xpf_stop = max(stop_cycle + C['HEAD0'] - C['XPF0'], max(r['issue_cycle'] for r in xrows) + 1,
                   max(r['first_write_cycle'] for r in xrows) + 1)

    # ---------------- assemble PW / DW
    pw = [0] * PW
    head = compile_head(a, C, R, words, stage, xpf_edges) if a.lm_head else None
    all_words = words + (head['words'] if head else [])
    if len(all_words) >= 60:
        raise CompileError(f'{len(all_words)} programme words exceed the 59-instruction ME store reservation')
    for pc, w in enumerate(all_words):
        for b in range(16):
            pw[16 * pc + b] = (w >> (64 * b)) & ((1 << 64) - 1)
    meta_rows = len(all_words)
    base = (16 * meta_rows + 7) // 8 * 8
    segs_e = {SEG_BOOT: boot, SEG_STAGE0: stage0, SEG_DECODE: decode}
    if head is not None:
        segs_e[SEG_HEAD] = head['cal']
    cpw, dw, cdesc, ents = cal_image(segs_e, base, meta_rows)
    tl_blocks = {}
    if tl_tab:
        row0 = (base + 2 * len(ents) + 15) // 16
        if row0 + len(tl_tab) > CMD_CEIL // 16:
            raise CompileError(f'slice tables do not fit the image: {len(tl_tab)} blocks from PW row {16 * row0} '
                               f'(free blocks {max(0, CMD_CEIL // 16 - row0)})')
        it = iter(range(len(tl_tab)))
        boot = [(d, cmd_tload(row0 + next(it), *[(c >> s) & m for s, m in ((10, 7), (13, 15), (21, (1 << 24) - 1))]), l)
                if is_tload(c) else (d, c, l) for d, c, l in boot]
        segs_e[SEG_BOOT] = boot
        cpw, dw, cdesc, ents = cal_image(segs_e, base, meta_rows)
        for i, (k_, d_, e_, pay) in enumerate(tl_tab):
            for b in range(16):
                tl_blocks[16 * (row0 + i) + b] = (pay >> (64 * b)) & ((1 << 64) - 1)
        tl_rec.update(rows=[row0 + i for i in range(len(tl_tab))], pw_first=16 * row0, pw_end=16 * (row0 + len(tl_tab)),
                      words=len(tl_tab), capacity_blocks=CMD_CEIL // 16 - row0)
        bi = cal_model(boot, C['CAL_S'])
        if bi != [C['CAL_S'] + t for t in _acc(boot)]:
            raise CompileError('cmd_cal model: BOOT issue edges differ from the compiled entry times')
    for k, v in tl_blocks.items():
        if k in cpw:
            raise CompileError('table block overlaps a calendar entry')
    for k, v in cpw.items():
        pw[k] = v
    for k, v in tl_blocks.items():
        pw[k] = v
    for n, r in enumerate(rows):
        pw[976 + n] = int(r['hex'], 16)
    pw[1016] = (0x43414C31 << 32) | stop_cycle
    pw[1017] = (0x43414C53 << 32) | (meta_rows << 18) | (stage << 12) | (0 << 6) | len(rows)
    pw[1018] = (0x43414C32 << 32) | stop_cycle
    for n, r in enumerate(xrows):
        for b in range(3):
            pw[1004 + 3 * n + b] = (r['value'] >> (64 * b)) & ((1 << 64) - 1)
    pw[1022] = (0x58504654 << 32) | xpf_stop
    cap = native_capability(words, stage)
    pw[1023] = (0x58504631 << 32) | (int(cap) << 12) | (stage << 6) | (len(xrows) << 2) | 2
    if head is not None:
        for n, r in enumerate(head['rows']):
            pw[984 + n] = int(r['hex'], 16)
        pw[992] = (0x43414C47 << 32) | head['stop_cycle']
        pw[993] = (0x43414C42 << 32) | (len(head['rows']) << 24) | head['base']
        for n, r in enumerate(head['xpf_rows']):
            for b in range(3):
                pw[994 + 3 * n + b] = (r['value'] >> (64 * b)) & ((1 << 64) - 1)
        pw[1003] = (0x58505447 << 32) | head['xpf_stop']
    image = pw + dw
    check_image(image, meta_rows, len(rows), len(xrows), stage, xpf_edges)
    check_head_image(image, head, stage, xpf_edges)

    # ---------------- expected events (bench contract)
    exp_cmd = [dict(edge=C['CAL_S'] + t, cmd=f'{c:029x}', label=l) for t, (d, c, l) in zip(_acc(decode), decode)
               if l != 'NOP' and (c >> 112) != 14]
    exp_loc = [dict(edge=C['CAL_S'] + t + C['LOC_EDGES'], kind='SEG' if (c >> 1) & 7 == 2 else 'EMB',
                    base=(c >> 4) & 0xFFF, label=l) for t, (d, c, l) in zip(_acc(decode), decode) if (c >> 112) == 14]
    exp_me = [dict(head_cycle=r['cycle'], edge=r['cycle'] + C['HEAD0'], pc=r['pc'], unit=r['unit']) for r in rows]
    nat_pcs = {p['pc'] for p in plan if p['kind'] == 'NATIVE'}
    exp_rom = [dict(edge=e['edge'] + C['ISSUE_TO_ROM'], pc=e['pc']) for e in exp_me if e['unit'] == 1 and e['pc'] not in nat_pcs]
    exp_nat = [dict(edge=e['edge'] + C['ISSUE_TO_NAT'], pc=e['pc']) for e in exp_me if e['pc'] in nat_pcs]
    exp_xpf = [dict(edge=C['XPF0'] + r['arm_cycle'] + C['XPF_ARM_EDGE'], xpf72=r['xpf72'], consumer_pc=r['consumer_pc'])
               for r in xrows]
    status = status_timeline(plan, R, C)
    rec = dict(
        schema='opentallas.qwen.ctlm-image.v1', tool='tools/qwen_layerbench/ctlm_image.py',
        scope='decode-layer stage image (stages 1..36) of qfd_tt_ctlm_dv; ONE image per epoch serves every stage '
              '(STAGE_ME 1 required: stage-0 / LM-head h_start must not restart the layer ME programme)',
        inputs={**({a.lane_ages: sha(ROOT / a.lane_ages)} if a.lane_ages else {}), a.program: sha(ROOT / a.program), a.lowering: sha(ROOT / a.lowering),
                a.token_path: sha(ROOT / a.token_path), a.relay: sha(ROOT / a.relay),
                a.sys_face_events: sha(ROOT / a.sys_face_events),
                **({a.head_plan: sha(ROOT / a.head_plan)} if head is not None else {})},
        stage_starts_T=[dict(cycle=c, stage=st) for c, st in starts],
        constants=C, relay=R, stage_label=stage, period=a.period, lead=lead, xpf_transport_edges=xpf_edges,
        me_observe_edges=a.me_observe_edges, su_first_write=a.su_first_write,
        programme=dict(words=meta_rows, segments=[dict(first=s['first'], end=s['end'], desc=s['desc']) for s in segs],
                       fused_native_capability=cap),
        plan=plan, plan_notes=notes, me_rows=rows, me_stop_cycle=stop_cycle, xpf_records=[
            {k: v for k, v in r.items() if k != 'value'} for r in xrows], xpf_stop=xpf_stop,
        cal=dict(base=base, nent=len(ents), descriptors=[f'{w:016x}' for w in dw],
                 segments={str(k): dict(first=v[0], count=v[1]) for k, v in cdesc.items()},
                 decode=[dict(delta=d, cmd=f'{c:029x}', label=l) for d, c, l in decode],
                 boot=[dict(delta=d, cmd=f'{c:029x}', label=l) for d, c, l in boot],
                 stage0=[dict(delta=d, cmd=f'{c:029x}', label=l) for d, c, l in stage0]),
        expected=dict(cmd_at_tt_ctlm=exp_cmd, local_at_tt_ctlm=exp_loc, me_issue=exp_me, rom_go_at_tt_ctlm=exp_rom,
                      native_go_at_tt_ctlm=exp_nat, xpf_arm_at_tt_ctlm=exp_xpf,
                      cmd_at_w5_pin=[dict(e, edge=e['edge'] + R['R_CMD']) for e in exp_cmd],
                      hr_rom_go_at_w5_pin=[dict(e, edge=e['edge'] + R['R_HR']) for e in exp_rom],
                      hr_xpf_arm_at_w5_pin=[dict(e, edge=e['edge'] + R['R_HR']) for e in exp_xpf],
                      boot_cmd_after_seal=[dict(edge=C['CAL_S'] + t, cmd=f'{c:029x}', label=l)
                                           for t, (d, c, l) in zip(_acc(boot), boot) if not is_tload(c)],
                      boot_tl_after_seal=[dict(edge=C['CAL_S'] + t + TL_OUT_EDGES, label=l,
                                               word=f'{tl_word(k_, d_, e_, pay):0272x}')
                                          for t, (d, c, l), (k_, d_, e_, pay) in
                                          zip([t for t, (d, c, l) in zip(_acc(boot), boot) if is_tload(c)],
                                              [x for x in boot if is_tload(x[1])], tl_tab)],
                      boot_end_after_seal=C['CAL_S'] + _acc(boot)[-1] + (TL_OUT_EDGES if tl_tab else 0),
                      stage0_local=[dict(edge=C['CAL_S'] + t + C['LOC_EDGES'], kind='EMB', label=l)
                                    for t, (d, c, l) in zip(_acc(stage0), stage0)]),
        status=status, tload=tl_rec,
        lm_head=None if head is None else {k: v for k, v in head.items() if k not in ('words', 'cal', 'xpf_rows')} | dict(
            cal=[dict(delta=d, cmd=f'{c:029x}', label=l) for d, c, l in head['cal']],
            xpf_records=[{k: v for k, v in r.items() if k != 'value'} for r in head['xpf_rows']]),
        digest=f'{digest(image):016x}', footer=f'{pw[1023]:016x}',
        not_compiled=[
            'G-C4 DV slice lowering: slice PROG image (the 457-b SU words of the SU commands\' pidx = ISA PC), STN / ROOT / '
            'STREAM / PORTS / AMAX command fields (need the DV row->slice ownership and slice-local VM address maps)',
            'stage-0 slice commands beyond the LOCAL EMB start (E calendar / embedding landing not compiled)',
            ('LM-head (stage 37) ME programme: compiled (--lm-head: segment-G calendar + G XPF, needs qfd_tt_ctlm_dv '
             'SEG_CAL 1); its SU ops still go out as broadcast SU commands (no DV slice lowering of the head)')
            if head is not None else
            'LM-head (stage 37) ME programme: not compiled (run with --lm-head; RTL needs qfd_tt_ctlm_dv SEG_CAL 1)',
            'per-layer ROM relocation needs qfd_tt_ctlm_dv STAGE_ME 1 (command_stage = running stage)'])
    if getattr(a, 'dv_lower', False):
        rec.update(dv_lower_section(rec))
    return image, rec


def dv_lower_section(rec):
    """QLB-C4 (G-C4): the DV slice lowering (tools/qwen_layerbench/dv_lower.py) of this image's programme."""
    sys.path.insert(0, str(ROOT / 'tools' / 'qwen_layerbench'))
    import dv_lower as DL
    lw = DL.lower()
    su_bc = [e['label'] for e in rec['cal']['decode'] if e['label'].startswith('SU PC') and
             int(e['label'][5:]) in lw['isa']['ssq_pcs']]
    nc = [x for x in rec['not_compiled'] if not x.startswith('G-C4 DV slice lowering')]
    nc = ['G-C4 DV slice lowering (dv_lower.py): LOWERED = slice map / SETID ids / cmd + scalar chain ages, row '
          'ownership of every matrix, slice-local VM map, PROG image + kind-3 stream words, the global RMSNorm sum of '
          'squares (per-slice SSQ, PSUM tags = golden block positions, fused ROOT r) with a collision-free scalar-chain '
          'schedule; NOT LOWERED: ' + '; '.join(lw['not_lowered'])] + nc
    nc.append('decode calendar still issues the sum-of-squares ops as broadcast SU commands (%s): dv_lower --mutant '
              'broadcast shows that schedule collides on the scalar chain (%d collisions); the calendar must take '
              "dv_lower's per-slice entries (ssq_entry) -- next step" % (', '.join(su_bc), len(DL.lower('broadcast')['expected']['collisions'])))
    if rec.get('lm_head') is None:
        nc.append('LM head: compile with --lm-head (RTL gap closed by QLB-C4b: qfd_tt_ctlm_head_static SEGCAL / '
                  'qfd_tt_ctlm_dv SEG_CAL = per-segment fixed-issue calendar + segment-G XPF schedule)')
    return dict(not_compiled=nc, dv_lowering=dict(
        tool='tools/qwen_layerbench/dv_lower.py', slices=lw['slice_map']['names'], cmd_arrival=lw['slice_map']['cmd_arrival'],
        residual_blocks=lw['ownership']['residual']['blocks_per_slice'], vm=lw['vm'], root=lw['root'],
        prog_sha256={s: hashlib.sha256(''.join(w).encode()).hexdigest() for s, w in lw['prog'].items()},
        commands=lw['commands'], ssq_entry=lw['ssq_entry'], ages=lw['ages'], die_gaps=lw['die_gaps']))


def _acc(entries):
    t, out = 0, []
    for d, _, _ in entries:
        t += d
        out.append(t)
    return out


def status_timeline(plan, R, C):
    """status the tt_ctlm pins must see (the slices' / native59's compiled responses), as level changes:
    [(edge at the tt_ctlm pin, field, value)]; fields su_busy, stn_busy (ag5), su_prog (ss5 [60:45]), native_idle."""
    ch = []                      # (edge, phase, field, value): on one edge an op's end (phase 0) precedes the next start
    for p in plan:
        if p['kind'] == 'SU':
            ch.append((p['at'] + R['R_SS'] + 1, 1, 'su_busy', 1))
            ch.append((p['at'] + R['R_SS'] + 1, 1, 'su_prog', 0))
            ch.append((p['done'], 0, 'su_busy', 0))
            ch.append((p['done'], 0, 'su_prog', p['words']))
        elif p['kind'] == 'ME':
            ch.append((p['at'] + 1, 1, 'stn_busy', 1))
            ch.append((p['done'], 0, 'stn_busy', 0))
        elif p['kind'] == 'NATIVE':
            ch.append((p['at'] + 1, 1, 'native_idle', 0))
            ch.append((p['done'], 0, 'native_idle', 1))
    ch.sort(key=lambda c: (c[0], c[1]))
    return [dict(edge=e, field=f, value=v) for e, _, f, v in ch]


def check_image(image, meta_rows, me_count, xpf_count, stage, xpf_edges):
    """the seal rules of the three consumers, on the emitted words (independent of how they were built)."""
    pw, dw = image[:PW], image[PW:]
    # ot_qwen_fixed_issue_dense_pw OWN 1
    meta = pw[1017]
    assert meta >> 32 == 0x43414C53 and (meta >> 28) & 15 == 0 and 0 < (meta >> 18) & 1023 < 61
    cnt = meta & 63
    assert 0 < cnt <= 8 and cnt == me_count
    for k in range(8):
        r = pw[976 + k]
        if k < cnt:
            assert r >> 47 == 0 and ((r >> 46) & 1) == int(k == cnt - 1) and (r >> 44) & 3 != 3
        else:
            assert r == 0
    assert pw[1016] >> 32 == 0x43414C31 and pw[1016] & 0xFFFFFFFF
    assert all(pw[k] == 0 for k in (1019, 1020, 1021))
    f = pw[1023]
    assert f >> 32 == 0x58504631 and (f >> 13) & ((1 << 19) - 1) == 0 and f & 3 == 2
    assert (f >> 6) & 63 == (meta >> 12) & 63 == stage and 0 < (f >> 2) & 15 == xpf_count <= 4
    # XPF loader: records 1004..1015 (3 beats, top nibble 0, LSB valid, same stage; zero padding after)
    pad = False
    for n in range(4):
        v = pw[1004 + 3 * n] | (pw[1005 + 3 * n] << 64) | (pw[1006 + 3 * n] << 128)
        assert pw[1006 + 3 * n] >> 60 == 0
        if v == 0:
            pad = True
            continue
        assert not pad and v & 1 and (v >> 86) & 63 == stage and (v >> 84) & 3 != 0
    assert pw[1022] >> 32 == 0x58504654 and pw[1022] & 0xFFFFFFFF
    # qfd_dv_cmd_cal seal
    d0 = dw[0]
    base, nent = (d0 >> 16) & 1023, d0 & 511
    assert d0 >> 32 == 0x43414C44 and (d0 >> 26) & 63 == 0 and (d0 >> 9) & 127 == 0 and base % 8 == 0 and nent
    assert base + 2 * nent <= 976 and base >= 16 * meta_rows and dw[5] == dw[6] == dw[7] == 0
    for s in range(1, 5):
        w = dw[s]
        assert w >> 32 == 0
        if w & 0xFFFF:
            assert (w >> 16) & 3 == 0 and ((w >> 16) & 0xFFFF) + (w & 0xFFFF) <= nent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--program', default=DEF_PROGRAM)
    ap.add_argument('--lowering', default=DEF_LOWERING)
    ap.add_argument('--token-path', default=DEF_TOKEN_PATH)
    ap.add_argument('--relay', default=DEF_RELAY)
    ap.add_argument('--lane-ages', default=None,
                    help='die lane ages in edges {R_CMD, R_HR, R_SS, R_AG} (the land plan); default: relay hop counts')
    ap.add_argument('--stage', type=int, default=1, help='image stage label (CALS / footer / XPF records)')
    ap.add_argument('--sys-face-events', default=DEF_SF_EVENTS, help='the compiled T calendar (stage starts)')
    ap.add_argument('--period', type=int, default=None,
                    help='decode stage window (default: the shortest decode-stage spacing of the T calendar)')
    ap.add_argument('--lead-margin', type=int, default=2)
    ap.add_argument('--xpf-transport-edges', type=int, default=None,
                    help='tt_ctlm XPF_TRANSPORT_EDGES (default 1 + R_HR: the hr register + the hr relays)')
    ap.add_argument('--me-observe-edges', type=int, default=1, help='head fixed issue -> actual_me_observe edges')
    ap.add_argument('--su-first-write', type=int, default=12, help='SU command at the W5 pin -> its first VM write')
    ap.add_argument('--dv-lower', action='store_true', help='attach the DV slice lowering (dv_lower.py, G-C4)')
    ap.add_argument('--lm-head', action='store_true',
                    help='compile the LM-head (stage 37) ME programme at base = decode words: segment-G calendar '
                         'PW984..993 + G XPF PW993..1003 (QLB-C4b; RTL qfd_tt_ctlm_dv SEG_CAL 1)')
    ap.add_argument('--head-plan', default=HEAD_PLAN, help='token source plan (head_geometry + head_profiles)')
    ap.add_argument('--tload', action='store_true',
                    help='QLB-C4b: compile the slice table words (dv_lower PROG streams) into the image as BOOT TLOAD '
                         'entries + PW blocks (the die load path tt_ctlm.tl -> dvs_W5.st_wi)')
    a = ap.parse_args()
    try:
        image, rec = compile_image(a)
    except (CompileError, AssertionError) as e:
        print(f'CTLM_IMAGE REFUSED: {e}')
        return 2
    except Exception as e:                       # dv_lower.LowerError
        if type(e).__name__ != 'LowerError':
            raise
        print(f'CTLM_IMAGE REFUSED (dv lowering): {e}')
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'program.memh').write_text(''.join(f'{w:016x}\n' for w in image))
    (out / 'ctlm_image.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(digest=rec['digest'], me_rows=len(rec['me_rows']), xpf=len(rec['xpf_records']),
                          cal_entries=rec['cal']['nent'], base=rec['cal']['base'], stop=rec['me_stop_cycle'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
