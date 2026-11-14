"""Opt-in structural composition before Graph: exact terminals, no aliases or timing edits."""
import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path


class CompositionError(ValueError):
    pass


def ident(s):
    return s if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', s) else '\\' + s + ' '


def compose(F, rules, spec, Cell, split=None, base='.'):
    """Return (generated sources, receipt); atomically replace complete member sets.

    spec={cores:[{inst,module,members:[full path],ports:{name:{dir,
    bits:[[ {member,port,bit}, ...], ...]}}}]}. Every listed endpoint is exact;
    multi-endpoint bits require identical original nets. Constants are endpoint-local.
    """
    allow_glue=spec.get('allow_glue',False)
    if type(allow_glue) is not bool:
        raise CompositionError('allow_glue must be boolean')
    original = list(F.cells)
    primitive_receipt=[]
    if 'primitive_splits' in spec:
        from bind_primitive_split import split_cells, PrimitiveSplitError
        try: original,primitive_receipt=split_cells(original,spec['primitive_splits'],Cell)
        except PrimitiveSplitError as exc: raise CompositionError(str(exc)) from exc
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
        # Optional explicit per-core leaf specialization (default absent = unchanged): {leaf module: {PARAM: value}}.
        # Used when the hardened master of this core was generated with leaf parameters that the bound netlist
        # leaves at their defaults (e.g. KV even head_eighth kit flags PORT_REGS/STRAP_*/S3_COPY/LT_COPY), so the
        # composed gold RTL matches the selected hard view. Every module must match a member; a conflicting
        # existing value fails closed (no silent override).
        mparams=core.get('member_params')
        overrides={}
        if mparams is not None:
            if not isinstance(mparams,dict) or not mparams:
                raise CompositionError(f'{path}: member_params must be a non-empty object')
            mods={c.module for c in cs}
            for lm,pv in mparams.items():
                if lm not in mods: raise CompositionError(f'{path}: member_params module {lm} matches no member')
                if not isinstance(pv,dict) or not pv:
                    raise CompositionError(f'{path}: member_params[{lm}] must be a non-empty object')
                for k,v in pv.items():
                    if (not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',k) or type(v) not in (int,str)
                            or not re.fullmatch(r"[0-9]+|[0-9]+'[bdh][0-9A-Fa-f_]+",str(v))):
                        raise CompositionError(f'{path}: unsafe member_params {lm}.{k}={v!r}')
            for c in cs:
                pv=mparams.get(c.module)
                if not pv: continue
                for k,v in pv.items():
                    if k in c.params and str(c.params[k])!=str(v):
                        raise CompositionError(f'{path}: member_params {c.path}.{k}={v} conflicts with bound value {c.params[k]}')
                overrides[c.path]={k:str(v) for k,v in pv.items()}
        parts={rules.part_of(c.path) for c in cs}
        if len(parts)!=1 or None in parts or rules.part_of(path) not in parts:
            raise CompositionError(f'{path}: members/replacement must share one mapped partition')
        if any(c.kind!='leaf' and not (allow_glue and c.kind=='glue') for c in cs):
            raise CompositionError(f'{path}: only actual leaf members supported unless allow_glue is explicit')
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
        # DIE-HBM-92-SU 11-08 (opt-in asbuilt.compose_split, absent = unchanged): members regrouped under hard sub-cores.
        srule=next((r for r in (split or []) if re.fullmatch(r['inst'],path)),None)
        sgroups=[]
        if srule is not None:
            import bind_compose_split as SP
            try:
                for sub in srule['subs']:
                    sgroups += [(sub,k,roles) for k,roles in SP.groups(sub,cs)]
            except SP.SplitError as exc: raise CompositionError(f'{path}: {exc}') from exc
        grouped={c.path for _,_,roles in sgroups for c in roles.values()}
        body=[f'module {mod} (',',\n'.join(declarations),');']
        body += [f'    wire {w};' for w in wire.values()] + assigns
        terminal_record=[]
        term_expr={}
        for ci,c in enumerate(cs):
            conns=[]; expressions={}
            for pn,bs in sorted(c.ports.items()):
                expr=[]
                for i,b in enumerate(bs):
                    key=(c.path,pn,i)
                    e=(mapped[key] if key in mapped and c.dirs[pn]=='input' else f"1'b{b}" if isinstance(b,str) else wire[b])
                    expr.append(e)
                    term_expr[key]=e
                    terminal_record.append([c.path,pn,i,c.dirs[pn],b,e])
                # Empty RTLIL connections stay open; {} is not valid Verilog.
                expression="{"+", ".join(reversed(expr))+"}" if expr else ""
                expressions[pn]=expression
                conns.append(f'.{ident(pn)}({expression})')
            if c.kind=='glue':
                # Preserve the actual primitive and every clock/reset/polarity.
                # Use the same emitter as ordinary bound parent glue; unsupported
                # cells fail closed instead of becoming black-box primitives.
                from bind import _glue, BindError
                try: body.append(_glue(c,expressions,'compose_m'+str(ci)))
                except BindError as exc: raise CompositionError(str(exc)) from exc
                continue
            if c.path in grouped:
                continue
            ps=', '.join(f'.{ident(k)}({v})' for k,v in sorted({**c.params,**overrides.get(c.path,{})}.items()))
            body.append(f'    {ident(c.module)}'+(f' #({ps})' if ps else '')+f' m{ci} ('+', '.join(conns)+');')
        split_record=None
        if srule is not None:
            mods={}
            term_net={k:v[0] for k,v in endpoints.items()}
            nterms=defaultdict(set)
            for k,(b,_) in endpoints.items():
                if isinstance(b,int): nterms[b].add(k)
            pnets=set(netports)
            split_record=dict(rule=srule['inst'],levels=srule.get('levels',[]),subs=[])
            try:
                for sub,k,roles in sgroups:
                    if sub['module'] not in mods: mods[sub['module']]=SP.load(sub,base)
                    conn,rec=SP.bind_sub(sub,mods[sub['module']],roles,term_expr,term_net,nterms,pnets)
                    name=sub['name'].format(k=k)
                    if sub.get('emit_module'): rec['emit']=SP.check_emit(sub,mods[sub['module']],base)
                    cx=', '.join(f'.{ident(p)}('+'{'+', '.join(reversed(v))+'})' for p,v in sorted(conn.items()))
                    body.append(f'    {ident(sub.get("emit_module") or sub["module"])} {name} ({cx});')
                    for w in rec.pop('tie0'):
                        if not re.fullmatch(r'n\d+',w): raise CompositionError(f'{path}: dropped export {w} is not a cut wire')
                        body.append(f"    assign {w} = 1'b0;  // dropped export of {name}: {sub.get('drop_reason','')}")
                    split_record['subs'].append(dict(rec,inst='.'.join(srule.get('levels',[])+[name])))
            except SP.SplitError as exc: raise CompositionError(f'{path}: {exc}') from exc
            if len(grouped)!=sum(len(r) for _,_,r in sgroups): raise CompositionError(f'{path}: split member overlap')
            mod=mod+srule['suffix']
            parts=SP.emit(mod,declarations,body[3:],srule.get('levels',[]))
            text='\n'.join(t for _,t in parts)
        else:
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
        extra={'member_params':{k:overrides[k] for k in sorted(overrides)}} if overrides else {}
        if split_record: extra['split']=split_record
        records.append(dict(inst=path,module=mod,members=members,terminal_count=len(got),terminal_equality=True,**extra,
                            terminals=terminal_record,rtl_sha256=hashlib.sha256(text.encode()).hexdigest()))
        used |= ms
    F.cells=[c for c in original if c.path not in used]+replacements
    return sources,dict(schema='opentallas.bind.compose.v1',cores=records,terminal_equality=True,primitive_splits=primitive_receipt)


def port_alias(spec,widths):
    """({(member leaf, port): (composite inst, composite port)}, {member leaf: composite inst}) for member ports that
    map whole and bit-identical onto one composite port (DIE-KV-64 11-03: tables written on the uncomposed bind, e.g.
    the KV r8 pad tables naming pv slices, follow the composite; any other mapping has no alias and stays stale)."""
    alias,cells={},{}
    for core in spec.get('cores',[]):
        tm=defaultdict(set)
        for pn,pd in core.get('ports',{}).items():
            bits=pd['bits']; idx=pd.get('indices',list(range(pd.get('lo',0),pd.get('lo',0)+len(bits))))
            for i,anchors in enumerate(bits):
                for a in ([anchors] if isinstance(anchors,dict) else anchors):
                    tm[(a['member'],a['port'])].add((pn,idx[i],a['bit']))
        for (m,p),ts in tm.items():
            if (len({t[0] for t in ts})==1 and all(t[1]==t[2] for t in ts) and len(ts)==len({t[2] for t in ts})
                    and len(ts)==widths.get(m,{}).get(p,-1)):
                alias[(m,p)]=(core['inst'],next(iter(ts))[0])
        cells.update({m:core['inst'] for m in core.get('members',[])})
    return alias,cells


def apply(binder, spec_path):
    path=Path(spec_path)
    if not path.is_absolute(): path=Path(binder.base)/path
    gz=path if path.name.endswith('.gz') else path.with_name(path.name+'.gz')
    if path.name.endswith('.gz') or (not path.exists() and gz.exists()):
        # Large composition specs are committed gzip-compressed (same JSON bytes inside).
        import gzip
        spec=json.loads(gzip.open(gz).read())
        path=gz.with_name(gz.name[:-3])
    else:
        spec=json.loads(path.read_text())
    widths={c.path:{p:len(bs) for p,bs in c.ports.items()} for c in getattr(binder.F,'cells',None) or []}
    split=(getattr(binder, "ab", None) or {}).get("compose_split")
    kw=dict(split=split,base=binder.base) if split else {}   # no compose_split: the pre-split call, unchanged
    sources,receipt=compose(binder.F,binder.R,spec,__import__('bind_elab').Cell,**kw)
    if split:
        # sub-core sources (the hard cores' own RTL) join the bind library so verify / kit-rtl resolve the masters
        for r in split:
            for sub in r['subs']:
                # a re-formed sub-core instantiates emit_module: only its sources join (the reference is proof only)
                for f in (sub.get('emit_sources',[]) if sub.get('emit_module') else sub.get('sources',[])):
                    p=f if Path(f).is_absolute() else str(Path(binder.base)/f)
                    if p not in binder.extra_lib: binder.extra_lib.append(p)
    binder.composition_alias,binder.composition_cells=port_alias(spec,widths)
    # Keep source paths outside the repository tree, immutable content-addressed.
    out=path.parent/'composed_rtl';out.mkdir(exist_ok=True)
    for mod,rtl in sources:
        digest=hashlib.sha256(rtl.encode()).hexdigest()
        p=out/(digest+'.sv')
        if p.exists():
            # Content-addressed and immutable: an existing file is never rewritten (source-follow delta snapshots
            # hard-link it read-only from the previous snapshot).
            if p.read_text()!=rtl: raise CompositionError('source hash collision')
        else:
            p.write_text(rtl)
        binder.extra_lib.append(str(p))
    rj=out/'receipt.json'; rtxt=json.dumps(receipt,indent=2)+'\n'
    if rj.exists() and rj.stat().st_size<65536 and '"opentallas.blob_pointer.v1"' in rj.read_text():
        pass   # blob pointer (full receipt kept on its host, too large for git): never overwrite the pointer
    elif not rj.exists() or rj.read_text()!=rtxt:
        tmp=out/'.receipt.json.tmp'; tmp.write_text(rtxt); os.replace(tmp,rj)
    binder.composition_receipt=receipt
