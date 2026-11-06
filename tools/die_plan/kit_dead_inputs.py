"""Re-prove literal narrow wrapper inputs after canonical wrapper transforms."""
import copy
import hashlib
import re
from pathlib import Path


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
    if not ranges or any(row not in manifest.get('narrow_buses', []) for row in ranges):
        raise ValueError('dead inputs: receipt differs from actual narrow mapping')
    allowed = set()
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
