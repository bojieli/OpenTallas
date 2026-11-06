# Shared fixed-child kit assembly

Source assembly only; no RTL function, cycle, clock constraint or signoff policy change.

- Ten focused tests PASS, including actual Yosys elaboration with one fixed child and a differently parameterized native soft sibling.
- Focused helper, signed_children and existing RTL-lint tests: 31 PASS total.
- Real S81 IDX binding source and SIGNED child BB: shared output byte-identical to the accepted specialization helper. Source sealing rejects changed bytes and wrong literal parameters before rewriting.
- Real HBM q_spb2: original native DD256/PAW11/PREL1/XSLOT1 calls at u_bound.u_u_xc_Q2/Q3 assembled against the actual SIGNED fixed-port BB. Actual Yosys hierarchy resolves exactly both expected macros; zero discrepancies (inventory.json). Active parent kit untouched.
- Real HBM q_su21 prefix-file collision: suffixed and unsuffixed modules aliased byte-for-byte. Overlapping modules, include-dependent files, and reserved BB/simulation model collisions remain errors.

## Callers

The existing RTL-lint frontend emits actual hierarchy JSON and kit_hierarchy.json only when kit_assembly.json is present. No second frontend or new signoff gate; default no-manifest output is unchanged. The helper stages itself into a flat kit and passes isolated Python loading.

S81 legacy generation uses assemble_fixed_children after existing SIGNED view/geometry/parameter-contract validation and BB staging, and writes kit_assembly.json. The HBM/other bind kit-rtl path uses shared source deduplication.

Standalone actual-parent adapters can call:

```sh
python3 tools/die_plan/kit_assembly.py assemble --rtl-dir KIT/rtl --contracts bindings.json --receipt KIT/kit_assembly.json
# Existing RTL frontend emits post-assembly Yosys write_json.
python3 tools/die_plan/kit_assembly.py inventory --yosys-json hierarchy.json --top TOP --contracts bindings.json --receipt KIT/kit_hierarchy.json
```

Bindings use existing children + parameter_contracts JSON and an optional explicit parent_profile (top plus actual effective parameters). S81 supplies the profile and checks recipe overrides against the sealed child-parent contract. No source is selected merely because a top name matches; selected instance bytes and child paths must match. The caller must validate child_params against its SIGNED view. Ambiguous lexical source instances are unsupported; actual elaborated inventory reports missing children, wrong masters, repeated elaborations and unplanned hardening. It is a preparation diagnostic, not a new signoff gate.

No P&R/STA was run for this tooling change. Current physical parent trials retain their own independent qualification obligations.
