"use strict";
// No storage, background capture, PTZ, recognition or automatic print path.
const $ = id => document.getElementById(id);
let enabled = false, token = null, stream = null, posterId = null;
let phase = "idle", epoch = 0, expiry = null, deadline = 0, dirty = false;
let exposureControl = null, exposureBusy = false;
const say = message => { $("status").textContent = message; };

async function api(action, data = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), action === "print" ? 30000 : 12000);
  try {
    const response = await fetch(`/api/camera/${action}`, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({token, ...data}), signal: controller.signal, cache: "no-store"
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "A művelet nem sikerült.");
    return result;
  } finally { clearTimeout(timeout); }
}
function stopCamera() {
  if (stream) stream.getTracks().forEach(track => { track.onended = null; track.stop(); });
  stream = null; $("video").srcObject = null; $("liveBox").hidden = true;
  exposureControl = null; exposureBusy = false; $("exposureBox").hidden = true;
  $("countdown").textContent = ""; $("frameOk").checked = false;
}
function controls() {
  const idle = phase === "idle", reviewing = phase === "preview";
  $("arm").disabled = !enabled || !idle || !$("consent").checked || !$("zone").checked || !$("camera").value;
  $("find").disabled = !enabled || !idle; $("camera").disabled = !idle;
  $("consent").disabled = !idle; $("zone").disabled = !idle;
  $("capture").disabled = phase !== "live" || exposureBusy || !$("frameOk").checked;
  $("exposure").disabled = phase !== "live" || exposureBusy;
  $("cancel").disabled = idle; $("reroll").disabled = !reviewing;
  $("retake").disabled = !reviewing;
  $("print").disabled = !reviewing || dirty || !posterId || !$("printer").value;
  $("alias").disabled = !reviewing; $("pad").disabled = !reviewing;
  $("brightness").disabled = !reviewing || dirty;
  $("badge").textContent = !enabled ? "KIKAPCSOLVA" : idle ? "KÉSZENLÉT" : reviewing ? "ELŐNÉZET • KAMERA ÁLL" : "ÉLESÍTVE";
}
function resetLocal() {
  epoch++; clearTimeout(expiry); expiry = null; deadline = 0;
  stopCamera(); token = null; posterId = null; phase = "idle"; dirty = false;
  $("review").hidden = true; $("preview").replaceChildren();
  $("consent").checked = false; $("zone").checked = false; $("alias").value = "";
  $("brightness").value = "1.6"; $("brightnessValue").textContent = "1,6×";
  controls();
}
function expireAfter(seconds) {
  clearTimeout(expiry); deadline = Date.now() + seconds * 1000;
  expiry = setTimeout(() => cancel("Lejárt az idő. A fotót töröltük; új résztvevőhöz élesíts újra."), seconds * 1000);
}
async function cancel(message = "Kikapcsolva. A fotót és az előnézetet töröltük.") {
  if (phase === "cancelling") return;
  const oldToken = token;
  resetLocal();
  if (oldToken) {
    // Clear the browser immediately, then release the server's memory too.
    phase = "cancelling"; controls();
    try { await api("cancel", {token: oldToken}); }
    catch { message += " A szerverpéldány legkésőbb 5 percen belül lejár."; }
    phase = "idle"; controls();
  }
  say(message);
}
async function findCameras(preferred = "") {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("Nyisd meg Chrome vagy Edge alatt: http://127.0.0.1:8765/eagle-eye");
  const devices = (await navigator.mediaDevices.enumerateDevices()).filter(d => d.kind === "videoinput");
  const select = $("camera"), previous = preferred || select.value;
  select.replaceChildren();
  select.add(new Option("Válassz USB-kamerát…", ""));
  devices.forEach((device, i) => select.add(new Option(device.label || `Kamera ${i + 1} (böngésző alapértelmezése; név engedély után)`, device.deviceId || "browser-default")));
  const eagle = devices.find(device => /eagleeye|eagle eye/i.test(device.label));
  select.value = previous && [...select.options].some(o => o.value === previous) ? previous : eagle?.deviceId || "";
  controls();
  if (!devices.length) say("Nincs elérhető USB-kamera. Ellenőrizd a csatlakozást és a Windows kameraengedélyeit.");
}
async function arm() {
  if ($("arm").disabled) return;
  const mine = ++epoch, deviceId = $("camera").value;
  phase = "arming"; controls(); say("Kameraengedély kérése…");
  try {
    const session = await api("arm", {consent: $("consent").checked, participant_only: $("zone").checked});
    if (mine !== epoch) { await api("cancel", {token: session.token}); return; }
    token = session.token; expireAfter(session.expires_in);
    const media = await navigator.mediaDevices.getUserMedia({audio: false, video: {
      ...(deviceId === "browser-default" ? {} : {deviceId: {exact: deviceId}}),
      width: {ideal: 1280}, height: {ideal: 720}, frameRate: {ideal: 15, max: 30}
    }});
    if (mine !== epoch) { media.getTracks().forEach(t => t.stop()); return; }
    stream = media;
    stream.getVideoTracks()[0].onended = () => cancel("A kamera megszakadt. Ellenőrizd az USB-kábelt, majd élesíts újra.");
    $("video").srcObject = stream; $("liveBox").hidden = false;
    await $("video").play();
    if (mine !== epoch) return;
    $("cameraName").textContent = `Aktív kamera: ${stream.getVideoTracks()[0].label}`;
    setupExposure(stream.getVideoTracks()[0]);
    await findCameras(stream.getVideoTracks()[0].getSettings().deviceId);
    if (mine !== epoch) return;
    phase = "live"; controls(); say("Élesítve, legfeljebb 2 percre. Igazítsd az arcot a keretbe, majd ellenőrizd a képet.");
  } catch (error) {
    if (mine === epoch) await cancel(`Nem indult el a kamera: ${error.message}`);
  }
}
function showPoster(result) {
  posterId = result.id; dirty = false; phase = "preview";
  const image = new Image(); image.alt = "A nyomtatásra váró körözési poszter pontos előnézete"; image.src = result.image;
  $("preview").replaceChildren(image); $("review").hidden = false;
  $("brightness").value = String(result.photo_gamma ?? $("brightness").value);
  $("brightnessValue").textContent = Number($("brightness").value).toFixed(1).replace(".", ",") + "×";
  expireAfter(result.expires_in); controls(); say("A kamera leállt. Nézd meg a posztert; csak a Nyomtatás gomb küldi a nyomtatóra.");
}
const options = () => ({wanted_alias: $("alias").value, pad_mm: Number($("pad").value), photo_gamma: Number($("brightness").value)});
function setupExposure(track) {
  const caps = track.getCapabilities?.() || {}, settings = track.getSettings();
  const modes = caps.exposureMode || [];
  const name = caps.exposureCompensation && modes.includes("continuous") ? "exposureCompensation" :
    caps.exposureTime && modes.includes("manual") ? "exposureTime" : null;
  const range = name && caps[name];
  if (!range || !Number.isFinite(range.min) || !Number.isFinite(range.max) || range.max <= range.min || !track.applyConstraints) {
    $("exposureBox").hidden = true;
    $("exposureHint").textContent = "A böngésző nem kínál állítható kameraexpozíciót. A kész poszter mellett a Fotó világosítása csúszka használható.";
    return;
  }
  exposureControl = {name, mode: name === "exposureTime" ? "manual" : "continuous"};
  const slider = $("exposure");
  slider.min = range.min; slider.max = range.max; slider.step = range.step > 0 ? range.step : (range.max-range.min)/100;
  slider.value = Math.min(range.max, Math.max(range.min, settings[name] ?? range.min));
  $("exposureValue").textContent = slider.value;
  $("exposureHint").textContent = "Ez a csúszka a kamera élőképének expozícióját állítja.";
  $("exposureBox").hidden = false;
}
async function changeExposure() {
  if (!exposureControl || phase !== "live" || exposureBusy) return;
  const mine = epoch, track = stream.getVideoTracks()[0], control = exposureControl;
  const value = Number($("exposure").value), oldValue = track.getSettings()[control.name];
  exposureBusy = true; $("frameOk").checked = false; controls();
  try {
    await track.applyConstraints({advanced: [{exposureMode: control.mode, [control.name]: value}]});
    if (mine !== epoch) return;
    const actual = track.getSettings()[control.name];
    if (!Number.isFinite(actual) || Math.abs(actual-value) > Number($("exposure").step)/2 + 0.001) throw new Error("A kamera nem fogadta el a beállítást.");
    $("exposure").value = actual; $("exposureValue").textContent = String(actual);
    say("Expozíció beállítva. Ellenőrizd az élőképet fotózás előtt.");
  } catch (error) {
    if (mine === epoch) { $("exposure").value = oldValue ?? $("exposure").min; say(`Az expozíció nem állítható: ${error.message}`); }
  } finally { if (mine === epoch) { exposureBusy = false; controls(); } }
}
async function adjustBrightness() {
  if (phase !== "preview" || dirty) return;
  const mine = epoch; phase = "adjusting"; controls(); say("A fotó világosítása…");
  try { const result = await api("adjust", {photo_gamma: Number($("brightness").value)}); if (mine === epoch) showPoster(result); }
  catch (error) { if (mine === epoch) { phase = "preview"; dirty = true; controls(); say(`${error.message} Az Új szöveg gombbal próbálhatod újra.`); } }
}
async function capture() {
  if ($("capture").disabled) return;
  const mine = epoch, frameStart = $("video").currentTime; phase = "countdown"; controls();
  try {
    for (let n = 3; n > 0; n--) {
      if (mine !== epoch) return;
      $("countdown").textContent = n;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    if (mine !== epoch) return;
    const video = $("video"), track = stream?.getVideoTracks()[0];
    if (!track || track.readyState !== "live" || track.muted || video.readyState < 2 || !video.videoWidth || video.currentTime <= frameStart) throw new Error("Nincs friss kamerakép.");
    const canvas = document.createElement("canvas"); canvas.width = 672; canvas.height = 822;
    const width = Math.min(video.videoWidth, video.videoHeight * 448 / 548), height = width * 548 / 448;
    const context = canvas.getContext("2d");
    context.drawImage(video, (video.videoWidth-width)/2, (video.videoHeight-height)/2, width, height, 0, 0, canvas.width, canvas.height);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let light = 0;
    for (let i = 0; i < pixels.length; i += 64) light += (pixels[i]+pixels[i+1]+pixels[i+2])/3;
    light /= pixels.length/64;
    if (light < 4 || light > 245) { canvas.width = canvas.height = 0; throw new Error("Túl sötét vagy túl világos a kép. Javíts a megvilágításon."); }
    let image = canvas.toDataURL("image/jpeg", 0.9); canvas.width = canvas.height = 0;
    stopCamera(); phase = "uploading"; controls(); say("A kamera leállt. Készül a körözés…");
    const pending = api("capture", {image, ...options()}); image = null;
    const result = await pending;
    if (mine === epoch) showPoster(result);
  } catch (error) { if (mine === epoch) await cancel(error.message); }
}
async function reroll() {
  const mine = epoch; phase = "rerolling"; controls(); say("Új vádak, ugyanaz a fotó…");
  try { const result = await api("reroll", options()); if (mine === epoch) showPoster(result); }
  catch (error) { if (mine === epoch) { phase = "preview"; controls(); say(error.message); } }
}
async function printPoster() {
  if ($("print").disabled) return;
  const mine = epoch; phase = "printing"; controls();
  try {
    const result = await api("print", {id: posterId, confirm_print: true, printer: $("printer").value, cut: $("cut").checked});
    if (mine === epoch) { resetLocal(); say(result.message); }
  } catch (error) {
    if (mine === epoch) { phase = "preview"; controls(); say(`${error.message} Ellenőrizd a Windows nyomtatási sort, mielőtt újra kattintasz.`); }
  }
}
async function printers() {
  try {
    const response = await fetch("/api/printers", {cache: "no-store"});
    if (!response.ok) throw new Error("Nem érhető el a nyomtatólista.");
    const result = await response.json(), select = $("printer"), previous = select.value;
    select.replaceChildren(); select.add(new Option("Válassz blokknyomtatót…", ""));
    result.printers.forEach(p => select.add(new Option(`${p.name} [${p.port}]`, p.name)));
    select.value = result.printers.some(p => p.name === previous) ? previous : result.printers.find(p => /cp-q1|birch/i.test(p.name))?.name || "";
    controls();
  } catch (error) { say(error.message); }
}
$("find").onclick = () => findCameras().catch(error => say(error.message));
$("arm").onclick = arm; $("capture").onclick = capture;
$("cancel").onclick = () => cancel(); $("retake").onclick = () => cancel("A régi fotót töröltük. Újrafotózáshoz ellenőrizd a beleegyezést, majd élesíts újra.");
$("reroll").onclick = reroll; $("print").onclick = printPoster; $("printers").onclick = printers;
$("brightness").oninput = () => { $("brightnessValue").textContent = Number($("brightness").value).toFixed(1).replace(".", ",") + "×"; };
$("brightness").onchange = adjustBrightness;
$("exposure").onchange = changeExposure;
for (const id of ["consent", "zone", "camera", "frameOk", "printer"]) $(id).onchange = controls;
for (const id of ["alias", "pad"]) $(id).oninput = () => { dirty = true; controls(); };
document.addEventListener("visibilitychange", () => {
  if (document.hidden && ["arming", "live", "countdown", "uploading"].includes(phase)) cancel("Az élőkép bezárult, mert elhagytad a lapot. Élesíts újra.");
  else if (!document.hidden && deadline && Date.now() >= deadline) cancel("Lejárt a fotó megőrzési ideje.");
});
window.addEventListener("pagehide", () => {
  const oldToken = token; resetLocal();
  if (oldToken) navigator.sendBeacon("/api/camera/cancel", new Blob([JSON.stringify({token: oldToken})], {type: "application/json"}));
});
async function init() {
  try {
    const response = await fetch("/api/camera/status", {cache: "no-store"});
    if (!response.ok) throw new Error("Nem érhető el a helyi alkalmazás.");
    enabled = (await response.json()).enabled;
    $("setup").textContent = enabled ? "USB fotófülke • a kamera csak élesítéskor indul." : "Kikapcsolva. Zárd be a futó appot, majd indítsd a start_eagle_eye.bat fájlt a projekt mappájából.";
    controls(); if (enabled) await printers();
  } catch (error) { say(error.message); }
}
init();
