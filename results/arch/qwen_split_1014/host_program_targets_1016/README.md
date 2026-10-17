Actual HOST target provenance and replay, 2026-10-16, component candidate.

Class8 BEGIN target bits42:39 and AUTH target bits91:88 explicitly identify
0 ISA, 1 layer roots (327 words), 2 writer programme (181), 3 ownership (4),
4 landing calendar (192), 5 front calendar (192), and 6/7/8/9 controller
WS/WN/ES/EN (1024 each). The actual RX rejects unsupported targets/reserved bits.
The actual loader latches the target at BEGIN, includes it in the digest seed,
requires matching independently supplied AUTH target/epoch/digest, and replays
actual SRAM words. Config images require exact lengths and zero descriptors.
Only target0 emits an authorized ISA footer; target0 retains existing ISA counts
and descriptor contract. The trusted external HOST supplies AUTH; the digest is
an error detector, not cryptographic authentication.

The source-wired root exports boot_pr143, boot_image_target4, boot_image_ready,
boot_image_fault, boot_image_epoch16, and boot_image_digest64 to the real boot
dispatcher. Only target0 pr/BEGIN/AUTH feed ISA consumers and record installation.
Actual native program_ready requires target0, existing installation/commit proof,
and the dispatcher's static_setup_ready input. Load config images first and the
final ISA last; a config image after ISA drops native readiness until ISA reload.
All boot output ports still need actual source-bound dispatcher connections.

Exact hardware proof covers all ten images through actual RX and four mapped
256x64 1RW SRAM functional models. External test frames carry declared data and
independent expected target/address/payload/epoch/digest. Hardware rejects cross
target AUTH, wrong count, and unsupported target. A real loader mutant skipping
target matching emits forbidden replay and fails the independent scoreboard.
Full root/slice/reduction lint passes 94 real sources. Initial negative fixture
mistakenly tested constant NEG rather than runtime negative in one compound
condition; actual RX rejected target10 correctly, and the corrected final proof
passes. Failed initial receipts are preserved.

No full native layer/token, production boot latency, physical pin/clock/area
closure, or end-to-end target dispatcher qualification is claimed here.
