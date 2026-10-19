# Actual release COLL v74 SAFE candidate

The current release binds NPT2/SOLO1 in SW and NPT1/SOLO0 elsewhere at VM_RT74. Old q2/q3 kits do not qualify these shapes.

The pre-RTL model is results/arch/hbm_coll_v74_safe_1019/model.json. SAFE_DELAY defaults off. Four physical SRAM fixed-delay rings replace all long VM and injection shift chains. SRAM read data ends at a local full-cycle capture. The reference capture ages remain VM metadata84, valid83, pair-select74/83 and injection12; sustained rate one entry per edge. Counter warmup masks arbitrary SRAM contents after every reset; data macros are not cleared. The smallest production-width mechanism bench passes 39,824 checks over10,000 edges with11reset bursts using Verilator5.050. Wrong VM slot, stale reset content, wrong select slot and wrong injection slot each fail committed witnesses m1..m4.log.

Actual NPT1/SOLO0 and NPT2/SOLO1 full VM-return/assembly benches each PASS1792pairs, and six wrong-budget/unpadded-lane mutants FAIL. Dense production benches each PASS8192pairs from2048consecutive read requests: II1 matches the simulator price exactly, zero added external edges. Clock832ps. No physical gate or adoption yet. There is no data constraint exception.

SAFE review: pins registered in existing core and ring output; reset requires retained-copy mapping audit; all candidate dimensions below405um but final reach unproven; pointer fanout requires retained mapping census; local SRAM-Q capture exists but measured stage depth pending; storage uses actual macros; actual compiler pin-access variants and synthesis-based full-band floorplan still pending; existing protocol root retained with native TT/FF audit owed; external schedule changes zero. Existing issuer_v7 already implements the256-row programme in six actual SRAM data macros plus four metadata copies. Programme priming and timing/fault integration remain required.

Do not submit these sources or reuse old q2/q3 gate evidence. Current macro pin density is a physical blocker until real compiler/periphery variants satisfy <=6pins/um and escape proof. Outline345.6square is only a model placeholder and is not a die grant.
