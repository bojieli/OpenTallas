# Adopt existing two-phase partition IR in fresh canonical kits

Current canonical gen_phys and KV/HBM/QC/S81 modern core runners omitted the approved partition_ir.py hook, not merely an old frozen KV snapshot. This patch stages the existing helper and installs its disposable-image patch before make, then exports OT_DEFER_PARTITION_IR=1. The approved patch/sidecar logic is unchanged.

Coverage: partition write_type_kit/RUN_KIT; core_flow.apply for KV,QC and modern S81; explicit HBM stage operation; static KV/HBM runners and generated QC/S81 modern runners. The S81 --legacy-flow output stays byte-identical (4055bytes, recorded SHA). Assembly/die runners are unchanged; actual die IR remains mandatory.

Staging writes partition_ir_policy.json naming the physical kit lane, initial NOT_RUN, automatic_sidecar=false and die_ir_required=true. Normal final ODB/SDC/SPEF checkpoint and timestamped NOT_RUN markers come from the already approved helper. No IR result/IR PASS is invented. A separately admitted sidecar remains the physical lane owner's task; INFRA handles actual recovery only. No automatic sidecar wave or fixed new analysis cap was added.

11 focused checks PASS: actual helper copy/policy/no-analysis staging, all4 core generator staging call paths plus partition call, actual generated/static Bash quoting for each5 runner families, defer flag seen by inner shell, patch failure31 preserved, and S81 legacy-byte invariant. Mock engines only; no new P&R/STA/IR execution. Existing/frozen/live kits are untouched, including the live current KV type c51. Its final-report failure has not been asserted by this source change.
