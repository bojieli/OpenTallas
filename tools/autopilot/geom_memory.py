"""Strict synchronous-memory boundary facts from the actual Liberty models.

No master-name guesses: a memory() declaration, typed clock and timing arcs
must prove every non-PG interface direction before macro-wide reach is used.
"""
import gzip
import re
from pathlib import Path


def _groups(text):
    """Yield immediate Liberty groups, ignoring quoted braces and comments."""
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    tok = re.compile(r'"(?:\\.|[^"\\])*"|[{}]|[^{}"]+', re.S)
    depth = 0; header = ''; start = 0
    for m in tok.finditer(text):
        t = m.group()
        if t == '{':
            if depth == 0:
                h = re.search(r'(\w+)\s*\(([^()]*)\)\s*$', header)
                kind, args = (h.group(1), h.group(2).strip().strip('"')) if h else ('', '')
                start = m.end()
            depth += 1
        elif t == '}':
            depth -= 1
            if depth < 0: raise ValueError('Unbalanced Liberty group')
            if depth == 0:
                yield kind, args, text[start:m.start()]
                header = ''
        elif depth == 0:
            header += t
    if depth: raise ValueError('Unclosed Liberty group')


def _attrs(body):
    # Remove nested groups so an output timing attribute cannot type its parent.
    top = re.sub(r'"(?:\\.|[^"\\])*"|[{}]|[^{}"]+', lambda m:m.group(), body)
    depth = 0; chunks = []
    for m in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]|[^{}"]+', top, re.S):
        s=m.group()
        if s=='{': depth+=1
        elif s=='}': depth-=1
        elif depth==0: chunks.append(s)
    return {k:v.strip().strip('"') for k,v in re.findall(r'([\w]+)\s*:\s*([^;]+);', ''.join(chunks))}


def liberty_models(paths):
    models = {}
    for path in paths:
        p=Path(path);text=gzip.decompress(p.read_bytes()).decode() if p.suffix=='.gz' else p.read_text()
        for kind, _, lib in _groups(text):
            if kind!='library': continue
            types={name:_attrs(body) for k,name,body in _groups(lib) if k=='type'}
            for k,name,body in _groups(lib):
                if k!='cell': continue
                groups=list(_groups(body)); memory=any(t=='memory' for t,_,_ in groups)
                if not memory:
                    model=dict(kind='nonmemory',source=str(p))
                else:
                    ports={};clocks=set();errors=[]
                    for t,pn,pb in groups:
                        if t not in ('pin','bus'):continue
                        at=_attrs(pb);direction=at.get('direction');names=[pn]
                        if t=='bus':
                            bt=types.get(at.get('bus_type'),{})
                            try:
                                lo,hi=sorted((int(bt['bit_from']),int(bt['bit_to'])))
                                names=[f'{pn}[{i}]' for i in range(lo,hi+1)]
                            except (KeyError,ValueError):errors.append('unknown bus '+pn)
                        arcs=[_attrs(tb) for tk,_,tb in _groups(pb) if tk=='timing']
                        clock=at.get('clock')=='true'
                        if clock:clocks.update(names)
                        for pin in names:ports[pin]=(direction,clock,arcs)
                    launches=[];captures=[]
                    if not clocks:errors.append('no typed clock')
                    for pin,(direction,clock,arcs) in ports.items():
                        if clock:
                            if direction!='input':errors.append('noninput clock '+pin)
                            continue
                        good=[arc.get('timing_type') for arc in arcs if arc.get('related_pin') in clocks]
                        if direction=='output' and ('rising_edge' in good or 'falling_edge' in good):launches.append(pin)
                        elif direction=='input' and (('setup_rising' in good and 'hold_rising' in good) or ('setup_falling' in good and 'hold_falling' in good)):captures.append(pin)
                        else:errors.append('unproven synchronous port '+pin)
                    if not launches or not captures:errors.append('missing launch/capture interface')
                    model=dict(kind='synchronous_memory' if not errors else 'unknown_memory',source=str(p),clocks=sorted(clocks),launches=sorted(launches),captures=sorted(captures),errors=errors)
                prev=models.get(name)
                if prev and {k:v for k,v in prev.items() if k!='source'}!={k:v for k,v in model.items() if k!='source'}:
                    model=dict(kind='unknown_memory',source=str(p),errors=['conflicting corner interfaces'])
                models[name]=model
    return models
