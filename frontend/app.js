
const input = document.getElementById("videoInput");
const button = document.getElementById("makeBtn");
const status = document.getElementById("status");
const results = document.getElementById("results");

input.addEventListener("change", () => {
  button.disabled = !input.files.length;
});

button.addEventListener("click", async () => {
  if (!input.files.length) return;

  button.disabled = true;
  status.textContent = "AI is finding your best moments...";

  const form = new FormData();
  form.append("video", input.files[0]);

  try {
    const response = await fetch("/api/clip", {
      method: "POST",
      body: form
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Processing failed");
    }

    results.innerHTML = "<h2>Your AI Clips</h2>";

    data.clips.forEach((clip, index) => {
      const item = document.createElement("div");
      item.innerHTML = `
        <h3>Clip ${index + 1}</h3>
        <video controls playsinline width="100%"
          src="${clip.url}"></video>
        <a href="${clip.url}" download>
          Download Clip
        </a>
      `;
      results.appendChild(item);
    });

    status.textContent = "Your clips are ready!";
  } catch (error) {
    status.textContent = "Error: " + error.message;
  }

  button.disabled = false;
});
