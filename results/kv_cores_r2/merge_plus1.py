import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
a["cores"].update(b["cores"]); a["cores"] = dict(sorted(a["cores"].items()))
a["note"] = ("Complete lists (face_guard uncapped; listed_complete=True for all 15). Clock/reset pins (kit freeze.json clocks/resets + ck/ck_phy/rst_n) "
             "and missing_port rows are excluded as in the kit gate; counts equal each kit's face_guard.json fail_counts except "
             "core_order (fresh synth: 4 bits dropped->feedthrough). por_n buses (core_guard u_native__por_n, core_prompt u_control__por_n) are "
             "classed in_fanout by the pricing rule (name lacks 'rst'); they are reset-class -> regional reset net 0 cyc candidate, TOK-QK/COORD to confirm. "
             "Sources: synth netlists of the 10-26 KVHR kits (pre zero-cycle recut); 7 re-synthesized 10-27 by KV-CORES-R2 "
             "(cdc_ch/ci/hi, core_order/peer/queue/rx); ingest_eng = KV-INGEST-R2 kit on current source. "
             "'source'/'sink' = core port and the internal net/cell (or other port) face_guard names; parent-side ends follow from the die plan nets.")
json.dump(a, open(sys.argv[3], "w"), indent=1)
with open(sys.argv[4], "w") as f:
    f.write("core\tbus\twidth\tbits_failing\tbit_lo\tbit_hi\tplus1_class\tclasses\tsource_n\tsink_n\tsource_examples\tsink_examples\n")
    for c, v in a["cores"].items():
        if not v.get("buses"):
            f.write(f"{c}\t-\t0\t0\t\t\tZERO_CYCLE\t{json.dumps(v.get('fail_counts'))}\t\t\t\t\n"); continue
        for p in v["buses"]:
            f.write("\t".join(map(str, [c, p["bus"], p["width"], p["bits_failing"], p["bit_range"][0], p["bit_range"][1], ",".join(p["plus1_class"]),
                    json.dumps(p["classes"]), p["source_n"], p["sink_n"], " | ".join(p["source"][:3]), " | ".join(p["sink"][:3])])) + "\n")
    tot = sum(v.get("plus1_buses", 0) for v in a["cores"].values())
    print("cores", len(a["cores"]), "plus1 buses", tot, {c: v.get("plus1_buses") for c, v in a["cores"].items()})
