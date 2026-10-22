import json, re, sys, itertools
for k in sys.argv[1:]:
    d = f'qfd_tt_ctlm_dv_{k}'
    f = json.load(open(f'{d}/floorplan.json')); W, H = f['die'][2], f['die'][3]
    t = open(f'{d}/lp_cone_regions.tcl').read()
    line = [l for l in t.split('\n') if l.startswith('set boxes')][0]
    m = re.match(r'set boxes \[dict create 1 \{(.*)\} 2 \{(.*)\}\]', line)
    boxes = [(n, tuple(map(float, b.split()))) for n, g in (('core', m.group(1)), ('hr', m.group(2))) for b in re.findall(r'\{([0-9. ]+)\}', g)]
    h = 5.4; bad = []
    bl = [(b['inst'], b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']) for b in f['blocks']]
    for n, x0, y0, x1, y1 in bl:
        if x0 - h < 2.16 or y0 - h < 2.16 or x1 + h > W - 2.16 or y1 + h > H - 2.16: bad.append(('outline', n))
        inb = [bn for bn, (a, b_, c, e) in boxes if x0 >= a - 1e-6 and x1 <= c + 1e-6 and y0 >= b_ - 1e-6 and y1 <= e + 1e-6]
        if not inb: bad.append(('not_in_one_box', n))
    for (a, *A), (b, *B) in itertools.combinations(bl, 2):
        if A[0] - h < B[2] + h and B[0] - h < A[2] + h and A[1] - h < B[3] + h and B[1] - h < A[3] + h:
            gx = max(B[0] - A[2], A[0] - B[2]); gy = max(B[1] - A[3], A[1] - B[3])
            if max(gx, gy) < 2 * h: bad.append(('halo_overlap', a, b, round(max(gx, gy), 3)))
    # box tiling: no overlap between boxes, total area = union box
    for (n1, A), (n2, B) in itertools.combinations(boxes, 2):
        if A[0] < B[2] - 1e-6 and B[0] < A[2] - 1e-6 and A[1] < B[3] - 1e-6 and B[1] < A[3] - 1e-6: bad.append(('box_overlap', A, B))
    area = sum((b[2] - b[0]) * (b[3] - b[1]) for _, b in boxes)
    ux = (min(b[0] for _, b in boxes), min(b[1] for _, b in boxes), max(b[2] for _, b in boxes), max(b[3] for _, b in boxes))
    hard = sum(b['w'] * b['h'] for b in f['blocks']); std = f['std_area_um2']
    print(k, 'outline', W, H, 'boxes union', ux, 'tiled', abs(area - (ux[2] - ux[0]) * (ux[3] - ux[1])) < 1e-3,
          'fill(hard+std)/outline %.1f%%' % (100 * (hard + std) / (W * H)), 'issues', bad or 'NONE')
    for b in bl: print('  ', b[0], [round(v, 3) for v in b[1:]], [bn for bn, (a, b_, c, e) in boxes if b[1] >= a - 1e-6 and b[3] <= c + 1e-6 and b[2] >= b_ - 1e-6 and b[4] <= e + 1e-6])
