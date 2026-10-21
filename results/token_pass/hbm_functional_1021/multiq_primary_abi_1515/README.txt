New source-bound primary-VM ABI only when non-SW VM banks are selected. Header PI[14:13] carries realquarter0SW/1SE/2NW/3NE, bank/row retaintheir existing bits; mirroraddresses are explicitly rejected in this newmode. M images have fivefields quarter,mirror0,bank,row,value. The actual selected vmb_Qbank instances decide backdoorcase keys0..31; mismatched eventquarter and absentbanks are rejected. LegacySW/mirror ABI and all compiled TBs remainunchanged.

Actual218instance minimalcut includes hb_ckgen (earlier217clockless plan was not executable); generates genuinePOR/refclk source. Pure32address check is packing/source validation only, syntheticdistinctinputs neverpresented asproduction/evidenceofRTLexecution. Actualfuturecoupledproof must checkmatchingPvalues ineachdestination andallactualfaultfaces.

Rerun existingpurefixture +32quarter/bank addresses +mirror/ambiguousquarter/missingclockrefusals:
PYTHONPATH=tools python3 tools/hbm_layer_vehicle/verify_multiq_vm_abi.py --legacy-case /home/ubuntu/scratch/tok-func2-hbm/conn_p40 --multi-boundary /home/ubuntu/scratch/tok-func2-hbm/multiq_primary_abi_1515/minimum_clock/boundary.json --out /home/ubuntu/scratch/tok-func2-hbm/multiq_primary_abi_1515/proof32_rerun

LegacyactualTB SHA2d514653142ffbb3170dc870479274d69961db26deee1b761b26127847099a9a and80hdr/val/msk/VMpre memoryfiles byte-identical. No hardwarebuild launchedbythisproof.
