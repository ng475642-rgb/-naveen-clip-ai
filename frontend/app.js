
const $ = (id) => document.getElementById(id);
document.querySelectorAll(".tab").forEach(btn => btn.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b === btn));
  $("clipPanel").classList.toggle("hidden", btn.dataset.tab !== "clip");
  $("filmPanel").classList.toggle("hidden", btn.dataset.tab !== "film");
}));
$("videoInput").addEventListener("change", e => {
  const f = e.target.files[0];
  if (f) document.querySelector(".upload strong").textContent = f.name;
});
$("clipForm").addEventListener("submit", async e => {
  e.preventDefault();
  const file = $("videoInput").files[0];
  if (!file) return;
  const data = new FormData();
  data.append("video", file);
  data.append("clip_seconds", $("duration").value);
  data.append("clip_count", $("count").value);
  $("makeBtn").disabled = true;
  $("clipStatus").textContent = "Preparing your video… this can take a while.";
  $("results").innerHTML = "";
  try {
    const res = await fetch("/api/clip", {method:"POST", body:data});
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "Could not process video.");
    $("clipStatus").textContent = json.note || "Your clips are ready.";
    $("results").innerHTML = json.clips.map(c => `<article class="clipcard"><div><b>${c.name}</b><small>${c.duration_seconds}s · starts at ${c.start_seconds}s</small></div><a class="download" href="${c.url}">Download ↓</a></article>`).join("");
  } catch(err) { $("clipStatus").textContent = "Error: " + err.message; }
  finally { $("makeBtn").disabled = false; }
});
$("filmForm").addEventListener("submit", async e => {
  e.preventDefault();
  $("filmStatus").textContent = "Writing your storyboard…";
  $("storyboard").innerHTML = "";
  try {
    const res = await fetch("/api/film/plan", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({
      prompt:$("story").value, duration_seconds:Number($("filmDuration").value), style:$("filmStyle").value
    })});
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || "Could not create storyboard.");
    $("filmStatus").textContent = json.notice;
    $("storyboard").innerHTML = json.scenes.map(s => `<article class="scene"><span>SCENE ${s.scene} · ${s.duration_seconds}s</span><p>${s.visual_prompt}</p><small>Voiceover draft: ${s.voiceover}</small></article>`).join("");
  } catch(err) { $("filmStatus").textContent = "Error: " + err.message; }
});
