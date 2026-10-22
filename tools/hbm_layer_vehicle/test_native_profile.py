#!/usr/bin/env python3
"""Price original record23 with the current native return contract, without RTL claims."""
import json
from pathlib import Path
from hbm_layer_vehicle import layer_images as LI
from hbm_layer_vehicle.native_profile import NativeTiming


def main():
    root = Path(__file__).resolve().parents[2]
    fixture = root / "results/rtl/hbm_ds_layer_tput_1018/fixtures/L00"
    records = LI.ds_dispatches_image(fixture / "images/ds_v41_1M_L00_per_die.json")
    original = LI.load_fixture(fixture)[23]
    _, dispatch, _ = records[23]
    import su_bench as SB
    raw = SB.pack_rec(dispatch)
    before = dict(original["vm_in"])
    def original_place():
        place = LI.Placement(0)
        # Original record23 image allocates its input rows33/34, outputs35/36.
        place.nxt = [33] * 8
        return place
    old = LI.su_record(raw, data=dict(before), place=original_place(), pad_zero=True)
    native = LI.su_record(raw, data=dict(before), place=original_place(), pad_zero=True, timing=NativeTiming(18, 15))
    for result in (old, native):
        LI.fixture_check(result, original)
        assert result["status"] == "emitted", result["reasons"]
        assert result["fixture"]["checked_words"] > 0
        assert result["fixture"]["mismatched_words"] == 0
    import importlib.util
    baseline_path = root / "layer_images_baseline.py"
    if not baseline_path.exists():
        baseline_path = root / "results/rtl/hbm_native_record23_1019/layer_images_baseline.py"
    spec = importlib.util.spec_from_file_location("layer_images_baseline", baseline_path)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    previous_place = baseline.Placement(0)
    previous_place.nxt = [33] * 8
    previous = baseline.su_record(raw, data=dict(before), place=previous_place, pad_zero=True)
    assert old["lines"] == previous["lines"], "default programme bytes changed"
    assert old["expect"] == previous["expect"], "default checks changed"
    assert old["preload"] == native["preload"]
    assert old["data"] == native["data"]
    for a, b in zip(old["expect"], native["expect"]):
        assert {k:v for k,v in a.items() if k != "edge"} == {k:v for k,v in b.items() if k != "edge"}
    assert NativeTiming(18, 15).fill_commit == 21
    assert NativeTiming(18, 15).drain_done == 20
    out = root / "record23_profile"
    out.mkdir(exist_ok=True)
    for label, result in (("legacy", old), ("native18", native)):
        LI.column_image(result["lines"], out / label)
        (out / (label + "_checks.json")).write_text(json.dumps(result["expect"], indent=2))
    (out / "inputs.json").write_text(json.dumps(native["data"], indent=2))
    (out / "preload.json").write_text(json.dumps(native["preload"], indent=2))
    vectors = dict(preload=[dict(sector=int(sector), value=sum(int(native["data"][str(addr)],16) << (32*i) for i,addr in enumerate(addrs)))
                              for sector,addrs in native["preload"].items()],
                   checks=[dict(sector=e["sector"], value=sum(int(v) << (32*i) for i,v in enumerate(e["value"])))
                           for e in native["expect"]])
    (out / "vectors.json").write_text(json.dumps(vectors, indent=2))
    print(json.dumps(dict(legacy=dict(setup=old["setup_edge"], issue=old["issue_edges"],
                                     last_commit=old["last_commit"], commands=len(old["lines"])),
                          native=dict(setup=native["setup_edge"], issue=native["issue_edges"],
                                     last_commit=native["last_commit"], commands=len(native["lines"])),
                          unchanged_numeric_words=old["fixture"]["checked_words"],
                          unchanged_input_words=len(old["data"])), indent=2))
    for rr, wr in [(9,7),(18,6),(18,19),(18.0,15),(True,7)]:
        try: NativeTiming(rr,wr)
        except ValueError: pass
        else: raise AssertionError((rr,wr))
    from hbm_layer_vehicle.native_su_calendar import compile_calendar
    kwargs=dict(first_serial=2675,bridge_serial=2675,bridge_stream=3567,host_launch=3500,rows=160)
    default,_=compile_calendar(native["lines"],**kwargs)
    zero,_=compile_calendar(native["lines"],**kwargs,request_lane_edges_by_bank=[0]*8,write_lane_edges_by_bank=[0]*8)
    assert default==zero
    _,model=compile_calendar(native["lines"],**kwargs,request_lane_edges_by_bank=[4,5,4,5,4,5,4,5],write_lane_edges_by_bank=[3]*8)
    for event in model["events"]:
        depth=3 if event["kind"]=="write" else 4+event["bank"]%2
        assert event["vm_pin_sample"]-event["lg_sample"]==2+depth
    for field in ("request_lane_edges_by_bank", "write_lane_edges_by_bank"):
        for bad in ([0]*7, [0]*7+[-1], [0]*7+[True]):
            try: compile_calendar(native["lines"],**kwargs,**{field:bad})
            except ValueError: pass
            else: raise AssertionError((field,bad))
    print("NATIVE_PROFILE PASS unchanged original record23 golden; RTL/topology unqualified")


if __name__ == "__main__":
    main()
