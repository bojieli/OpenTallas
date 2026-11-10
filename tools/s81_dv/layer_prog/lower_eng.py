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
RETURN_AGE = 1536  # main's default of dsdv_eng_rr_e; measured first/last fragment and lookup II are RETURN_AGE + 44 / 139 / 64


def latency(return_age):
    """the row-read table at one lookup RETURN_AGE (the fixed offsets are measured relative to it)"""
    return dict(win=4, first_request=26, return_age=return_age, first_fragment=return_age + 44,
                last_fragment=return_age + 139, ii=return_age + 64)


ENG_RE = r'(?<![\w$])(?<!module )(dsdv_eng_rr(?:_e)?)\s*(?:#\s*\((.*?)\))?\s*(\w+)\s*\('


def bound_return_age(rtl_dir):
    """S81-PLAN-1 11-10 (TOK-VERIFY-1: main schedules 1536, the candidate eng partition is 640): the lookup RETURN_AGE
    of a bind = the explicit .RETURN_AGE(n) on every dsdv_eng_rr / dsdv_eng_rr_e instance in its emitted RTL.  At least
    one instance, every one explicit, all equal; else refuse (never fall back to this module's constant)."""
    import re
    from pathlib import Path
    found = []
    for f in sorted(Path(rtl_dir).glob('*.sv')) + sorted(Path(rtl_dir).glob('*.v')):
        text = f.read_text(errors='replace')
        if 'dsdv_eng_rr' not in text:
            continue
        for m in re.finditer(ENG_RE, text, re.S):
            v = re.search(r'\.RETURN_AGE\s*\(\s*(\d+)\s*\)', m.group(2) or '')
            if v is None:
                raise ValueError(f'bound eng instance {m.group(3)} ({m.group(1)}, {f.name}) has no explicit RETURN_AGE')
            found.append((f.name, m.group(3), int(v.group(1))))
    if not found:
        raise ValueError(f'no dsdv_eng_rr / dsdv_eng_rr_e instance in the bound RTL {rtl_dir}')
    ages = {a for _, _, a in found}
    if len(ages) != 1:
        raise ValueError(f'bound eng instances disagree on RETURN_AGE: {found}')
    return ages.pop(), found


def lat_for(ctx=None):
    """the table the compiler schedules: the bind's own RETURN_AGE under --bound-data (ctx['bound_eng']), else the
    OT_BOUND_DATA bind's (tools that import this table at module level), else main's constant"""
    import os
    from pathlib import Path
    if ctx is not None and ctx.get('bound_eng') is not None:
        return latency(ctx['bound_eng']['return_age'])
    if os.environ.get('OT_BOUND_DATA'):
        return latency(bound_return_age(Path(os.environ['OT_BOUND_DATA']) / 'rtl')[0])
    return latency(RETURN_AGE)


LAT = lat_for()


def check_programme(record, rtl_dir):
    """a compiled programme's Engram table (its bound_eng.json record, or a latency dict) against a bind's RTL;
    raises on any difference (a programme compiled at another RETURN_AGE expects the rows early or late)"""
    lat = record.get('latency', record)
    want = latency(bound_return_age(rtl_dir)[0])
    diff = {k: (lat.get(k), v) for k, v in want.items() if lat.get(k) != v}
    if diff:
        raise ValueError(f'programme Engram latency differs from the bind RTL (programme, bind): {diff}')
    return want


def lower(die, op, ctx):
    t = int(ctx.get('t_issue', 0))
    name = op['op']
    ev = []
    LAT = lat_for(ctx)
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
