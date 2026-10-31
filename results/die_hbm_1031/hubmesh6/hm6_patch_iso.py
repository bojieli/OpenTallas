import sys
p = sys.argv[1]; s = open(p).read()
rep = [
('''                eg["iso"], eg["iso_p"] = iso, put(iso, *lpath(root, q, min(20.0, manh(root, q) / 2.0)))''',
'''                ix, iy = lpath(root, q, min(20.0, manh(root, q) / 2.0))
                if isep > 0:          # HUBMESH-6 opt-in: stagger the trunk heads (+-k*sep in y) so they leave on separate rows
                    iy += isep * ((i + 1) // 2) * (1 if i % 2 else -1)
                eg["iso"], eg["iso_p"] = iso, put(iso, ix, iy)'''),
('''            mpre[0] = "XN"
''', '''            mpre[0] = "XN"
            isep = float(G["early"].get("iso_sep_um", 0.0))
'''),
('''    gs = early_groups_of(e)
''', '''    if float(e.get("iso_sep_um", 0.0)) < 0:
        raise MeshConfigError("region.mesh.grid.early.iso_sep_um must be >= 0 (0 = trunk heads on the root row)")
    gs = early_groups_of(e)
'''),
('''        early: {form: subtree, mesh_ps: {<part>: ps}, groups: {<name>: {lead_ps: ps, taps: {<part>: [clk_cN, ...]}}, ...}}''',
'''        early: {form: subtree, mesh_ps: {<part>: ps}, groups: {<name>: {lead_ps: ps, taps: {<part>: [clk_cN, ...]}}, ...},
                iso_sep_um: um (optional, default 0 = old bytes: trunk-head cells XI<i> stagger +-k*sep in y off the root
                row; HUBMESH-6 a3e6 NE GRT-0228 = the NDR trunks all leave the root on one M8 row)}'''),
]
for a, b in rep:
    assert s.count(a) == 1, a[:60]
    s = s.replace(a, b)
open(p, "w").write(s)
print("patched")
