p="/srv/opentallas-scratch2/claude/die-qc38/fixed_tree_diag.py"; s=open(p).read()
anchor="def access_census(shapes):"
patch='''_PROV_OLD = """                if ld.startswith("port:"):           # port loads: as the default comb (drop one track pair off)
                    if abs(p[1] - ty) > 1e-6:"""
_PROV_NEW = """                if ld.startswith("port:provider_clk_") and _PROV_MODE in ("A", "B"):
                    # DIE-QC-38 provider M1 CLK landing selection (no M8 landing on the pin row):
                    # near load -> on-trunk VIA78 + M7 riser to the pin row (as a clock-cell pin stack);
                    # far load  -> A: M9 drop to the nearest PG-clear M8 row, B: router-legal M8 jog + M9 drop (cell L-drop rule)
                    near = _PROV_NEAR_A if _PROV_MODE == "A" else STACK_RISER_MAX_UM
                    if abs(p[1] - ty) <= near:
                        branches.append((ld, p[0], ty)); xs_.append(p[0]); _PROV_STATS["near"] += 1
                        continue
                    if _PROV_MODE == "A":
                        yl = _prov_pg_clear(p[1])
                        bx, bm = track("M9", p[0] + off, ty, yl, nm, f"drop {ld}")
                        add(("M9", bx, min(ty, yl), bx, max(ty, yl)), bm)
                        branches.append((ld, bx, yl)); xs_.append(bx); _PROV_STATS["far_pgclear"] += 1
                        continue
                    sg = 1.0 if ty >= p[1] else -1.0
                    by, jm = track("M8", p[1] + sg * off, p[0] - mm, p[0] + mm, nm, f"jog {ld}")
                    bx, bm = track("M9", p[0], ty, by, nm, f"drop {ld}")
                    add(("M9", bx, min(ty, by), bx, max(ty, by)), bm)
                    if abs(bx - p[0]) > 1e-6:
                        add(("M8", min(bx, p[0]), by, max(bx, p[0]), by), jm)
                    branches.append((ld, bx, by)); xs_.append(bx); _PROV_STATS["far_jog"] += 1
                    continue
                if ld.startswith("port:"):           # port loads: as the default comb (drop one track pair off)
                    if abs(p[1] - ty) > 1e-6:"""
import os as _os, inspect as _inspect, bisect as _bisect
_PROV_MODE = _os.environ.get("OT_DQC38_PROV", "")
_PROV_NEAR_A = float(_os.environ.get("OT_DQC38_NEAR_A", "2.5"))
_PROV_STATS = Counter()
_PROV_STRAPS = []
def _prov_pg_clear(y, sp=.32, h=.04, step=.005, lim=8.64):
    lo = [a for a, b in _PROV_STRAPS]
    def bad(v):
        j = _bisect.bisect_right(lo, v + sp + h) - 1
        return any(v + h > a - sp and v - h < b + sp for a, b in _PROV_STRAPS[max(0, j - 1):j + 2])
    k = 0
    while k * step <= lim:
        for v in (y - k * step, y + k * step):
            if not bad(v): return round(v, 4)
        k += 1
    return y
def _prov_install():
    src = _inspect.getsource(C128._fixed_wires_stack)
    if src.count(_PROV_OLD) != 1: raise ValueError("C128 provider anchor changed")
    src = src.replace(_PROV_OLD, _PROV_NEW)
    g = C128.__dict__
    g.update(_PROV_MODE=_PROV_MODE, _PROV_NEAR_A=_PROV_NEAR_A, _PROV_STATS=_PROV_STATS, _prov_pg_clear=_prov_pg_clear)
    exec(compile(src, C128.__file__, "exec"), g)


'''
assert s.count(anchor)==1; s=s.replace(anchor,patch+anchor)
a2="    (out/'pg_rects.json').write_text(json.dumps(pg)+'\\n')\n"
assert s.count(a2)==1
s=s.replace(a2,a2+"""    _PROV_STRAPS[:] = sorted((r[3], r[5]) for r in pg if r[1] == 'M8')
    if _PROV_MODE: _prov_install()
""")
a3="    (out/'diag_top.json')"
assert s.count(a3)==1
s=s.replace(a3,"    (out/'prov_stats.json').write_text(json.dumps(dict(mode=_PROV_MODE,near_a=_PROV_NEAR_A,**_PROV_STATS))+'\\n')\n"+a3)
open(p.replace('fixed_tree_diag.py','fixed_tree_prov.py'),'w').write(s)
import py_compile; py_compile.compile(p.replace('fixed_tree_diag.py','fixed_tree_prov.py'),doraise=True); print('ok')
