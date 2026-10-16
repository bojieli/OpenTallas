# WSCATTER full-master bench correction

The original `s81_vm_master_current_scatter_20261016` receipt labeled one run PIPE1, but its bench never passed `OT_VM_NATIVE_WSCATTER` into the DUT. Both runs instantiated the default PIPE0. Preserve that original receipt as historical evidence; its PIPE1 qualification label is invalid.

This recovered run completed through admitted `ot-run` on EPYC4 and uses the corrected bench. Its 48 input files match source `89c48ea9d` exactly except for that bench fix. Four Verilator argument/source manifests prove the active READ4/CAP2/WSCATTER1 defines, and `artifact_sha256.txt` records source, runner and binary hashes. Both base seeds, all eight fault modes and all three observed mutants pass their expected outcomes.

This is component evidence at the historical source, including its historical WFC implementation. It does not qualify current WFCr5 or A2F/hop1 integration. It does not measure raw macro cycles or throughput and must not be used to rehash a stale compiler profile onto current sources. The independently measured A2F parent receipt `72bc4d4f5` owns the new compiler ABI.
