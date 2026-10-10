# Qwen r25 TOKEN18 command processor candidate

Base: `961688ad8` (`claude/qwen-hbm-unify-20261008`). This executes G2's open-block change in the P-min plan. The DS command processor, SRAM successor, n/s die wrappers and closed accept/DSpark sources remain byte-identical. New explicitly selected `ot_qwen_r25_cmdproc18*` and `hfd_cmdproc_{n,s}_qwen18` masters provide the candidate.

## Measured exactness and cycles

- Register command processor, NSM16/NCMD256: all **151,936** doorbell and result tokens pass, including 131071, 131072 and 151935. High position20, job32 and generation4 are checked. Every successful completion is stalled for two cycles and retained. Normal LAUNCH + END step takes **5 cycles after doorbell acceptance** under the bench's immediate SM result/done response.
- SRAM command processor at the actual RDREG2/NSM16/NCMD256 shape and original SRAM model: the same exhaustive domain passes. Normal step takes **9 cycles** after acceptance. The four-cycle difference is the existing two read stages for each of two commands; TOKEN18 adds **zero cycles**.
- Invalid doorbells 151936 and 262143 produce status3 without launching; invalid RESULT 151936 or bit18 set also produces status3. These bound checks enable safe embedding admission.
- The same exhaustive bench with a mutant that truncates launch tokens to17 fails at **131072 → 0**. Its terminal failure is retained in `token17_mutant.log`.
- Real n/s wrapper pair, original output-register/clock-inverter and SRAM models: three launches per band at token boundary values pass through the loader, south/north split and all four SU token publications. Position/job/generation remain intact.
- Python host/program ABI exhaustively checks every token's packed doorbell and embedding address. INT8 rows use full integer offsets `token*4096`, BF16 scale rows `token*2`; maximum row offsets are 622325760 and 303870. Replicated HBM embedding base is64bit; overflow is refused. A **38-word** 36-layer/head/END skeleton fits NCMD256. Entry kernels must be supplied and qualified separately.

Logs, model and source SHA256 are committed beside this report. Reproduce with `python tools/qwen_r25_cmdproc18_gate.py --output <new-directory>`; it refuses an existing result directory. The bench's50-cycle bound is a finite component-test assertion, not a production resource cap.

## ABI, sizing, and remaining integration

The new doorbell tuple is148bits: cmd_we[0], cmd_addr[8:1], cmd_wdata[72:9], db_v[73], token[91:74], pos[111:92], job[143:112], generation[147:144]. The loader concatenates south then north (`north<<148 | south`), retaining47 spare high bits for343bits total. The south→north xl link grows147→148bits. SU token publications retain their64bit ports and now carry all18bits.

Model-before-build: `tools/uarch_model_qwen_cmdproc18.py`, using the unified model's calibrated FF area constant. Two existing processor replicas; estimated29 added active FF bits (including constant-zero→signal SU stages), 8.4564µm² FF body plus128µm² logic reservation, ~248.10µm² at55% utilization. Added latency0; no speed credit. Four incremental input/link signal tracks require pin/route qualification. SRAM capacity and all macro timing assumptions are unchanged. Area is an analytical reservation, not synthesis/route evidence.

This is **component evidence**, not a working whole Qwen decode. The physical n/s wrapper has always folded command completion/result channels into kept sink/config registers; the candidate retains that boundary. The direct command processor exposes and tests the host completion interface. Production host/result routing must be composed with the selected die-level binding and widened loader/link pin contracts. Existing DS source-entry TOKEN17 and protected full73/PCWB paths are intentionally untouched and cannot accept this candidate as a drop-in.

The embedding checks establish host address computation and processor token preservation; they do not execute an HBM embedding fetch. Actual SU dequant/loader stages remain separate plan work. EOS/max-length stay host policy. Global argmax/SU accept remain the plan's FP32-ID program path and are not claimed by this gate.

No SS/FF, routing-layer, DRC, IR or physical sign-off is claimed. Existing n/s closures/revocations remain historical. These candidates require new wrapper budget/pin generation and measured implementation before adoption. No docs/ files were edited.
