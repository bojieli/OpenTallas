#!/usr/bin/env python3
"""Declare the missing native R8 pad-count port on cbn_q11 (no RTL/count/value change).

The original profile3_pad bind manifest emits this four-bit r8pad_strap,
but the plan declared only its five sibling R8 ports. GEN therefore refuses
the top-level ID. Physical sites use the same legal strap-lattice allocator
as the existing CB parent IDs; existing sites and declarations stay fixed.
Usage: delta_cbnq11_r8strap_1101.py PLAN_IN PLAN_OUT REPORT
"""
import json
import sys

from delta_cbid_1101 import sites

TYPE = "cbn_q11__cl49ae4555"
PORT = "strap_r8pad_u_t_2_2_n_b"


def main():
    pin, pout, report = sys.argv[1:]
    raw = json.load(open(pin))
    t = raw["partition_types"][TYPE]
    straps = t["count_straps"]
    assert not any(s["name"] == PORT for s in straps), "already declared"
    assert any(s["name"] == "strap_r8pad_u_t_2_2_n_a" and s["width"] == 4 for s in straps)
    addition = dict(name=PORT, width=4,
                    note="OWNER 10-28 R8 pad-count strap; bind parent manifest, unchanged values/cycles",
                    layer="M5", sites_um=sites(t, 4))
    straps.append(addition)
    open(pout, "w").write(json.dumps(raw) + "\n")
    open(report, "w").write(json.dumps(dict(type=TYPE, added=addition, added_cycles=0,
        source="profile3_pad/bind_parent_id_straps.json: width4 kind r8pad_strap",
        scope="plan pin declaration only; existing native parent values and RTL unchanged"), indent=1) + "\n")


if __name__ == "__main__":
    main()
