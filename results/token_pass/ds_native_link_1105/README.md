# DS native vehicle link recovery

V1c3 compiled all 395 hierarchical libraries, but the aggregate static archive contained 4,295,884,338 bytes of text. The executable link failed with PC-relative relocation and PLT offset overflows. The top itself contains only a small amount of code; further top hierarchy does not remove the aggregate static text.

The existing child objects were built with `-fPIC`. Linking each hierarchy as a shared library keeps each text image within the linker reach, and preserves the original generated protected-library ABI and hash checks. The top links only its own objects and the single Verilator runtime, exports its symbols, and loads every child library with `--no-as-needed`. No RTL, elaboration, cycles, or compiled input objects changed.

Actual recovery: all 395 shared libraries linked, the top executable linked with exit 0, and `ldd -r` resolved every symbol with exit 0. No whole-die simulation ran. The restored executable is the pinned historical V1c3 vehicle, not a current-main functional qualification.

The output binary and `so/` directory must stay together. They are on epyc2 under `/srv/opentallas-scratch2/claude/codex-ds-link-1105`. Source objects remain untouched in `/home/ubuntu/scratch-root/claude/tok-ds-2/build_v1c3/obj`. The original failure logs remain untouched under `tok-ds-5-v1c3r`.

Replay the link into a fresh output directory through `ot-run`:

```sh
python3 -I tools/s81/verilator_shared_link.py \
  --obj /home/ubuntu/scratch-root/claude/tok-ds-2/build_v1c3/obj \
  --out /srv/opentallas-scratch2/claude/ds-link-new \
  --expect-libs 395 --jobs 4
```

IMG2 was also collected: 390/395 child archives exist, no live build process remains. The missing five are the final service libraries. They are not interchangeable with the V1c3 source cohort. Its continuation needs those five component builds and the same shared-link method; intel1 scratch was 49 GB free when collected, below new-unit admission.
