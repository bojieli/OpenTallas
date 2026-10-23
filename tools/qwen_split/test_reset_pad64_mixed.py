"""QDIE-R56 10-22: OT_RST_PAD64_MIXED keeps every reset edge's age exact.
(1) no-fallback toy: mixed == compact-only (byte-identical cells/wires/stats less the fallback counter);
(2) crowded toy (only 20-um channels: the 43.2/25.92-um compact pad has no legal site, 12.96-um p8/rep do):
    compact-only raises, mixed builds with the SAME depth_cycles / levels as the default (p8/rep) palette and
    every pad chain sums to the same cycles (p62=64, p8=10, rep=2)."""
import ast, math, os, sys
from pathlib import Path
src = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'qwen_rom_fulldie_b3r2.py')
CYC = {'qfd_rst_rep': 2, 'qfd_rst_rep_p8': 10, 'qfd_rst_rep_p62': 64}


def build(variant, mixed, nets, rects, W, H):
    ns = dict(math=math, os=os, RST_W=12.96, RST_H=6.48, RST_GAP_UM=2.16, RST_NET_UM=380., RST_PAD_GAP_UM=2.16,
              RST_REP='qfd_rst_rep', RST_PAD='qfd_rst_rep_p8', RST_PAD_LV=5, RST_PITCH_UM=220., RST_LEAF_UM=200.,
              _rst_pad_cluster=True, _rst_pad_street=True, RST_PAD64='qfd_rst_rep_p62', RST_PAD64_VARIANT=variant,
              RST_PAD64_MIXED=mixed)
    tree = ast.parse(src.read_text())
    defs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
            and n.name in ('_rst_frame', '_rst_cycles', '_hp', '_RstOcc', '_rst_tree_build')]
    exec(compile(ast.Module(body=defs, type_ignores=[]), str(src), 'exec'), ns)
    return ns['_rst_tree_build'](nets, rects, W, H, 2.16, 2.16)


def ages(res):
    """sink -> reset age in cycles, walked over the emitted wires (driver first)."""
    cells, wires = res[0], res[1]
    master = {c[0]: c[1] for c in cells}
    drv = {}
    for _, _, eps in wires:
        for e in eps[1:]:
            drv[e] = eps[0]
    out = {}
    for e, d in drv.items():
        if e[0] in master:
            continue
        cyc, cur = 0, d
        while cur[0] in master:
            cyc += CYC[master[cur[0]]]
            cur = drv[(cur[0], 'd')]
        out[e] = cyc
    return out


nets = [dict(bid='rst_long', dom='field', drv=('a', 'q', (80., 100.)), sinks=[('s1', 'rst', (8600., 1500.)), ('s2', 'rst', (8500., 200.))]),
        dict(bid='rst_short', dom='field', drv=('b', 'q', (100., 800.)), sinks=[('s3', 'rst', (600., 900.))])]
for v in ('a', 'b'):
    x = build(v, False, nets, [], 9000., 1800.)
    y = build(v, True, nets, [], 9000., 1800.)
    assert sum(st['pad_p62'] for st in x[2].values()) > 0, 'toy must use compact pads'
    for st in y[2].values():
        assert st.pop('pad_p62_fallback') == 0
    assert x == y, 'mixed changed a build with no fallback'
    print('PASS open', v, 'p62', sum(st['pad_p62'] for st in x[2].values()), 'ages', sorted(set(ages(x).values())))
# crowded: vertical blocks 40 um wide, 20-um channels -> no 43.2 / 25.92 frame fits anywhere, 12.96 does
W, H = 9000., 1800.
rects = [(x0, 0., min(x0 + 40., W), H) for x0 in [i * 60. + 20. for i in range(150)]]
cnets = [dict(n, sinks=[(s[0], s[1], (s[2][0] // 60 * 60 + 10., s[2][1])) for s in n['sinks']],
              drv=(n['drv'][0], n['drv'][1], (n['drv'][2][0] // 60 * 60 + 10., n['drv'][2][1]))) for n in nets]
base = build('', False, cnets, rects, W, H)
assert not base[3], base[3]
for v in ('a', 'b'):
    try:
        build(v, False, cnets, rects, W, H)
        raise AssertionError('compact-only should have no site in the crowded toy')
    except ValueError as e:
        assert 'no free site' in str(e), e
    m = build(v, True, cnets, rects, W, H)
    assert not m[3], m[3]
    fb = sum(st['pad_p62_fallback'] for st in m[2].values())
    assert fb > 0, 'expected compact fallbacks'
    for k, st in m[2].items():
        for f in ('sinks', 'depth_cycles', 'levels', 'nets'):
            assert st[f] == base[2][k][f], (v, k, f, st[f], base[2][k][f])
        assert st['pad_p62'] == 0
    assert ages(m) == ages(base), (ages(m), ages(base))
    print('PASS crowded', v, 'fallbacks', fb, 'ages', sorted(set(ages(m).values())))
print('PAD64_MIXED PASS: no-fallback build byte-identical; crowded fallback keeps every sink age and depth')
