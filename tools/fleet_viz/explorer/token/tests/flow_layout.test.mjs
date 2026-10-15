import assert from 'node:assert/strict';
import { bundleSegments, spatialOverview, bundleLabel, placeLabel } from '../../flow_layout.js';

const segment = (id, x, width = 32) => ({ from: [x, 10], to: [x + 1, 15], directed: false, edge: { id, width_bits: width } });
// A source-ordered prefix contains only the left region. Both regions must survive an overview cap.
const all = Array.from({ length: 1000 }, (_, i) => segment(`left${i}`, i / 100))
  .concat(Array.from({ length: 1000 }, (_, i) => segment(`right${i}`, 90 + i / 100)));
const shown = spatialOverview(all, { width: 100, height: 100, limit: 20 });
assert.equal(shown.length, 20);
assert.ok(shown.some(s => s.from[0] > 80));
assert.ok(shown.some(s => s.from[0] < 20));
assert.ok(shown.every(s => all.includes(s)), 'sampling must preserve actual endpoint geometry');
const first = segment('a', 1), second = segment('b', 1, 512);
const bundled = bundleSegments([first, second, { ...first, from: first.to, to: first.from }]);
assert.equal(bundled.length, 1, 'undirected endpoint pair is one bundle');
assert.equal(bundled[0].edges.length, 2, 'retain individual source connections once');
assert.equal(bundleLabel(bundled[0]), '2 connections · 32–512 bits each');
assert.equal(bundleSegments([{ ...first, directed: true }, { ...first, directed: true, from: first.to, to: first.from }]).length, 2);
const occupied = [];
assert.ok(placeLabel({ x: 10, y: 10, w: 50, h: 14 }, occupied, 200, 200));
assert.equal(placeLabel({ x: 20, y: 14, w: 40, h: 14 }, occupied, 200, 200), false);
assert.equal(placeLabel({ x: -10, y: 100, w: 40, h: 14 }, occupied, 200, 200), false);
assert.ok(placeLabel({ x: 10, y: 50, w: 50, h: 14 }, occupied, 200, 200));
console.log('Spatial dataflow overview, source-preserving bundles and label collision checks: PASS');
