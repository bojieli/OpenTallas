Actual native VM4 fixture

The provider RTL under adapters/native_b2/su_quadrant is byte-identical to
64fced1f9 (five imported .sv files). B2 VM, ring, CDC FIFO, SECDED SRAM and
SRAM FIFO dependencies are unchanged between this branch base58f61205c and
that fixed provider commit. The fixture instantiates four native_h clients,
actual VM4 B2 slices/rings and 96 native1024x256 SRAM macros. Client clocks
833.33325ps and VM1111.111ps retain the real4:3 ratio and phase parameter.

The147 unchanged Qwen LOADs retain immutable price15674.320143998484 cycles.
Before each LOAD, actual SU wdr writes seed values throughout all four private
VM slices. During actual posted DMA packets, all four SU clients issue reads
and writes to a separate last-row scratch range, using ten actual credits.
After real producer/transport done, actual SU stage reads populate every word
of the comparison image. Independent HBM decode and untouched-word checks
read only that actual returned image. No direct SRAM peek or VM model writes
are used. Prefill/readback verification cycles are excluded from LOAD timing.

This is a private stable DMA-grant fixture. Group1 peers remain idle. It does
not establish integration of the separately developed shared peer lease,
full quant/XP contention, actual HBM first access or physical die adoption.
The prior native destination-model ratio1.310359863 is preserved as a real
immutable-price failure and must not be replaced with the component ratio.

Run using ot-run with memory admission after complete input transfer. The
run.sh argument1 selects observed front MUT1/BF16 or MUT6/ignored capacity
credits, argument2 selects phase61 or487. +CHECK_PRICE on the resulting
executable enforces the unchanged1.10 bound with a real fatal on failure.

Initial8a451a3cc run reached all147LOADs with actual macros, but the fixture
reported65errors: scratch d_lb remainedzero, so its eight sectors overwrote
first64INT8 destinationwords; the128word FP32 donepulse was inspected after
waiting concurrentSUtraffic and was missed. Both are corrected explicitly:
scratch d_lb=su_lo and DMA done captured by the timing monitor. The original
failed receipt remains initial_fixture_failure.log and conveys no acceptance.
