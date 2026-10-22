#!/usr/bin/env python3
"""pair_check: the per-pair die hop statement and the generators' gate.  Run: python3 tools/hier_contract/test_pair_check.py"""
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 's81'))
import pair_check as P          # noqa: E402
import die_hop_gate as HG       # noqa: E402


def reg(R, O, S, l=None, h=None, spread=10.0, edge='r', clk='ck', R_ff=None):
    return dict(view='x', clocks={clk: dict(R_tt=R, R_ff=R * 0.8 if R_ff is None and R is not None else R_ff, spread=spread, n=1)},
                buses=dict(i=dict(dir='input', bits=4, arcs=[dict(clk=clk, edge=edge, O=None, l=None, S=S, h=h)]),
                           o=dict(dir='output', bits=4, arcs=[dict(clk=clk, edge=edge, O=O, l=l, S=None, h=None)])),
                clock_out={})


# a station of the S81 forwarded lane (dsfd_stnh_512x1 TT / FF numbers): negedge capture, inverted forwarded clock
STN = dict(view='stn', clocks={'fi': dict(R_tt=93.3, R_ff=71.0, spread=14.0, n=512)},
           buses=dict(di=dict(dir='input', bits=512, arcs=[dict(clk='fi', edge='f', O=None, l=None, S=-61.5, h=84.2)]),
                      do=dict(dir='output', bits=512, arcs=[dict(clk='fi', edge='f', O=216.1, l=128.3, S=None, h=None)])),
           clock_out=dict(fo=dict(clk='fi', sense='inv', tt=dict(rr=[3.3, 3.3], rf=[146.1, 146.1], fr=[152.1, 152.1], ff=[185.7, 185.7]),
                                  ff=dict(rr=[2.3, 2.3], rf=[110.3, 110.3], fr=[112.9, 112.9], ff=[135.7, 135.7]))))
T = dict(PIN=reg(100.0, 100.0 + 180.0, 150.0 - 100.0, l=100.0 * 0.8 + 120.0, h=100.0 * 0.8 - 60.0),       # o 180, s 150: C 330
         SLOW=reg(120.0, 120.0 + 420.0, 400.0 - 120.0, l=96.0 + 300.0, h=96.0 - 60.0),                   # o 420, s 400
         DEEP=reg(400.0, 400.0 + 180.0, 150.0 - 400.0, l=320.0 + 120.0, h=320.0 - 60.0),                 # R over the level
         RACE=reg(100.0, 100.0 + 180.0, 150.0 - 100.0, l=80.0 + 20.0, h=80.0 + 40.0),                    # l - h = -20
         NOINS=reg(None, 300.0, 50.0), STN=STN)
ok = fail = 0


def expect(name, got, want, tol=0.11):
    global ok, fail
    good = (got == want) if not isinstance(want, float) else (got is not None and abs(got - want) <= tol)
    ok += good
    fail += not good
    print(('PASS ' if good else 'FAIL ') + name + ('' if good else f': got {got!r}, want {want!r}'))


die = P.Die(T, {})
hop = lambda ma, mb, um, a='a', b='b', pa='o', pb='i': dict(a=(a, ma, pa), b=(b, mb, pb), um=um)

# ---- placeholders: the flat rule, exactly
r = P.check(die, hop('X', 'Y', 500.0))
expect('two placeholders pass at 500 um', (r['model'], r['status']), ('DEFAULT', 'pass'))
expect('two placeholders fail at 500.1 um', P.check(die, hop('X', 'Y', 500.1))['status'], 'fail')
expect('placeholder share', round(P.SHARE, 2), 151.67)
# ---- TREE, both real
r = P.check(die, hop('PIN', 'PIN', 400.0))
expect('pin-registered pair: reach (683.33 - 330) / 0.76', r['reach_um'], 464.9)
expect('pin-registered pair at 400 um: setup margin', r['setup_ps'], 683.33 - 330 - 304.0)
expect('pin-registered pair at 400 um: hold margin', r['hold_ps'], (200.0 - 80.0) + 0.112 * 400.0 - (20.0 - 80.0) - 100.0)
expect('pin-registered pair passes at 464 um', P.check(die, hop('PIN', 'PIN', 464.0))['status'], 'pass')
expect('... and fails at 466 um although under 500', P.check(die, hop('PIN', 'PIN', 466.0))['status'], 'fail')
r = P.check(die, hop('SLOW', 'SLOW', 10.0))
expect('two closed tiles that do not compose: o + s = 820 > 683', (r['status'], r['reach_um'] < 0), ('fail', True))
r = P.check(die, hop('DEEP', 'PIN', 100.0))
expect('a tile deeper than the level pays SKEW 150', (r['skew'], r['avail']), (150.0, 623.3))
r = P.check(die, hop('PIN', 'RACE', 100.0))
expect('hold-only miss is reported as hold', (r['status'], r['hold_ps'] < 0), ('hold', True))
# ---- one real end: the placeholder takes the flat share
r = P.check(die, hop('PIN', 'Y', 400.0))
expect('half-real pair: o 180 + share', (r['model'], r.get('half'), r['reach_um']), ('TREE', True, round((683.333 - 180 - P.SHARE) / 0.76, 1)))
# ---- no estimates
r = P.check(die, hop('NOINS', 'PIN', 100.0))
expect('a clock tree without a measured insertion is not judged', (r['model'], r['status']), ('UNMEASURED', 'n/e'))
expect('no pin geometry is not judged', P.check(die, hop('PIN', 'PIN', None))['model'], 'NOPIN')
# ---- forwarded clock: B's clock pin is driven by A's forwarded clock output
dfw = P.Die(T, {}, {('b', 'fi'): ('a', 'fo', 400.0, 'f_ab')})
r = P.check(dfw, hop('STN', 'STN', 400.0, pa='do', pb='di'))
expect('forwarded link model / window T/2 / inverted', (r['model'], r['window'], r['sense']), ('FWD', 416.7, 'inverted'))
expect('forwarded setup margin', r['setup_ps'], 416.667 + 146.1 - 60 - 216.1 + 61.5 + 0.76 * 400 * (0.95 - 1.05))
expect('forwarded hold margin', r['hold_ps'], 128.3 + P.W_FF * 400 * 0.95 + 416.667 - 84.2 - 110.3 - P.W_FF * 400 * 1.05 - 25.0)
expect('forwarded link passes', r['status'], 'pass')
# the same two stations on ONE tree would race (l - h = 128.3 - 84.2 = 44 < 100): the audit's min_delay flag
r = P.check(die, hop('STN', 'STN', 400.0, pa='do', pb='di'))
expect('same stations on a common tree: hold fails', (r['model'], r['status']), ('TREE', 'hold'))
# ---- unrelated clock sources
dx = P.Die(T, {}, {('a', 'ck'): ('p', 'x', 1.0, 'n1'), ('b', 'ck'): ('q', 'y', 1.0, 'n2')})
expect('clock crossing is not judged as a synchronous hop', P.check(dx, hop('PIN', 'PIN', 100.0))['status'], 'cross')
dn = P.Die(T, {}, {}, {('a', 'ck'): 'n_clk', ('b', 'ck'): 'n_clk_hbm'})
expect('two tree nets of different domains cross', P.check(dn, hop('PIN', 'PIN', 100.0))['status'], 'cross')
# ---- fixes
co, cs = P.relay_class(T, '^PIN$')
expect('relay class residuals', (co, cs), (180.0, 150.0))
r = P.check(die, hop('PIN', 'PIN', 480.0))
expect('15 um over: re-plan', P.fix(r, 480.0, co, cs)['fix'], 'replan')
r = P.check(die, hop('PIN', 'PIN', 700.0))
f = P.fix(r, 700.0, co, cs)
expect('700 um between pin-registered tiles: one relay', (f['fix'], f['relays'], f['cycles']), ('relay', 1, 1))
r = P.check(die, hop('PIN', 'PIN', 1500.0))
expect('1,500 um: three relays', P.fix(r, 1500.0, co, cs)['relays'], 3)
r = P.check(die, hop('SLOW', 'PIN', 300.0))        # o 420: reach to a relay (683.3 - 420 - 150) / 0.76 = 149 um
f = P.fix(r, 300.0, co, cs)
expect('slow launch, 300 um: one relay inside its 149 um reach', (f['fix'], f['relays'], f['reach_src_to_relay_um']), ('relay', 1, 149.1))
T['DEAD'] = reg(100.0, 100.0 + 560.0, 50.0)                                 # o 560: not even a relay abutted closes
r = P.check(die, hop('DEAD', 'PIN', 50.0))
f = P.fix(r, 50.0, co, cs)
expect('launch that no abutted relay can take: pin register in the source tile', (f['fix'], f['pinreg'], f['cycles']), ('pinreg', ['src'], 1))
# ---- the generators' gate
g = P.Gate(table=T, default_um=500.0)
expect('gate: placeholders keep the flat limit', g.limit('a', 'X', 'o', 'b', 'Y', 'i'), 500.0)
expect('gate: a real pair gets its reach', g.limit('a', 'PIN', 'o', 'b', 'PIN', 'i'), 464.9)
expect('gate: never looser than the flat limit', P.Gate(table=dict(F=reg(50.0, 50.0 + 60.0, 40.0 - 50.0)), default_um=500.0).limit('a', 'F', 'o', 'b', 'F', 'i'), 500.0)
expect('gate: unmeasured insertion keeps the flat limit', g.limit('a', 'NOINS', 'o', 'b', 'PIN', 'i'), 500.0)
gf = P.Gate(table=T, default_um=500.0, buses=[('f_ab', 'fclk', 1, [('a', 'fo'), ('b', 'fi')])])
expect('gate: a forwarded link is judged as one (ceiling 500)', gf.limit('a', 'STN', 'do', 'b', 'STN', 'di'), 500.0)
expect('gate without a table = the flat rule', P.Gate(table={}, default_um=500.0).limit('a', 'PIN', 'o', 'b', 'PIN', 'i'), 500.0)

# ---- die_hop_gate with the per-pair limit: 480 um between two real pin-registered tiles fails, between placeholders passes
It = lambda n, m, x: types.SimpleNamespace(name=n, master=m, x=x, y=0.0, w=10.0, h=10.0, orient='R0')
lef = lambda m: f"MACRO {m}\n SIZE 10 BY 10 ;\n PIN o[0]\n PORT\n RECT 9.9 5 10 5.1 ;\n END\n END o[0]\n PIN i[0]\n PORT\n RECT 0 5 0.1 5.1 ;\n END\n END i[0]\nEND {m}\n"
insts = [It('a', 'PIN', 0.0), It('b', 'PIN', 489.9), It('c', 'X', 0.0), It('d', 'Y', 489.9)]
buses = [('n1', 'lane', 1, [('a', 'o'), ('b', 'i')]), ('n2', 'lane', 1, [('c', 'o'), ('d', 'i')])]
ps = lambda p: (p, None, None)
flat = HG.gate(insts, buses, [lef(m) for m in ('PIN', 'X', 'Y')], ps, limit_um=500.0)
expect('flat gate passes both 480 um hops', (flat['verdict'], flat['bits_over_limit']), ('PASS', 0))
pg = HG.gate(insts, buses, [lef(m) for m in ('PIN', 'X', 'Y')], ps, limit_um=500.0, pair=P.Gate(table=T, default_um=500.0, buses=buses))
expect('pair gate fails the real pair only', (pg['verdict'], pg['bits_over_limit'], pg['pair_check']['bits_over_pair_limit']), ('FAIL', 1, 1))
expect('pair gate names the limit', pg['classes'][0]['limit_um'], 464.9)
# a forwarded link sampled on its launch edge (rising capture behind an inverted forward): hold fails at any length
T['RXR'] = dict(view='rx', clocks={'xf': dict(R_tt=252.4, R_ff=200.0, spread=40.0, n=566)}, clock_out={},
                buses=dict(xd=dict(dir='input', bits=566, arcs=[dict(clk='xf', edge='r', O=None, l=None, S=-46.7, h=179.0)])))
dfr = P.Die(T, {}, {('b', 'xf'): ('a', 'fo', 247.9, 'f')})
r = P.check(dfr, hop('STN', 'RXR', 246.7, pa='do', pb='xd'))
expect('forwarded link sampled on the launch edge: full window, hold fails', (r['model'], r['window'], r['status'], r['hold_ps'] < -150), ('FWD', 833.3, 'hold', True))
bz = [('f', 'fclk', 1, [('a', 'fo'), ('b', 'xf')]), ('d', 'lane', 1, [('a', 'do'), ('b', 'xd')])]
lef2 = lambda m, o, i: f"MACRO {m}\n SIZE 10 BY 10 ;\n PIN {o}[0]\n PORT\n RECT 9.9 5 10 5.1 ;\n END\n END {o}[0]\n PIN {i}[0]\n PORT\n RECT 0 5 0.1 5.1 ;\n END\n END {i}[0]\nEND {m}\n"
hz = HG.gate([It('a', 'STN', 0.0), It('b', 'RXR', 200.0)], bz, [lef2('STN', 'do', 'di'), lef2('RXR', 'q', 'xd')], ps, limit_um=500.0,
             pair=P.Gate(table=T, default_um=500.0, buses=bz))
expect('pair gate fails a hold race although the hop is 190 um', (hz['verdict'], hz['bits_over_limit'], len(hz['pair_check']['hold_fail'])), ('FAIL', 0, 1))
# a die master whose port names are not the view's: bound by direction = an upper bound, listed, never a build failure
gd = P.Gate(table=T, default_um=500.0)
expect('gate: direction-bound pair keeps the flat limit', (gd.limit('a', 'SLOW', 'zz', 'b', 'PIN', 'i'), len(gd.candidates)), (500.0, 1))
expect('gate: ... unless asked to judge the upper bound', P.Gate(table=T, default_um=500.0, judge_direction=True).limit('a', 'SLOW', 'zz', 'b', 'PIN', 'i'), 149.1)
r = P.check(die, hop('SLOW', 'PIN', 100.0, pa='zz'))
expect('check: direction binding is marked', r.get('bind'), 'direction')
print(f'{ok} passed, {fail} failed')
sys.exit(1 if fail else 0)
