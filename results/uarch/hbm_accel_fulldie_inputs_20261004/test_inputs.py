"""Small compiler API fixtures only: no actual accelerator model/build/proof.

Synthetic one-pin blocks exercise binding/placement formatting and refusal.
They must never be used as physical instances or performance evidence.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("inputs", ROOT/"tools/hbm_accel_fulldie_inputs.py")
U = importlib.util.module_from_spec(spec)
spec.loader.exec_module(U)


def fixture(root):
    def save(path, value):
        raw = value if isinstance(value, str) else json.dumps(value)
        (root/path).write_text(raw)
        return dict(path=path, sha256=hashlib.sha256(raw.encode()).hexdigest())
    rtl = save("fixture.sv", "module parser_fixture; endmodule\n")
    uarch = save("fixture_uarch.py", "# Parser fixture, NOT unified accelerator model\n")
    tech = save("fixture_tech.json", {})
    pin_names = ["p["+str(i)+"]" for i in range(8)]
    lef = save("fixture.lef", "MACRO parser_fixture\n SIZE 2 BY 2 ;\n"+
               "".join(" PIN "+p+"\n END "+p+"\n" for p in pin_names)+"END parser_fixture\n")
    lib = save("fixture.lib", "library(parser_fixture) { cell(parser_fixture) {} }\n")
    view = save("view.json", dict(actual_macro_abstract=True, master="parser_fixture", rtl_source=rtl,
                parameters={}, lef=lef, size_um=[2,2], liberty=dict(ss=lib, ff=lib)))
    instances, slots = [], {}
    roles = ["sm", "rf", "l2", "service", "controller", "phy", "collective"]
    port = dict(p=dict(kind="signal", physical_bits=8, bits_per_cycle=8, lef_pins=pin_names))
    for n, role in enumerate(roles):
        name = "fixture"+str(n)
        instances.append(dict(name=name, role=role, master="parser_fixture", module="parser_fixture",
                              rtl_source=rtl, parameters={}, lef=lef, abstract_provenance=view,
                              ports=port, tied_ports=[]))
        slots[name] = dict(parameters={}, ports=port, reservation_um=[4*n,0,4,4], location_um=[4*n,0],
                          orientation="R0", macs_per_cycle=0, communication_intensity=0,
                          mux_demux_fanout_area_um2=0, latency_cycles=1)
    selection = save("selection.json", dict(design_kind="hbm_accelerator", target="deepseek", adopted=True,
                      census_complete=True, top="parser_fixture", top_source=rtl, top_parameters={}, source_pins=[rtl],
                      instances=instances))
    model = dict(design_kind="hbm_accelerator", target="deepseek", slot_latency_route_ready=True,
                 selection_sha256=selection["sha256"], uarch_source=uarch, technology_source=tech,
                 top_parameters={}, die_um=[0,0,32,8], core_um=[0,0,32,8], reticle_mm2=1,
                 routing_layers=["M5"], macro_grid_um=[1,1], required_roles=roles,
                 replica_counts={r:1 for r in roles}, instances=slots,
                 boundaries=[dict(endpoints=[[i["name"],"p"] for i in instances], layers=["M5"],
                                  tracks_per_bit=1, required_tracks=8, capacity_tracks=16,
                                  wire_cycles=1, cdc_cycles=0, credit_cycles=0, composed_latency_cycles=1)],
                 layer_reservations=[dict(layers=["M5"], box_um=[0,0,32,8], purpose="signal")],
                 clock_domains_ns=dict(fixture=1), uncertainty_ps=dict(setup_ss=60,hold_ff=25),
                 composed_token_cycles=1)
    manifest = dict(schema="hbm_accel_fulldie_bindings.v1", target="deepseek", inputs=[],
                    selected_instances=selection, unified_model=save("model.json",model), uarch_source=uarch)
    return manifest, model, save


class Check(unittest.TestCase):
    def test_format_and_refusals(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest, model, save = fixture(root)
            result = U.compile_inputs(root, manifest)
            U.emit(root/"out",result)
            text = (root/"out/macro_place.tcl").read_text()
            self.assertEqual(text.count("place_macro -macro_name"),7)
            self.assertLess(text.rfind('error "selected master mismatch"'),text.index("place_macro -macro_name"))
            self.assertFalse(result["signoff"])
            with self.assertRaisesRegex(ValueError,"overwrite"):
                U.emit(root/"out",result)
            # No placement output exists for any rejected record.
            for change, reason in (("slot", "undersized"), ("route", "over capacity"), ("clock", "uncertainty")):
                bad = copy.deepcopy(model)
                if change == "slot": bad["instances"]["fixture0"]["reservation_um"][2]=1
                if change == "route": bad["boundaries"][0]["capacity_tracks"]=4
                if change == "clock": bad["uncertainty_ps"]["setup_ss"]=0
                m = dict(manifest, unified_model=save("bad.json",bad))
                with self.assertRaisesRegex(ValueError,reason): U.compile_inputs(root,m)
            with self.assertRaisesRegex(ValueError,"missing source-pinned"):
                U.compile_inputs(root,dict(manifest,selected_instances=None))
            (root/"fixture.sv").write_text("changed")
            with self.assertRaisesRegex(ValueError,"source drift"):
                U.compile_inputs(root,manifest)


if __name__ == "__main__":
    unittest.main()
