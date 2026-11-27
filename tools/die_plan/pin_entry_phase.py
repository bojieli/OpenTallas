"""Strap-selected reset/START pin entry phase (FABLE-FIX-HEAD-RESET 2026-11-17).

Mechanism it answers: a die reset/START seam (parent rst_o / start_o relay -> child pin entry) fails hold or setup
because the two partitions sit on different clock regions whose insertion phases differ by up to two periods.  The
data delay is short and constant; only the phase is wrong.  Delay cells or per-phase views cannot follow a new clock.

Form (opt-in per type, reset.pin_entry_phase = true):
  * one cell ot_dp_rrelay_ph per entry (reset and START): a rising capture, a falling capture, one static select
    `ph` (the 1-bit ID strap strap_rst_ph, tied per instance at the die top, false path), one rising local handoff.
    The type view is phase-agnostic: after any clock regeneration only strap values and labels change.
  * per instance, partitions[].reset_entry_phase = h (integer half cycles): the declared capture edge is h * T/2
    EARLIER than the nominal next rising edge of the launch edge.  h odd = falling capture (strap 1).  The whole-cycle
    part is a label only: die STA checks the seam at that edge (setup multiplier 1 - floor(h/2)) and the published
    wavefront release moves by -ceil(h/2) cycles against the two-stage nominal entry.
No delay cell, no clock fork, no new type.  Timing of each seam is proven by die STA on real views, not here.
"""
import copy
import math

STRAP = 'strap_rst_ph'
CELL = 'ot_dp_rrelay_ph'
CELL_RTL = '''(* keep_hierarchy, keep *)
module ot_dp_rrelay_ph (input wire clk, input wire ph, input wire d, output reg q);
    (* keep *) reg cap_r;
    (* keep *) reg cap_f;
    always @(posedge clk) cap_r <= d;
    always @(negedge clk) cap_f <= d;
    always @(posedge clk) q <= ph ? cap_f : cap_r;
endmodule
'''
NOMINAL_STAGES = 2          # cap_r + q at h = 0

# SEAMHOLD-HB4-HOSTN-RST (HEAD-INT-R2 11-26, opt-in reset.pin_entry_hb4 {"reset": N, "start": M}, absent = byte-identical):
# the same phase entry with N kept HB4xp67 (gen_rtl.ot_dp_hd, instance u_hdly_in) between the pin and BOTH capture registers.
# A zero-logic reset / START seam whose selected capture sits FF-hold-negative (host_n sp5 -> u_rst_in/cap_f -1.446 ps)
# gains ~N x 30 ps with no FF and no whole cycle (identity in RTL); the pin still feeds only the entry cell's d (por_gate G3,
# bind_component reset edge unchanged).  The pad is also on the unselected capture register (false path, no cost).
CELL_HB = 'ot_dp_rrelay_ph_hb'
CELL_RTL_HB = '''(* keep_hierarchy, keep *)
module ot_dp_rrelay_ph_hb #(parameter integer N = 1) (input wire clk, input wire ph, input wire d, output reg q);
    wire dh;
    ot_dp_hd #(.W(1), .N(N)) u_hdly_in (.a(d), .y(dh));
    (* keep *) reg cap_r;
    (* keep *) reg cap_f;
    always @(posedge clk) cap_r <= dh;
    always @(negedge clk) cap_f <= dh;
    always @(posedge clk) q <= ph ? cap_f : cap_r;
endmodule
'''


def hb4_spec(t):
    return (t.get('reset') or {}).get('pin_entry_hb4')


def uses_hb(raw):
    return any(isinstance(hb4_spec(t), dict) and (hb4_spec(t).get('reset', 0) or hb4_spec(t).get('start', 0))
               for t in (raw.get('partition_types') or {}).values())


def hb_count(T, signal):
    return int((T.get('pin_entry_hb4') or {}).get(signal, 0))


def enabled(t):
    return (t.get('reset') or {}).get('pin_entry_phase') is True


def uses(raw):
    return any(enabled(t) for t in (raw.get('partition_types') or {}).values())


def configure(P, tn, T, error=ValueError):
    flag = (P.types[tn].get('reset') or {}).get('pin_entry_phase', False)
    if type(flag) is not bool:
        raise error(f'type {tn}: reset.pin_entry_phase must be boolean')
    if not flag:
        if hb4_spec(P.types[tn]) is not None:
            raise error(f'type {tn}: reset.pin_entry_hb4 needs reset.pin_entry_phase')
        return T
    if T.get('entry') != 'relayed':
        raise error(f'type {tn}: pin_entry_phase requires a synchronous relayed entry')
    for other in ('pin_entry_fall', 'pin_entry_delay', 'pin_entry_handoff', 'pin_root_copies', 'pin_start_copies'):
        if T.get(other):
            raise error(f'type {tn}: pin_entry_phase cannot combine with {other}')
    straps = {s['name']: s['width'] for s in P.types[tn].get('id_straps', [])}
    if straps.get(STRAP) != 1:
        raise error(f'type {tn}: pin_entry_phase needs the 1-bit id_strap {STRAP}')
    spec = hb4_spec(P.types[tn])
    out = dict(T, pin_entry_phase=True, pin_entry_added_flops=2 * (1 + int(bool(T.get('start')))))
    if spec is not None:
        if (not isinstance(spec, dict) or not set(spec) <= {'reset', 'start'} or not spec
                or any(type(v) is not int or not 0 <= v <= 8 for v in spec.values())):
            raise error(f'type {tn}: reset.pin_entry_hb4 must be {{"reset": 0..8, "start": 0..8}}')
        if spec.get('start') and not T.get('start'):
            raise error(f'type {tn}: pin_entry_hb4 START needs a broadcast input')
        out['pin_entry_hb4'] = dict(spec)
    return out


def port_text(T):
    """extra port connection of the entry cell instance."""
    return f', .ph({STRAP})' if T.get('pin_entry_phase') else ''


def half_cycles(part):
    return int(part.get('reset_entry_phase', 0))


def strap_value(h):
    return h % 2


def release_delta(h):
    """whole cycles added to the nominal two-stage entry: the handoff q rises ceil(h/2) cycles earlier."""
    return -math.ceil(h / 2)


def setup_multiplier(h):
    """die STA setup multicycle of the selected capture (default 1): rising h even, falling h odd."""
    return 1 - h // 2


def plan_errors(raw):
    """plan-level consistency: the field only on instances of an opted-in type, strap value = h mod 2."""
    errs = []
    types = raw.get('partition_types') or {}
    for p in raw.get('partitions', []):
        on = enabled(types.get(p.get('type'), {}))
        if 'reset_entry_phase' in p and not on:
            errs.append(f"partition {p.get('name')}: reset_entry_phase without type reset.pin_entry_phase")
        if on:
            h = half_cycles(p)
            got = (p.get('id_straps') or {}).get(STRAP)
            if got != strap_value(h):
                errs.append(f"partition {p.get('name')}: id_strap {STRAP}={got} != reset_entry_phase {h} mod 2")
    return errs


def part_delta(P, name):
    p = P.parts[name]
    return release_delta(half_cycles(p)) if enabled(P.types[p['type']]) else 0


def sta_rows(P, entries=('u_rst_in', 'u_run_in')):
    """per opted-in instance: the selected capture register, its setup multiplier and the unselected register
    (static-mux masked, false path).  The die STA applies these to the seam endpoints; nothing else is waived."""
    rows = []
    for name, p in sorted(P.parts.items()):
        if not enabled(P.types[p['type']]):
            continue
        h = half_cycles(p)
        sel, off = ('cap_f', 'cap_r') if h % 2 else ('cap_r', 'cap_f')
        for e in entries:
            rows.append(dict(part=name, type=p['type'], entry=e, half_cycles=h, strap=strap_value(h),
                             capture=f'{e}/{sel}', setup_multiplier=setup_multiplier(h),
                             false_path_to=f'{e}/{off}', release_delta_cycles=release_delta(h)))
    return rows


def sta_tcl_lines(rows):
    """die STA constraints of the declared edges.  Every row must resolve BOTH capture registers of the instance
    (flattened names u_rst_in/cap_r... or u_rst_in.cap_r...); a miss is printed as OT_ENTRY_PHASE_MISS and exits,
    so a renamed register can never silently leave a seam on the wrong edge."""
    out = ['proc ot_ep_pins {part reg} { foreach sep {/ .} { set e [string map [list / $sep] $reg]; '
           'set p [get_pins -quiet "$part/*$e*/D"]; if {[llength $p]} { return $p } }; '
           'puts "OT_ENTRY_PHASE_MISS $part $reg"; exit 3 }']
    for r in rows:
        out.append(f"set_false_path -to [ot_ep_pins {{{r['part']}}} {{{r['false_path_to']}}}]")
        if r['setup_multiplier'] != 1:
            out.append(f"set_multicycle_path {r['setup_multiplier']} -setup -to "
                       f"[ot_ep_pins {{{r['part']}}} {{{r['capture']}}}]")
    out.append(f'puts "OT_ENTRY_PHASE rows {len(rows)}"')
    return out


def main(argv):
    """pin_entry_phase.py rows PLAN.json OUT.json : the per-instance die STA rows of a plan (die_sta.py --entry-phase)."""
    import json
    import sys
    from pathlib import Path
    if len(argv) != 4 or argv[1] != 'rows':
        print(main.__doc__, file=sys.stderr)
        return 2
    import schema
    P = schema.Plan(json.loads(Path(argv[2]).read_text()), argv[2])
    errs = plan_errors(P.raw)
    if errs:
        print('\n'.join(errs), file=sys.stderr)
        return 1
    rows = sta_rows(P)
    Path(argv[3]).write_text(json.dumps(dict(schema='opentallas.pin_entry_phase_rows.v1', rows=rows), indent=1) + '\n')
    print(f'{argv[3]}: {len(rows)} rows')
    return 0


def summary(T):
    if not T.get('pin_entry_phase'):
        return {}
    hb = ({} if not T.get('pin_entry_hb4') else dict(pin_entry_hb4=dict(
        cell='HB4xp67_ASAP7_75t_R', reset=hb_count(T, 'reset'), start=hb_count(T, 'start'), added_flops=0,
        added_whole_cycles=0)))
    return dict(**hb, pin_entry_phase=dict(cell=CELL, strap=STRAP, added_flops=T['pin_entry_added_flops'],
                                     nominal_entry_stages=NOMINAL_STAGES, delay_cells=0, clock_forks=0,
                                     per_instance='partitions[].reset_entry_phase (half cycles); release delta = '
                                                  '-ceil(h/2); die STA proves each seam'))


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
