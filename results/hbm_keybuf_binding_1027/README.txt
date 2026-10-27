Native keybuf source staging, 2026-10-27.

The U6d query-proxy placement has no legal source binding. Query units produce
ql_* (queries), while keybuf stores key lines from HBM and feeds scorer key_lines.
The current canonical quad client uses two8792-bit stack streams and four4396-bit
quarter scorers, each needing four1099-bit slices. The alternate P3 N_Q=4 full
scorer parent would need32slices, but has not been bound to the U6d die or selected
by any current native proof. The accepted1905.97tok/s price and SU nativePR0/1
proofs do not establish a keybuf source topology.

New rtl/hbm_next/idxn/ot_hnx_idxn_quad_key_replay.sv stages the canonical16-slice
key ABI exactly, with real native control ports and no added cycles. Quarter
half=1 regenerates PC tags4..7 rather than incorrectly restarting at0.
Unresolved physical mapping and calendar controls are explicit in the contract.
The existing full8-slice wrapper/proof remains untouched.

run.sh compares each quarter half against sourceNP4,RS0 native keybuf, plus a
wrong-half strap mutant. It exercises171addresses, three replay rows, random live
inputs during replay, invalid reads and live/replay collision fault behavior.
Reference source is preserved from origin/codex/p3-compiler-2018@e938fd6db;
its NP4,RS0 implementation is the canonical quarter key storage equation.

Actual native programme cut completed on intel1 unit1470774: calendar_positive.log
2516checks0errors,171live855replay,6rows,rowII232,F1315,issuerdone2477,833psclock.
calendar_mutant.log samebinary wrongPCstrap caught855mismatches. The sourceissuer
and SRAMstorage are exercised by the real registered programme. This cut does
not include scorer/selector/nativeTX/physicalstations/unifiedtop. Bare slice
live pass-through is combinational; R2registeredphysicalfaces remain tocompose.
