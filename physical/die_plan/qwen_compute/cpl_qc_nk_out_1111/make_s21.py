"""CPL-QC-NK-OUT 11-11: plan_qc99_s21_nkout = plan_qc99_s20 + budgets.core_out_land_types (NK types).
Placement opt-in only: no partition_types / lanes / latency / clock / reset field changes (EQ by construction)."""
import hashlib, json, sys
src, dst = sys.argv[1], sys.argv[2]
raw = open(src, "rb").read()
assert hashlib.sha256(raw).hexdigest().startswith("42478be02a67"), "base must be s20"
p = json.loads(raw)
assert json.dumps(p, indent=1).encode() == raw
nk = sorted(t for t, T in p["partition_types"].items()
            if any(h["module"] == "qfd_tile_nk_a0c" for h in T.get("hard_cores", [])))
# types whose hard cores are only NK (+ the NL in cbx_q10); the two cbn_q00 types that also carry sle_cland_* landing
# cores stay out until their landing-core outputs are checked against landing_placement
sel = [t for t in nk if all(h["module"] in ("qfd_tile_nk_a0c", "qfd_tile_nl_a0c")
                            for h in p["partition_types"][t]["hard_cores"])]
assert "core_out_land_types" not in p["budgets"]
p["budgets"]["core_out_land_types"] = sel
p["note"] = (p.get("note") or "") + (" | s21_nkout (CPL-QC-NK-OUT 11-11): s20 + budgets.core_out_land_types = %d NK types "
             "(NK output landing flops FIRM at the NK pins; 0 pin cycles)" % len(sel)) if isinstance(p.get("note"), str) else p.get("note")
out = json.dumps(p, indent=1)
open(dst, "w").write(out)
print("types", len(sel), sel)
print("left out", [t for t in nk if t not in sel])
print("sha256", hashlib.sha256(out.encode()).hexdigest())
