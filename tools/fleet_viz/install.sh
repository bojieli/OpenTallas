#!/usr/bin/env bash
# Install tools/fleet_viz into ~/.local/share/fleet-viz and (re)start the user service.
set -euo pipefail
src=$(cd "$(dirname "$0")" && pwd); dst=$HOME/.local/share/fleet-viz
mkdir -p "$dst" "$HOME/.config/systemd/user"
cp "$src"/{server.py,agent.py,recorder.py,elements.py,export_replay.py,index.html,fv_stale.js,fleet_hosts.json} "$dst"/
cp "$src"/{landing.py,coverage.py,native_provenance.py,elem_shell.py,elem_desc.py,explorer.py,explorer_geom.py,explorer.html,explorer.js,explorer_story.js,explorer_dies.json,explorer_names.json,explorer_compose.json,stories_import.py} "$dst"/
mkdir -p "$dst/stories" "$dst/explorer"
cp "$src/explorer_chip_dataflow.js" "$dst/"
cp "$src/explorer_dataflow.py" "$dst/"
cp "$src/explorer/dataflow.js" "$src/explorer/flow_layout.js" "$dst/explorer/"
cp "$src"/stories/*.json "$dst/stories/"
rm -rf "$dst/explorer/token"; cp -r "$src/explorer/token" "$dst/explorer/token"
rm -rf "$dst/explorer/coverage"; cp -r "$src/explorer/coverage" "$dst/explorer/coverage"
# element pages: page + pages.json from the repo; explorer/element/data/ is deploy data (tools/explorer_elem_export.py pack), kept
mkdir -p "$dst/explorer/element/data"; cp "$src"/explorer/element/{index.html,elem.js,shell.js,shell.css,pages.json} "$dst/explorer/element/"
# layout viewer (Layout tab): client, vendored deck.gl, tiling service, and the host-side tools it ships to fleet hosts
cp "$src"/explorer/element/{layout.js,lv_worker.js,lv_decode.js} "$dst/explorer/element/"
mkdir -p "$dst/explorer/element/vendor"; cp "$src"/explorer/element/vendor/*.js "$dst/explorer/element/vendor/"
cp "$src"/layout_service.py "$src"/layout_store.py "$dst/"
mkdir -p "$dst/layout_viewer"; cp "$src"/../layout_viewer/{lv_extract.py,lv_tile.py,lv_lint.py,lv_verify.js,lv_post_record.sh} "$src"/../hier_contract/child_lint.py "$dst/layout_viewer/"
mkdir -p "$dst/layout_store"   # static layout store (layout_store.py): content-addressed closure exports, kept across deploys
# python 3.14 fleet hosts have no brotli module: ship the wheel's contents next to lv_tile.py (pylib314/)
if [ ! -f "$dst/layout_viewer/pylib314/brotli.py" ]; then
  tmp=$(mktemp -d); python3 -m pip download -q brotli==1.2.0 --python-version 3.14 --only-binary=:all: \
    --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --no-deps -d "$tmp" \
    && mkdir -p "$dst/layout_viewer/pylib314" && (cd "$dst/layout_viewer/pylib314" && python3 -m zipfile -e "$tmp"/brotli-*.whl .)
  rm -rf "$tmp"
fi
rm -rf "$dst/landing"; mkdir -p "$dst/landing/recordings"
cp "$src"/landing/{index.html,landing.css,landing.js} "$dst/landing/"; cp "$src"/landing/recordings/*.json "$dst/landing/recordings/"
cp "$src"/fleet-viz.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable fleet-viz.service >/dev/null
systemctl --user restart fleet-viz.service
rm -f "$dst"/landmask.js
