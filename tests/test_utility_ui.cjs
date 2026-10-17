"use strict";
// Validate the actual classic-page inline JS without a browser or dependencies.
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const html = fs.readFileSync(path.join(__dirname, "../static/index.html"), "utf8");
const match = html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(match, "main page must have an inline JS program");
const script = match[1];
const firstLoad = script.lastIndexOf("translate();usbPrinters();");
assert.ok(firstLoad > 0, "must preserve regular page initialization");

test("thermal toolbox UI script parses and all mode labels stay aligned", () => {
  const mockDocument = {getElementById() {return {};}};
  const values = vm.runInNewContext(script.slice(0, firstLoad) +
       "\n({MODES,TXT})", {document:mockDocument});
  assert.equal(values.MODES.length, values.TXT.en.name.length);
  assert.equal(values.MODES.length, values.TXT.hu.name.length);
  assert.equal(values.MODES.length, values.TXT.en.desc.length);
  assert.equal(values.MODES.length, values.TXT.hu.desc.length);
  assert.equal(new Set([...values.MODES].map(m=>m.id)).size, values.MODES.length);
  for (const id of ["qr", "checklist", "note", "cheatsheet", "legal", "deposit"]) {
    assert.ok([...values.MODES].find(m=>m.id===id), "Missing "+id);
  }
});

test("all utility form options and non-refundable-foglaló disclaimer exist", () => {
  for (const token of ["qr_type", "qr_value", "ssid", "wifi_password",
        "items", "sheet", "price_huf", "sale_kind", "sale_channel",
        "customer", "part", "paid_huf", "payment_kind", "earnest_agreed"]) {
    assert.ok(script.includes(token), "Missing form: "+token);
  }
  assert.ok(script.includes("ÚJ VÁDAK"), "Must preserve wanted photo reroll");
  assert.ok(script.includes("Az előleg nem automatikusan"), "Advance payment warning missing");
  assert.ok(script.includes("nem jótállási jegy"), "Durable warranty document reminder missing");
});
