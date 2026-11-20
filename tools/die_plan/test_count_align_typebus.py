"""QC-PLAN-R3 (COORD 11-20): count_align_plan --type-bus-classes.  Twin instances of one type bus (same source type + bus,
same destination type + bus) take ONE count-align shift vs the plan, the class max; raise only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_plan as CAP  # noqa: E402
from test_count_align_seampad import AP, T, xing  # noqa: E402


def twin_plan():
    # sl_W1 / sl_W3 su_l0 are one type (su_l0_t) feeding one fe type; lanes of 2 hops each; sl_W2 is a different fe type
    parts = [dict(name="sl_W1_su", type="su_t"), dict(name="sl_W3_su", type="su_t"), dict(name="sl_W2_su", type="su_t"),
             dict(name="sl_W1_fe", type="fe_t"), dict(name="sl_W3_fe", type="fe_t"), dict(name="sl_W2_fe", type="fe_u")]
    ports, lanes, base = [], [], {}
    for i in ("W1", "W3", "W2"):
        ln = f"sl_{i}_su__ctl"
        ps = [f"{ln}__0", f"{ln}__1"]
        ports += [dict(id=ps[0], src=dict(part=f"sl_{i}_su", bus="x_ctl_o"), dst=dict(part="cbf", bus="t")),
                  dict(id=ps[1], src=dict(part="cbf", bus="t"), dst=dict(part=f"sl_{i}_fe", bus="x_ctl_i"))]
        lanes.append(dict(id=ln, ports=ps))
        base.update({p: 3 for p in ps})
    return dict(partitions=parts, ports=ports, lanes=lanes, clock=dict(landing_network=dict(count_aligned_cycles=base)))


def test_twin_instances_of_one_type_bus_get_the_same_shift():
    d = twin_plan()
    # re-plan: W1 shifted -1 (hop 0), W3 shifted 0, W2 (other dst type) shifted -2
    out = [xing("sl_W1_su__ctl__0", 2), xing("sl_W1_su__ctl__1", 3), xing("sl_W3_su__ctl__0", 3), xing("sl_W3_su__ctl__1", 3),
           xing("sl_W2_su__ctl__0", 1), xing("sl_W2_su__ctl__1", 3)]
    f, s = CAP.type_bus_class_floor(d, out)
    assert f == {"sl_W1_su__ctl__1": 4} and s["classes"] == 1 and s["classes_unequal"] == 1
    CAP.seam_pad_rules(out, [], f, T, AP, 8)
    lat = {o["port"]: o["lat_cycles"] for o in out}
    shift = {i: lat[f"sl_{i}_su__ctl__0"] + lat[f"sl_{i}_su__ctl__1"] - 6 for i in ("W1", "W3", "W2")}
    assert shift["W1"] == shift["W3"] == 0
    assert shift["W2"] == -2                      # a different destination type is its own class: untouched


def test_equal_class_and_singletons_unchanged():
    d = twin_plan()
    out = [xing(p, 2) for p in d["clock"]["landing_network"]["count_aligned_cycles"]]
    f, s = CAP.type_bus_class_floor(d, out)
    assert f == {} and s["classes_unequal"] == 0


def test_destination_type_bus_takes_one_depth():
    d = twin_plan()
    out = [xing("sl_W1_su__ctl__1", 3, depth=8, hi=3000.0), xing("sl_W3_su__ctl__1", 3, depth=4, hi=2000.0),
           xing("sl_W2_su__ctl__1", 3, depth=4, hi=2000.0)]
    s = CAP.type_bus_class_depth(d, out, T, AP)
    dep = {o["port"]: o["depth"] for o in out}
    assert dep["sl_W3_su__ctl__1"] == 8 and dep["sl_W2_su__ctl__1"] == 4      # W2 lands on another fe type
    assert s == dict(classes_mixed=1, ports_promoted=1)
    o = out[1]
    assert o["rtl"]["DEPTH"] == 8 and o["margin_hi_ps"] == round(7.5 * T - 2000.0, 1) and o["lat_cycles"] == 3
