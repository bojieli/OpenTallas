`partition_types.<type>.ft_full_stage_placement_file` is an optional plan-relative
JSON file for complete, existing **normal (unlanded)** FT stations. It changes
placement only; station count, RTL and cycles remain unchanged. Omit the field to
retain the existing kit byte for byte. `bit_sites_um` keeps its original k−1
indexing and cannot also be set for the selected slot.

Packet format:

```json
{
  "schema": "opentallas.ft_full_stage.v1",
  "module": "actual_wrapper_module",
  "outline_um": [1442.88, 1226.88],
  "slots": {
    "ft0": {
      "stations": 6, "width": 1120, "in_face": "E", "out_face": "N",
      "targets": [
        {"stage": 0, "bit": 0, "name": "exact_mapped_instance",
         "master": "DFFHQNx1_ASAP7_75t_R", "xy": [1416.258, 304.83],
         "size": [1.08, 0.27]}
      ]
    }
  }
}
```

The example target list is abbreviated. All k × (payload width + epoch) cells
must be present, stage 0 through k−1 and bit 0 through width. Coordinates are
cell lower-left in micrometres, taken from a reviewed, legalized physical coupon.
Names and masters must match the actual mapped checkpoint exactly. A new
synthesis inventory requires a new packet. Keep unrelated landed slots unchanged.

Generation rejects missing/duplicate cells, stale type/outline, impossible
footprints and internal centre-to-centre hops over 405um. At placement the helper
checks every actual input bit and its output k-chain; row segments, sites,
orientation, core bounds, fixed taps, macros, hard blockages and other fixed
reservations. Endpoint pin p90 must be ≤30um with the existing 150um maximum
backstop. It validates all targets before applying any, and repeats validation
before detail placement. Exact legal targets remain FIRM. No cell cloning,
snapping, stage insertion or automatic collision recovery is performed.

These checks do not replace the native full geometry, clock, timing or route
gates. In particular, scalar/control paths and other slots still need their
ordinary G1 checks. Analytic plan readers using the old station approximation do
not acquire authority from this physical-only override; use the actual placed
geometry for qualification.
