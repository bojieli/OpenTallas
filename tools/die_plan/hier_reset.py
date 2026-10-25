"""Surgical, opt-in hierarchical reset-vector ports; no RTL body re-emission.

Rules name source-level module/child instances and symbolic vector slices. The
caller must classify each replaced edge as external reset distribution. Private
core reset logic is never parsed, dissolved, removed, or bypassed. This helper
alone does not authorize a bind: physical reset identity/offset checks still gate
adoption. Existing interfaces and behavior are retained when OT_HIER_RST=0.
"""
import re
import itertools


class LiftError(ValueError):
    pass


def mask(text):
    """Hide comments and strings while preserving every source offset."""
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',
                  lambda m: re.sub(r'[^\n]', ' ', m.group()), text, flags=re.S)


def close_paren(text, start):
    if text[start] != '(':
        raise LiftError('expected parenthesis')
    depth=0
    for i in range(start,len(text)):
        depth += (text[i]=='(')-(text[i]==')')
        if depth==0:
            return i
    raise LiftError('unbalanced source parentheses')


def skip(text,pos):
    while pos<len(text) and text[pos].isspace():
        pos+=1
    return pos


def header(text,module):
    clean=mask(text)
    hits=list(re.finditer(r'\bmodule\s+'+re.escape(module)+r'\b',clean))
    if len(hits)!=1:
        raise LiftError(f'{module}: expected one module declaration, found{len(hits)}')
    name_end=hits[0].end(); pos=skip(clean,name_end); params=None
    if clean[pos:pos+1]=='#':
        p=skip(clean,pos+1)
        q=close_paren(clean,p);params=(p,q);pos=skip(clean,q+1)
    if clean[pos:pos+1]!='(':
        raise LiftError(f'{module}: ANSI port list required')
    end=close_paren(clean,pos)
    if not re.search(r'\b(input|output|inout)\b',clean[pos+1:end]):
        raise LiftError(f'{module}: non-ANSI or empty port list unsupported')
    tail=re.search(r'\bendmodule\b',clean[end:])
    if not tail:
        raise LiftError(f'{module}: missing endmodule')
    return clean,name_end,params,(pos,end),end+tail.end()


def conditional_masks(clean,start,end):
    """View both sides of source conditionals without expanding or rewriting SV.

    Some RTL shares the closing instance ports after `endif, so the raw source
    has two alternative opening parentheses. Enumerate only local define choices
    and retain exact source positions for the selected instance sites.
    """
    body=clean[start:end]
    directives=list(re.finditer(r"(?m)^[ \t]*`(ifdef|ifndef|else|endif|elsif)\b([^\n]*)",body))
    names=sorted({m.group(2).strip() for m in directives if m.group(1) in ('ifdef','ifndef')})
    if len(names)>5 or any(m.group(1)=='elsif' for m in directives):
        raise LiftError('complex source conditionals require an explicit parser view')
    if not directives:
        return [clean]
    views=[]
    for bits in itertools.product((False,True),repeat=len(names)):
        defines=dict(zip(names,bits));stack=[];active=True;chunks=[];last=0
        for m in directives:
            segment=body[last:m.start()]
            chunks.append(segment if active else re.sub(r'[^\n]',' ',segment))
            chunks.append(re.sub(r'[^\n]',' ',m.group()))
            kind=m.group(1)
            if kind in ('ifdef','ifndef'):
                condition=defines[m.group(2).strip()]
                if kind=='ifndef':condition=not condition
                stack.append((active,condition));active=active and condition
            elif kind=='else':
                if not stack:raise LiftError('unmatched source else')
                parent,condition=stack[-1];stack[-1]=(parent,not condition);active=parent and not condition
            else:
                if not stack:raise LiftError('unmatched source endif')
                active=stack.pop()[0]
            last=m.end()
        segment=body[last:];chunks.append(segment if active else re.sub(r'[^\n]',' ',segment))
        if stack:raise LiftError('unterminated source conditional')
        views.append(clean[:start]+''.join(chunks)+clean[end:])
    return views


def instances(clean,start,end,module,instance):
    out=[]
    for m in re.finditer(r'\b'+re.escape(module)+r'\b',clean[start:end]):
        p=start+m.end();p=skip(clean,p);params=None
        if clean[p:p+1]=='#':
            a=skip(clean,p+1);b=close_paren(clean,a);params=(a,b);p=skip(clean,b+1)
        name=re.match(r'[A-Za-z_$][\w$]*',clean[p:])
        if not name or name.group()!=instance:
            continue
        name_start=p;p=skip(clean,p+name.end())
        if clean[p:p+1]!='(':
            raise LiftError(f'{module}/{instance}: instance arrays or positional syntax unsupported')
        q=close_paren(clean,p)
        if q>=end:
            raise LiftError(f'{module}/{instance}: connection list leaves module')
        out.append((name_start,params,(p,q)))
    return out


def lift_module(text,module,width,edges,port='ot_core_rst_n',enable='OT_HIER_RST'):
    """Add one default-off reset-vector interface to a structural master.

    edge={module, instance, kind:'leaf'|'pass', expr, expected:1}.
    leaf also requires pin, old, role:'external_distribution'; only that exact
    original connection is replaced. pass wires an already-lifted child's vector
    and propagates enable. Symbolic expressions preserve generate loops and IDs.
    """
    clean,name_end,params,ports,mod_end=header(text,module)
    if re.search(r'\b(?:'+re.escape(port)+'|'+re.escape(enable)+r')\b',clean[name_end:mod_end]):
        raise LiftError(f'{module}: lift names already present; refuse double transformation')
    edits=[];receipt=[]
    declaration=f'parameter {enable} = 1\'b0'
    if params:
        comma=', ' if clean[params[0]+1:params[1]].strip() else ''
        edits.append((params[1],params[1],comma+declaration))
    else:
        edits.append((name_end,name_end,f' #({declaration})'))
    edits.append((ports[1],ports[1],f',\n    input wire [({width})-1:0] {port}\n'))
    claimed=set()
    for edge in edges:
        sites={}
        for view in conditional_masks(clean,ports[1]+1,mod_end):
            for site in instances(view,ports[1]+1,mod_end,edge['module'],edge['instance']):
                sites.setdefault(site[0], (*site,view))
        matches=list(sites.values())
        want=edge.get('expected',1)
        if len(matches)!=want:
            raise LiftError(f'{module}/{edge["instance"]}: expected{want} source instances, found{len(matches)}')
        for inst_start,inst_params,conn,view in matches:
            if inst_start in claimed:
                raise LiftError('instance selected by multiple lift rules')
            claimed.add(inst_start)
            if edge['kind']=='leaf':
                if edge.get('source_role',edge.get('role'))!='external_distribution':
                    raise LiftError('replaced reset edge requires explicit external_distribution role; private/unknown reset forbidden')
                pin=edge['pin'];cs=view[conn[0]+1:conn[1]]
                ps=list(re.finditer(r'\.\s*'+re.escape(pin)+r'\s*\(',cs))
                if len(ps)!=1:
                    raise LiftError(f'{module}/{edge["instance"]}.{pin}: expected one named connection')
                a=conn[0]+1+ps[0].end()-1;b=close_paren(view,a)
                old=text[a+1:b]
                if re.sub(r'\s+','',mask(old))!=re.sub(r'\s+','',mask(edge['old'])):
                    raise LiftError(f'{module}/{edge["instance"]}.{pin}: original reset expression changed: {old}')
                new=f'({enable} ? ({edge["expr"]}) : ({old}))'
                edits.append((a+1,b,new))
            elif edge['kind']=='pass':
                target_port=edge.get('port',port)
                if re.search(r'\.\s*'+re.escape(target_port)+r'\s*\(',clean[conn[0]+1:conn[1]]):
                    raise LiftError('child reset vector already connected')
                edits.append((conn[1],conn[1],f', .{target_port}({edge["expr"]})'))
                assignment=f'.{edge.get("enable",enable)}({enable})'
                if inst_params:
                    inside=clean[inst_params[0]+1:inst_params[1]].strip()
                    if inside and not inside.startswith('.'):
                        raise LiftError('positional child parameters unsupported')
                    edits.append((inst_params[1],inst_params[1],(', ' if inside else '')+assignment))
                else:
                    edits.append((inst_start,inst_start,f'#({assignment}) '))
            else:
                raise LiftError('unknown lift edge kind')
        receipt.append(dict(edge, source_sites=len(matches)))
    # No edits to child bodies, generate syntax, arithmetic, parameter expressions,
    # reset registers, or process blocks. Splices retain all untouched source bytes.
    unique={}
    for a,b,replacement in edits:
        if (a,b) in unique and unique[(a,b)]!=replacement:
            raise LiftError('conditional source views disagree on a shared edit')
        unique[(a,b)]=replacement
    for (a,b),replacement in sorted(unique.items(),reverse=True):
        text=text[:a]+replacement+text[b:]
    return text,dict(module=module,port=port,width=str(width),enable=enable,default=0,
                     added_sequential_edges=0,edges=receipt,
                     adoption='requires reset role audit, planned offsets, strict bind and exact smoke')
