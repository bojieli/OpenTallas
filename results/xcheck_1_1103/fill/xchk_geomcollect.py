"""XCHECK-1: collect every kit-wave auto_geom.json (any age) -> one TSV row per file:
die event type mtime outline_w outline_h fill_of_free macro_area_pct std_cells verdict
usage: python3 -I xchk_geomcollect.py ROOT [ROOT...]  (prints TSV)"""
import json, os, sys, glob
for root in sys.argv[1:]:
    for f in glob.glob(os.path.join(root, 'kit-wave', '*', '*', 'items', '*', '**', 'auto_geom.json'), recursive=True):
        parts = f.split(os.sep)
        i = parts.index('kit-wave')
        die, ev, ty = parts[i + 1], parts[i + 2], parts[i + 4]
        try:
            d = json.load(open(f)); m = d.get('metrics') or {}
            o = m.get('outline') or [0, 0]
            print('\t'.join(str(x) for x in (die, ev, ty, int(os.path.getmtime(f)), o[0], o[1], m.get('fill_of_free'),
                                              m.get('macro_area_pct'), m.get('std_cells'), d.get('verdict'), f)))
        except Exception:
            pass
