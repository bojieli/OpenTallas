fn = "tools/die_plan/s81_pd9/mesh_rec_s81.py"; s = open(fn).read()
old = """    s = v['site']
    assert v['strap'] == 'M9' and abs(xs[v['i']] - s[0]) < 1.0, (k, s)   # PG-track snap <= 0.68 um (meta pg_axis_snap_max_um)
    a = {C: sum(arr[c][C] for c in v['cells']) / len(v['cells']) for C in ('TT', 'FF')}
    nodes.append(dict(tag='~' * dep(c0) + 'D%06d' % nm, cell=k, parent=tag[p], leg_um=450.0, driver=True,
                      site=[xs[v['i']], r3(s[1])], xy=[xs[v['i']], r3(s[1])], arr=a, mult=len(v['cells'])))"""
new = """    s = v['site']
    if v['strap'] == 'M8':
        # PATH-S81-PD9: off_core_resite driver slid along its M8 row j (same continuous mesh node line)
        assert abs(ys[v['j']] - s[1]) < 1.0, (k, s)
        ds = [r3(s[0]), ys[v['j']]]
    else:
        assert v['strap'] == 'M9' and abs(xs[v['i']] - s[0]) < 1.0, (k, s)   # PG-track snap <= 0.68 um (meta pg_axis_snap_max_um)
        ds = [xs[v['i']], r3(s[1])]
    a = {C: sum(arr[c][C] for c in v['cells']) / len(v['cells']) for C in ('TT', 'FF')}
    nodes.append(dict(tag='~' * dep(c0) + 'D%06d' % nm, cell=k, parent=tag[p], leg_um=450.0, driver=True,
                      site=ds, xy=ds, arr=a, mult=len(v['cells']), strap=v['strap']))"""
assert s.count(old) == 1
s = s.replace(old, new)
s = s.replace('"""CLOCK-KV-R18 (copy', '"""PATH-S81-PD9 copy of kv_r18/mesh_rec18.py, + M8-row drivers (off_core_resite); dropped drivers are simply absent.\nCLOCK-KV-R18 (copy', 1)
open(fn, "w").write(s); print("ok")
