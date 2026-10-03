import json,glob,sys,os
for d in sys.argv[1:]:
  for f in sorted(glob.glob(d+'/*.json')):
    r=json.load(open(f)); ra=r['phases']['raw']; rp=r['phases']['rep']; p=rp['r2r_path']
    fmt=lambda x:'-' if x is None else f'{x:.0f}'
    print(f"{r['label']:16} {r['period_ns']} raw {fmt(ra['r2r_fmax_mhz'])} | rep {fmt(rp['r2r_setup_wns_ps'])}ps {fmt(rp['r2r_fmax_mhz'])}MHz | {p['startpoint']} -> {p['endpoint']} cells={p['logic_cells']} maxfo={p['max_fanout_on_path']} util={r.get('floorplan',{}).get('used','30')}")
    for n,fo in rp['focus'].items():
      print(f"   focus {n}: {fmt(fo['setup_wns_ps'])}ps {fmt(fo['fmax_mhz'])}MHz {fo['path']['startpoint']} -> {fo['path']['endpoint']}")
