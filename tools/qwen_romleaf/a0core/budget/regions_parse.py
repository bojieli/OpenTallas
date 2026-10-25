"""Parse a qrl_groups regions tcl (list of dict create name/type/regex/boxes) into python."""
import re
def parse(path):
    txt = open(path).read()
    out = []
    for m in re.finditer(r'\[dict create name (\S+) type (\S+) regex \{(.*?)\} boxes \{(.*?)\} min (\d+) max (\d+)\]', txt):
        name, typ, rx, boxes, mn, mx = m.groups()
        bl = [tuple(map(float, b.split())) for b in re.findall(r'\{([^{}]*)\}', boxes)]
        out.append(dict(name=name, type=typ, regex=rx, rc=re.compile(rx), boxes=bl, min=int(mn), max=int(mx)))
    return out
SEQ = re.compile(r'^(DFF|SDF|DHL|DLL|ASYNC|ICG)')
def assign(groups, name):
    n = name.replace('\\', '')
    for g in groups:
        if g['rc'].search(n): return g['name']
    return None
