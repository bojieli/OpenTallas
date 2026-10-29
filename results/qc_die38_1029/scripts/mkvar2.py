p="/srv/opentallas-scratch2/claude/die-qc38/fixed_tree_prov.py"; s=open(p).read()
old='''    src = src.replace(_PROV_OLD, _PROV_NEW)
'''
new='''    src = src.replace(_PROV_OLD, _PROV_NEW)
    if _NAT_MODE:
        o2 = """                    by, bm = track("M8", p[1] + sg * off, tx, p[0], nm, f"drop {ld}")"""
        n2 = """                    nat = port and _NAT_MODE and not ld.startswith("port:provider_clk_")
                    by, bm = track("M8", p[1] + (0.0 if nat else sg * off), tx, p[0], nm, f"drop {ld}")
                    if nat: _PROV_STATS["nat_drop_on_landing" if abs(by - p[1]) < 1e-6 else "nat_drop_moved"] += 1"""
        if src.count(o2) != 1: raise ValueError("C128 native drop anchor changed")
        src = src.replace(o2, n2)
'''
assert s.count(old)==1; s=s.replace(old,new)
s=s.replace('''_PROV_STATS = Counter()''','''_PROV_STATS = Counter()
_NAT_MODE = _os.environ.get("OT_DQC38_NAT", "") == "1"''')
s=s.replace("g.update(_PROV_MODE=_PROV_MODE,","g.update(_NAT_MODE=_NAT_MODE, _PROV_MODE=_PROV_MODE,")
s=s.replace("json.dumps(dict(mode=_PROV_MODE,near_a=_PROV_NEAR_A,","json.dumps(dict(mode=_PROV_MODE,nat=_NAT_MODE,near_a=_PROV_NEAR_A,")
open(p,'w').write(s)
import py_compile; py_compile.compile(p,doraise=True); print('ok')
