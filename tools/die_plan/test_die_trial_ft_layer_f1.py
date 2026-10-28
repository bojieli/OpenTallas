"""F1 (KV-PLAN-DELTA-8): die_trial reports FT bits whose face-pin layer class changes inside a partition."""
import types
import die_trial as DT


def test_ft_layer_audit_counts_class_switches(monkeypatch):
    P = types.SimpleNamespace(types={"a": dict(ft_slots=[dict(name="ft")]), "b": dict(ft_slots=[dict(name="ft")]),
                                     "c": dict(ft_slots=[dict(name="ft")])},
                              parts={"pa": dict(type="a"), "pb": dict(type="b")})
    tab = {"a": [("ft_i", 0, "M4"), ("ft_i", 1, "M6"), ("ft_o", 0, "M5"), ("ft_o", 1, "M7")],   # turn, same class
           "b": [("ft_i", 0, "M4"), ("ft_i", 1, "M6"), ("ft_o", 0, "M6"), ("ft_o", 1, "M6")]}   # bit 0 switches
    monkeypatch.setattr(DT.gen_phys, "type_pins", lambda P_, tn: [(b, i, l, 0., 0., "E") for b, i, l in tab[tn]])
    r = DT.ft_layer_audit(P)
    assert r == dict(slot_bits=4, class_switch_bits=1, by_type={"b": 1})   # type c has no instance: skipped
