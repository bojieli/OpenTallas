# Seven/eight-capture indexed metadata helper

Functional alignment support for ROOT-approved stream leaf7→8, modeled at dad9fdb99. Model-first commit0cba629bd precedes RTL54f8a3172; exact tested/mapped tree6be681462. No feed, producer, compiler, or cold-admission changes. Default DELAY7 preserves the original byte/cycle contract. The appended DELAY parameter keeps existing positional W/MUT use compatible.

The ring writes eight indexed slots; read uses old slot data on each capture edge. Reset wp=0 and rp=(9-DELAY)mod8; saturating warm enables output at capture DELAY. Therefore input at capture n appears at capture n+DELAY−1. DELAY8 adds exactly one capture without adding a slot or reset-release stage. No long shift chain is introduced.

W35 uses six kept helper instances of at most six bits. Actual mapped state for both delays is369 FFs:280 unreset runtime slot bits,35 resettable output bits, and54 distinct pointer/counter FFs (three three-bit registers per slice). The earlier16-bit-slice structure had27 pointer/counter bits; this implementation explicitly prices +27. Post-ABC flattening preserves real state copies without opt_merge. All35 outputs trace through at most BUF/INV to distinct FF Q.

| DELAY | Exact positive | Wrong-slot MUT1 | TT area um² | Direct max data/control | Recursive BUF/INV max |
|---|---|---|---:|---:|---:|
|7|PASS2,111 checks, original cycle miter|FAIL expected|194.16186|12|15|
|8|PASS2,111 checks, history scoreboard|FAIL expected|194.78880|13|15|

Both positives cover full-rate wrap and occupied asynchronous reset at all eight write-pointer phases. The scoreboard explicitly clears history on asynchronous assertion. The reference file preserves the original module body with only its module name changed; its original hash is in the pre-RTL model. Each mutant changes only the read slot by+1. Individual committed `.log` files retain both positive results and exact failing witnesses. Tests use Verilator5.050; maps use ORFS RVT TT ABC833.333ps structural census; standalone mapped unknown0,369 clock sinks, no SRAM.

Raw reset has119 direct terminal pins and125 after recursive BUF/INV collapse, including reset-as-enable logic for unreset slots. This violates native reset fanout qualification. It is reported openly; no hidden reset landing, release edge, or waiver was added. Input data also enters the indexed storage write-selection logic directly. This helper is functional alignment glue inside the existing OPEN frontend reset/clock scope, not a native tile or whole-front SAFE claim. Placement,405um reach, clock spread and actual timing remain OPEN; no gate/REVIEW/submission was run.

`results.json` binds source and mapped hashes. `mapped_receipts.json.gz` contains the full actual mapped JSON, original generic census, and recursive terminal-pin reports for each delay. `load_audit.py` uses the exact455fc9ff4 BUF/INV rule with sequential-only clock-pin classification. The generic runner is the unchanged parent version; source hash is recorded.

Fleet roots:

- Sim: ot-agidock128 `/srv/opentallas-scratch/claude/codex-meta-delay-6be681462-sim`.
- Map: ot-epyc8 `/srv/opentallas-scratch/claude/codex-meta-delay-6be681462-map`.

Reproduce the four component cases with `bash rtl/test/hbm_accel/svg_rel/run_svg_meta_delay.sh <absolute-output> <7|8> <0|1>` through fleet admission. MUT1 must exit nonzero with `META_FAIL D=`. Map using the unchanged generic runner and both map7/map8 specs. All bench dependencies are explicit in the run script. Sim loop console was retained locally before its shared output path was reused; the committed per-case logs are exact segments of that console.
