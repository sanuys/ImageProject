/* ============================================================
   PC1 : FRONTEND — main.js   (หน้า index.html)
   ------------------------------------------------------------
   เดิมไฟล์นี้อาศัย Jinja เรนเดอร์ประวัติภาพมาให้ตอนโหลดหน้า
   ตอนนี้หน้าเว็บเป็น static อยู่คนละเครื่องกับ Flask แล้ว
   จึงต้องดึงข้อมูลทุกอย่างผ่าน API ของ Backend (PC2) เอง
   ============================================================ */
document.addEventListener("DOMContentLoaded", async () => {
  // เช็คล็อกอินก่อน (แทน @login_required + redirect ของ Flask เดิม)
  const user = await requireLogin();
  if (!user) return;

  consumeFlash();

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
  //  Tabs: สร้างภาพ / แก้ไขภาพ
  // ============================================================
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");
  const VALID_TABS = ["generate", "edit"];

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

  function showStatus(message, isError = false) {
    statusBox.style.display = "block";
    statusBox.textContent = message;
    statusBox.classList.toggle("error", isError);
  }

  function hideStatus() {
    statusBox.style.display = "none";
  }

  // ============================================================
  //  โหลดประวัติของผู้ใช้จาก GET /api/history
  //  (เดิม Jinja เรนเดอร์ 3 จุดนี้มาให้: ประวัติสร้างภาพ,
  //   ตัวเลือก "เลือกจากภาพที่เคยสร้าง", ประวัติการแก้ไข)
  // ============================================================
  const editHistoryPicker = document.getElementById("edit-history-picker");
  const editHistoryGrid = document.getElementById("edit-history-grid");

  function renderGenerationHistory(items) {
    if (!items.length) {
      historyGrid.innerHTML = '<p class="placeholder-text">ยังไม่มีประวัติการสร้างภาพ</p>';
      editHistoryPicker.innerHTML =
        '<p class="placeholder-text">ยังไม่มีภาพที่เคยสร้างไว้ ลองสร้างภาพในแท็บ "สร้างภาพ" ก่อน</p>';
      return;
    }

    historyGrid.innerHTML = items
      .map(
        (it) => `
      <div class="history-item">
        <img src="${mediaUrl(it.image_url)}" alt="${escapeHtml(it.prompt)}">
        <p title="${escapeHtml(it.prompt)}">${escapeHtml(it.prompt)}</p>
        <p class="history-seed">Seed: ${escapeHtml(it.seed)}</p>
      </div>`
      )
      .join("");

    editHistoryPicker.innerHTML = items
      .map(
        (it) => `
      <img src="${mediaUrl(it.image_url)}" class="history-picker-item"
           data-id="${it.id}" title="${escapeHtml(it.prompt)}" alt="${escapeHtml(it.prompt)}">`
      )
      .join("");
  }

  function editItemHtml(it) {
    const paramsRow = it.params_summary
      ? `<p class="history-seed">${escapeHtml(it.params_summary)}</p>`
      : "";
    return `
      <div class="history-item">
        <img src="${mediaUrl(it.image_url)}" alt="${escapeHtml(it.operation_label)}">
        <p title="${escapeHtml(it.operation_label)}">${escapeHtml(it.operation_label)}</p>
        ${paramsRow}
        <button type="button" class="btn-danger edit-delete-btn" data-id="${it.id}">ลบ</button>
      </div>`;
  }

  function renderEditHistory(items) {
    editHistoryGrid.innerHTML = items.length
      ? items.map(editItemHtml).join("")
      : '<p class="placeholder-text">ยังไม่มีประวัติการแก้ไขภาพ</p>';
  }

  try {
    const hist = await apiJson("/api/history");
    renderGenerationHistory(hist.generations);
    renderEditHistory(hist.edits);
  } catch (err) {
    historyGrid.innerHTML = `<p class="placeholder-text">โหลดประวัติไม่สำเร็จ: ${escapeHtml(err.message)}</p>`;
  }

  // --- ลบรายการแก้ไขภาพ (เดิมเป็น form POST ไป Flask) ---
  editHistoryGrid.addEventListener("click", async (e) => {
    const delBtn = e.target.closest(".edit-delete-btn");
    if (!delBtn) return;
    if (!confirm("ลบรายการนี้ถาวร?")) return;

    delBtn.disabled = true;
    try {
      await apiJson(`/api/edit/delete/${delBtn.dataset.id}`, { method: "POST" });
      delBtn.closest(".history-item").remove();
      if (!editHistoryGrid.querySelector(".history-item")) {
        editHistoryGrid.innerHTML = '<p class="placeholder-text">ยังไม่มีประวัติการแก้ไขภาพ</p>';
      }
    } catch (err) {
      alert(err.message);
      delBtn.disabled = false;
    }
  });

  // ============================================================
  //  Checkpoint preset
  // ============================================================
  // ค่า fallback เผื่อ checkpoint ไหนไม่ได้กำหนด steps/cfg ไว้จากฝั่ง backend
  const DEFAULT_STEPS = "20";
  const DEFAULT_CFG = "7";

  // พอเลือก checkpoint ใหม่ (หรือหลังโหลด dropdown เสร็จครั้งแรก) ให้ปรับ sampler/ความละเอียด/
  // steps/cfg ตาม preset ของ checkpoint นั้น "ทุกครั้ง" ที่สลับ — ไม่ปล่อยให้ค้างค่าเดิม
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

    const steps = opt.dataset.steps || DEFAULT_STEPS;
    stepsInput.value = steps;
    stepsVal.textContent = steps;

    const cfg = opt.dataset.cfgScale || DEFAULT_CFG;
    cfgInput.value = cfg;
    cfgVal.textContent = cfg;
  }

  checkpointSelect.addEventListener("change", applyCheckpointPreset);

  // โหลด sampler ก่อน แล้วค่อยโหลด checkpoint ตาม เพื่อให้ dropdown sampler มีตัวเลือกครบ
  // ก่อนจะลองเซ็ต sampler ตาม preset ของ checkpoint ตัวแรก
  apiFetch("/api/samplers")
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
      apiFetch("/api/checkpoints")
        .then((r) => r.json())
        .then((checkpoints) => {
          if (!checkpoints || checkpoints.length === 0) {
            // ตั้งใจไม่ใส่ opt.disabled = true เพราะถ้า option เดียวใน <select> เป็น disabled
            // บางเบราว์เซอร์จะไม่แสดงข้อความอะไรเลย (กล่องว่างเปล่า งงว่าเกิดอะไรขึ้น)
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "⚠ โหลด checkpoint ไม่สำเร็จ — รีเฟรชหน้านี้อีกครั้ง";
            checkpointSelect.appendChild(opt);
            showStatus(
              "โหลดรายชื่อ checkpoint จาก AI Server (PC3) ไม่สำเร็จ ตรวจสอบว่า Stability Matrix / Forge " +
                "เปิดอยู่, ตั้ง --api ไว้แล้ว, และ FORGE_API_URL ใน pc2-backend/config.py ยังถูกต้อง แล้วรีเฟรชหน้านี้",
              true
            );
            return;
          }

          checkpoints.forEach((cp) => {
            const opt = document.createElement("option");
            opt.value = cp.title;
            opt.textContent = cp.model_name;
            // เก็บ preset ไว้กับตัว <option> เอง ให้ applyCheckpointPreset() หยิบไปเติมฟอร์ม
            opt.dataset.sampler = cp.sampler || "";
            opt.dataset.width = cp.width || "";
            opt.dataset.height = cp.height || "";
            opt.dataset.steps = cp.steps || "";
            opt.dataset.cfgScale = cp.cfg_scale || "";
            checkpointSelect.appendChild(opt);
          });

          applyCheckpointPreset();
        })
        .catch(() => {
          const opt = document.createElement("option");
          opt.value = "";
          opt.textContent = "⚠ โหลด checkpoint ไม่สำเร็จ — รีเฟรชหน้านี้อีกครั้ง";
          checkpointSelect.appendChild(opt);
          showStatus("เชื่อมต่อ Backend (PC2) ไม่ได้ ตรวจสอบว่าเครื่อง Backend ยังรันอยู่ แล้วรีเฟรชหน้านี้ใหม่", true);
        });
    });

  // ============================================================
  //  สร้างภาพ
  // ============================================================
  function prependHistory(imageUrl, prompt, seed, generationId) {
    const placeholder = historyGrid.querySelector(".placeholder-text");
    if (placeholder) placeholder.remove();

    const item = document.createElement("div");
    item.className = "history-item";
    item.innerHTML = `
      <img src="${imageUrl}" alt="${escapeHtml(prompt)}">
      <p title="${escapeHtml(prompt)}">${escapeHtml(prompt)}</p>
      <p class="history-seed">Seed: ${escapeHtml(seed)}</p>
    `;
    historyGrid.prepend(item);

    // เติมภาพนี้เข้า "เลือกจากภาพที่เคยสร้าง" ในแท็บแก้ไขภาพด้วย ไม่งั้นต้องรีเฟรชหน้าก่อน
    if (editHistoryPicker && generationId) {
      const pickerPlaceholder = editHistoryPicker.querySelector(".placeholder-text");
      if (pickerPlaceholder) pickerPlaceholder.remove();

      const img = document.createElement("img");
      img.src = imageUrl;
      img.className = "history-picker-item";
      img.dataset.id = generationId;
      img.title = prompt;
      img.alt = prompt;
      editHistoryPicker.prepend(img);
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
      const data = await apiJson("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const imgUrl = mediaUrl(data.image_url);
      resultArea.innerHTML = `
        <div class="result-wrap">
          <img src="${imgUrl}" alt="${escapeHtml(data.prompt)}">
          <div class="seed-row">
            <span>Seed ที่ใช้จริง: <strong>${escapeHtml(data.seed)}</strong></span>
            <button type="button" id="reuse-seed-btn" class="btn-small">ใช้ seed นี้อีกครั้ง</button>
          </div>
        </div>
      `;
      prependHistory(imgUrl, data.prompt, data.seed, data.id);
      hideStatus();

      const reuseBtn = document.getElementById("reuse-seed-btn");
      if (reuseBtn) {
        reuseBtn.addEventListener("click", () => {
          document.getElementById("seed").value = data.seed;
        });
      }
    } catch (err) {
      showStatus(err.message, true);
    } finally {
      btn.disabled = false;
      btn.textContent = "สร้างภาพ";
    }
  });

  // ============================================================
  //  แก้ไขภาพ: Point Operation / Auto Contrast / Linear Filter / Non-linear Filter
  // ============================================================
  const editSourceTabBtns = document.querySelectorAll(".source-tab-btn");
  const editSourcePanels = document.querySelectorAll(".edit-source-panel");
  const editDropzone = document.getElementById("edit-dropzone");
  const editFileInput = document.getElementById("edit-file");
  const editPreviewBox = document.getElementById("edit-preview-box");
  const editPreviewImg = document.getElementById("edit-preview-img");
  const editPreviewLabel = document.getElementById("edit-preview-label");
  const opBtns = document.querySelectorAll(".op-btn");
  const opParamsBoxes = document.querySelectorAll(".op-params");
  const editApplyBtn = document.getElementById("edit-apply-btn");
  const editStatusBox = document.getElementById("edit-status-box");
  const editResultArea = document.getElementById("edit-result-area");

  let editSourceMode = "upload"; // "upload" | "history"
  let editSelectedFile = null;
  let editSelectedGenerationId = null;
  let currentOp = "point_op";

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

  // --- แหล่งภาพ: เลือกจากประวัติที่เคยสร้าง ---
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

  // --- เลือกวิธีย่อยในแต่ละกลุ่ม: แสดงเฉพาะคำอธิบาย/ช่องตั้งค่าของวิธีที่เลือก ---
  //     (element ที่มี class method-fields ระบุวิธีที่ใช้ไว้ใน data-methods)
  function updateMethodFields(panel) {
    const method = panel.querySelector(".op-method").value;
    panel.querySelectorAll(".method-fields").forEach((el) => {
      el.style.display = el.dataset.methods.split(" ").includes(method) ? "" : "none";
    });
  }
  opParamsBoxes.forEach((panel) => {
    const select = panel.querySelector(".op-method");
    if (!select) return;
    select.addEventListener("change", () => updateMethodFields(panel));
    updateMethodFields(panel);
  });

  // --- แสดงตัวเลขข้าง slider ---
  document.querySelectorAll("#tab-edit input[type=range][data-param]").forEach((input) => {
    const out = document.querySelector(`[data-val-for="${input.id}"]`);
    if (out) input.addEventListener("input", () => (out.textContent = input.value));
  });

  // อ่านวิธี + ค่าตั้งค่าของกลุ่มที่เลือกอยู่ ใส่ลง formData (ส่งเฉพาะช่องที่แสดงอยู่)
  function collectOpParams(formData) {
    const panel = document.getElementById("op-params-" + currentOp);
    formData.append("method", panel.querySelector(".op-method").value);
    panel.querySelectorAll("[data-param]").forEach((el) => {
      const box = el.closest(".method-fields");
      if (box && box.style.display === "none") return;
      formData.append(el.dataset.param, el.value);
    });
  }

  function prependEditHistory(item) {
    const placeholder = editHistoryGrid.querySelector(".placeholder-text");
    if (placeholder) placeholder.remove();
    editHistoryGrid.insertAdjacentHTML("afterbegin", editItemHtml(item));
  }

  // --- กด "แปลงภาพ" ---
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
    collectOpParams(formData);

    editApplyBtn.disabled = true;
    editApplyBtn.textContent = "กำลังแปลงภาพ...";
    showEditStatus("กำลังประมวลผล...");

    try {
      const data = await apiJson("/api/edit", { method: "POST", body: formData });

      const paramsTag = data.params_summary ? `<span>${escapeHtml(data.params_summary)}</span>` : "";
      editResultArea.innerHTML = `
        <div class="result-wrap">
          <img src="${mediaUrl(data.image_url)}" alt="${escapeHtml(data.operation_label)}">
          <div class="seed-row">
            <span><strong>${escapeHtml(data.operation_label)}</strong></span>
            ${paramsTag}
          </div>
        </div>
      `;
      prependEditHistory(data);
      hideEditStatus();
    } catch (err) {
      showEditStatus(err.message, true);
    } finally {
      editApplyBtn.disabled = false;
      editApplyBtn.textContent = "แปลงภาพ";
    }
  });
});
