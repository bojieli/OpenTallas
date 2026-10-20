# Binding native census, 2026-10-20

Actual immutable mapped netlists from the existing rs/rs2/xs3 gates were read without changing any writer tree. RS and RS2 mapped logic are identical; each has 54,604 transparent non-clock roots, 466 above 32 loads, maximum 202. XS3 has 155,502 roots, 1,156 above 32, maximum 2,529. These counts BLOCK submission/adoption under the 23:45 native rule, independent of the progressing gate verdict.

RS offending cones include each slice's sid_c[0] (up to 202), four regional reset roots (up to 164), and own/assembled slot and direction controls. Reducing a payload slice alone will not fix control-to-decode and input/control fanout. A successor needs a bounded registered distribution tree for controls, local decode per use, sufficient reset leaves, and a source-priced pipeline alignment contract before RTL/build. Existing exact rs_equiv/XG benches remain the behavioral reference; added distribution stages must be aligned explicitly.

XS3 offending cones include family bits gf_q (2,529), macro write-mask roots mw_m (1,024 sinks), ctl reset (548), and merged bc_hr_x/lookup selectors. A successor needs per-bank kept family/header/mask distribution, bounded registered selectors, local reset, and a storage census. The macro mask roots require actual bank-pin fanout handling, not a report exception. No existing gate was restarted or cancelled.

Audits: agidock units551324/551393, ep7 unit1693437; initial rs locality attempts1693610/1693611 exited127 without reading a netlist and were superseded. Tools/source hash and per-root input/sink examples are embedded in JSON. A complete geometry/pin/storage audit remains owed; this is an all-driver load census only.
