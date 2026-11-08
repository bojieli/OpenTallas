"""Read-only LOCAL component checks for an emitted type in a failing die bind.

This never repairs/stamps a bind or proves a complete die.  It recognizes the
native emitter's literal interfaces and a relayed wavefront reset tree.  The
ordinary KIT factories, source census, inventory and physical gates still run.
"""
import hashlib
import json
import re
from pathlib import Path

from kit_assembly import _masked_rtl, _literal_integer
from landing_raw_branches import RawBranches
import kit_topology as KT


def read(path):
    return json.loads(Path(path).read_text())


def parens(text, start):
    if start >= len(text) or text[start] != '(':
        raise ValueError('expected canonical native parenthesis')
    depth = 1
    end = start + 1
    while end < len(text) and depth:
        depth += (text[end] == '(') - (text[end] == ')')
        end += 1
    if depth:
        raise ValueError('unbalanced canonical native parenthesis')
    return text[start+1:end-1], end


def interface(text, module):
    """Inspect the literal header emitted by bind.py, without another HDL frontend."""
    code = _masked_rtl(text)
    mods = list(re.finditer(r'\bmodule\s+(\w+)\b', code))
    if len(mods) != 1 or mods[0][1] != module:
        raise ValueError('selected file must contain its one recorded native module')
    pos = mods[0].end()
    while pos < len(code) and code[pos].isspace(): pos += 1
    if pos == len(code): raise ValueError('missing native interface')
    defaults = {}
    if code[pos] == '#':
        pos += 1
        while pos < len(code) and code[pos].isspace(): pos += 1
        declaration, pos = parens(code, pos)
        for item in declaration.split(','):
            match = re.fullmatch(r'\s*parameter\s+(?:\[(\d+):0\]\s+)?(\w+)\s*=\s*([^,]+?)\s*', item)
            if not match or _literal_integer(match[3]) is None or match[2] in defaults:
                raise ValueError('component defaults must be unique native literal parameters')
            defaults[match[2]] = dict(width=int(match[1])+1 if match[1] else None,
                                      literal=match[3].strip(), value=_literal_integer(match[3]))
    while pos < len(code) and code[pos].isspace(): pos += 1
    declaration, _ = parens(code, pos)
    ports = {}
    for item in declaration.split(','):
        match = re.fullmatch(r'\s*(input|output)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)\s*', item)
        if not match or match[3] in ports:
            raise ValueError('component ports must be unique literal native input/output declarations')
        ports[match[3]] = dict(direction=match[1], width=int(match[2])+1 if match[2] else 1)
    return ports, defaults


def _native_summary(value, type_name):
    return dict(type=value['types'][type_name],
                metadata={k:v for k,v in value.items() if k not in ('types', 'ownership')})


def _reset(text, type_name, metadata, errors, expected_taps, bound_core_resets=None):
    expected = metadata['types'][type_name]
    if expected.get('entry') != 'relayed' or expected.get('entry_stages') != 1:
        errors.append('component proof currently requires the recorded relayed wavefront entry')
    index = RawBranches.driver_index(text)
    edges = [(inst,pins['d'],net,pins['clk']) for net,hits in index.items() for inst,pins in hits
             if inst == 'u_rst_in' or inst.startswith('u_rrl_')]
    roots = [row for row in edges if row[0] == 'u_rst_in']
    if roots != [('u_rst_in','arst_n','rst_root_n','clk')] or re.search(r'\bu_rst_root\b', _masked_rtl(text)):
        errors.append('native reset entry differs from the one recorded synchronous input relay')
    for _,_,net,clock in edges:
        if len(index[net]) != 1 or clock != 'clk':
            errors.append(f'ambiguous/noncanonical native reset driver of {net}')
    aliases = re.findall(r'(?:assign|wire)\s+(\w+)\s*=\s*(\w+)\s*;', _masked_rtl(text))
    depths = {'arst_n': 0}
    for _ in range(len(edges)+len(aliases)+1):
        for _,source,net,_ in edges:
            if source in depths: depths[net] = depths[source]+1
        for net,source in aliases:
            if source in depths: depths[net] = depths[source]
    taps = sorted(set(re.findall(r'\bwire\s+(rst_n_t\d+)\s*;', _masked_rtl(text))))
    if set(taps) != {f'rst_n_t{i}' for i in range(expected_taps)}:
        errors.append('native reset tap declaration census differs from context')
    if len(edges) != expected['relays']+expected['entry_stages']+len(expected.get('outs', [])):
        errors.append('native reset relay census differs from recorded tree/entry/output copies')
    release = expected['release_after_pin']
    if not taps or release != expected['depth_K']+expected['entry_stages']:
        errors.append('native reset metadata lacks consistent depth/release')
    for net in taps + [row[0] for row in expected.get('outs', [])]:
        if depths.get(net) != release:
            errors.append(f'{net}: source reset depth {depths.get(net)}, expected {release}')
    consumers = []
    for match in re.finditer(r'\.rst_n\((\w+)\)', _masked_rtl(text)):
        net = match[1]
        if depths.get(net) != release:
            errors.append(f'reset consumer {net} bypasses recorded release {release}')
    # DIE-HBM-89 11-07: bind_core_resets.json (written by the bind) names the leaf instance/pin that serves each plan
    # core reset (sub_core_leaf parents, reset_from_master, aliases); the leaf must carry a recorded tap at the same
    # depth. Absent file: the plan instance name, unchanged.
    bound = {}
    for b in (bound_core_resets or {}).get(type_name, []):
        bound.setdefault(b['inst'], []).append(b)
    for row in expected.get('core_resets', []):
        rec = bound.get(row['inst'])
        if rec is not None:
            if len(rec) != 1:
                errors.append(f"{row['inst']}: bind records {len(rec)} reset leaves")
                continue
            rec = rec[0]
            inst = rec['leaf']
            hits = list(re.finditer(r'\b'+re.escape(inst)+r'\s*\(', _masked_rtl(text)))
            if len(hits) != 1:
                errors.append(f'{inst}: expected one native reset leaf')
                continue
            args,_ = parens(_masked_rtl(text), _masked_rtl(text).find('(', hits[0].start()))
            connections = dict(re.findall(r'\.(\w+)\(([^()]*)\)', args))
            want = 'rst_n_t'+str(row['tap'])
            if (connections.get(rec['pin']) != rec['reset'] or not re.fullmatch(r'rst_n_t\d+', rec['reset'])
                    or depths.get(rec['reset']) is None or depths.get(rec['reset']) != depths.get(want)):
                errors.append(f"{inst}.{rec['pin']}: reset differs from recorded {want}")
            consumers.append(dict(inst=inst, pin=rec['pin'], reset=connections.get(rec['pin']),
                                  plan_inst=row['inst'], reference_internal_depth=row.get('internal_depth')))
            continue
        inst = 'u_'+re.sub(r'[^A-Za-z0-9_$]', '_', row['inst'])
        # The reset metadata names a native leaf, not a guessed physical proxy.
        hits = list(re.finditer(r'\b'+re.escape(inst)+r'\s*\(', _masked_rtl(text)))
        if len(hits) != 1:
            errors.append(f'{inst}: expected one native reset leaf')
            continue
        args,_ = parens(_masked_rtl(text), _masked_rtl(text).find('(', hits[0].start()))
        connections = dict(re.findall(r'\.(\w+)\(([^()]*)\)', args))
        required = 'rst_n_t'+str(row['tap'])
        if connections.get(row['pin']) != required:
            errors.append(f'{inst}.{row["pin"]}: reset differs from recorded {required}')
        consumers.append(dict(inst=inst, pin=row['pin'], reset=connections.get(row['pin']),
                              reference_internal_depth=row.get('internal_depth')))
    return dict(entry=expected.get('entry'), depth=expected.get('depth_K'), release_after_pin=release,
                tap_depths={t:depths.get(t) for t in taps}, relay_edges=len(edges),
                outputs={r[0]:depths.get(r[0]) for r in expected.get('outs', [])}, consumers=consumers)


def inspect(reference_plan, bind_out, type_name, instance, *, prepared_plan, context_plan=None, asbuilt=None):
    import gen_rtl
    import schema as S
    reference_plan, bind_out, prepared_plan = map(lambda p:Path(p).resolve(),
                                                 (reference_plan, bind_out, prepared_plan))
    context_plan = Path(context_plan or reference_plan).resolve()
    reference, context, prepared = map(read, (reference_plan, context_plan, prepared_plan))
    report = read(bind_out/'bind_report.json')
    errors = []
    global_errors = report.get('errors', [])
    if report.get('n_errors') != len(global_errors): errors.append('global error count/list mismatch')
    for error in global_errors:
        match = re.match(r'^EMIT wavefront core reset ([A-Za-z_]\w*)/', error)
        if not match or match[1] == type_name or match[1] not in reference['partition_types']:
            errors.append('global error is not a proved other-type emission failure: '+error)
    row = report['types'][type_name]
    module = row['module']
    source = bind_out/'rtl'/(module+'.sv')
    text = source.read_text()
    ports, defaults = interface(text, module)
    if len(defaults) != row.get('params',0)+row.get('straps',0):
        errors.append('native default parameter/strap declaration count differs from bind report')
    for label, raw in [('reference',reference), ('context',context)]:
        parts = [p for p in raw['partitions'] if p['type'] == type_name]
        if len(parts) != 1 or parts[0]['name'] != instance or row.get('instances') != 1:
            errors.append(label+': unique native instance/default binding is not proved')
        if raw['partition_types'][type_name]['module'] != module:
            errors.append(label+': selected module identity differs')
    provenance = read(bind_out/'provenance_bind.json').get('provenance', {})
    if Path(provenance.get('plan','')).resolve() != reference_plan:
        errors.append('reference context is not the recorded producer context')
    if not asbuilt and not reference.get('asbuilt'):
        raise ValueError('component proof requires the actual explicit or embedded asbuilt configuration')
    if asbuilt and not str(Path(asbuilt).resolve()).endswith('/'+provenance.get('manifest','').lstrip('/')):
        errors.append('asbuilt path differs from the recorded producer manifest')
    native = KT.native_contract(reference, asbuilt, reference_plan)
    current = KT.native_contract(context, asbuilt, context_plan)
    if _native_summary(native,type_name) != _native_summary(current,type_name):
        errors.append('native-owned selected/context fields changed; native regeneration required')
    selected_native = KT.native_contract(prepared, asbuilt, prepared_plan)
    if selected_native['types'][type_name] != native['types'][type_name]:
        errors.append('prepared plan changes native-owned selected fields')
    typ = prepared['partition_types'][type_name]
    physical = S.Plan(prepared, str(prepared_plan))
    epochs = gen_rtl.bus_epochs(physical)
    wanted = {}
    native_width = {e['conn'][4:]:e.get('native_width') for e in typ.get('internal_stations', [])
                    if e.get('conn','').startswith('bus:')}
    narrowed = []
    for bus in typ.get('buses', []):
        ep = epochs.get((type_name,bus['name']), bus.get('kind','data') in ('data','ctl'))
        wanted[bus['name']] = dict(direction='input' if bus['dir']=='in' else 'output', width=bus['width']+int(ep))
        actual = ports.get(bus['name'])
        if actual != wanted[bus['name']]:
            if (actual and actual['direction']=='input' and bus['dir']=='in'
                    and 0 < actual['width']-int(ep) < bus['width']
                    and native_width.get(bus['name']) == actual['width']-int(ep)):
                narrowed.append(dict(port=bus['name'], plan=bus['width'], bound=actual['width']-int(ep),
                                     prepared_wrapper_dead_input_proof='REQUIRED'))
            else: errors.append('selected native bus mismatch: '+bus['name'])
    reference_slots = {s['name']:s for s in reference['partition_types'][type_name].get('ft_slots', [])}
    ft = []
    for slot in typ.get('ft_slots', []):
        name = slot['name']; old = reference_slots.get(name, {})
        if any(old.get(k)!=slot.get(k) for k in ('width','stations')):
            errors.append('native FT width/stages changed: '+name)
        for suffix,direction in [('_i','input'),('_o','output')]:
            ep = epochs.get((type_name,name+suffix), True)
            wanted[name+suffix] = dict(direction=direction,width=slot['width']+int(ep))
            if ports.get(name+suffix) != wanted[name+suffix]: errors.append('native FT port mismatch: '+name+suffix)
        hits = re.findall(r'\bot_dp_st\s+#\(\.W\((\d+)\)\)\s+u_ft_'+re.escape(name)+r'_o_(\d+)\s*\(', _masked_rtl(text))
        if sorted(int(k) for _,k in hits)!=list(range(slot['stations'])) or any(int(w)!=slot['width'] for w,_ in hits):
            errors.append('actual native FT stage census differs: '+name)
        ft.append(dict(name=name,width=slot['width'],stages=len(hits)))
    reset_meta = read(bind_out/'bind_reset.json')
    reset_type = reset_meta['types'][type_name]
    expected_taps = len(S.tap_grid(physical,type_name))+len(reset_type.get('outs',[]))+len(reset_type.get('core_resets',[]))
    bcr = bind_out/'bind_core_resets.json'
    reset = _reset(text,type_name,reset_meta,errors,expected_taps,
                   read(bcr).get('types', {}) if bcr.is_file() else None)
    extras = {'clk','arst_n'} | set(reset['outputs'])
    if set(ports) != set(wanted)|extras: errors.append('unexpected/missing selected native header ports')
    for name in extras:
        if ports.get(name) != dict(direction='output' if name in reset['outputs'] else 'input',width=1):
            errors.append('native clock/reset port mismatch: '+name)
    return dict(schema='opentallas.bind_component.v1',scope='LOCAL_COMPONENT',
                verdict='FAIL' if errors else 'PASS',source_preparation_only=True,
                global_bind=dict(status='FAIL' if report.get('n_errors') else 'PASS',
                                 n_errors=report.get('n_errors'),errors=global_errors),
                reference_plan=str(reference_plan),context_plan=str(context_plan),prepared_plan=str(prepared_plan),
                bind_out=str(bind_out),type=type_name,instance=instance,
                asbuilt=str(Path(asbuilt).resolve()) if asbuilt else None,
                asbuilt_sha256=hashlib.sha256(Path(asbuilt).read_bytes()).hexdigest() if asbuilt else KT.digest(reference['asbuilt']),
                source=dict(path=str(source),module=module,sha256=hashlib.sha256(text.encode()).hexdigest()),
                ports=ports,default_parameters=defaults,parameter_binding='UNIQUE_NATIVE_INSTANCE_DEFAULTS',
                native_contract=_native_summary(native,type_name),
                prepared_contract=KT.contract(prepared)['types'][type_name],
                reset=reset,ft_stages=ft,narrow_buses=narrowed,producer_context=provenance,
                selected_errors=errors)


def verify(receipt_path, *, context_plan, prepared_plan, bind_out, type_name, instance=None, asbuilt=None):
    old = read(receipt_path)
    if (old.get('scope') != 'LOCAL_COMPONENT' or old.get('verdict') != 'PASS'
            or old.get('source_preparation_only') is not True):
        raise ValueError('component proof is not a passing LOCAL source-preparation report')
    if (old.get('type')!=type_name or Path(old['bind_out']).resolve()!=Path(bind_out).resolve()
            or instance not in (None,old['instance'])):
        raise ValueError('component proof selected identity differs')
    fresh = inspect(old['reference_plan'],bind_out,type_name,old['instance'],prepared_plan=prepared_plan,
                    context_plan=context_plan,asbuilt=asbuilt or old.get('asbuilt'))
    if fresh['selected_errors']:
        raise ValueError('selected component check failed: '+'; '.join(fresh['selected_errors']))
    for key in ('source','default_parameters','native_contract','prepared_contract','ports','reset','global_bind','asbuilt_sha256'):
        if old.get(key)!=fresh.get(key): raise ValueError('component proof identity changed: '+key)
    return fresh
