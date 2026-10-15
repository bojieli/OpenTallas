COMPONENT ONLY. No production binding or physical slot grant.

qkd_kv_calendar_replay is a new bounded static event mechanism. Actual input
pin flops capture boot writes and start; a sealed, sequential 64-event table
uses actual boot flops. Registered output slots keep their compiled cycles
without producer arrival, valid, ready, credit or completion inputs. Two source
widths are exercised: HBM64 and CORE33. HBM64 has reserved bit63, block_go62,
epoch61:46, reserved_write45, reserved_static44, reserved_rd43 and command42:0.
CORE33 has layer32:27, epoch26:11, sector10:1 and expected_put0. These are leaf
packing contracts; no downstream master has yet been bound to these outputs.
static_cmd_owner must be separately joined to actual active execution at the
controller boundary, including its actual reset and control window semantics.

The boot images here are independent declared COMPONENT boundary stimuli.
They are not compiled from controller output traces, nor from actual all36
programme bytes. They deliberately exercise output bit patterns and both dense
and sparse event intervals. The leaf's exact proof does not establish legal
JEDEC commands, front occupancy, return lifetimes or a native layer schedule.
The image compiler rejects missing/changed source manifests, observed traces,
ambiguous origin, collisions, overflow, missing stop, production scope and any
stage_count other than1. Default64event capacity cannot claim all36 support.

Default HBM64/CORE33 source flops and die-scale storage are in receipt.json.
This is an explicitly costed COMPONENT mechanism, not an adopted die design.
At least512 return events perPC perlayer already require >=8 leaves/domain;
command/front extras and all36 resident calendars add more. An uncompressed
all36/128PC implementation has no area or throughput acceptance. Actual source
rowcount/analytical compression/reuse and bootloader/storage plan must precede
full integration. There is NO physical slot, mapped view, CTS, TT/FF/DRC,
phi-R delivery, token-rate receipt or die qualification for this candidate.

NEXT: derive the actual persistent perPC HBM schedule from source-bound boot,
ingest, writer commits and controller refresh state, prove independent front
release/return/landing consumer slots, choose real storage/compression and
price it before hardening. Do not use PROFILE1 discovery replay as a native
production schedule. Writer r4 and return r2 adoption remain HELD until the
actual writer/controller/front/ring composition and physical receipts exist.

Reproduce: python3 tools/qwen_static_kv/check_calendar_replay.py FRESH_OUT
