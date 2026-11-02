SOURCE-ONLY STATIC CLASS INTAKE; NOT RUN

Exact frozen SOURCE13 hfd_ep_static defaults IDLE_K204/MUT0, four actual callers,
2288 true ABI bits, six selected logic definitions plus native 64x512 hard-macro
blackbox, four actual SRAM instances. Selected behavioral SRAM definition remains
in the source packet but is excluded from synthesis/equivalence to preserve the
ordinary hard-macro abstraction. No external shell or added pipeline cycles.

The additive source profile requests component_proof_reset_cycles=4 and is
release_eligible=false. The generator leaves default die64 staging untouched;
this source-only path stages NO die reset receipt. Ordinary lec.py native4 must
actually pass; unknown/refused/failure remains a failure. No proof checker edits.

The reference pin table/four-macro geometry is used to generate a NEW source kit,
not as a qualified physical view. Planning-only250/202.5 clock budgets do not
adopt the parent435/352 or any die calendar. No P&R/STA/CTS/DRT authorized.

Prepare: python3 tools/hbm_b2/hfdep_current_native_kit.py --prepare-only \
 --views results/hbm_hfdep_native_0250/intake/views.json \
 --view hfd_ep_static@source13_native4 --profile-out /OWN/prepared_profile.json
GEN uses the same command without --prepare-only, plus --out /OWN/gen.
Then ordinary run_kit_hbm.sh /OWN/gen/hfd_ep_static_source13_native4 synth 8 2
with OT_LEC_RESET_CYCLES=4. No goal beyond synth, no reset64 fallback.

Normal ot-run request8GB/2threads/disk5. Old outside-shell HF proof measured gold
275.88MB and gate645.19MB frontend peaks; full old proof921.8s/16350points.
These are resource references, not equivalence/current-source credit.
