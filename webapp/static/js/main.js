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

  // ============================================================
  //  Tabs: สร้างภาพ / แก้ไขภาพ / PNG Info
  // ============================================================
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");
  const VALID_TABS = ["generate", "edit", "pnginfo"];

  function showTab(name) {
    if (!VALID_TABS.includes(name)) name = "generate";
    tabButtons.forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    tabPanels.forEach((p) => p.classList.toggle("active", p.id === "tab-" + name));
  }

  tabButtons.forEach((b) => {
    b.addEventListener("click", () => {
      showTab(b.dataset.tab);
      history.replaceState(null, "", "#" + b.dataset.tab);
    });
  });

  showTab((location.hash || "#generate").slice(1));

  // ค่า fallback เผื่อ checkpoint ไหนไม่ได้กำหนด steps/cfg ไว้จากฝั่ง backend (ไม่ควรเกิดขึ้นแล้ว
  // เพราะตอนนี้ตั้งไว้ครบทุกตัวใน ALLOWED_CHECKPOINTS แล้ว แต่กันไว้เผื่อเพิ่ม checkpoint ใหม่แล้วลืมใส่)
  const DEFAULT_STEPS = "20";
  const DEFAULT_CFG = "7";

  // พอเลือก checkpoint ใหม่ (หรือหลังโหลด dropdown เสร็จครั้งแรก) ให้ปรับ sampler/ความละเอียด/steps/cfg
  // ตาม preset ที่แนะนำของ checkpoint นั้น "ทุกครั้ง" ที่สลับ — ไม่ปล่อยให้ค้างค่าจาก checkpoint ก่อนหน้า
  function applyCheckpointPreset() {
    const opt = checkpointSelect.options[checkpointSelect.selectedIndex];
    if (!opt) return; // dropdown ยังไม่มีตัวเลือกเลย (เช่น กำลังโหลดอยู่)

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

    // เซ็ต steps/cfg แบบไม่มีเงื่อนไขทุกครั้งที่สลับ checkpoint (ใช้ค่า fallback ถ้า checkpoint
    // นั้นดันไม่ได้กำหนดไว้) เพื่อไม่ให้ค่าค้างจาก checkpoint ก่อนหน้าที่เพิ่งสลับออกไป
    const steps = opt.dataset.steps || DEFAULT_STEPS;
    stepsInput.value = steps;
    stepsVal.textContent = steps;

    const cfg = opt.dataset.cfgScale || DEFAULT_CFG;
    cfgInput.value = cfg;
    cfgVal.textContent = cfg;
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
            // หมายเหตุ: ตั้งใจไม่ใส่ opt.disabled = true เพราะถ้า option เดียวใน <select>
            // เป็น disabled บางเบราว์เซอร์จะปฏิเสธไม่แสดงข้อความอะไรเลย (กล่องว่างเปล่า งงว่าเกิดอะไรขึ้น)
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "⚠ โหลด checkpoint ไม่สำเร็จ — รีเฟรชหน้านี้อีกครั้ง";
            checkpointSelect.appendChild(opt);
            showStatus(
              "โหลดรายชื่อ checkpoint จาก AI Server ไม่สำเร็จ (ได้ผลลัพธ์ว่างเปล่า) " +
                "ตรวจสอบว่า Stability Matrix / Forge เปิดอยู่, ตั้ง --api ไว้แล้ว, และ IP/พอร์ตใน app.py ยังถูกต้อง จากนั้นรีเฟรชหน้านี้ใหม่",
              true
            );
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
            opt.dataset.steps = cp.steps || "";
            opt.dataset.cfgScale = cp.cfg_scale || "";
            checkpointSelect.appendChild(opt);
          });

          // checkpoint ตัวแรกในลิสต์ถูกเลือกเป็นค่าเริ่มต้นโดย browser อยู่แล้ว
          // เติม sampler/ความละเอียดให้ตรงกับ preset ของมันทันที ไม่ต้องรอผู้ใช้กดเปลี่ยนเอง
          applyCheckpointPreset();
        })
        .catch(() => {
          const opt = document.createElement("option");
          opt.value = "";
          opt.textContent = "⚠ โหลด checkpoint ไม่สำเร็จ — รีเฟรชหน้านี้อีกครั้ง";
          checkpointSelect.appendChild(opt);
          showStatus(
            "เชื่อมต่อเพื่อโหลดรายชื่อ checkpoint ไม่ได้ ตรวจสอบการเชื่อมต่อเครือข่ายหรือว่า Flask server ยังรันอยู่ แล้วรีเฟรชหน้านี้ใหม่",
            true
          );
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

  function prependHistory(imageUrl, prompt, seed, generationId) {
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

    // เติมภาพนี้เข้า "เลือกจากภาพที่เคยสร้าง" ในแท็บแก้ไขภาพด้วย ไม่งั้นต้องรีเฟรชหน้าก่อน
    // ถึงจะเอาภาพที่เพิ่งสร้างไปแก้ไขได้ (picker เดิมเรนเดอร์จาก server แค่ตอนโหลดหน้าครั้งแรก)
    const picker = document.getElementById("edit-history-picker");
    if (picker && generationId) {
      const pickerPlaceholder = picker.querySelector(".placeholder-text");
      if (pickerPlaceholder) pickerPlaceholder.remove();

      const img = document.createElement("img");
      img.src = imageUrl;
      img.className = "history-picker-item";
      img.dataset.id = generationId;
      img.title = prompt;
      img.alt = prompt;
      picker.prepend(img);
    }
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
      prependHistory(data.image_url, data.prompt, data.seed, data.id);
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

    showStatus("โหลดค่าจาก PNG Info มาใส่ในฟอร์มแล้ว กด \"สร้างภาพ\" ได้เลย");
    showTab("generate");
    history.replaceState(null, "", "#generate");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // ============================================================
  //  แก้ไขภาพ (Image Editing): Resize / Grayscale / Brightness-Contrast / Negative
  // ============================================================
  const editSourceTabBtns = document.querySelectorAll(".source-tab-btn");
  const editSourcePanels = document.querySelectorAll(".edit-source-panel");
  const editDropzone = document.getElementById("edit-dropzone");
  const editFileInput = document.getElementById("edit-file");
  const editHistoryPicker = document.getElementById("edit-history-picker");
  const editPreviewBox = document.getElementById("edit-preview-box");
  const editPreviewImg = document.getElementById("edit-preview-img");
  const editPreviewLabel = document.getElementById("edit-preview-label");
  const opBtns = document.querySelectorAll(".op-btn");
  const opParamsBoxes = document.querySelectorAll(".op-params");
  const editAlphaInput = document.getElementById("edit-alpha");
  const editAlphaVal = document.getElementById("edit-alpha-val");
  const editBetaInput = document.getElementById("edit-beta");
  const editBetaVal = document.getElementById("edit-beta-val");
  const editApplyBtn = document.getElementById("edit-apply-btn");
  const editStatusBox = document.getElementById("edit-status-box");
  const editResultArea = document.getElementById("edit-result-area");
  const editHistoryGrid = document.getElementById("edit-history-grid");

  let editSourceMode = "upload"; // "upload" | "history"
  let editSelectedFile = null;
  let editSelectedGenerationId = null;
  let currentOp = "resize";

  // สลับระหว่าง "อัปโหลดภาพ" กับ "เลือกจากภาพที่เคยสร้าง"
  editSourceTabBtns.forEach((b) => {
    b.addEventListener("click", () => {
      editSourceMode = b.dataset.source;
      editSourceTabBtns.forEach((x) => x.classList.toggle("active", x === b));
      editSourcePanels.forEach((p) =>
        p.classList.toggle("active", p.id === "edit-source-" + editSourceMode)
      );
    });
  });

  function showEditStatus(message, isError = false) {
    editStatusBox.style.display = "block";
    editStatusBox.textContent = message;
    editStatusBox.classList.toggle("error", isError);
  }
  function hideEditStatus() {
    editStatusBox.style.display = "none";
  }

  function setEditPreview(src, label) {
    editPreviewImg.src = src;
    editPreviewLabel.textContent = label || "";
    editPreviewBox.style.display = "block";
  }

  // --- แหล่งภาพ: อัปโหลดเอง ---
  if (editDropzone) {
    editDropzone.addEventListener("click", () => editFileInput.click());
    editFileInput.addEventListener("change", () => {
      const file = editFileInput.files[0];
      if (!file) return;
      editSelectedFile = file;
      editSelectedGenerationId = null;
      setEditPreview(URL.createObjectURL(file), `อัปโหลด: ${file.name}`);
    });
    ["dragover", "dragenter"].forEach((evt) =>
      editDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        editDropzone.classList.add("dropzone-active");
      })
    );
    ["dragleave", "drop"].forEach((evt) =>
      editDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        editDropzone.classList.remove("dropzone-active");
      })
    );
    editDropzone.addEventListener("drop", (e) => {
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      if (!file) return;
      editSelectedFile = file;
      editSelectedGenerationId = null;
      setEditPreview(URL.createObjectURL(file), `อัปโหลด: ${file.name}`);
    });
  }

  // --- แหล่งภาพ: เลือกจากประวัติที่เคยสร้าง ---
  if (editHistoryPicker) {
    editHistoryPicker.addEventListener("click", (e) => {
      const img = e.target.closest(".history-picker-item");
      if (!img) return;
      editSelectedGenerationId = img.dataset.id;
      editSelectedFile = null;
      editHistoryPicker
        .querySelectorAll(".history-picker-item")
        .forEach((el) => el.classList.toggle("selected", el === img));
      setEditPreview(img.src, img.title ? `ภาพที่สร้างไว้: ${img.title}` : "ภาพที่เลือกจากประวัติ");
    });
  }

  // --- เลือกฟังก์ชันแก้ไข ---
  opBtns.forEach((b) => {
    b.addEventListener("click", () => {
      currentOp = b.dataset.op;
      opBtns.forEach((x) => x.classList.toggle("active", x === b));
      opParamsBoxes.forEach((p) => {
        p.style.display = p.id === "op-params-" + currentOp ? "" : "none";
      });
    });
  });

  if (editAlphaInput) {
    editAlphaInput.addEventListener("input", () => (editAlphaVal.textContent = editAlphaInput.value));
  }
  if (editBetaInput) {
    editBetaInput.addEventListener("input", () => (editBetaVal.textContent = editBetaInput.value));
  }

  function prependEditHistory(imageUrl, operationLabel, paramsSummary, recordId) {
    if (!editHistoryGrid) return;
    const placeholder = editHistoryGrid.querySelector(".placeholder-text");
    if (placeholder) placeholder.remove();

    const item = document.createElement("div");
    item.className = "history-item";
    item.innerHTML = `
      <img src="${imageUrl}" alt="${operationLabel}">
      <p title="${operationLabel}">${operationLabel}</p>
      ${paramsSummary ? `<p class="history-seed">${paramsSummary}</p>` : ""}
      <form method="POST" action="/edit/delete/${recordId}" class="admin-delete-form"
            onsubmit="return confirm('ลบรายการนี้ถาวร?');">
        <button type="submit" class="btn-danger">ลบ</button>
      </form>
    `;
    editHistoryGrid.prepend(item);
  }

  // --- กด "แปลงภาพ" ---
  if (editApplyBtn) {
    editApplyBtn.addEventListener("click", async () => {
      if (editSourceMode === "upload" && !editSelectedFile) {
        showEditStatus("กรุณาเลือกไฟล์ภาพที่จะอัปโหลดก่อน", true);
        return;
      }
      if (editSourceMode === "history" && !editSelectedGenerationId) {
        showEditStatus("กรุณาเลือกภาพจากประวัติก่อน", true);
        return;
      }

      const formData = new FormData();
      formData.append("operation", currentOp);
      if (editSourceMode === "upload") {
        formData.append("image", editSelectedFile);
      } else {
        formData.append("generation_id", editSelectedGenerationId);
      }
      if (currentOp === "resize") {
        formData.append("width", document.getElementById("edit-width").value);
        formData.append("height", document.getElementById("edit-height").value);
      } else if (currentOp === "brightness_contrast") {
        formData.append("alpha", editAlphaInput.value);
        formData.append("beta", editBetaInput.value);
      }

      editApplyBtn.disabled = true;
      editApplyBtn.textContent = "กำลังแปลงภาพ...";
      showEditStatus("กำลังประมวลผล...");

      try {
        const res = await fetch("/api/edit", { method: "POST", body: formData });
        const data = await res.json();

        if (!res.ok) {
          showEditStatus(data.error || "แก้ไขภาพไม่สำเร็จ", true);
          return;
        }

        editResultArea.innerHTML = `
          <div class="result-wrap">
            <img src="${data.image_url}" alt="${data.operation_label}">
            <div class="seed-row">
              <span><strong>${data.operation_label}</strong></span>
              ${data.params_summary ? `<span>${data.params_summary}</span>` : ""}
            </div>
          </div>
        `;
        prependEditHistory(data.image_url, data.operation_label, data.params_summary, data.id);
        hideEditStatus();
      } catch (err) {
        showEditStatus("เชื่อมต่อ server ไม่ได้: " + err.message, true);
      } finally {
        editApplyBtn.disabled = false;
        editApplyBtn.textContent = "แปลงภาพ";
      }
    });
  }
});
