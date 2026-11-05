HBM-REFORM-B9 kshare skid replication form (kit-local, from DIE-HBM-66 kshare4c kit).
skid lock-step old vs new, 200k cycles, W=277/286/340/5, reset every 997: MUT0/0 PASS, MUT1/1 PASS, MUT0/1 FAIL errs=215022, MUT1/0 FAIL errs=215022.
verilator --binary -DMO=a -DMN=b --top-module tb tb_skid.sv skid_old.sv skid_new.sv
