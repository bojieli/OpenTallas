"""Recover M6 stub policy from actual kit hooks; ambiguous policy fails closed."""
import re
import sys
from pathlib import Path


def depth(config):
    p = Path(config)
    if not p.is_file():
        return ''
    text = p.read_text()
    if not re.search(r'^export MAX_ROUTING_LAYER\s*=\s*M6\s*$', text, re.M):
        return ''
    hooks = re.findall(r'^export (?:PRE_GLOBAL_ROUTE_TCL|POST_DETAIL_ROUTE_TCL)\s*=\s*(\S+)', text, re.M)
    values, visited = set(), set()
    def resolve(hook):
        if hook.startswith('/work/'):
            return p.parent / hook[len('/work/'):]
        if hook.startswith('/src/'):
            return Path.cwd() / hook[len('/src/'):]
        q = Path(hook)
        return q if q.is_absolute() else p.parent / q
    def walk(hook):
        f = resolve(hook)
        if f in visited:
            return
        visited.add(f)
        if not f.is_file():
            raise ValueError(f'route hook missing; cannot establish M6 policy: {f}')
        source = f.read_text()
        if 'm6_pin_access.tcl' in source:
            found = re.findall(r'set ::ot_m6_stub_um ([0-9.]+)', source)
            if len(found) != 1 or not 0 < float(found[0]) <= 1:
                raise ValueError('M6 pin hook missing/invalid explicit stub depth')
            values.add(float(found[0]))
        for child in re.findall(r'^source\s+([^\s;]+)', source, re.M):
            if child.startswith('/src/') and not child.startswith('/src/physical/ref_tile/'):
                # Generated policy is in the kit hook, not in implementation
                # helpers (which can source runtime QDM_SDC_DIR expressions).
                continue
            if '$' in child or '[' in child:
                raise ValueError(f'cannot resolve dynamic route hook: {child}')
            walk(child)
    for hook in hooks:
        walk(hook)
    if len(values) > 1:
        raise ValueError('conflicting M6 pin hook depths')
    return str(next(iter(values))) if values else ''


if __name__ == '__main__':
    print(depth(sys.argv[1]))
