"""Explicit physical FT interfaces of the two qualified QC core families.

No pins are removed and no pin comparison is waived. The full physical ABI is
planned only after its captured routed netlist proves independent unary cones.
"""
import gzip, hashlib, json, re
from pathlib import Path

SUPPORTED = {'qfd_dv_s8x_vmr', 'qfd_dv_s8_crh_rp1'}
SCHEMA = 'opentallas.core_ft_physical.v1'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def blocks(text, kind):
    for m in re.finditer(r'\b'+kind+r'\s*\(\s*"?([^"()]+)"?\s*\)\s*\{', text):
        i=m.end();depth=1;quoted=False;escape=False
        while depth and i<len(text):
            c=text[i]
            if escape:escape=False
            elif c=='\\' and quoted:escape=True
            elif c=='"':quoted=not quoted
            elif not quoted:depth += (c=='{')-(c=='}')
            i+=1
        if depth:raise ValueError('unclosed '+kind)
        yield m.group(1).strip(),text[m.end():i-1]

def read_text(path):
    return gzip.open(path,'rt').read() if str(path).endswith('.gz') else Path(path).read_text()

def unary_cells(path):
    text=read_text(path)
    out={}
    for name,body in blocks(text,'cell'):
        pins={n:b for n,b in blocks(body,'pin')}
        ins=[n for n,b in pins.items() if re.search(r'direction\s*:\s*input\s*;',b)]
        outs=[n for n,b in pins.items() if re.search(r'direction\s*:\s*output\s*;',b)]
        if len(ins)!=1 or len(outs)!=1:continue
        f=re.search(r'function\s*:\s*"([^";]+)"',pins[outs[0]])
        fun=re.sub(r'[\s()]','',f.group(1)) if f else ''
        if fun in (ins[0],'!'+ins[0],'~'+ins[0]):out[name]=(ins[0],outs[0],fun)
    return out

def isolation(text,module,decl,library):
    """Re-prove every consumer of the declared inputs, not a name-based exemption."""
    if re.findall(r'^\s*module\s+(\w+)\s*\(',text,re.M)!=[module]:raise ValueError('routed module mismatch')
    ports={n:d.upper() for d,n in re.findall(r'\b(input|output|inout)\s+(?:wire\s+)?(\w+)\s*;',text)}
    wanted={p['name']:p['direction'] for p in decl['ports']}
    if len(wanted)!=4 or any(ports.get(n)!=d for n,d in wanted.items()):raise ValueError('declared physical ports missing/different')
    cells={};uses={};complex_uses={}
    for m in re.finditer(r'^\s*(\w+)\s+(\\\S+|[\w$]+)\s*\((.*?)\);',text,re.M|re.S):
        master,inst,body=m.groups();connections=dict(re.findall(r'\.(\w+)\s*\(\s*([^()]*)\s*\)',body))
        if not connections:continue
        if inst in cells:raise ValueError('duplicate routed cell')
        cells[inst]=(master,{k:v.strip() for k,v in connections.items()})
        for p,n in cells[inst][1].items():
            if re.fullmatch(r'\w+',n):uses.setdefault(n,[]).append((inst,p))
            else:
                for token in re.findall(r'\b\w+\b',n):complex_uses.setdefault(token,[]).append((inst,p))
    aliases={};alias_drivers={}
    for dst,src in re.findall(r'\bassign\s+([^;=]+)=([^;]+);',text):
        dst,src=dst.strip(),src.strip()
        if re.fullmatch(r'\w+',dst) and re.fullmatch(r'\w+',src):
            aliases.setdefault(src,[]).append(dst);alias_drivers[dst]=alias_drivers.get(dst,0)+1
        else:
            for token in re.findall(r'\b\w+\b',dst+' '+src):complex_uses.setdefault(token,[]).append(('assign','expression'))
    results=[];occupied=set()
    for arc in decl['arcs']:
        todo=[arc['source']];seen=set();pathcells=set();outputs=set()
        while todo:
            n=todo.pop()
            if n in seen:continue
            seen.add(n)
            if n in complex_uses:raise ValueError('FT reaches compound expression')
            drivers=alias_drivers.get(n,0)+(ports.get(n)=='INPUT')
            drivers+=sum(cells[i][0] in library and p==library[cells[i][0]][1] for i,p in uses.get(n,[]))
            if drivers>1:raise ValueError('FT net has multiple drivers')
            if n in ports:
                if ports[n]=='INPUT' and n!=arc['source']:raise ValueError('FT reaches another input')
                if ports[n]=='OUTPUT':outputs.add(n)
                if ports[n]=='INOUT':raise ValueError('FT reaches inout')
            todo.extend(aliases.get(n,[]))
            for inst,pin in uses.get(n,[]):
                master,con=cells[inst]
                if master not in library:raise ValueError('FT reaches non-unary/core cell '+inst+'/'+pin)
                inp,out,fun=library[master]
                if pin==out:continue
                if pin!=inp or inp not in con or out not in con:raise ValueError('FT uses non-signal primitive pin')
                if not re.fullmatch(r'\w+',con[out]):raise ValueError('non-scalar FT output')
                pathcells.add(inst);todo.append(con[out])
        if outputs!={arc['sink']} or not set(arc['cells'])<=pathcells:raise ValueError('FT cone differs from declared isolated arc')
        if occupied & seen:raise ValueError('FT cones share signals')
        occupied|=seen
        results.append({'source':arc['source'],'sink':arc['sink'],'kind':arc['kind'],'cells':sorted(pathcells),'nets':sorted(seen)})
    if sorted(a['kind'] for a in results)!=['clock','reset']:raise ValueError('expected declared clock/reset pair')
    return results

RECT_RE=re.compile(r'RECT\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;')

def _lef_obs(text):
    """-> (text before OBS, OBS body, text after OBS) of a one-macro LEF"""
    found=list(re.finditer(r'^[ \t]*OBS[ \t]*\n(.*?)^[ \t]*END[ \t]*\n',text,re.M|re.S))
    if len(found)!=1:raise ValueError('detail view: expected exactly one OBS block')
    m=found[0];return text[:m.start()],m.group(1),text[m.end():]

def _lef_pins(text):
    out={}
    for full,name in re.findall(r'^([ \t]*PIN[ \t]+(\S+)[ \t]*\n.*?^[ \t]*END[ \t]+\2[ \t]*\n)',text,re.M|re.S):
        if name in out:raise ValueError('detail view: duplicate PIN '+name)
        out[name]=full
    return out

def _obs_layers(body):
    out=[]
    for ln in body.splitlines():
        if not ln.strip():continue
        m=re.fullmatch(r'\s*LAYER\s+(\S+)\s*;\s*',ln)
        if m:out.append((m.group(1),[]));continue
        if not out:raise ValueError('detail view: OBS geometry before a LAYER')
        out[-1][1].append(ln)
    return out

def detail_view(selected,captured,receipt):
    """DIE-QC-97 11-11 ISLAND-VIEW (b): a selected LEF that is the captured qualified FT LEF plus refined OBS only (the
    abstract_detail splice: DRT-0073 pin access on the same signed ODB).  Accepted only when ALL hold, else ValueError:
      - the detail receipt names the captured LEF as its base and the selected file as its output (sha256),
        says detail_pins_equal_base and check_ok, has no pin-clear cut and no problems, and lists the detailed layers;
      - re-parsed, every PIN block is byte-equal to the captured LEF and all text outside OBS is byte-equal;
      - inside OBS, the layer order is unchanged, unlisted layers are byte-equal, a listed layer holds only RECT
        statements and every one lies inside a captured OBS rect of the same layer (a refinement, never new blockage
        outside the signed footprint, never a removed layer)."""
    if not isinstance(receipt,dict):raise ValueError('detail view: no detail receipt')
    if receipt.get('base_sha256')!=sha(captured):raise ValueError('detail view: receipt base is not the captured FT LEF')
    if receipt.get('out_sha256')!=sha(selected):raise ValueError('detail view: receipt output is not the selected LEF')
    if receipt.get('detail_pins_equal_base') is not True or receipt.get('check_ok') is not True:raise ValueError('detail view: receipt lacks its pin/geometry check')
    if receipt.get('pin_clear_um') is not None or receipt.get('problems'):raise ValueError('detail view: receipt has pin-clear cuts or problems')
    layers=receipt.get('layers_detailed')
    if not isinstance(layers,list) or not layers or not all(isinstance(l,str) for l in layers) or len(set(layers))!=len(layers):raise ValueError('detail view: receipt lists no detailed layers')
    a=Path(captured).read_text();b=Path(selected).read_text()
    pa,pb=_lef_pins(a),_lef_pins(b)
    if not pa or pa!=pb:raise ValueError('detail view: pins differ from the captured FT LEF')
    a0,ao,a1=_lef_obs(a);b0,bo,b1=_lef_obs(b)
    if (a0,a1)!=(b0,b1):raise ValueError('detail view: change outside OBS')
    la,lb=_obs_layers(ao),_obs_layers(bo)
    if [l for l,_ in la]!=[l for l,_ in lb]:raise ValueError('detail view: OBS layer order changed')
    rects={}
    for (layer,ga),(_,gb) in zip(la,lb):
        if ga==gb:continue
        if layer not in layers:raise ValueError('detail view: OBS changed on unlisted layer '+layer)
        base=[]
        for ln in ga:
            m=RECT_RE.fullmatch(ln.strip())
            if not m:raise ValueError('detail view: non-RECT captured OBS on '+layer)
            base.append([float(x) for x in m.groups()])
        n=0
        for ln in gb:
            m=RECT_RE.fullmatch(ln.strip())
            if not m:raise ValueError('detail view: non-RECT OBS statement on '+layer)
            x0,y0,x1,y1=[float(x) for x in m.groups()]
            if not any(r[0]-1e-6<=x0 and r[1]-1e-6<=y0 and x1<=r[2]+1e-6 and y1<=r[3]+1e-6 for r in base):raise ValueError('detail view: OBS rect outside the captured blockage on '+layer)
            n+=1
        if not n:raise ValueError('detail view: OBS removed on '+layer)
        rects[layer]=n
    if not rects:raise ValueError('detail view: no OBS difference although the LEF bytes differ')
    return dict(signed_view_ok='via detail receipt',base_sha256=receipt['base_sha256'],out_sha256=receipt['out_sha256'],layers_detailed=sorted(rects),rects=rects)

def receipt_beside(lef):
    """the detail receipt prov_view.py stages next to a selected detailed LEF (<module>.detail_receipt.json), or None"""
    p=Path(lef).with_name(Path(lef).name[:-len('.lef')]+'.detail_receipt.json') if str(lef).endswith('.lef') else None
    return json.loads(p.read_text()) if p and p.is_file() else None

def load(entry,module,lef,tt,ff,root=None,ppins=None,plan_dir=None,detail_receipt=None):
    spec=entry.get('physical_ft')
    if not spec:return None
    if module not in SUPPORTED or set(spec)!={'proof','proof_sha256','unconsumed_outputs'}:raise ValueError('unsupported physical FT contract')
    p=Path(spec['proof']);p=p if p.is_absolute() else Path(root or '.')/p
    if sha(p)!=spec['proof_sha256']:raise ValueError('physical FT proof bytes changed')
    r=json.loads(p.read_text())
    if r.get('schema')!=SCHEMA or r.get('module')!=module:raise ValueError('physical FT proof module/schema mismatch')
    files={}
    required={'lef','tt','ff','declaration','interface','signoff','provenance','primitive_lib','netlist','core_pins','lec'}
    if set(r.get('files',{}))!=required:raise ValueError('physical FT evidence closure incomplete')
    for key,v in r['files'].items():
        rel=Path(v['path'])
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('FT evidence must be self-contained')
        f=p.parent/rel
        if sha(f)!=v['sha256']:raise ValueError('physical FT captured '+key+' changed')
        files[key]=f
    via=None
    for key,actual in [('lef',lef),('tt',tt),('ff',ff)]:
        if sha(actual)!=sha(files[key]):
            if key=='lef' and detail_receipt is not None:via=detail_view(actual,files[key],detail_receipt);continue
            raise ValueError('selected '+key+' differs from captured qualified FT view')
    import sdc_lint
    decl=json.loads(files['declaration'].read_text())
    errors=sdc_lint.ft_verify(decl)
    if errors:raise ValueError('invalid FT declaration: '+str(errors))
    model=json.loads(files['interface'].read_text())
    errors=sdc_lint.ft_model_errors(decl,model,require_characterised=True)
    if errors:raise ValueError('uncharacterised FT model: '+str(errors))
    so=json.loads(files['signoff'].read_text());prov=json.loads(files['provenance'].read_text());lec=json.loads(files['lec'].read_text())
    if lec.get('verdict')!='EQUIVALENT' or lec.get('top')!=module or Path(lec.get('netlist','')).name!='6_final.v':raise ValueError('FT source lacks matching routed LEC identity')
    if so.get('inputs',{}).get('ft_interface_model')!=model:raise ValueError('FT interface is not the captured signoff model')
    if so.get('verdict')!='SIGNED' or not prov.get('flow_tag') or prov.get('lec_verdict')!='EQUIVALENT':raise ValueError('FT source lacks exact qualified signoff/LEC/flow')
    nettext=read_text(files['netlist'])
    if hashlib.sha256(nettext.encode()).hexdigest()!=r['routed_netlist_sha256']:raise ValueError('routed netlist identity changed')
    graph=isolation(nettext,module,decl,unary_cells(files['primitive_lib']))
    if graph!=r['isolation']:raise ValueError('FT isolation graph changed')
    import die_sta_related as D
    if ppins is None:
        pinpath=Path(entry['pins_file']);pinpath=pinpath if pinpath.is_absolute() else Path(plan_dir or '.')/pinpath
        ppins=json.loads(pinpath.read_text())
    expected=D.canon_sha256(D.canon_pins(json.loads(files['core_pins'].read_text()),r['outline_um']))
    if D.canon_sha256(D.canon_pins(ppins,entry.get('outline_um')))!=expected:raise ValueError('physical FT canonical core pins differ from qualified source')
    ftnames={p['name'] for p in decl['ports']}
    for key in ['tt','ff']:
        cell=next((b for n,b in blocks(files[key].read_text(),'cell') if n==module),None)
        if cell is None:raise ValueError('captured timing model module missing')
        for name,body in blocks(cell,'pin'):
            if name not in ftnames:
                for refs in re.findall(r'related_pin\s*:\s*"([^"]+)"',body):
                    if set(refs.split())&ftnames:raise ValueError('FT timing reference reaches retained core pin')
    inputs={p['name'] for p in decl['ports'] if p['direction']=='INPUT'}
    outputs={p['name'] for p in decl['ports'] if p['direction']=='OUTPUT'}
    adapter=entry.get('native_port_adapter',{})
    if adapter.get('merge')!={} or adapter.get('cycles')!=0 or adapter.get('tie')!={n:"1'b0" for n in inputs}:raise ValueError('FT inputs need explicit zero ties without other port edits')
    if set(spec['unconsumed_outputs'])!=outputs:raise ValueError('FT outputs need explicit unconsumed accounting')
    out=dict(ports=decl['ports'],core_header_sha256=r['core_header_sha256'],proof=str(p),proof_sha256=sha(p),module=module,isolation=graph)
    if via:out.update(signed_view_ok=via['signed_view_ok'],detail_view=via)
    return out

def extend_header(header,contract,raw_header=None):
    if hashlib.sha256((raw_header or header).encode()).hexdigest()!=contract['core_header_sha256']:raise ValueError('logical core header changed')
    for p in contract['ports']:
        if re.search(r'\b'+re.escape(p['name'])+r'\b',header):raise ValueError('physical port already in logical header')
    m=re.search(r'\)\s*;\s*$',header)
    if not m:raise ValueError('unsupported physical header')
    added=',\n'+',\n'.join('    '+p['direction'].lower()+' wire '+p['name'] for p in contract['ports'])+'\n'
    return header[:m.start()].rstrip()+added+header[m.start():]

def contracts(cores,macros,staged,root=None,plan_dir=None):
    out={}
    for c in cores or []:
        if not c.get('physical_ft'):continue
        mod=c['module'];matches=[m for m in macros if m[1]==mod]
        if not matches:raise ValueError('physical FT macro missing')
        _,_,lef,tt,*_=matches[0];tt=Path(tt);ff=tt.with_name(tt.name.replace('_tt.lib','_ff.lib'))
        value=load(c,mod,lef,tt,ff,root,plan_dir=plan_dir,detail_receipt=receipt_beside(lef))
        inst='u_'+c['inst'];pattern=r'^\s*'+re.escape(mod)+r'(?:\s+#\([^\n]*\))?\s+'+re.escape(inst)+r'\s*\((.*?)^\s*\);'
        bodies=re.findall(pattern,staged,re.M|re.S)
        if len(bodies)!=1:raise ValueError('physical FT target instance identity missing/ambiguous '+inst)
        body=bodies[0]
        for p in value['ports']:
            n=p['name'];connection=re.findall(r'\.'+re.escape(n)+r'\(([^()]*)\)',body)
            if p['direction']=='INPUT' and connection!=["1'b0"]:raise ValueError('physical FT input tie not emitted '+inst+'/'+n)
            if p['direction']=='OUTPUT' and connection:raise ValueError('declared unconsumed FT output is connected '+inst+'/'+n)
        if mod in out and out[mod]['proof_sha256']!=value['proof_sha256']:raise ValueError('mixed FT proof for repeated macro')
        if mod not in out:out[mod]=dict(value,instances=[])
        out[mod]['instances'].append({'instance':c['inst'],'physical_instance':c.get('physical_inst'),'input_ties':c['native_port_adapter']['tie'],'unconsumed_outputs':c['physical_ft']['unconsumed_outputs']})
    return out


def retain(contracts,directory):
    import shutil
    directory=Path(directory);receipt={}
    for module,c in contracts.items():
        original=Path(c['proof']);doc=json.loads(original.read_text());out=directory/module;out.mkdir(parents=True,exist_ok=True)
        for item in doc['files'].values():
            rel=Path(item['path']);(out/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original.parent/rel,out/rel)
        shutil.copy2(original,out/'proof.json')
        receipt[module]={**c,'proof':str(Path('ft_physical')/module/'proof.json')}
    if receipt:(directory.parent/'physical_ft_interfaces.json').write_text(json.dumps(receipt,indent=1)+'\n')
