"""Explicit AP metadata carry for an approved, shape-identical master swap.

No placement, net, wire, guide or timing-constraint change is made here.
Cell timing changes with the variant; no timing qualification is supplied.
The caller must separately authorize the cell variant and prove its functions.
Only preferred AP positions consumed by core-pin GRT are copied. Full AP
via/segment/catalog payload and DRT are NOT qualified. All copied APs are owned
by NEW master MPins; old-master pointers are never reused.
"""


class AccessPointCarryError(ValueError):
    pass


def _xy(point):
    return tuple(point) if isinstance(point, (tuple, list)) else (point.x(), point.y())


def _rect(rect):
    return rect.xMin(), rect.yMin(), rect.xMax(), rect.yMax()


def _value(value):
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, 'getString'):
        return value.getString()
    if hasattr(value, 'getValue'):
        return value.getValue()
    raise AccessPointCarryError('unsupported native AP enum binding')


def _boxes(boxes, variant_layers):
    result = []
    for box in boxes:
        layer = box.getTechLayer()
        if layer is None:
            raise AccessPointCarryError('non-layer pin/obstruction shape unsupported')
        name = layer.getName()
        if name in variant_layers:
            if layer.getType() not in ('MASTERSLICE', 'IMPLANT'):
                raise AccessPointCarryError('variant exception cannot hide routing/cut geometry')
            continue
        result.append((name, _rect(box)))
    return tuple(sorted(result))


def _pin_identity(pin):
    master = pin.getMaster()
    return master.getLib().getName(), master.getName(), pin.getId()


def _pin_map(old, new, variant_layers):
    if (old.getWidth(), old.getHeight(), old.getType(), _xy(old.getOrigin())) != (
            new.getWidth(), new.getHeight(), new.getType(), _xy(new.getOrigin())):
        raise AccessPointCarryError('master footprint/type/origin differs')
    old_site, new_site = old.getSite(), new.getSite()
    if (old_site.getName() if old_site else None) != (new_site.getName() if new_site else None):
        raise AccessPointCarryError('master site differs')
    if _boxes(old.getObstructions(), variant_layers) != _boxes(new.getObstructions(), variant_layers):
        raise AccessPointCarryError('master routing obstructions differ')
    a = {term.getName(): term for term in old.getMTerms()}
    b = {term.getName(): term for term in new.getMTerms()}
    if set(a) != set(b):
        raise AccessPointCarryError('master pin names differ')
    mapping = {}
    for name in a:
        if (a[name].getIoType(), a[name].getSigType()) != (b[name].getIoType(), b[name].getSigType()):
            raise AccessPointCarryError('master pin direction/signal role differs: ' + name)
        def index(term):
            out = {}
            for pin in term.getMPins():
                if list(pin.getPolygonGeometry()):
                    raise AccessPointCarryError('polygon pin geometry unsupported')
                signature = _boxes(pin.getGeometry(), variant_layers)
                if signature in out:
                    raise AccessPointCarryError('ambiguous equal-shape MPins: ' + name)
                out[signature] = pin
            return out
        x, y = index(a[name]), index(b[name])
        if set(x) != set(y):
            raise AccessPointCarryError('master pin geometry differs: ' + name)
        mapping.update({pin.getId(): y[signature] for signature, pin in x.items()})
    return mapping


def _grt_signature(ap):
    return _xy(ap.getPoint()), ap.getLayer().getName()


class GlobalRouteAccessPointCarry:
    """Exclusive metadata-only session for CORE preferred-AP GRT positions.

    The caller must explicitly accept this narrow scope. Never use its result
    for detailed routing, all-access-point GRT, non-core pins, or an AP catalog
    preservation claim. The pinned native core-pin GRT consumes only preferred
    AP point and routing layer. It does not consume AP vias/segments/types.
    """
    SCOPE = 'core_preferred_global_routing_only'

    def __init__(self, db, *, variant_layers, scope):
        if scope != self.SCOPE or not variant_layers:
            raise AccessPointCarryError('explicit GRT-only scope and variant layers required')
        self.db = db
        self.block = db.getChip().getBlock()
        self.variant_layers = frozenset(variant_layers)
        self.initial_owners = {_pin_identity(ap.getMPin()) for ap in self.block.getAccessPoints()
                               if ap.getMPin() is not None}
        self.clones = {}

    def swap(self, inst, replacement):
        import odb
        old = inst.getMaster()
        if inst.getBlock() != self.block or inst.isDoNotTouch() or inst.isHierarchical():
            raise AccessPointCarryError('wrong block or protected/hierarchical instance')
        if old.getType() != 'CORE' or replacement.getType() != 'CORE':
            raise AccessPointCarryError('only native CORE preferred-pin GRT is qualified')
        index = inst.getPinAccessIdx()
        if index < 0 or index >= 2**31:
            raise AccessPointCarryError('source has invalid pin_access_idx')
        mapping = _pin_map(old, replacement, self.variant_layers)
        if any(_pin_identity(pin) in self.initial_owners for pin in mapping.values()):
            raise AccessPointCarryError('target already has an unqualified AP catalog')
        pose = (tuple(inst.getLocation()), _value(inst.getOrient()),
                _value(inst.getPlacementStatus()), _rect(inst.getBBox()))
        nets = {it.getMTerm().getName(): it.getNet().getId() if it.getNet() else None
                for it in inst.getITerms()}
        selected = {}
        for it in inst.getITerms():
            name = it.getMTerm().getName()
            preferred = list(it.getPrefAccessPoints())
            if it.getNet() and it.getSigType() not in ('POWER', 'GROUND'):
                if it.getNet().getWire() is not None:
                    raise AccessPointCarryError('selected routed net is outside GRT-only scope')
                if not preferred:
                    raise AccessPointCarryError('connected source pin lacks preferred AP: ' + name)
            seen = set()
            for ap in preferred:
                pin = ap.getMPin()
                if (pin is None or pin.getId() not in mapping
                        or _pin_identity(pin) != _pin_identity(next(
                            p for p in it.getMTerm().getMPins() if p.getId() == pin.getId()))):
                    raise AccessPointCarryError('source preferred AP has wrong MPin owner')
                if pin.getId() in seen or ap.getLayer().getRoutingLevel() <= 0:
                    raise AccessPointCarryError('ambiguous preferred selection or nonrouting AP')
                seen.add(pin.getId())
            selected[name] = preferred
        translated = {}; cloned = 0
        for aps in selected.values():
            for ap in aps:
                pin = mapping[ap.getMPin().getId()]
                key = (_pin_identity(pin), index, _grt_signature(ap))
                new_ap = self.clones.get(key)
                if new_ap is None:
                    new_ap = odb.dbAccessPoint.create(self.block, pin, index)
                    new_ap.setPoint(odb.Point(*_xy(ap.getPoint()))); new_ap.setLayer(ap.getLayer())
                    self.clones[key] = new_ap; cloned += 1
                translated[ap.getId()] = new_ap
        if not inst.swapMaster(replacement):
            raise AccessPointCarryError('native swapMaster refused')
        if (inst.getMaster().getLib().getName(), inst.getMaster().getName()) != (
                replacement.getLib().getName(), replacement.getName()):
            raise AccessPointCarryError('native swap did not install requested master')
        inst.setPinAccessIdx(index)
        for name, aps in selected.items():
            it = inst.findITerm(name)
            for ap in aps:
                it.setAccessPoint(mapping[ap.getMPin().getId()], translated[ap.getId()])
            actual = list(it.getPrefAccessPoints())
            if sorted(_grt_signature(ap) for ap in actual) != sorted(_grt_signature(ap) for ap in aps):
                raise AccessPointCarryError('preferred GRT positions changed')
            if {(_pin_identity(ap.getMPin()), _grt_signature(ap)) for ap in actual} != {
                    (_pin_identity(mapping[ap.getMPin().getId()]), _grt_signature(ap)) for ap in aps}:
                raise AccessPointCarryError('preferred AP does not belong to new MPin')
        after_pose = (tuple(inst.getLocation()), _value(inst.getOrient()),
                      _value(inst.getPlacementStatus()), _rect(inst.getBBox()))
        after_nets = {it.getMTerm().getName(): it.getNet().getId() if it.getNet() else None
                      for it in inst.getITerms()}
        if pose != after_pose or nets != after_nets or inst.getPinAccessIdx() != index:
            raise AccessPointCarryError('native swap changed pose/nets/index')
        return dict(instance=inst.getName(), old_master=old.getName(), new_master=replacement.getName(),
                    scope=self.SCOPE, pin_access_idx=index, cloned_preferred_positions=cloned,
                    preferred_APs=sum(map(len, selected.values())), pose_unchanged=True,
                    nets_unchanged=True, full_AP_catalog_preserved=False, detailed_route_qualified=False)
