# Optional forward-input copy guard — source candidate only

Root scope: future own frontends only; no broad backend redeploy. Legacy recovery policy stays unchanged. EPYC4 t36's active06:19 spill sweep is BACKCOPY of unique results, not a physical retry or forward-input copy; leave it running and preserve all partial files.

OT_RUN_FORWARD_OWNER_GUARD=1 optionally checks the original client boot/PID/start identity before each forward input-copy attempt. An explicit STOP/HOLD JSON file named by OT_RUN_FORWARD_HOLD_FILE must match pid, boot_id and start_ticks exactly to block a future forward attempt. If the original process is gone, stopped or its incarnation cannot be verified, the opt-in guard holds that forward attempt for review; this is never evidence of semantic cancellation and removes no data. A hold returns before any copy or pending-record write. Missing/unreadable explicitly requested intent fails closed for forward input copies.

New pending records include client_identity. Existing pending records are neither rewritten nor classified as cancelled. spill_sweep and back-copy recovery never call the forward guard, including when a legacy record's client is dead or an opt-in STOP file exists. Ordinary defaults do not probe or hold the forward owner.

Validation:7 targeted tests cover live/dead/stopped/reused identities, exact-intent matching, unchanged legacy default, no copy or record mutation on a forward hold, and continued dead-client back-copy recovery with the forward opt-in active. No live install, no records/data changed, no legacy scheduler deployment.
