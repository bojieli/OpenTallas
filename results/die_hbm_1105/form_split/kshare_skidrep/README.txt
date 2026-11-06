HBM-REFORM-B9 kshare skid replication form (kit-local, from DIE-HBM-66 kshare4c kit).
skid lock-step old vs new, 200k cycles, W=277/286/340/5, reset every 997: MUT0/0 PASS, MUT1/1 PASS, MUT0/1 FAIL errs=215022, MUT1/0 FAIL errs=215022.
verilator --binary -DMO=a -DMN=b --top-module tb tb_skid.sv skid_old.sv skid_new.sv
Formal proof (HBM-FORM-SPLIT-7+REFORM-B10, 2026-11-05 23:21 UTC): yosys equiv_make + equiv_add state pairing (cnt/wp/rp -> each slice cnt_k/wp_k/rp_k, e0/e1 slice -> slice e0/e1) + equiv_induct: EQUIVALENT at WIDTH 277/286/340/5 (MUT=0); MUT=1 unproven at all widths (negative control). eq/eq3_<W>_m<M>.ys, tails in eq/*.tail.txt. ORFS yosys 0.68.
