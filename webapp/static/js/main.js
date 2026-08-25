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
  const checkpointSelect = document.getElementById("checkpoint");

  stepsInput.addEventListener("input", () => (stepsVal.textContent = stepsInput.value));
  cfgInput.addEventListener("input", () => (cfgVal.textContent = cfgInput.value));

  // พอเลือก checkpoint ใหม่ (หรือหลังโหลด dropdown เสร็จครั้งแรก) ให้ปรับ sampler/ความละเอียด
  // ตาม preset ที่แนะนำของ checkpoint นั้นให้อัตโนมัติ
  function applyCheckpointPreset() {
    const opt = checkpointSelect.options[checkpointSelect.selectedIndex];
    if (!opt || !opt.dataset.sampler) return; // ไม่มีตัวเลือกอยู่เลย หรือไม่มี preset ก็ไม่ต้องทำอะไร

    const samplerOpt = [...samplerSelect.options].find((o) => o.value === opt.dataset.sampler);
    if (samplerOpt) samplerSelect.value = opt.dataset.sampler;

    const widthSelect = document.getElementById("width");
    const heightSelect = document.getElementById("height");
    if (opt.dataset.width && [...widthSelect.options].some((o) => o.value === opt.dataset.width)) {
      widthSelect.value = opt.dataset.width;
    }
    if (opt.dataset.height && [...heightSelect.options].some((o) => o.value === opt.dataset.height)) {
      heightSelect.value = opt.dataset.height;
    }
  }

  checkpointSelect.addEventListener("change", applyCheckpointPreset);

  // โหลด sampler ก่อน แล้วค่อยโหลด checkpoint ตาม เพื่อให้ dropdown sampler มีตัวเลือกครบ
  // ก่อนที่จะลองเซ็ต sampler ตาม preset ของ checkpoint ตัวแรกที่ถูกเลือกไว้อัตโนมัติ
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
    })
    .finally(() => {
      // โหลดรายชื่อ checkpoint จริงจาก Forge มาใส่ dropdown (ถูกกรองไว้แค่ 2 ตัวที่อนุญาตแล้วจากฝั่ง backend)
      fetch("/api/checkpoints")
        .then((r) => r.json())
        .then((checkpoints) => {
          if (!checkpoints || checkpoints.length === 0) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "(โหลดรายชื่อ checkpoint ไม่สำเร็จ ลองรีเฟรชหน้า)";
            opt.disabled = true;
            checkpointSelect.appendChild(opt);
            return;
          }

          checkpoints.forEach((cp) => {
            const opt = document.createElement("option");
            opt.value = cp.title;
            opt.textContent = cp.model_name;
            // เก็บ preset (sampler/width/height) ที่แนะนำไว้กับตัว <option> เอง
            // ไว้ให้ applyCheckpointPreset() หยิบไปเติมฟอร์มอัตโนมัติ
            opt.dataset.sampler = cp.sampler || "";
            opt.dataset.width = cp.width || "";
            opt.dataset.height = cp.height || "";
            checkpointSelect.appendChild(opt);
          });

          // checkpoint ตัวแรกในลิสต์ถูกเลือกเป็นค่าเริ่มต้นโดย browser อยู่แล้ว
          // เติม sampler/ความละเอียดให้ตรงกับ preset ของมันทันที ไม่ต้องรอผู้ใช้กดเปลี่ยนเอง
          applyCheckpointPreset();
        })
        .catch(() => {
          const opt = document.createElement("option");
          opt.value = "";
          opt.textContent = "(โหลดรายชื่อ checkpoint ไม่สำเร็จ ลองรีเฟรชหน้า)";
          opt.disabled = true;
          checkpointSelect.appendChild(opt);
        });
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
      checkpoint: checkpointSelect.value,
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

  // ============================================================
  //  PNG Info: อัปโหลดภาพ -> อ่าน prompt/ค่าตั้งค่าที่ฝังอยู่ในไฟล์
  // ============================================================
  const dropzone = document.getElementById("pnginfo-dropzone");
  const fileInput = document.getElementById("pnginfo-file");
  const pnginfoStatus = document.getElementById("pnginfo-status");
  const pnginfoResult = document.getElementById("pnginfo-result");
  const pnginfoPreviewImg = document.getElementById("pnginfo-preview-img");
  const pnginfoFields = document.getElementById("pnginfo-fields");
  const pnginfoPromptEl = document.getElementById("pnginfo-prompt");
  const pnginfoNegativeEl = document.getElementById("pnginfo-negative");
  const pnginfoNegativeRow = document.getElementById("pnginfo-negative-row");
  const pnginfoLoadBtn = document.getElementById("pnginfo-load-btn");

  let lastParsed = null; // เก็บค่าที่ parse ได้ล่าสุด ไว้ให้ปุ่ม "ใช้ค่านี้สร้างภาพ" หยิบไปใช้

  function showPnginfoStatus(message, isError = false) {
    pnginfoStatus.style.display = "block";
    pnginfoStatus.textContent = message;
    pnginfoStatus.classList.toggle("error", isError);
  }

  function hidePnginfoStatus() {
    pnginfoStatus.style.display = "none";
  }

  // หยิบค่าจาก parameters dict โดยลองหลายรูปแบบชื่อ key เผื่อเวอร์ชัน Forge ต่างกันเล็กน้อย
  function pick(params, ...keys) {
    for (const k of keys) {
      if (params[k] !== undefined && params[k] !== null && params[k] !== "") {
        return params[k];
      }
    }
    return null;
  }

  function renderPngInfo(previewSrc, parameters) {
    lastParsed = parameters;

    pnginfoPreviewImg.src = previewSrc;

    const prompt = pick(parameters, "Prompt", "prompt") || "(ไม่พบ prompt)";
    const negative = pick(parameters, "Negative prompt", "negative_prompt", "Negative Prompt") || "";
    const steps = pick(parameters, "Steps", "steps");
    const sampler = pick(parameters, "Sampler", "sampler_name", "sampler");
    const cfg = pick(parameters, "CFG scale", "cfg_scale");
    const seed = pick(parameters, "Seed", "seed");
    const size = pick(parameters, "Size", "size");
    const model = pick(parameters, "Model", "model_name", "sd_model_name");

    pnginfoPromptEl.textContent = prompt;

    if (negative) {
      pnginfoNegativeRow.style.display = "";
      pnginfoNegativeEl.textContent = negative;
    } else {
      pnginfoNegativeRow.style.display = "none";
    }

    const tags = [];
    if (steps) tags.push(`Steps: ${steps}`);
    if (cfg) tags.push(`CFG: ${cfg}`);
    if (size) tags.push(size);
    if (sampler) tags.push(sampler);
    if (seed) tags.push(`Seed: ${seed}`);
    if (model) tags.push(model);
    pnginfoFields.innerHTML = tags.map((t) => `<span>${t}</span>`).join("");

    pnginfoResult.style.display = "grid";
  }

  async function handlePngFile(file) {
    if (!file) return;
    if (!file.type.includes("png")) {
      showPnginfoStatus("รองรับเฉพาะไฟล์ .png เท่านั้น (ไฟล์ที่ Stable Diffusion สร้างจะฝังข้อมูลไว้ในรูปแบบนี้)", true);
      return;
    }

    pnginfoResult.style.display = "none";
    showPnginfoStatus("กำลังอ่านข้อมูลจากไฟล์...");

    const previewSrc = URL.createObjectURL(file);
    const formData = new FormData();
    formData.append("image", file);

    try {
      const res = await fetch("/api/png-info", { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        showPnginfoStatus(data.error || "อ่านข้อมูลไม่สำเร็จ", true);
        return;
      }

      hidePnginfoStatus();
      renderPngInfo(previewSrc, data.parameters || {});
    } catch (err) {
      showPnginfoStatus("เชื่อมต่อ server ไม่ได้: " + err.message, true);
    }
  }

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => handlePngFile(fileInput.files[0]));

  ["dragover", "dragenter"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dropzone-active");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dropzone-active");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    handlePngFile(file);
  });

  pnginfoLoadBtn.addEventListener("click", () => {
    if (!lastParsed) return;

    const prompt = pick(lastParsed, "Prompt", "prompt");
    const negative = pick(lastParsed, "Negative prompt", "negative_prompt", "Negative Prompt");
    const steps = pick(lastParsed, "Steps", "steps");
    const sampler = pick(lastParsed, "Sampler", "sampler_name", "sampler");
    const cfg = pick(lastParsed, "CFG scale", "cfg_scale");
    const seed = pick(lastParsed, "Seed", "seed");
    const size = pick(lastParsed, "Size", "size");

    if (prompt) document.getElementById("prompt").value = prompt;
    if (negative) document.getElementById("negative_prompt").value = negative;
    if (steps) {
      stepsInput.value = steps;
      stepsVal.textContent = steps;
    }
    if (cfg) {
      cfgInput.value = cfg;
      cfgVal.textContent = cfg;
    }
    if (seed) document.getElementById("seed").value = seed;

    if (size && typeof size === "string" && size.includes("x")) {
      const [w, h] = size.split("x").map((n) => n.trim());
      const widthSelect = document.getElementById("width");
      const heightSelect = document.getElementById("height");
      if ([...widthSelect.options].some((o) => o.value === w)) widthSelect.value = w;
      if ([...heightSelect.options].some((o) => o.value === h)) heightSelect.value = h;
    }

    if (sampler) {
      const opt = [...samplerSelect.options].find(
        (o) => o.value.toLowerCase() === String(sampler).toLowerCase()
      );
      if (opt) samplerSelect.value = opt.value;
    }

    showStatus("โหลดค่าจาก PNG Info มาใส่ในฟอร์มแล้ว เลื่อนขึ้นไปกด \"สร้างภาพ\" ได้เลย");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
});
