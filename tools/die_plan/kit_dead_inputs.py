"""Re-prove narrow and whole-unbound wrapper inputs after canonical transforms."""
import copy
import hashlib
import re
from pathlib import Path


def _hash_file(path):
    path=Path(path).resolve()
    return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def _strict_mapping(path):
    import json
    doc=json.loads(Path(path).read_text())
    proof=doc.get('proof',{})
    if doc.get('n_errors')!=0 or doc.get('errors')!=[] or doc.get('unmapped')!=0 or any(
            proof.get(k)!=0 for k in ('unbound','tied','undriven','multiply_bound')):
        raise ValueError('whole-unbound inputs require strict native source mapping')
    return {k:proof[k] for k in ('unbound','tied','undriven','multiply_bound')}


def _native_ports(path,module):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    import die_port_bind as D
    mods=[m for m in D.parse_modules(Path(path).read_text(),str(path)) if m.name==module]
    if len(mods)!=1:
        raise ValueError('whole-unbound inputs: exact native module absent/ambiguous')
    return set(mods[0].ports)


def unbound_receipt(rows, missing, report, source, module):
    """Strict source-relative proof; no independent Yosys or LEC claim."""
    if not rows:
        return None
    _strict_mapping(report)
    ports=_native_ports(source,module)
    for row in rows:
        if (set(row)!={'port','width'} or not isinstance(row['port'],str) or
                not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',row['port']) or
                type(row['width']) is not int or row['width']<1 or
                row['port'] not in missing or row['port'] in ports):
            raise ValueError('whole-unbound input differs from missing native ABI')
    return dict(basis='strict native source mapping plus absent native ABI; not LEC/EQ',
                bind_report=_hash_file(report),bound_source=_hash_file(source),
                bound_module=module,absent_ports=[r['port'] for r in rows])


def validate_unbound(manifest,receipt):
    rows=receipt.get('unbound_input_buses',[])
    if not rows:
        return set()
    if rows!=manifest.get('unbound_input_buses'):
        raise ValueError('whole-unbound inputs differ from actual kit mapping')
    proof=receipt.get('unbound_source_proof',{})
    for key in ('bind_report','bound_source'):
        ref=proof.get(key,{})
        if not ref.get('path') or _hash_file(ref['path'])!=ref:
            raise ValueError('whole-unbound source/mapping hash changed')
    actual=unbound_receipt(rows,manifest.get('plan_buses_unbound',[]),
            proof['bind_report']['path'],proof['bound_source']['path'],proof.get('bound_module'))
    if actual!=proof:
        raise ValueError('whole-unbound source receipt differs')
    return {f"{r['port']}[{i}]" for r in rows for i in range(r['width'])}


def refresh(manifest, wrapper):
    doc = manifest.get('dead_inputs')
    if not doc:
        return
    from kit_assembly import _masked_rtl
    wrapper = Path(wrapper).resolve()
    code = _masked_rtl(wrapper.read_text())
    proof = doc.get('proof', {})
    receipt = proof.get('receipt', {})
    if proof.get('verdict') != 'PASS' or not receipt.get('sha256'):
        raise ValueError('dead inputs: missing original PASS receipt')
    if re.search(r'\.\s*\*', code):
        raise ValueError('dead inputs: wildcard connection unsupported')
    ranges = receipt.get('narrow_buses', [])
    whole=receipt.get('unbound_input_buses',[])
    if (not ranges and not whole) or any(row not in manifest.get('narrow_buses', []) for row in ranges):
        raise ValueError('dead inputs: receipt differs from actual narrow mapping')
    allowed = validate_unbound(manifest,receipt)
    for row in whole:
        port,width=row['port'],row['width']
        pat=r'\binput\s+(?:wire\s+)?\[\s*'+str(width-1)+r'\s*:\s*0\s*\]\s+'+re.escape(port)+r'\b'
        body,n=re.subn(pat,'',code)
        if n!=1 or re.search(r'\b'+re.escape(port)+r'\b',body):
            raise ValueError(f'whole-unbound input is read or declaration differs: {port}')
    for row in ranges:
        port, lo, hi = row['port'], int(row['bound']), int(row['plan'])
        if not 0 < lo < hi:
            raise ValueError('dead inputs: invalid narrow mapping')
        allowed.update(f'{port}[{i}]' for i in range(lo, hi))
        # Only the canonical literal-vector input declaration and literal-select
        # reads are supported. Any whole-vector/dynamic/implicit read refuses.
        pat = r'\binput\s+(?:wire\s+)?\[\s*'+str(hi)+r'\s*:\s*0\s*\]\s+'+re.escape(port)+r'\b'
        body, n = re.subn(pat, '', code)
        if n != 1:
            raise ValueError(f'dead inputs: unsupported declaration {port}')
        if re.search(r'\.\s*'+re.escape(port)+r'\s*[,)]', body):
            raise ValueError(f'dead inputs: implicit connection {port}')
        for hit in re.finditer(r'(?<![.\w])'+re.escape(port)+r'\b', body):
            sel = re.match(r'\s*\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\]', body[hit.end():])
            if not sel:
                raise ValueError(f'dead inputs: nonliteral/whole-vector use {port}')
            a = int(sel[1]); b = int(sel[2]) if sel[2] else a
            if min(a,b) < 0 or max(a,b) > hi or any(lo <= bit < hi for bit in range(min(a,b),max(a,b)+1)):
                raise ValueError(f'dead inputs: omitted payload bit is read: {port}{sel[0]}')
    if set(doc.get('bits', [])) != allowed:
        raise ValueError('dead inputs: incomplete or unexpected dead bit inventory')
    previous = copy.deepcopy(receipt)
    receipt.update(wrapper=str(wrapper), sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest())
    if previous != receipt:
        proof.setdefault('transform_checks', []).append(dict(method='literal wrapper input select audit', previous=previous))
