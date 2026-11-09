q_su00__physical_v1 whole spare-input class, 2026-11-08

Actual failure: E6 kw26-wave-1106/runs/hbm/kit-wave/hbm/d44v/items/
q_su00__physical_v1/gen/q_su00__physical_v1, AP b037e970d6821/a1.
PLACE-stage face_guard checked20522 / ok19289, dropped93. Every dropped bit is
L1213_i[92:0]. Actual input has no load because the bound native module has
no L1213_i port; its generated plan wrapper contains only the93-bit declaration.
kit_rtl.json already records plan_buses_unbound=[L1213_i]. This is not a lost
KEEP register. The old dead-input proof included1140 spare bits of two narrowed
inputs but omitted the entire unbound input, including its unused epoch bit.

Source condition: asbuilt_p37su5 / exp/bind_e0, strict native connectivity report
n_errors0/errors[], unmapped0, proof unbound/tied/undriven/multiply_bound all0,
420 crossings /378992bits. This checks the actual leaf source-load mapping.
No independent Yosys verify or LEC is claimed. The receipt binds exact hashes
of that report and the native bound-module source, checks the port is absent
from that exact ABI, requires the manifest's missing-bus entry and proves the
final literal wrapper has no use of any bit. KITRTL and GEN refresh the source
proof; any future read or ABI change rejects it. Planned ports are preserved.
Faceguard's ordinary declared-dead rule still independently requires0loads and
0drivers on every declared bit. No placeholder KEEP or blanket exception.

Actual retained synthesis netlist (1_2_yosys.v, from the failed PLACE-stage kit)
rechecked privately with that proof: PASS20522 /ok19289 /fails{}, dead1233.
E6 unit oth-ubuntu-388720-1794168177 exit0, private files:
/srv/opentallas-scratch3/claude/codex-hbm-unbound-1113/{dead_inputs.json,face_guard_private.json}.
The original failure and checkpoints were not changed. The first probe's path
translation failed (/work inside the container); v2 resolves it to the retained
host kit. Both probe logs remain on I2 ~/codex-kcls-1113-logs/. No P&R retried.

Seven focused tests PASS: source+GEN positive; added literal read with a fresh
wrapper hash; added native ABI port with a fresh source hash; wrong missing-bus
record; failed strict source mapping with a fresh report hash; stale native
source hash; and unchanged legacy narrow-payload behavior. Normal native kit
LEC/sign-off still gate release. Root wave owns any fresh single PLACE pilot
and batch adoption; no shared source/config or plan of record was edited.
