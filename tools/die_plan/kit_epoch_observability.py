"""Conservative observability proof for scalar epochs in canonical station RTL."""
import re
from kit_assembly import _masked_rtl

ID=r'[A-Za-z_]\w*'

def inspect(text, instance):
    code=_masked_rtl(text)
    safe=[];edges={};outputs={}
    for m in re.finditer(r'\bwire\s+'+ID+r'\s*;',code):safe.append(m.span())
    for m in re.finditer(r'\bot_dp_ste?\s+#\(\.W\(\d+\)\)\s+('+ID+r')\s*\(([^;]*)\);',code,re.S):
        pins={p[1]:p for p in re.finditer(r'\.(ea|eq)\s*\(\s*('+ID+r')\s*\)',m[2])}
        if 'eq' in pins:
            outputs[m[1]]=pins['eq'][2]
            safe.append((m.start(2)+pins['eq'].start(2),m.start(2)+pins['eq'].end(2)))
        if 'ea' in pins and 'eq' in pins:
            edges.setdefault(pins['ea'][2],set()).add(pins['eq'][2])
            safe.append((m.start(2)+pins['ea'].start(2),m.start(2)+pins['ea'].end(2)))
    # A literal wire alias preserves epoch-only lineage; all other expressions
    # remain reads and make the proof fail closed.
    for m in re.finditer(r'\bassign\s+('+ID+r')\s*=\s*('+ID+r')\s*;',code):
        edges.setdefault(m[2],set()).add(m[1]);safe.append(m.span())
    start=outputs.get(instance)
    if start is None:return dict(unobserved=False,reason='unsupported/missing epoch output',signals=[])
    todo=[start];seen=set()
    while todo:
        signal=todo.pop()
        if signal in seen:continue
        seen.add(signal)
        for hit in re.finditer(r'\b'+re.escape(signal)+r'\b',code):
            if not any(a<=hit.start() and hit.end()<=b for a,b in safe):
                return dict(unobserved=False,reason='observed or unsupported read of '+signal,signals=sorted(seen))
        todo.extend(edges.get(signal,()))
    return dict(unobserved=True,reason='entire scalar epoch cone unobserved outside epoch-only chains',signals=sorted(seen))
