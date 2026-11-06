# Typed hard-child landing composition

The HC0 parent previously failed1553 landing inputs because its four SIGNED ring
children are opaque macros, while land_slots still required expanded D4 soft
slot flops. The unchanged actual parent synthesis netlist now passes5726/5726
checked bits, including1549 child data bits and4 child START inputs. The original
failed parent kit was not edited. Exact result is hc0_face_guard.json; source run:
epyc6:/srv/opentallas-scratch2/claude/codex-typed-landing-v2-1106/canary_hc0.

The emitter recognizes only selected ot_dp_clk_landing_ca/cas parameter wrappers
with matching D, WREG1 and WFALL1. It stages the actual signed child views,
signoff, frozen face-tool identity, captured face result/netlist and land_slots.
The child d hold-mux and t_rst_n ring-start are re-proved, including the actual
fclk writer domain. Parent checks require exact instance/master/port, full
ordered bit mapping, exclusive direct loads and the actual declared forwarded
clock input. The actual parent LEF/TT library must match the signed export.
No arbitrary hard macro, prefix, timing exception or added cycle is introduced.

A generated macros/landing/<master> bundle can be retained in the selected
view's landing_evidence directory. Fresh kits then consume that self-contained
bundle rather than requiring the original build host. The memo only reuses a
proof after all captured hashes and the parent's selected views are rechecked.

Validation:12 focused tests PASS (wrong master, instance, port, bit order, clock,
extra load, depth, width, missing evidence and escaped evidence path rejected).
Actual W2 portable bundle:3/3 parent bits PASS; changing its netlist after a
cached proof is rejected by the byte-identity check. The full HC0 result above
also re-proved all four actual child contracts. This is a construction guard
result, not parent placement/routing/timing or token qualification. Ordinary
hard-child ports outside this explicit landing-ring form keep existing rules.

The first canary failed because the prototype misread the frozen face_guard.py
tool hash as a JSON result hash. The corrected canary binds the actual tool and
signoff's captured face input; no child evidence or historical failure changed.
