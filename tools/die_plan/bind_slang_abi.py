"""Opt-in Slang parameterized leaf interfaces, without elaborating private bodies.

Slang's explicit/empty blackbox importer reuses the first instance's port ABI.
Elaborate a harmless interface placeholder per instance, then Yosys-blackbox it.
Evaluated attributes on one real port preserve the parameters Slang otherwise
removes from specialized modules. Real verification sources remain untouched.
"""
import hashlib
import json
import re
from pathlib import Path

PREFIX = 'ot_bind_parameter_'
STRING_PREFIX = 'ot_bind_string_parameter_'
IDENT = r'[A-Za-z_][A-Za-z0-9_$]*'


def _split(text):
    parts, start, stack, quoted, escape = [], 0, [], False, False
    for i, c in enumerate(text):
        if quoted:
            if escape: escape = False
            elif c == '\\': escape = True
            elif c == '"': quoted = False
        elif c == '"': quoted = True
        elif c in '([{': stack.append(c)
        elif c in ')]}':
            if not stack: raise ValueError('unbalanced parameter expression')
            stack.pop()
        elif c == ',' and not stack:
            parts.append(text[start:i]); start = i+1
    if stack or quoted: raise ValueError('unbalanced parameter expression')
    return parts + [text[start:]]


def _parameters(header, body):
    chunks = []
    pm = re.search(r'#\s*\(', header)
    if pm:
        # The caller's header ends after the port list; find the matching #().
        start = header.index('(', pm.start()); level=0; quoted=False; escape=False
        for i in range(start, len(header)):
            c=header[i]
            if quoted:
                if escape: escape=False
                elif c=='\\': escape=True
                elif c=='"': quoted=False
            elif c=='"': quoted=True
            elif c=='(': level+=1
            elif c==')':
                level-=1
                if not level:
                    chunks.append(header[start+1:i]); break
        else: raise ValueError('unbalanced module parameter header')
    chunks += re.findall(r'\bparameter\b([^;]*);', body)
    names=[]
    for chunk in chunks:
        kind='parameter'
        for decl in _split(chunk):
            m=re.match(r'\s*(parameter|localparam)\b',decl)
            if m: kind=m.group(1)
            if kind=='localparam': continue
            lhs=decl.split('=',1)[0].strip()
            if re.search(r'\btype\b',lhs): raise ValueError('type parameters require explicit frontend support')
            m=re.search(r'('+IDENT+r')\s*$',lhs)
            if not m or '=' not in decl: raise ValueError(f'unsupported parameter declaration: {decl[:120]}')
            if m.group(1) not in names: names.append(m.group(1))
    return names


def stage(files, keep, requested, out, module_re, strip, match):
    """Stage only named interface leaves; return files and a small source receipt."""
    if not isinstance(requested,list) or not requested or any(not isinstance(n,str) or not re.fullmatch(IDENT,n) for n in requested):
        raise ValueError('slang_parameterized_blackboxes must be a nonempty list of module names')
    wanted=set(requested)
    if wanted & set(keep): raise ValueError(f'placeholder cannot replace structural parents: {sorted(wanted & set(keep))}')
    found=set(); staged=[]; records=[]; out=Path(out)
    for name in files:
        source=Path(name); text=strip(source.read_text()); edits=[]
        for m in module_re.finditer(text):
            master=m.group(1)
            if master not in wanted: continue
            end=text.index('endmodule',m.end())
            # Skip the parameter block, then locate the module port list.
            pos=m.end()
            while text[pos].isspace(): pos+=1
            if text[pos]=='#': pos=match(text,text.index('(',pos))+1
            port=text.find('(',pos); semi=text.find(';',pos)
            if port<0 or semi<port: raise ValueError(f'{master}: parameterized leaf needs actual ports')
            header_end=text.find(';',match(text,port))+1
            header=text[m.start():header_end]; body=text[header_end:end]
            interface_body=re.sub(r'\bfunction\b.*?\bendfunction\b','',body,flags=re.S)
            interface_body=re.sub(r'\b(?:parameter|localparam|input|output|inout)\b[^;]*;','',interface_body)
            interface_body=re.sub(r'^\s*`[^\n]*','',interface_body,flags=re.M)
            if interface_body.strip():
                raise ValueError(f'{master}: placeholder requires an interface-only stub; private body is forbidden')
            params=_parameters(header,body)
            if not params: raise ValueError(f'{master}: no overridable parameters to preserve')
            # Prefer ANSI port declarations. For old-style declarations ignore
            # constant functions while locating an actual module port.
            direction=re.search(r'\b(input|output|inout)\b',text[port:header_end])
            if direction: anchor=port+direction.start()
            else:
                masked=re.sub(r'\bfunction\b.*?\bendfunction\b',lambda z:' '*len(z.group()),body,flags=re.S)
                direction=re.search(r'\b(input|output|inout)\b',masked)
                if not direction: raise ValueError(f'{master}: no real port for evaluated parameter attributes')
                anchor=header_end+direction.start()
            if '_ot_bind_abi_anchor' in text[m.start():end]: raise ValueError(f'{master}: reserved placeholder name collision')
            attr='(* '+', '.join([f'{PREFIX}{p}={p}' for p in params] + [f'{STRING_PREFIX}{p}=($typename({p})=="string")' for p in params])+' *) '
            edits += [(anchor,anchor,attr),(end,end,"wire _ot_bind_abi_anchor; assign _ot_bind_abi_anchor=1'b0;\n")]
            found.add(master);records.append({'module':master,'parameters':params,'source':str(source)})
        if edits:
            for a,b,replacement in sorted(edits,reverse=True):text=text[:a]+replacement+text[b:]
            out.mkdir(parents=True,exist_ok=True)
            dest=out/(hashlib.sha256(str(source).encode()).hexdigest()[:12]+'_'+source.name)
            dest.write_text(text);staged.append(str(dest))
        else: staged.append(name)
    if found!=wanted:raise ValueError(f'parameterized leaf definitions missing: {sorted(wanted-found)}')
    return staged,records


def restore(path, requested):
    """Restore exact evaluated per-instance parameter values after late blackboxing."""
    path=Path(path); design=json.loads(path.read_text()); marked={}; masters=set()
    for name,module in design['modules'].items():
        values={}; string_kinds={}
        for port in module.get('ports',{}):
            attrs=module.get('netnames',{}).get(port,{}).get('attributes',{})
            for key,value in attrs.items():
                if key.startswith(STRING_PREFIX):
                    string_kinds[key[len(STRING_PREFIX):]]=bool(int(str(value),2))
                    continue
                if not key.startswith(PREFIX):continue
                param=key[len(PREFIX):]
                if param in values and values[param]!=value:raise ValueError(f'{name}: conflicting parameter marker {param}')
                values[param]=value
        if not values:continue
        if set(string_kinds)!=set(values):raise ValueError(f'{name}: parameter type markers missing')
        for param,is_string in string_kinds.items():
            if not is_string:continue
            value=values[param]
            if isinstance(value,str) and re.fullmatch('[01]+',value):
                if len(value)%8:raise ValueError(f'{name}: non-byte string parameter {param}')
                value=bytes(int(value[i:i+8],2) for i in range(0,len(value),8)).decode('latin1')
            if not isinstance(value,str):raise ValueError(f'{name}: invalid string parameter {param}')
            if any(ord(ch)<32 or ord(ch)>126 for ch in value):raise ValueError(f'{name}: string parameter {param} requires unsupported literal escaping')
            # Yosys marks string literals made entirely of bit digits with a space.
            values[param]=value+' ' if re.fullmatch('[01xz]+',value) else value
        master=module.get('attributes',{}).get('hdlname',name).rstrip()
        if master not in requested:raise ValueError(f'{name}: marker on undeclared leaf master {master}')
        if module.get('cells') or module.get('processes') or module.get('memories'):
            raise ValueError(f'{name}: private body survived placeholder blackboxing')
        if not int(str(module.get('attributes',{}).get('blackbox','0')),2):raise ValueError(f'{name}: placeholder is not blackboxed')
        defaults=module.setdefault('parameter_default_values',{})
        for k,v in values.items():
            if k in defaults and defaults[k]!=v:raise ValueError(f'{name}: conflicting existing parameter {k}')
            defaults[k]=v
        marked[name]=values;masters.add(master)
    if masters!=set(requested):raise ValueError(f'parameterized leaf markers missing: {sorted(set(requested)-masters)}')
    instances=0
    for module in design['modules'].values():
        for name,cell in module.get('cells',{}).items():
            if cell['type'] not in marked:continue
            parameters=cell.setdefault('parameters',{})
            for k,v in marked[cell['type']].items():
                if k in parameters and parameters[k]!=v:raise ValueError(f'{name}: existing parameter conflicts with evaluated {k}')
                parameters[k]=v
            instances+=1
    temp=path.with_suffix(path.suffix+'.abi.tmp')
    with temp.open('w') as f:json.dump(design,f,indent=2);f.write('\n')
    temp.replace(path)
    return {'masters':sorted(masters),'specialized_modules':len(marked),'instances':instances}
