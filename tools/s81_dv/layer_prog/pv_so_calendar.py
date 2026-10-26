"""Static source calendar for the two landed P.V halves and local SO ingress.

Actual observed route ages are required. No field is inferred from an expected
or closed view alone. This only books source transport/control; it does not
claim numerical or physical qualification of the whole layer.
"""
from __future__ import annotations


def plan_halves(east_earliest, west_earliest, route_ages, cfg_capture_edge, parameter_last_pin_edge, gap=1):
    keys=('E_E','E_W','W_E','W_W')
    if set(route_ages)!=set(keys) or any(type(route_ages[k]) is not int or route_ages[k]<0 for k in keys):
        raise ValueError('Four actual nonnegative integer route/landing ages required')
    if any(type(x) is not int or x<0 for x in (east_earliest,west_earliest,cfg_capture_edge,parameter_last_pin_edge,gap)):
        raise ValueError('Calendar events must be nonnegative integer rising edges')
    ea=max(route_ages['E_E'],route_ages['E_W']);wa=max(route_ages['W_E'],route_ages['W_W'])
    ed=east_earliest;wd=max(west_earliest,ed+ea+320+gap-wa)
    er=ed+ea;wr=wd+wa
    if min(er,wr)-cfg_capture_edge<3 or max(er,wr)-cfg_capture_edge>65535:
        raise ValueError('Join first-record dates exceed exact16-bit source field or configuration guard')
    launch=max(wr+319+2,parameter_last_pin_edge+1)
    return dict(east_departure=ed,west_departure=wd,east_arrival=er,west_arrival=wr,
        route_age=route_ages,extra_padding={k:(ea if k[0]=='E' else wa)-route_ages[k] for k in keys},
        entry_E=dict(local_first=er-cfg_capture_edge,peer_first=wr-cfg_capture_edge),
        entry_W=dict(local_first=wr-cfg_capture_edge,peer_first=er-cfg_capture_edge),
        cfg_capture_edge=cfg_capture_edge,joined_records=640,source_records_per_half=320,
        launch_pin_edge=launch,first_generated_q=launch+2,last_generated_q=launch+535,
        generated_words=534,generated_frames=17,job_gate_added_frames=17,
        calendar_qualified=False,
        remaining='Patch each half GO PVO and its job completion to these departures; book originalSOT14 '
                  'beforeSE with actual write/read/retire edges; prove actual composed numerical programme')


def control_frames(owner,position,se_jid,so_jid,local_first,peer_first,parameters):
    """Return privateCFG15, PARAM15 and LAUNCH15 words for actual entry q.

    Parameters must be the position-owned obase/coslo/coshi/sinlo/sinhi rows.
    This function encodes bits and performs no tensor arithmetic.
    """
    from layer_prog.lower_svc import hdr
    if not (type(owner) is int and 0<=owner<2**20 and type(position) is int and 0<=position<2**21):
        raise ValueError('Owner/position outside actual source field')
    if any(type(v) is not int or not 0<=v<256 for v in (se_jid,so_jid)):
        raise ValueError('SE/SO identity outside8-bit source field')
    if any(type(v) is not int or not 3<=v<65536 for v in (local_first,peer_first)) or abs(local_first-peer_first)<320:
        raise ValueError('Two320-edge windows must be disjoint and follow configuration')
    if len(parameters)!=5 or any(type(v) is not int or not 0<=v<2**512 for v in parameters):
        raise ValueError('Actual five512-bit parameter rows required')
    def h(subop,n,spec):
        return hdr(15,n,owner&255,spec=spec|(subop<<444),pos=position,user=(owner>>8)&1023)
    cfg=owner|(se_jid<<20)|(so_jid<<28)|(local_first<<36)|(peer_first<<52)
    return dict(CFG=[h(0,0,cfg)],PARAM=[h(1,5,owner)]+list(parameters),LAUNCH=[h(2,0,owner)])
