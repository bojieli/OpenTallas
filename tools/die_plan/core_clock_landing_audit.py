"""OpenROAD Python: actual two-terminal clock-metal connectivity and macro access.

ODB MASTER COUNT OUTPUT.json. This audits native wire geometry, including via
metal enclosures and transformed real ITerm PORT shapes; STA names do not count
as evidence of a completed physical connection. The landing helper's partial
FIXED output must FAIL until normal detailed routing connects the real driver.
"""
import json, sys
import odb


def rect(q):
    return (q.xMin(), q.yMin(), q.xMax(), q.yMax())


def overlap(a, b):
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def body_intersection(a, b):
    q = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
    return q if q[0] < q[2] and q[1] < q[3] else None


def contained(q, p):
    return q[0] >= p[0] and q[1] >= p[1] and q[2] <= p[2] and q[3] <= p[3]


def audit_net(net, receiver):
    terms = list(net.getITerms())
    if str(net.getSigType()) != 'CLOCK' or len(terms) != 2 or list(net.getBTerms()):
        raise ValueError('expected CLOCK with exactly two ITerms and no BTerms')
    for box in receiver.getInst().getMaster().getObstructions():
        layer = box.getTechLayer()
        if str(layer.getType()) == 'ROUTING' and layer.getRoutingLevel() >= 6:
            raise ValueError('M6 escape requires actual child OBS below M6')
    if list(net.getSWires()):
        raise ValueError('selected CLOCK must not use special-wire routing skip')
    driver = next(t for t in terms if t != receiver)
    if str(driver.getIoType()) != 'OUTPUT' or driver.getInst().getMaster().isBlock():
        raise ValueError('expected native standard-cell output driver')
    nodes, bonds = [], []
    def add(layer, box):
        nodes.append((layer, box)); return len(nodes) - 1
    wire = net.getWire()
    if wire is None:
        raise ValueError('missing actual native wire')
    it = odb.dbWirePathItr(); it.begin(wire)
    p, ps = odb.dbWirePath(), odb.dbWirePathShape()
    while it.getNextPath(p):
        while it.getNextShape(ps):
            s = ps.shape
            if not s.isVia():
                add(s.getTechLayer().getName(), rect(s))
            else:
                v = s.getTechVia() or s.getVia()
                if v is None:
                    raise ValueError('unknown native via')
                x, y = s.getViaXY()
                pieces = []
                for box in v.getBoxes():
                    layer = box.getTechLayer()
                    if str(layer.getType()) != 'ROUTING':
                        continue
                    a, b, c, d = rect(box)
                    pieces.append(add(layer.getName(), (a+x, b+y, c+x, d+y)))
                if len(pieces) < 2:
                    raise ValueError('via lacks native metal enclosures')
                bonds.extend((pieces[0], n) for n in pieces[1:])
    metal_count = len(nodes)
    if any(layer.startswith('M') and layer[1:].isdigit() and int(layer[1:]) > 6 for layer, _ in nodes):
        raise ValueError('selected CLOCK metal exceeds reviewed M6 ceiling')
    port_shapes = [(layer.getName(), rect(q)) for layer, q in receiver.getGeometries()]
    macro = rect(receiver.getInst().getBBox())
    bad_access = []
    for layer, q in nodes:
        if layer.startswith('M') and layer[1:].isdigit() and int(layer[1:]) <= 5:
            inside = body_intersection(q, macro)
            if inside is not None and not any(layer == l and contained(inside, r) for l, r in port_shapes):
                bad_access.append(dict(layer=layer, rect=q, inside=inside))
    term_ids = []
    for term in (driver, receiver):
        pieces = [add(layer.getName(), rect(q)) for layer, q in term.getGeometries()]
        if not pieces:
            raise ValueError('terminal has no native PORT metal')
        bonds.extend((pieces[0], n) for n in pieces[1:])
        term_ids.append(pieces[0])
    parent = list(range(len(nodes)))
    def root(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]; n = parent[n]
        return n
    def join(i, j):
        parent[root(i)] = root(j)
    for i, j in bonds:
        join(i, j)
    for i, (layer, a) in enumerate(nodes):
        for j in range(i):
            if nodes[j][0] == layer and overlap(a, nodes[j][1]):
                join(i, j)
    connected = root(term_ids[0]) == root(term_ids[1])
    islands = sum(root(n) != root(term_ids[0]) for n in range(metal_count))
    return dict(net=net.getName(), receiver=receiver.getInst().getName()+'/clk',
                driver=driver.getInst().getName()+'/'+driver.getMTerm().getName(),
                native_wire_metal_shapes=metal_count, connected=connected, orphan_metal_shapes=islands,
                illegal_macro_access=bad_access,
                passed=connected and not bad_access and islands == 0)


def main():
    source, master, expected, output = sys.argv[1:]
    db = odb.dbDatabase.create(); odb.read_db(db, source)
    block = db.getChip().getBlock(); rows = []
    for inst in block.getInsts():
        if inst.getMaster().getName() != master:
            continue
        term = inst.findITerm('clk')
        try:
            if term is None or term.getNet() is None:
                raise ValueError('missing native clk/net')
            rows.append(audit_net(term.getNet(), term))
        except Exception as exc:
            rows.append(dict(receiver=inst.getName()+'/clk', passed=False, error=str(exc)))
    passed = len(rows) == int(expected) and all(r['passed'] for r in rows)
    result = dict(schema='opentallas.fixed_clock_landing_audit.v1', source=source,
                  master=master, expected=int(expected), count=len(rows), rows=rows,
                  verdict='PASS' if passed else 'FAIL')
    with open(output, 'w') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print('OT_CLAND_NATIVE_CONNECTIVITY', result['verdict'], 'selected', len(rows),
          'connected', sum(r.get('connected', False) for r in rows),
          'illegal_access', sum(bool(r.get('illegal_macro_access')) for r in rows))
    return 0 if passed else 1

if __name__ == '__main__':
    sys.exit(main())
