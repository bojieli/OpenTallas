# Ordinary PC sr15f: sr15a with abutment-aligned chain pins (FT-KV-PC 10-23)

sr15f = sr15a with ONLY the pin plan changed: S o_prev / i_prev / pc__ko / pc__fi take the exact x range of their N partners i_next / o_next / pc__ki / pc__fo (pc__hfx moved to free S [300,301]). Balanced placer puts bit k at lo+(hi-lo)(k+.5)/n, ascending, M5, on both faces, so the 124 stacked tiles (single-orientation columns W R0 / E MY) meet bit-for-bit straight across the 19.5-um gap. RTL, outline, macros, clocks, layer cap unchanged.

## Base (sr15a)

Ordinary PC structural replacement for the old hold-repair loop: complete ck/hck domains with canonical physical clock-pin dedup, exact unique owner verification, bounded physical leaves, equal stage budgets and same-depth SRAM drivers. Source payload and existing group landing ABI unchanged; no new data edge or domain.

Retain source geometry and every distinct SRAM clock pin. The corrected PC_H construction is reused byte for byte; global owner conflicts refuse. The two variants retain distinct depth/repeater/equalization recipes. No physical or native result from PC_H transfers. Actual MAIN and fallback gates, source/native obligations and ROOT image review remain required for normal submission. Existing non-host sr13 repair jobs continue unchanged.
