Qualified source-only q3 common-clock adapters (2026-10-25).

Native wiring evidence is projected from the actual producer split instances and
its testbench clock connections (tb_q3prog_trace.sv:84-86); hashes and exact
expressions are in manifest.json. The testbench supplies one scalar clock to all
bits, including link[14:0], VM writer and reduce/ring roles. The native bit-ID
vehicle proves all147 exposed clock bits alias one input bit. H0/H1 are excluded.

The five generated wrappers preserve all36674 non-clock bits, including reset,
valid and fault. Yosys blackbox connection identity passes for each actual fixed
interface. The small clock mechanism miter passes500 cycles at exactly833ps,
checking data/valid/fault on both half-edges after2 warmup edges. Inverting the
inner EDGE arg clock fails on negedge2; changing the native source bit is caught
independently. Four focused refusal tests pass. No data/BOOT cycle or define change.

Use q3_common_clock.adapt_recipe(core,recipe,staged,receipt,this_directory) from
the q3 source-profile API. It checks the qualification, wrapper hashes and exact
selected generated source bytes; unrelated main changes do not invalidate an
identical source cohort. It selects the new inner __oneclk top and exports only
physical clk. The ordinary source-vs-plan interface gate MUST reject an unchanged
old clock pin table. HBM owns the explicit clock-pin plan batch and physical
position of the new clk pin. Non-clock pins and outlines remain unchanged.

No physical build, clock-stage latency, sign-off or whole-token result is claimed.
The existing multiport PRE_CTS guard stays active until the pin batch and a new
common-root tree are reviewed. Inner q3 bodies retain their separate qualification.
