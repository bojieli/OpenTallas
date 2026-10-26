# Real issued identities and fallback position

PASS against the actual HSF0 controller, with two accepted issues and two local-final pops for both tagged user777 and untagged fallback. Both physical FIFO entries are exercised. Head identity, occupancy, counter and overflow/underflow events match the original edge by edge. The tagged fallback position stays0; the untagged counter reaches2. High identity-bit corruption and incrementing the fallback on tagged issues each fail the corresponding comparison.

The extracted block retains the original delayed kept write enables and read-select copies. Payload flops do not reset. Added source cycles:0. Issue and local-final acceptance remain live caller inputs. The FIFO pop is local-final acceptance, not job/token retirement; job_active remains the separate indexed-XB lifecycle. It does not supply the unresolved HBC programme/START producer or replace it with historical autoissue.

Actual source9336012efd, ot-run unit729468-1793013387 on tender-ray; immutable runtime epyc1:/srv/opentallas-scratch2/claude/codex-head-tags-1026/src/proof_0. Reproduce with tools/s81_head/issued_tags_bench.sh inside ot-run.
