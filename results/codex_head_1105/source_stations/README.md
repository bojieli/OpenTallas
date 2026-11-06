# Planned HEAD source station realization

Default-off `realize_internal_stations` emits the already planned station banks in the logical source and preserves its exact placement sidecar across physical export/rebind. Before this fix, hd_spn had zero of its 24 planned banks and hd_spn_end zero of 12. Each bank carries all 565 data bits and its epoch bit. These are previously priced stages; no model latency or K increase.

Proof compares the complete nonstation RTL token stream after inverting only declared station rewiring and normalizing the equivalent registered output boundary forms. Literal generated station instances are tested against the explicit delay model; the output boundary forms are independently compared under arbitrary epoch. Positive checks 14196 / 10150, zero mismatches. Three mechanism mutants per type fail. Initial inverse-certificate failure (output-boundary hierarchy normalization missing) remains in scratch.

Geometry reviewed from actual pins, native leaf coordinates and retained actual clock entry points. Exact x_o placement bounds bank-to-entry Manhattan reach at197.232um and data hops351.54um; hd_spn_end148.133/336.87um. No physical timing pass claimed. Geometry changes require same-depth raw-reset reference remapping before final publication. Source-realization two targeted tests and actual export/rebind GEN passed before this geometry refinement.
