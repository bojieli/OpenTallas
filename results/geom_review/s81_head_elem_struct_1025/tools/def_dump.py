# HEAD-ELEM render dump: DEF -> compact JSON (components, pins, clock-net + selected-net route segments). Read-only.
import json, re, sys, gzip
deff, out = sys.argv[1], sys.argv[2]
want = set(sys.argv[3].split(',')) if len(sys.argv) > 3 and sys.argv[3] else set()
comps, pins, nets = [], [], {}
sec = None; cur = None; buf = ''
pt = re.compile(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)(?:\s+\S+)?\s*\)')
def flush_net(text):
    m = re.match(r'-\s+(\S+)', text)
    if not m: return
    name = m.group(1)
    isclk = name.startswith('clknet') or name == 'clk' or '+ USE CLOCK' in text
    if not (isclk or name in want): return
    conns = re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)', text.split('+ ROUTED')[0])
    segs = []
    for part in re.split(r'\+ ROUTED|NEW', text)[1:]:
        tok = part.split()
        if not tok: continue
        layer = tok[0]
        ps = pt.findall(part); prev = None; line = []
        for x, y in ps:
            if prev is None: px, py = int(x), int(y)
            else: px = prev[0] if x == '*' else int(x); py = prev[1] if y == '*' else int(y)
            line.append((px, py)); prev = (px, py)
        if len(line) >= 2: segs.append([layer] + [c for p in line for c in p])
    nets[name] = dict(clk=isclk, conns=conns, segs=segs)
for raw in open(deff):
    s = raw.strip()
    if s.startswith('COMPONENTS'): sec = 'C'; continue
    if s.startswith('PINS'): sec = 'P'; continue
    if s.startswith('NETS'): sec = 'N'; continue
    if s.startswith('END '): 
        if sec == 'N' and buf: flush_net(buf)
        sec = None; buf = ''; continue
    if sec == 'C' and s.startswith('- '):
        m = re.match(r'-\s+(\S+)\s+(\S+).*?(PLACED|FIXED|FIRM)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)', s)
        if m and not m.group(2).startswith(('FILLER', 'TAPCELL', 'DECAP')):
            comps.append([m.group(1), m.group(2), int(m.group(4)), int(m.group(5))])
    elif sec == 'P':
        if s.startswith('- '): cur = s.split()[1]
        m = re.search(r'(PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)', s)
        if m and cur: pins.append([cur, int(m.group(2)), int(m.group(3))]); cur = None
    elif sec == 'N':
        if s.startswith('- '):
            if buf: flush_net(buf)
            buf = s
        else: buf += ' ' + s
json.dump(dict(comps=comps, pins=pins, nets=nets), gzip.open(out, 'wt'))
print('comps', len(comps), 'pins', len(pins), 'nets', len(nets))
