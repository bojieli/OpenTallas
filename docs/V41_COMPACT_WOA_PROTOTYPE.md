# Compact wo_a local decode prototype

This is root-authorized analysis and standalone arithmetic, not a change to the
adopted storage representation or rate model. `ot_chip_v41x_woa_fp8_decode`
accepts one E4M3 code and one UE8M0 scale and emits one registered BF16 value
per cycle. It preserves signed zero, handles subnormal RNE and overflow, and
refuses reserved NaN codes/UE8M0 255 with a fault.

The Icarus gate tests all 65,536 code/scale pairs: 64,770 valid combinations
against the golden dequantization/BF16 conversion, and 766 explicit refusals.
A second test checks all 8,388,608 actual layer25/rank0 values against the
golden's `Q8.dense` followed by `to_bf16`, with zero mismatches. It uses the
exhaustively RTL-checked lookup table; this is not an 8-million-cycle connected
ME replay. All sources and checkpoint tensor headers/blob IDs are pinned.

## Capacity and bandwidth

The rank's expanded BF16 tensor occupies 16,777,216 bytes. Codes with scale
replicated once per32columns per output row occupy 8,650,752 bytes, saving
8,126,464 bytes. Retaining checkpoint32x32 scale sharing reduces storage
further, but needs a scale-bank service contract; the conservative proposal
uses row-local scales.

The existing eight-bank/eight-lane ME consumes 64 weights per beat (1024 BF16
bits). It therefore needs **64 parallel one-result/cycle decoder lanes** to
preserve that service. Codes require512bits/beat. Scale demand depends on exact
ME address mapping; the pessimistic independentscale bound is another512bits.
The decoder's one registered stage must be integrated into the accepted weight
latency and activation alignment; simply adding it without retiming is unsafe.
The current qtile 264bit compact format is not automatically the ME bank format.

No area estimate is substituted for synthesized decoder lanes, no code macro
bank count is claimed to preserve the ME stream, and no clock closure is
claimed. Next gate: derive the actual64weight address-to-code/scale mapping,
then run real ME vectors before approving representation adoption.
