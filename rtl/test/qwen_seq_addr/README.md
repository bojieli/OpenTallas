The native compute sequencer transports a complete20-bit VM row address. The actual `qfd_seq_su` die ports are `vrd[20:0] = {re,row20}` and `vwr[532:0] = {we,row20,data512}`. No row base is inferred from a stage or token.

A native64-bit descriptor keeps kind[1:0], rowLow[9:2], count[17:10], vocabularyHigh[19:18], programBase[47:32], and vocabularyLow[63:48]. RowHigh[31:20] completes the20-bit row. All-reduce count0 encodes256; an overflowing range faults before core launch or memory access. The `ot_qfd_seq_su_bi` native body selects the extension when VWA>8. The embedded generic sequencer keeps VM_ADDR_EXT=0 by default. Existing low-row descriptor bytes are unchanged.

Use `hdc_qwen_fullshape_isa_w12.encode_descriptor(...,vm_addr_ext=True)` / `encode_segments(...,vm_addr_ext=True)` for this native body. Legacy consumers must keep the option false. This row ABI is specific to the synchronous native sequencer: the experimental asynchronous CUT descriptor uses bit20 and must not consume a native row descriptor.

Run from the repository root:

```
python3 rtl/test/qwen_seq_addr/test_descriptor.py
bash rtl/test/qwen_seq_addr/run.sh /tmp/qwen-seq-address
```

The RTL gate elaborates the real sequencer embedded in `ot_qfd_seq_su_bi.sv` and exercises the production7-edge path (OS1+relay2+read1+relay2+IS1), random collective stalls, read and write row/data checks, row256, high rows,256-word regions, exact upper boundary, and overflow rejection. Observed failing mutants disable high-row decoding, shorten the read pipeline, and remove the range fence. Wrapper elaboration proves the widened real die-port binding; the focused gate does not certify die physical closure or variable-latency DVM behavior. The DVM handshake integration has its own gate.
