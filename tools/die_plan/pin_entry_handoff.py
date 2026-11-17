"""Structural entry handoff, with an explicitly separate planned physical phase fork.

The functional form adds one local-clock stage. A physical build must fork ONLY
capture CLK pins after ordinary CTS/route and measure incoming, capture->handoff,
and outgoing paths. This module never claims that GEN has built the phase fork.
"""
import copy
CELL_RTL='''(* keep_hierarchy, keep *)
module ot_dp_rrelay_handoff(input wire clk,input wire d,output reg q);
    (* keep *) reg cap;
    always @(posedge clk) cap<=d;
    always @(posedge clk) q<=cap;
endmodule
'''


def uses(raw):
    return any(t.get('reset',{}).get('pin_entry_handoff') is not None
               for t in (raw.get('partition_types') or {}).values())


def configure(P,tn,T,error=ValueError):
    s=P.types[tn].get('reset',{}).get('pin_entry_handoff')
    if s is None:return T
    if (not isinstance(s,dict) or set(s)!={'clock_buffers','physical_form'} or
        type(s['clock_buffers'])is not int or s['clock_buffers']<1 or
        s['physical_form']!='post_route_branch_fork'):
        raise error('pin_entry_handoff needs positive clock_buffers and explicit post_route_branch_fork')
    if T.get('entry')!='relayed' or not T.get('start'):
        raise error('pin_entry_handoff requires synchronous relayed reset and START')
    if T.get('pin_entry_fall') or T.get('pin_entry_delay') or T.get('pin_root_copies') or T.get('pin_start_copies'):
        raise error('pin_entry_handoff cannot silently combine other entry forms')
    return dict(T,pin_entry_handoff=copy.deepcopy(s))


def physical_contract(T):
    s=T.get('pin_entry_handoff')
    if not s:return {}
    return dict(mode='post_route_branch_fork',status='PLANNED_NOT_BUILT_BY_GEN',
                clock_cell='BUFx4_ASAP7_75t_R',clock_buffers=s['clock_buffers'],
                capture_clock_pin_pattern=r'(^|[/.])u_(rst|run)_in[/.]cap[^/]*[/.]CLK$',
                local_handoff_clock_pin_pattern=r'(^|[/.])u_(rst|run)_in[/.]q[^/]*[/.]CLK$',
                required_capture_pins=2,required_local_handoff_pins=2,
                shared_source='original local entry clock branch',
                timing='actual incoming + capture-to-handoff + outgoing TT/FF and pulse/period; no CTS after fork',
                added_whole_boot_cycles=1,added_arithmetic_cycles=0)


def summary(T):
    s=T.get('pin_entry_handoff')
    return {} if not s else dict(pin_entry_handoff=dict(added_flops=2,planned_clock_buffers=s['clock_buffers'],
                        planned_area_um2=2*.2916+s['clock_buffers']*.10206,
                        added_whole_boot_cycles=1,added_arithmetic_cycles=0,
                        physical_contract=physical_contract(T)))
