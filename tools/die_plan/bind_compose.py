"""Opt-in structural composition before Graph: exact terminals, no aliases or timing edits."""
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


class CompositionError(ValueError):
    pass


def ident(s):
    return s if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', s) else '\\' + s + ' '


def compose(F, rules, spec, Cell):
    """Return (generated sources, receipt); atomically replace complete member sets.

    spec={cores:[{inst,module,members:[full path],ports:{name:{dir,
    bits:[[ {member,port,bit}, ...], ...]}}}]}. Every listed endpoint is exact;
    multi-endpoint bits require identical original nets. Constants are endpoint-local.
    """
    original = list(F.cells)
    bypath = {c.path:c for c in original}
    if len(bypath) != len(original):
        raise CompositionError('duplicate original cell paths')
    outside = defaultdict(set)
    for c in original:
        for p,bs in c.ports.items():
            for i,b in enumerate(bs):
                if isinstance(b,int): outside[b].add(c.path)
    topnets = {b for _,bs in F.top_ports.values() for b in bs if isinstance(b,int)}
    used=set(); replacements=[]; sources=[]; records=[]; module_sources={}
    for core in spec['cores']:
        path,mod=core['inst'],core['module']
        members=core['members']; ms=set(members)
        if not ms or len(ms)!=len(members) or used&ms:
            raise CompositionError(f'{path}: empty, duplicate or overlapping members')
        if path in bypath and path not in ms: raise CompositionError(f'{path}: replacement path exists')
        if any(x not in bypath for x in ms): raise CompositionError(f'{path}: missing exact member')
        cs=[bypath[x] for x in members]
        parts={rules.part_of(c.path) for c in cs}
        if len(parts)!=1 or None in parts or rules.part_of(path) not in parts:
            raise CompositionError(f'{path}: members/replacement must share one mapped partition')
        if any(c.kind!='leaf' for c in cs): raise CompositionError(f'{path}: only actual leaf members supported')
        endpoints={(c.path,p,i):(b,c.dirs.get(p)) for c in cs for p,bs in c.ports.items() for i,b in enumerate(bs)}
        if any(d not in ('input','output') for _,d in endpoints.values()):
            raise CompositionError(f'{path}: missing/inout terminal direction')
        nets={b for b,_ in endpoints.values() if isinstance(b,int)}
        boundary={b for b in nets if outside[b]-ms or b in topnets}
        net_terms=defaultdict(list)
        for k,(b,d) in endpoints.items():
            if isinstance(b,int): net_terms[b].append((k,d))
        ports={}; dirs={}; mapped={}; netports={}; declarations=[]; assigns=[]
        for pn,pd in core['ports'].items():
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',pn): raise CompositionError('unsafe port name')
            d=pd['dir']; bits=pd['bits']
            if d not in ('input','output') or not bits: raise CompositionError(f'{path}.{pn}: invalid port')
            indices=pd.get("indices",list(range(pd.get("lo",0),pd.get("lo",0)+len(bits))))
            if len(indices)!=len(bits) or indices!=list(range(indices[0],indices[0]+len(bits))) or indices[0]<0:
                raise CompositionError(f"{path}.{pn}: indices must be contiguous increasing and match bits")
            ports[pn]=[];dirs[pn]=d
            declarations.append(f"    {d} wire [{indices[-1]}:{indices[0]}] {pn}")
            for i,anchors in enumerate(bits):
                if isinstance(anchors,dict): anchors=[anchors]
                if not anchors: raise CompositionError(f'{path}.{pn}[{i}]: missing terminal')
                keys=[(a['member'],a['port'],a['bit']) for a in anchors]
                if any(k not in endpoints for k in keys): raise CompositionError(f'{path}.{pn}[{i}]: unknown terminal')
                vals={endpoints[k][0] for k in keys}
                if len(vals)!=1 or any(endpoints[k][1]!=d for k in keys):
                    raise CompositionError(f'{path}.{pn}[{i}]: net or direction mismatch')
                b=next(iter(vals)); ports[pn].append(b); ref=f'{pn}[{indices[i]}]'
                for k in keys:
                    if k in mapped: raise CompositionError(f'{path}: terminal mapped twice')
                    mapped[k]=ref
                if isinstance(b,int):
                    netports.setdefault(b,[]).append((d,ref))
                elif d!='input' or b not in ('0','1'):
                    raise CompositionError(f'{path}: only known input constant straps supported')
        if boundary-set(netports): raise CompositionError(f'{path}: omitted boundary nets {sorted(boundary-set(netports))[:8]}')
        # Fully anchored input terminals use their exact port expressions. Their
        # external parent nets may alias differently across instances; retain that
        # in F.ports, never encode unused parent-only wires in the reusable master.
        port_only={b for b,ts in net_terms.items() if all(d=='input' and k in mapped for k,d in ts)}
        wire={b:f'n{i}' for i,b in enumerate(dict.fromkeys(b for c in cs for p in sorted(c.ports) for b in c.ports[p] if isinstance(b,int) and b not in port_only))}
        # Check directions against real drivers. An output boundary has exactly one
        # original internal driver; input boundary has none. No driver disappears.
        for b,aliases in netports.items():
            d=aliases[0][0]
            if any(ad!=d for ad,_ in aliases) or (d=='output' and len(aliases)!=1):
                raise CompositionError(f'{path}: incompatible aliases on original net {b}')
            if len(aliases)>1:
                required={k for k,di in net_terms[b] if di=='input'}
                if not required.issubset(mapped):
                    raise CompositionError(f'{path}: live input aliases require exact complete terminal coverage {b}')
            elif b not in port_only:
                ref=aliases[0][1]
                assigns.append('    assign '+(f'{wire[b]} = {ref};' if d=='input' else f'{ref} = {wire[b]};'))
            drivers=[k for k,di in net_terms[b] if di=='output']
            if len(drivers)!=(1 if d=='output' else 0): raise CompositionError(f'{path}: boundary driver mismatch {b}')
        for b in nets:
            drivers=[k for k,di in net_terms[b] if di=='output']
            constant=F.const_drivers.get(b)
            if len(drivers)>1 or (drivers and constant):
                raise CompositionError(f'{path}: multiple original internal drivers {b}')
            if not drivers and b not in netports:
                if not constant or constant[0] not in ('0','1'):
                    raise CompositionError(f'{path}: original net has no preserved driver {b}')
                assigns.append(f"    assign {wire[b]} = 1'b{constant[0]};")
        body=[f'module {mod} (',',\n'.join(declarations),');']
        body += [f'    wire {w};' for w in wire.values()] + assigns
        terminal_record=[]
        for ci,c in enumerate(cs):
            conns=[]
            for pn,bs in sorted(c.ports.items()):
                expr=[]
                for i,b in enumerate(bs):
                    key=(c.path,pn,i)
                    e=(mapped[key] if key in mapped and c.dirs[pn]=='input' else f"1'b{b}" if isinstance(b,str) else wire[b])
                    expr.append(e)
                    terminal_record.append([c.path,pn,i,c.dirs[pn],b,e])
                conns.append(f'.{ident(pn)}({"{"+", ".join(reversed(expr))+"}"})')
            ps=', '.join(f'.{ident(k)}({v})' for k,v in sorted(c.params.items()))
            body.append(f'    {ident(c.module)}'+(f' #({ps})' if ps else '')+f' m{ci} ('+', '.join(conns)+');')
        body.append('endmodule\n')
        text='\n'.join(body)
        # The terminal map is exhaustive and every generated expression resolves to
        # the identical original net/constant; no transport is collapsed here.
        expected={(c.path,p,i,d,b) for (cpath,p,i),(b,d) in endpoints.items() for c in [bypath[cpath]]}
        got={tuple(row[:5]) for row in terminal_record}
        if got!=expected: raise CompositionError(f'{path}: terminal equality failed')
        if mod in module_sources and module_sources[mod] != text:
            raise CompositionError(f"{path}: same module has different actual structure; use explicit variants")
        if mod not in module_sources: sources.append((mod,text))
        module_sources[mod]=text
        replacements.append(Cell(path,mod,{},ports,dirs,'leaf',ytype=mod,yparams={}))
        records.append(dict(inst=path,module=mod,members=members,terminal_count=len(got),terminal_equality=True,
                            terminals=terminal_record,rtl_sha256=hashlib.sha256(text.encode()).hexdigest()))
        used |= ms
    F.cells=[c for c in original if c.path not in used]+replacements
    return sources,dict(schema='opentallas.bind.compose.v1',cores=records,terminal_equality=True)


def apply(binder, spec_path):
    path=Path(spec_path)
    if not path.is_absolute(): path=Path(binder.base)/path
    sources,receipt=compose(binder.F,binder.R,json.loads(path.read_text()),__import__('bind_elab').Cell)
    # Keep source paths outside the repository tree, immutable content-addressed.
    out=path.parent/'composed_rtl';out.mkdir(exist_ok=True)
    for mod,rtl in sources:
        digest=hashlib.sha256(rtl.encode()).hexdigest()
        p=out/(digest+'.sv')
        if p.exists() and p.read_text()!=rtl: raise CompositionError('source hash collision')
        p.write_text(rtl)
        binder.extra_lib.append(str(p))
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    binder.composition_receipt=receipt
