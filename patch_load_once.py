from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
def sub(old,new):
 global s
 assert s.count(old)==1,(old[:70],s.count(old));s=s.replace(old,new)
sub('elif h and h[0] == "fill" and side == "gold" and k in self.fill_live:', 'elif h and h[0] in ("fill", "load_once") and side == "gold" and k in self.fill_live:')
sub('                if h[0] == "fill":\n                    # filled\'', '''                if h[0] == "load_once":
                    # A persistent tool-owned ghost records a conditional constant load.
                    # The guard is evaluated on NEXT state (a registered write-valid).
                    # If no load has happened, the RTL must still be X; a false enable
                    # therefore cannot hide a known value. Once loaded, every next D
                    # must be the claimed constant AND known, including hold cycles.
                    gn = guard_lit(m, h[2], lambda key: self.dlit[("gold", key)])
                    anyx = 0
                    for cube in h[2]:
                        for key, _ in cube:
                            anyx = m.AND(anyx ^ 1, self.dxlit.get(key, 0) ^ 1) ^ 1
                    en = m.AND(gn, anyx ^ 1)
                    fn = m.AND(self.fill_in[k] ^ 1, en ^ 1) ^ 1
                    dx = self.dxlit.get(k, 0)
                    bad = m.AND((d ^ h[1]) ^ 1, dx ^ 1) ^ 1
                    m.outs.append(m.AND(m.AND(fn, bad) ^ 1, m.AND(fn ^ 1, dx ^ 1) ^ 1) ^ 1)
                    m.onames.append(f"hyp:{side}:{k}")
                    continue
                if h[0] == "fill":
                    # filled\'''' )
sub('    return {k for k, ok in live.items() if ok}\n', '''    # Conditional ghosts may stay zero forever, but their obligation requires
    # the RTL to remain X for exactly that duration; they never erase known data.
    return {k for k, ok in live.items() if ok} | {
        k for (sd, k), h in hyp.items() if sd == "gold" and h and h[0] == "load_once"}
''')
sub('    rec["fill"], rec["fill_refused"] = [], []\n', '''    rec["fill"], rec["fill_refused"] = [], []
    rec["load_once"], rec["load_once_refused"] = [], []
    once = {e[1] for e in hints if isinstance(e, (list, tuple)) and len(e) == 3 and e[0] == "gold"
            and isinstance(e[2], (list, tuple)) and e[2] and e[2][0] == "load_once"}
''')
needle='''    for e in hints:
        if isinstance(e, (list, tuple)) and len(e) == 3 and isinstance(e[2], (list, tuple)) and e[2] \\
                and e[2][0] == "fill":
            continue
        refs = []'''
replacement='''    for e in hints:
        if isinstance(e, (list, tuple)) and len(e) == 3 and isinstance(e[2], (list, tuple)) and e[2] \\
                and e[2][0] == "load_once":
            try:
                sd, k, (_, c, guard) = e
                ok = (sd == "gold" and k in L.gonly and gk(k) and c in (0, 1)
                      and k not in getattr(L, "unwritten", ()) and guard
                      and all(cube and all(gk(x) and v in (0, 1) and x not in once | loaded | set(fills)
                                           for x, v in cube) for cube in guard))
            except (ValueError, TypeError):
                ok = False
            if not ok:
                rec["skipped"].append(e)
                continue
            if not hasattr(L, "rst_val"):
                noreset_classify(L)
            rv = L.rst_val.get(("gold", k), (None, None))[0]
            if rv == 1 - c:
                rec["load_once_refused"].append(dict(register=k, why="reset state is the other constant"))
                continue
            L.hyp[(sd, k)] = ("load_once", c, tuple(tuple((x, int(v)) for x, v in cube) for cube in guard))
            rec["applied"] += 1
            continue
        if isinstance(e, (list, tuple)) and len(e) == 3 and isinstance(e[2], (list, tuple)) and e[2] \\
                and e[2][0] == "fill":
            continue
        refs = []'''
sub(needle,replacement)
sub('''            rec["fill"] = [dict(register=k, value=h[1], pred=h[2],''', '''            rec["load_once"] = [dict(register=k, value=h[1], next_write_guard=h[2],
                                     base_filled=L.rst_val.get(("gold", k), (None, None))[0] == h[1])
                                for (sd, k), h in sorted(L.hyp.items()) if h[0] == "load_once"]
            rec["fill"] = [dict(register=k, value=h[1], pred=h[2],''')
p.write_text(s)
