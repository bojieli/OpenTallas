#!/usr/bin/env python3
"""S81-RTLGAP/RG-ENG (10-21): family lowering of the Engram row read (eng.lead_flit / eng.hash / eng.hbm_read) onto
dsdv_eng_rr + 16 dsdv_eng_tap (rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr.sv; bench results/rtl/s81_rtlgap_eng_1021).

The row read has NO compiler-written rows: it is triggered by the user's token start on the die (f_ks, the s_7N ->
seqhost start lane) and runs at fixed offsets from that edge (measured, tb_dsdv_eng_rr TB_ENG_RR_LAT, CS 2 relay stages a
chain hop):
    window (compiler slot = rotating 0..7)      f_ks + 4
    first one-atom HBM request (54 a window)    f_ks + 26
    responses at the lookup engine              age <= RETURN_AGE 512 (measured 346 / 394 / 435 at HBM 60 / 100 / 160 ns)
    first / last XQ fragment on column 6's rung f_ks + 556 / + 651 (24 x beats x 4 fragments, both rung directions)
    lookup II                                   576 edges: Engram token starts of one die >= 576 edges apart
The compiler's duties: (1) the svc calendar leaves every PC free of svc words while its tap holds the Engram reader
window (f_ks + 27 .. about f_ks + 140); (2) column 6's rung carries no other V word in [f_ks + 555, f_ks + 651]; (3) the
idx reader windows may overlap but no reader word may share an edge with an Engram word on a lane (tap fault);
(4) the frames' engram.wkv phase starts after the 96 x beats (this rank's 24 + 72 from the TP4 all-gather,
eng.rows_allgather = TOK.DS.XDIE) are in the streamers; (5) the HBM image places the Engram tables at sector PCBASE of
every PC, atom-interleaved (atom a -> PC a[4:0], sector PCBASE + a >> 5).
Status PARTIAL until the die netlist binds the cluster (NOTICE in lanes/S81-LINK5.md, lanes/LEAD-S81.md) and the closed
lookup view is re-kitted at RETURN_AGE 512 (closed view 84352a2c7 is RETURN_AGE 128 < the measured service age).
"""
OPS = [r'^eng\.(lead_flit|hash|hbm_read)$']
UNIT = 'dsdv_eng_rr (window former + dsfd_engram_lkp_static14 + head + XQ join) + dsdv_eng_tap x16 on the reader links'
INSTS = ['u_eng (dsdv_eng_rr)'] + [f'u_etap_{k:02d} (dsdv_eng_tap{"_w" if k == 0 else ""})' for k in range(16)]
BENCH = 'results/rtl/s81_rtlgap_eng_1021'
LAT = dict(win=4, first_request=26, return_age=512, first_fragment=556, last_fragment=651, ii=576)


def lower(die, op, ctx):
    t = int(ctx.get('t_issue', 0))
    name = op['op']
    ev = []
    if name == 'eng.lead_flit':
        ev.append(dict(cycle=t, inst='u_eng', port='f_ks', dir='in', kind='KS', tag=name, plan_only=True,
                       payload='{start, user, tok, pos} of the token start (tap of the s_7N -> seqhost start lane)'))
    elif name == 'eng.hash':
        ev.append(dict(cycle=t + LAT['win'], inst='u_eng', port='(window -> lookup)', dir='int', kind='ENG', tag=name,
                       plan_only=True, payload='4 compressed ids, slot'))
    else:
        ev.append(dict(cycle=t + LAT['first_fragment'], inst='u_eng', port='vo_s / vo_n (column 6 V rung)', dir='out',
                       kind='XQ', tag=name, plan_only=True, payload='24 XQ x beats idx 24 rank .. +23, 4 fragments each'))
    return dict(status='PARTIAL', unit=UNIT, insts=INSTS, bench=BENCH, rows=[], templates=[], gunit_rows=[],
                svc_jobs=[], files={}, events=ev, latency=LAT,
                gap=dict(module='die netlist (S81-LINK5 / LEAD-S81-G3 G4)', port='u_eng / u_etap_* bindings',
                         missing='dsdv_eng_rr + 16 taps not bound in the 72-frame die yet; closed lookup view is '
                                 'RETURN_AGE 128, needs the RETURN_AGE 512 re-kit (critical tile: coordinator)'))
