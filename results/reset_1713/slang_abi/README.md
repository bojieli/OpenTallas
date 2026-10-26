Opt-in Slang parameterized leaf ABI repair

Enable only named, parameterized interface leaves in an asbuilt recipe:

    "slang_parameterized_blackboxes": ["ot_pl_land_reset_forest", "ot_s81sl_rly"]

The default frontend remains unchanged. Named leaves retain their original source
header but receive an interface-only temporary placeholder and evaluated parameter
attributes on one real port. Slang specializes these interfaces per instance;
Yosys then blackboxes them, and the JSON post-pass restores each actual numeric
and string parameter. Original verification RTL, original master names, private
RAM bodies, data/reset logic and pipeline depths are unchanged. No new reset root,
extra reset stage, width narrowing or false path is introduced.

Private bodies, structural parents, missing definitions/type markers, conflicting
parameters and unsupported type/literal forms fail explicitly. Printable ASCII
string parameters are supported; nonprintable strings require additional literal
escaping support before adoption. The final placeholder modules contain no cells,
processes or memories. This is a source/interface fix, not physical signoff.

Actual F2 input audit (path-s81-f2/f2/asbuilt.json):
- forest q ABI278 vs r1 LEAVES289: eleven high leaves padded0; root/ft1/age dynamic.
- relay d/q ABI594 vs u_up0..4 W667:73 bits lost; u_x0..3 W1104:510 bits lost.
  Old apparent dead-X/RDOUT tie classes must be reclassified on a fresh bind.

Validation: 8 focused tests pass, including the old595/668 truncation control,
per-instance numeric and typed/untyped string parameter restoration, no private
body leakage, and original-vs-rebound RTL lockstep189 active checks with a wrong
D5->D4 mutant caught189 times (+0 cycles). Actual S81 strict re-elaboration and
post-fix tie counts are owned by the canonical source/manifest worker.
