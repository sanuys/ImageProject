document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("generate-form");
  const btn = document.getElementById("generate-btn");
  const statusBox = document.getElementById("status-box");
  const resultArea = document.getElementById("result-area");
  const historyGrid = document.getElementById("history-grid");

  const stepsInput = document.getElementById("steps");
  const stepsVal = document.getElementById("steps-val");
  const cfgInput = document.getElementById("cfg_scale");
  const cfgVal = document.getElementById("cfg-val");
  const samplerSelect = document.getElementById("sampler");

  stepsInput.addEventListener("input", () => (stepsVal.textContent = stepsInput.value));
  cfgInput.addEventListener("input", () => (cfgVal.textContent = cfgInput.value));

  // โหลดรายชื่อ sampler จริงจาก Forge มาใส่ dropdown
  fetch("/api/samplers")
    .then((r) => r.json())
    .then((names) => {
      samplerSelect.innerHTML = "";
      names.forEach((name) => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        samplerSelect.appendChild(opt);
      });
    })
    .catch(() => {
      // เงียบไว้ ใช้ค่า default "Euler a" ที่มีอยู่แล้วในหน้า
    });

  function showStatus(message, isError = false) {
    statusBox.style.display = "block";
    statusBox.textContent = message;
    statusBox.classList.toggle("error", isError);
  }

  function hideStatus() {
    statusBox.style.display = "none";
  }

  function prependHistory(imageUrl, prompt, seed) {
    const placeholder = historyGrid.querySelector(".placeholder-text");
    if (placeholder) placeholder.remove();

    const item = document.createElement("div");
    item.className = "history-item";
    item.innerHTML = `
      <img src="${imageUrl}" alt="${prompt}">
      <p title="${prompt}">${prompt}</p>
      <p class="history-seed">Seed: ${seed}</p>
    `;
    historyGrid.prepend(item);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      prompt: document.getElementById("prompt").value,
      negative_prompt: document.getElementById("negative_prompt").value,
      steps: Number(stepsInput.value),
      cfg_scale: Number(cfgInput.value),
      width: Number(document.getElementById("width").value),
      height: Number(document.getElementById("height").value),
      sampler: samplerSelect.value,
      seed: Number(document.getElementById("seed").value),
    };

    btn.disabled = true;
    btn.textContent = "กำลังสร้างภาพ...";
    showStatus("กำลังส่งคำขอไปที่ AI Server กรุณารอสักครู่ (อาจใช้เวลาหลายสิบวินาที)...");

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok) {
        showStatus(data.error || "เกิดข้อผิดพลาด", true);
        return;
      }

      resultArea.innerHTML = `
        <div class="result-wrap">
          <img src="${data.image_url}" alt="${data.prompt}">
          <div class="seed-row">
            <span>Seed ที่ใช้จริง: <strong>${data.seed}</strong></span>
            <button type="button" id="reuse-seed-btn" class="btn-small">ใช้ seed นี้อีกครั้ง</button>
          </div>
        </div>
      `;
      prependHistory(data.image_url, data.prompt, data.seed);
      hideStatus();

      const reuseBtn = document.getElementById("reuse-seed-btn");
      if (reuseBtn) {
        reuseBtn.addEventListener("click", () => {
          document.getElementById("seed").value = data.seed;
        });
      }
    } catch (err) {
      showStatus("เชื่อมต่อ server ไม่ได้: " + err.message, true);
    } finally {
      btn.disabled = false;
      btn.textContent = "สร้างภาพ";
    }
  });
});
