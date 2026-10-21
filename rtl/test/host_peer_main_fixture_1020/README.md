# Historical r6 peer SRAM fixture

Main-based package atop9cc4f6b98 (complete parent p192 batch; ROOT review pending). This is an isolated opt-in derivative of sourcea7b57f71f/r6 with link7338ce567. No existing main RTL, generated top, guard FIFO, context record, kit, or default parameter is changed.

The manifest pins96 compile inputs:82 existing main files are byte-identical;14 historical/candidate dependencies live under this fixture. The historical context-record and guard-FIFO variants are explicitly scoped to this vehicle; they do not replace newer main implementations. Reversing only the derivative top/module renames and SAFE_SRAM(1) specialization reproduces the exact historical hashes.

Run `python3 rtl/test/host_peer_main_fixture_1020/check_manifest.py` to verify completeness and reverse-diff identity. Run mechanism benchmarks on the fleet with `bash rtl/test/host_peer_main_fixture_1020/mechanism/run.sh` (V5.050 required). `synth_main7.sh` is synthesis-only with the exact historical recipe4 pin stations and standard2stage reset landing, balanced64final/2first copies and split32. It never invokes layout.

Recipe4 already adds one input and one output station edge. This derivative adds zero station edges and zero link datapath edges. Existing peer_rr async assertion/three-edge release and outer2edge reset landing remain the original boundary ages. The internal peer RX handshake remains the historical one; the full leaf's external data ports keep their existing stations.

Direct link and reset-only native receipts are in the parent source branchc1e8214b4. Full historical leaf mapped native and packing evidence are pending; known sibling reset groups already exceed32. No full-leaf PASS or gate approval is claimed. Provisional standalone census tools are vendored exactly from94de8573f for reproducibility and remain subject to ROOT helper acceptance. See MODEL.md and leaf_model.json for costs, limits and preliminary legal macro packing.
