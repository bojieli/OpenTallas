"""HBM-GAPS-5-Q3SPLIT: fill plan-referenced core files missing from an unpacked d44v dir.

d44v/cores in git lacks 17 files the plan references (native128 pin tables, canon outlines kept
outside git); views_b2r2.py reads them.  Copies ONLY missing files from FILL (a kit-wave d44v
cores tree); never overwrites.   fill_cores.py PLANDIR FILLCORES
"""
import os, re, shutil, sys
d, fill = sys.argv[1], sys.argv[2]
s = open(os.path.join(d, 'die_plan.json')).read()
refs = sorted(set(re.findall(r'"(cores/[^"]+)"', s)))
done = miss = 0
for r in refs:
    t = os.path.join(d, r)
    if os.path.exists(t):
        continue
    src = os.path.join(fill, os.path.basename(r))
    if os.path.isfile(src):
        shutil.copyfile(src, t); done += 1
    else:
        print('MISSING core file', d, r); miss += 1
print('fill_cores', d, 'refs', len(refs), 'filled', done, 'missing', miss)
