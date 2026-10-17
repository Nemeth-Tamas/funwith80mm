// Browser workflow, with fake media tracks, pixels, clock and HTTP. No hardware.
const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname, "../static/eagle-eye.js"), "utf8");
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise(setImmediate); };
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => {resolve=a; reject=b;}); return {promise,resolve,reject}; };

async function booth() {
  const calls = [], mediaCalls = [], timers = new Map(), elements = new Map();
  let timerId = 0;
  class Element {
    constructor() { this.value=""; this.checked=false; this.disabled=false; this.hidden=false; this.options=[]; this.children=[]; this.textContent=""; }
    add(option) { this.options.push(option); }
    replaceChildren(...children) { this.children=children; this.options=[]; }
  }
  const element = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  element("pad").value="20"; element("cut").checked=true; element("brightness").value="1.6";
  Object.assign(element("video"), {videoWidth:1280, videoHeight:720, readyState:2, currentTime:0, play:async()=>{}});
  const track = {readyState:"live", muted:false, label:"Polycom EagleEye IV USB Camera", stopped:false,
    stop() {this.stopped=true; this.readyState="ended";}, getSettings:()=>({deviceId:"eagle"})};
  const media = {getTracks:()=>[track], getVideoTracks:()=>[track]};
  const state = {light:128, track, media, enabled:true, pending:{}, failPrint:false, devices:[{kind:"videoinput",deviceId:"eagle",label:track.label}]};
  const events = {}, beacons = [];
  const context = vm.createContext({
    console, AbortController, Blob, Date, Image:Element,
    Option:class {constructor(text,value) {this.text=text; this.value=value;}},
    setTimeout:(fn, delay)=>{const id=++timerId; timers.set(id,{fn,delay}); return id;},
    clearTimeout:id=>timers.delete(id),
    document:{hidden:false, getElementById:element,
      createElement:()=>({width:672,height:822,getContext:()=>({drawImage(){},getImageData:()=>({data:new Uint8ClampedArray(64).fill(state.light)})}),toDataURL:()=>"data:image/jpeg;base64,c2FtcGxl"}),
      addEventListener:(name,fn)=>events[name]=fn},
    window:{addEventListener:(name,fn)=>events[name]=fn},
    navigator:{mediaDevices:{enumerateDevices:async()=>state.devices,
      getUserMedia:async options=>{mediaCalls.push(options); return state.pending.media ? state.pending.media.promise : media;}},
      sendBeacon:(url,body)=>beacons.push({url,body})},
    fetch:async(url,options={})=>{
      const action=url.split("/").pop(), body=options.body?JSON.parse(options.body):{};
      calls.push({action,body});
      if(state.pending[action]) return state.pending[action].promise;
      const data = action==="status" ? {enabled:state.enabled} : action==="printers" ? {printers:[{name:"CP-Q1UN",port:"USB001"}]} :
        action==="arm" ? {token:"session",expires_in:120} : ["capture","reroll","adjust"].includes(action) ? {id:`poster-${calls.length}`,image:"data:image/png;base64,cG9zdGVy",expires_in:299,photo_gamma:body.photo_gamma??1.6} :
        action==="print" ? (state.failPrint?{error:"offline"}:{message:"queued and cleared"}) : {ok:true};
      return {ok:!(action==="print"&&state.failPrint),json:async()=>data};
    }
  });
  vm.runInContext(source,context); await settle();
  const tick = async delay => { if(!state.stalled) element("video").currentTime+=delay/1000; for (const [id,timer] of [...timers]) if(timer.delay===delay) {timers.delete(id); timer.fn();} await settle(); };
  const select = async()=>{await element("find").onclick();};
  const arm = async()=>{await select(); element("consent").checked=true; element("zone").checked=true; element("consent").onchange(); return element("arm").onclick();};
  const capture = async()=>{element("frameOk").checked=true; element("frameOk").onchange(); const pending=element("capture").onclick(); await tick(1000); await tick(1000); await tick(1000); await pending;};
  return {element, state, calls, mediaCalls, events, beacons, context, tick, select, arm, capture};
}

test("page load and device discovery cannot start capture or print",async()=>{
  const b=await booth(); await b.select();
  assert.equal(b.mediaCalls.length,0); assert.equal(b.element("arm").disabled,true);
  assert.equal(b.calls.some(c=>["arm","capture","print"].includes(c.action)),false);
});
test("one-shot stops USB, freezes poster, rerolls without camera, prints only after click",async()=>{
  const b=await booth(); await b.arm(); assert.equal(b.mediaCalls.length,1); await b.capture();
  assert.equal(b.state.track.stopped,true); assert.equal(b.element("review").hidden,false);
  await b.element("reroll").onclick(); assert.equal(b.mediaCalls.length,1);
  assert.equal(b.calls.filter(c=>c.action==="capture").length,1);
  assert.equal(b.calls.some(c=>c.action==="print"),false);
  await b.element("print").onclick();
  const prints=b.calls.filter(c=>c.action==="print"); assert.equal(prints.length,1);
  assert.equal(prints[0].body.confirm_print,true); assert.equal(prints[0].body.printer,"CP-Q1UN");
  assert.equal(b.element("preview").children.length,0); assert.equal(b.element("consent").checked,false);
});
test("cancel during countdown cannot create a photo",async()=>{
  const b=await booth(); await b.arm(); b.element("frameOk").checked=true; b.element("frameOk").onchange();
  const capturing=b.element("capture").onclick(); await b.element("cancel").onclick(); await b.tick(1000); await capturing;
  assert.equal(b.state.track.stopped,true); assert.equal(b.calls.some(c=>["capture","print"].includes(c.action)),false);
});
test("late camera permission is stopped after cancel",async()=>{
  const b=await booth(); b.state.pending.media=deferred(); const arming=b.arm(); await settle();
  await b.element("cancel").onclick(); b.state.pending.media.resolve(b.state.media); await arming;
  assert.equal(b.state.track.stopped,true); assert.equal(b.element("liveBox").hidden,true);
});
test("late arm response is released without opening camera",async()=>{
  const b=await booth(); b.state.pending.arm=deferred(); const arming=b.arm(); await settle();
  await b.element("cancel").onclick(); b.state.pending.arm.resolve({ok:true,json:async()=>({token:"late",expires_in:120})}); await arming;
  assert.equal(b.mediaCalls.length,0); assert.equal(b.calls.find(c=>c.action==="cancel").body.token,"late");
});
test("USB disconnect and arm timeout disarm without printing",async()=>{
  for (const trigger of [b=>b.state.track.onended(),b=>b.tick(120000)]) {
    const b=await booth(); await b.arm(); await trigger(b); await settle();
    assert.equal(b.state.track.stopped,true); assert.equal(b.element("consent").checked,false);
    assert.equal(b.calls.some(c=>c.action==="print"),false);
  }
});
test("poor lighting fails safely",async()=>{
  const b=await booth(); await b.arm(); b.state.light=0; await b.capture();
  assert.equal(b.state.track.stopped,true); assert.equal(b.calls.some(c=>c.action==="capture"),false);
});
test("a stalled video cannot capture an old frame",async()=>{
  const b=await booth(); await b.arm(); b.state.stalled=true; await b.capture();
  assert.equal(b.state.track.stopped,true); assert.equal(b.calls.some(c=>c.action==="capture"),false);
});
test("retake erases old preview and requires deliberate consent and arm again",async()=>{
  const b=await booth(); await b.arm(); await b.capture(); await b.element("retake").onclick();
  assert.equal(b.element("preview").children.length,0); assert.equal(b.element("arm").disabled,true);
  assert.equal(b.mediaCalls.length,1); assert.equal(b.calls.some(c=>c.action==="cancel"),true);
});
test("printer failure preserves preview, no automatic retry",async()=>{
  const b=await booth(); await b.arm(); await b.capture(); b.state.failPrint=true; await b.element("print").onclick();
  assert.equal(b.element("review").hidden,false); assert.equal(b.calls.filter(c=>c.action==="print").length,1);
});
test("edited poster options disable print until regenerated",async()=>{
  const b=await booth(); await b.arm(); await b.capture(); b.element("alias").value="Kekszgróf"; b.element("alias").oninput();
  assert.equal(b.element("print").disabled,true); await b.element("print").onclick();
  assert.equal(b.calls.some(c=>c.action==="print"),false); await b.element("reroll").onclick();
  assert.equal(b.element("print").disabled,false);
});
test("a late capture response cannot restore a cancelled face",async()=>{
  const b=await booth(); await b.arm(); b.state.pending.capture=deferred();
  b.element("frameOk").checked=true; b.element("frameOk").onchange(); const capture=b.element("capture").onclick();
  await b.tick(1000); await b.tick(1000); await b.tick(1000); await b.element("cancel").onclick();
  b.state.pending.capture.resolve({ok:true,json:async()=>({id:"stale",image:"old",expires_in:299})}); await capture;
  assert.equal(b.element("preview").children.length,0); assert.equal(b.element("review").hidden,true);
});
test("leaving the page stops USB and releases session",async()=>{
  const b=await booth(); await b.arm(); b.events.pagehide();
  assert.equal(b.state.track.stopped,true); assert.equal(b.beacons.length,1);
  assert.equal(JSON.parse(await b.beacons[0].body.text()).token,"session");
});
test("anonymous initial device can request permission only on arm",async()=>{
  const b=await booth(); b.state.devices=[{kind:"videoinput",deviceId:"",label:""}]; await b.select();
  b.element("camera").value="browser-default"; await b.arm();
  assert.equal(b.mediaCalls.length,1); assert.equal(b.mediaCalls[0].audio,false);
  assert.equal(b.mediaCalls[0].video.deviceId,undefined);
});
test("brightness refresh uses the existing shot without reroll or print",async()=>{
  const b=await booth(); await b.arm(); await b.capture();
  b.element("brightness").value="2.1"; await b.element("brightness").onchange();
  const adjustment=b.calls.find(c=>c.action==="adjust"); assert.equal(adjustment.body.photo_gamma,2.1);
  assert.equal(b.calls.filter(c=>c.action==="capture").length,1);
  assert.equal(b.calls.some(c=>["reroll","print"].includes(c.action)),false);
});
test("hardware exposure appears only with supported capabilities and verifies readback",async()=>{
  const b=await booth(); let exposure=0;
  b.state.track.getCapabilities=()=>({exposureMode:["continuous"],exposureCompensation:{min:-2,max:2,step:0.5}});
  b.state.track.getSettings=()=>({deviceId:"eagle",exposureCompensation:exposure});
  b.state.track.applyConstraints=async constraints=>{exposure=constraints.advanced[0].exposureCompensation;};
  await b.arm(); assert.equal(b.element("exposureBox").hidden,false);
  b.element("exposure").value="1.5"; await b.element("exposure").onchange();
  assert.equal(exposure,1.5); assert.equal(b.calls.some(c=>["capture","print"].includes(c.action)),false);
});
test("unsupported hardware exposure leaves photo lightening available",async()=>{
  const b=await booth(); await b.arm(); assert.equal(b.element("exposureBox").hidden,true);
  await b.capture(); assert.equal(b.element("brightness").disabled,false);
});
