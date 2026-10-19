"use strict";
const $=id=>document.getElementById(id);
let stream=null,track=null,ranges={},busy=false;
const say=s=>$("status").textContent=s;
const range=a=>{const r=ranges[a];return r&&Number.isFinite(r.min)&&Number.isFinite(r.max)&&r.max>r.min?r:null};
function buttons(){
$("connect").disabled=!!track||busy;$("disconnect").disabled=!track;
for(const [id,a] of Object.entries({left:"pan",right:"pan",up:"tilt",down:"tilt",minus:"zoom",plus:"zoom",center:"pan"}))
$(id).disabled=!track||busy||!range(a)||(id==="center"&&!range("tilt"));
}
function stop(){
if(stream)stream.getTracks().forEach(t=>{t.onended=null;t.stop()});
stream=null;track=null;ranges={};$("video").srcObject=null;buttons();
}
async function scan(){
const ds=(await navigator.mediaDevices.enumerateDevices()).filter(d=>d.kind==="videoinput");
const prev=$("camera").value;
$("camera").replaceChildren(new Option("Válassz kamerát",""));
ds.forEach((d,i)=>$("camera").add(new Option(d.label||"Kamera "+(i+1),d.deviceId)));
$("camera").value=ds.some(d=>d.deviceId===prev)?prev:(ds.find(d=>/eagle.?eye/i.test(d.label))?.deviceId||"");
}
async function connect(){
if(track||busy)return;busy=true;buttons();
try{
if(!navigator.mediaDevices?.getUserMedia)throw Error("A böngésző nem támogatja a kamera API-t.");
const id=$("camera").value;
stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{...(id?{deviceId:{exact:id}}:{}),pan:true,tilt:true,zoom:true}});
track=stream.getVideoTracks()[0];track.onended=()=>{stop();say("A kamera lecsatlakozott.")};
$("video").srcObject=stream;await $("video").play();
const c=track.getCapabilities?.()||{};ranges={pan:c.pan,tilt:c.tilt,zoom:c.zoom};
$("info").textContent=track.label+" — "+["pan","tilt","zoom"].map(a=>a+": "+(range(a)?range(a).min+"…"+range(a).max:"nem támogatott")).join(" | ");
say(["pan","tilt","zoom"].some(a=>range(a))?"PTZ készen áll.":"Van élőkép, de a böngésző nem teszi elérhetővé a hardveres USB PTZ-t. Ellenőrizd a PTZ engedélyt; szükség lehet külön USB/VISCA vezérlőre.");
await scan();
}catch(e){stop();say("Csatlakozási hiba: "+e.message+"\nEllenőrizd a PTZ engedélyt és zárd be a kamerát használó programokat.")}
finally{busy=false;buttons()}
}
async function setAxes(axes){
if(!track||busy)return;busy=true;buttons();
try{await track.applyConstraints({advanced:[axes]});say("Pozíciókérés elküldve: "+JSON.stringify(axes))}
catch(e){say("A kamera elutasította a mozgatást: "+e.message)}
finally{busy=false;buttons()}
}
function move(a,dir){
const r=range(a);if(!r||!track||busy)return;
const current=track.getSettings?.()[a];let v=Number.isFinite(current)?current:(r.min+r.max)/2;
v=Math.max(r.min,Math.min(r.max,v+dir*(r.max-r.min)*Number($("step").value)));
if(r.step>0)v=Math.max(r.min,Math.min(r.max,r.min+Math.round((v-r.min)/r.step)*r.step));
return setAxes({[a]:v});
}
$("scan").onclick=()=>scan().catch(e=>say(e.message));$("connect").onclick=connect;
$("disconnect").onclick=()=>{stop();say("Kamera leválasztva.")};
for(const [id,a,d] of [["left","pan",-1],["right","pan",1],["up","tilt",1],["down","tilt",-1],["minus","zoom",-1],["plus","zoom",1]])$(id).onclick=()=>move(a,d);
$("center").onclick=()=>{if(!range("pan")||!range("tilt"))return;const p=range("pan"),t=range("tilt");setAxes({pan:(p.min+p.max)/2,tilt:(t.min+t.max)/2})};
window.addEventListener("pagehide",stop);scan().catch(e=>say(e.message));buttons();