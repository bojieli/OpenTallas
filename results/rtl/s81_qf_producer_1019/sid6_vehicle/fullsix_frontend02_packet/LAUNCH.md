# Corrected source dependency: frontend02 only

Original frontend01 exit1 is preserved in fullsix_frontend01_result and its immutable remote directory. It measured9.62s/3387540KiB and emitted no obj/CPP because the source manifest omitted existing ot_hdc_delay_rf. dependency_repair.json pins both actual ot_s81_retn_static instantiations and exact CEA source/hash; the added module is self-contained (no includes/imports/submodules). No new RTL hardware is designed.

The staged directory is ot-epyc4:/srv/opentallas-scratch/claude/s81-qf-producer-source-1019/fullsix_frontend_02. frozen_inputs.json proves the ONLY execution-input differences from frontend01: append actual existing src/rtl/hdc/ot_hdc_delay_rf.sv, append its source_files.f line, update source manifest. All125 original source bytes, actual clocks/reset/TB/72tagEFmonitors/weights/gold/CTL/15epochs/settings and original deadlines are identical.

Exact proposed invocation, ROOT technical review before launch:

```
ot-run --mem 256 --threads 1 --disk 80 --dir /srv/opentallas-scratch/claude/s81-qf-producer-source-1019/fullsix_frontend_02 -- bash frontend.sh
```

Same frontend-only Verilator5.050 --cc --main --exe --timing; no C++build/sim.256GB is a fleet capacity reservation, not measured need/hardlimit; frontend01 peak does not predict completed fullsix elaboration. No arbitrary wall/address-space limits and no object restart. Preserve outputs on failure and collect actual generatedCPP/modules/bytes/RSS before C++admission. CAP remains genuine resetrcnt0: any F9/drain failures are evidence, no numericPASS; fixed SOURCE-owned CAP programme awaits actual coupled tag chronology. NativephysicalphaseNULL, no GEN/QR/MU/token adoption. No frontend02 run yet.
