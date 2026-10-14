/* ============================================================
   PC1 : FRONTEND — main.js   (หน้า index.html)
   ------------------------------------------------------------
   เดิมไฟล์นี้อาศัย Jinja เรนเดอร์ประวัติภาพมาให้ตอนโหลดหน้า
   ตอนนี้หน้าเว็บเป็น static อยู่คนละเครื่องกับ Flask แล้ว
   จึงต้องดึงข้อมูลทุกอย่างผ่าน API ของ Backend (PC2) เอง
   ============================================================ */
document.addEventListener("DOMContentLoaded", async () => { //รอให้ HTML โหลดเสร็จก่อนค่อยรันโค้ด
  // เช็คล็อกอินก่อน (แทน @login_required + redirect ของ Flask เดิม)
  const user = await requireLogin(); //เรียกฟังก์ชันเช็คล็อกอินแล้ว รอผล (เพราะต้องถาม Backend ผ่านเครือข่าย)
  if (!user) return; //ถ้าไม่ได้ผู้ใช้กลับมา (ยังไม่ล็อกอิน หรือติดต่อ Backend ไม่ได้) ให้หยุดทำงานทันที ไม่โหลดข้อมูลหน้าหลักต่อ

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

  function renderGenerationHistory(items) { //เติมประวัติสร้างภาพลงใน historyGrid และ editHistoryPicker
    if (!items.length) { //ถ้าไม่มีประวัติการสร้างภาพเลย ให้แสดงข้อความ placeholder แทน
      historyGrid.innerHTML = '<p class="placeholder-text">ยังไม่มีประวัติการสร้างภาพ</p>'; //เติมข้อความ placeholder ลงใน historyGrid
      editHistoryPicker.innerHTML = 
        '<p class="placeholder-text">ยังไม่มีภาพที่เคยสร้างไว้ ลองสร้างภาพในแท็บ "สร้างภาพ" ก่อน</p>'; //เติมข้อความ placeholder ลงใน editHistoryPicker
      return;
    }

    historyGrid.innerHTML = items
      .map( //วนทุกรายการใน items แปลงแต่ละอันเป็นสตริง HTML 1 ก้อน (it = item ตัวนั้น) ได้ผลเป็นอาร์เรย์ของสตริง
        (it) => `
      <div class="history-item">
        <img src="${mediaUrl(it.image_url)}" alt="${escapeHtml(it.prompt)}"> //แสดงภาพที่สร้างแล้ว โดย mediaUrl() แปลง URL ของ Backend (PC2) ให้เป็น URL ของ Nginx (PC1) และคำสั่ง alt คือ ข้อความทดแทนเมื่อรูปไม่โหลด (ปลายบรรทัดถูกตัดในรูป)
        <p title="${escapeHtml(it.prompt)}">${escapeHtml(it.prompt)}</p> //แสดง prompt ส่วน title ทำให้เอาเมาส์ชี้แล้วเห็น prompt เต็มเมื่อข้อความโดนตัดด้วย CSS
        <p class="history-seed">Seed: ${escapeHtml(it.seed)}</p> //เลข seed ของการสร้างภาพ (ค่าที่ใช้สุ่ม ถ้าใช้ seed เดิมกับ prompt เดิมจะได้ภาพเดิม)
      </div>`
      )
      .join(""); //.join("") ต่อสตริงทั้งหมดเข้าด้วยกัน คั่นด้วยสตริงว่าง ถ้าไม่ใส่ join อาร์เรย์จะถูกแปลงเป็นข้อความที่มีเครื่องหมาย , คั่นแทรกอยู่ในหน้า

    editHistoryPicker.innerHTML = items 
      .map(
        (it) => `
      <img src="${mediaUrl(it.image_url)}" class="history-picker-item" //แสดงภาพที่เคยสร้างแล้วในแท็บแก้ไขภาพ
           data-id="${it.id}" title="${escapeHtml(it.prompt)}" alt="${escapeHtml(it.prompt)}">` //เก็บ id ของ generation ไว้ใน data-id เพื่อให้ผู้ใช้เลือกภาพนี้ไปแก้ไขต่อได้
      )
      .join(""); //ต่อสตริงทั้งหมดเข้าด้วยกัน คั่นด้วยสตริงว่าง ถ้าไม่ใส่ join อาร์เรย์จะถูกแปลงเป็นข้อความที่มีเครื่องหมาย , คั่นแทรกอยู่ในหน้า
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
    const hist = await apiJson("/api/history"); //เรียก GET /api/history ของ Backend (PC2) เพื่อดึงประวัติของผู้ใช้ปัจจุบัน
    renderGenerationHistory(hist.generations); //เติมประวัติสร้างภาพลงใน historyGrid
    renderEditHistory(hist.edits); //เติมประวัติแก้ไขภาพลงใน editHistoryGrid
  } catch (err) { //ถ้าเกิด error (เช่น ติดต่อ Backend ไม่ได้) ให้แสดงข้อความใน historyGrid แทน
    historyGrid.innerHTML = `<p class="placeholder-text">โหลดประวัติไม่สำเร็จ: ${escapeHtml(err.message)}</p>`; //เติมข้อความ error ลงใน historyGrid
  }

  // --- ลบรายการแก้ไขภาพ (เดิมเป็น form POST ไป Flask) ---
  editHistoryGrid.addEventListener("click", async (e) => { //เมื่อผู้ใช้คลิกที่ปุ่มลบใน editHistoryGrid ให้ทำงานฟังก์ชันนี้
    const delBtn = e.target.closest(".edit-delete-btn"); //หา element ที่เป็นปุ่มลบ (class="edit-delete-btn") ที่อยู่ใกล้กับ element ที่ผู้ใช้คลิกที่สุด (e.target) ถ้าไม่มีปุ่มลบอยู่ใกล้ก็ return null
    if (!delBtn) return; //ถ้าไม่ได้คลิกที่ปุ่มลบ ให้ return ออกจากฟังก์ชัน ไม่ทำอะไร
    if (!confirm("ลบรายการนี้ถาวร?")) return; //ถามผู้ใช้ยืนยันการลบ ถ้าไม่ยืนยันก็ return ออกจากฟังก์ชัน ไม่ทำอะไร

    delBtn.disabled = true; //ปิดปุ่มลบชั่วคราว เพื่อป้องกันผู้ใช้กดซ้ำหลายครั้ง (เพราะต้องรอให้ Backend ลบเสร็จ)
    try {
      await apiJson(`/api/edit/delete/${delBtn.dataset.id}`, { method: "POST" }); //เรียก POST /api/edit/delete/<id> ของ Backend (PC2) เพื่อให้ลบรายการแก้ไขภาพนั้น (id เก็บใน data-id ของปุ่มลบ)
      delBtn.closest(".history-item").remove(); //ลบ element ของรายการแก้ไขภาพนั้นออกจาก DOM (ไม่ต้องโหลดหน้าใหม่)
      if (!editHistoryGrid.querySelector(".history-item")) {  //ถ้าไม่มีรายการแก้ไขภาพเหลืออยู่ใน editHistoryGrid ให้แสดงข้อความ placeholder แทน
        editHistoryGrid.innerHTML = '<p class="placeholder-text">ยังไม่มีประวัติการแก้ไขภาพ</p>'; //เติมข้อความ placeholder ลงใน editHistoryGrid
      }
    } catch (err) { //ถ้าเกิด error (เช่น ติดต่อ Backend ไม่ได้) ให้แสดงข้อความ alert แทน
      alert(err.message); //แสดงข้อความ error ใน alert ของเบราว์เซอร์ (ไม่ใช่ในหน้าเว็บ)
      delBtn.disabled = false; //เปิดปุ่มลบกลับมาให้ผู้ใช้กดใหม่ (เพราะลบไม่สำเร็จ)
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

  function applyCheckpointPreset() { //ฟังก์ชันสำหรับปรับ sampler/ความละเอียด/steps/cfg ตาม preset ของ checkpoint ที่เลือกอยู่
    const opt = checkpointSelect.options[checkpointSelect.selectedIndex];//options คือรายการ <option> ทั้งหมด, selectedIndex คือลำดับที่เลือกอยู่
    if (!opt) return; // dropdown ยังไม่มีตัวเลือกเลย (เช่น กำลังโหลดอยู่)

    const samplerOpt = [...samplerSelect.options].find((o) => o.value === opt.dataset.sampler); //แปลง options (ที่ไม่ใช่อาร์เรย์จริง) เป็นอาร์เรย์ เพื่อใช้ .find ได้
    if (samplerOpt) samplerSelect.value = opt.dataset.sampler; //เฉพาะเมื่อเจอ เพราะถ้าตั้งค่าที่ไม่มีใน dropdown ช่องจะกลายเป็นว่างเปล่า (เหมือนกรณีโหลด sampler ไม่สำเร็จ ก็ยังคงค่า default ไว้ได้)

    const widthSelect = document.getElementById("width"); //ดึงช่อง width/height มา (เป็น dropdown เช่นกัน เพราะมี .options)
    const heightSelect = document.getElementById("height"); //ดึงช่อง width/height มา (เป็น dropdown เช่นกัน เพราะมี .options)
    if (opt.dataset.width && [...widthSelect.options].some((o) => o.value === opt.dataset.width)) {
      widthSelect.value = opt.dataset.width;
    }
    /* opt.dataset.width ไม่ว่าง (preset กำหนดค่ามา จำได้ว่าตอนเก็บใช้ || "")
      .some(...) มี option ใน dropdown ที่ค่าตรงกัน (ท้ายบรรทัดถูกตัด คาดว่าเทียบกับ opt.dataset.width)*/
    if (opt.dataset.height && [...heightSelect.options].some((o) => o.value === opt.dataset.height)) {
      heightSelect.value = opt.dataset.height;
    }

    const steps = opt.dataset.steps || DEFAULT_STEPS; //ใช้ค่าจาก preset ถ้าว่างใช้ค่า DEFAULT_STEPS (ค่าคงที่ที่ประกาศไว้ที่อื่น)
    stepsInput.value = steps; //ตั้งสองที่: stepsInput.value คือตัวช่อง
    stepsVal.textContent = steps; //คือข้อความตัวเลขที่แสดงข้างๆ เพราะการเปลี่ยน .value ด้วยโค้ด ไม่ทำให้ข้อความที่แสดงเปลี่ยนตาม ต้องอัปเดตเอง

    const cfg = opt.dataset.cfgScale || DEFAULT_CFG; //แบบเดียวกับ steps ทุกอย่าง ใช้ dataset.cfgScale (ชื่อที่ตั้งไว้ตอนสร้าง option) และ DEFAULT_CFG เป็นค่าสำรอง
    cfgInput.value = cfg;
    cfgVal.textContent = cfg;
  }

  checkpointSelect.addEventListener("change", applyCheckpointPreset); //เมื่อผู้ใช้เลือก checkpoint ใหม่ event change จะเรียกฟังก์ชันนี้ให้อัตโนมัติ ส่งชื่อฟังก์ชันไปเฉยๆ ไม่ใส่ () เพราะต้องการ "ส่งฟังก์ชันไปให้เรียกทีหลัง" ไม่ใช่เรียกตอนนี้ (เมื่อต้นทางบรรทัด 229 เรียกด้วย () เพื่อใช้ทันทีหลังโหลดเสร็จ)

  // โหลด sampler ก่อน แล้วค่อยโหลด checkpoint ตาม เพื่อให้ dropdown sampler มีตัวเลือกครบ
  // ก่อนจะลองเซ็ต sampler ตาม preset ของ checkpoint ตัวแรก
  apiFetch("/api/samplers") //คืน response ดิบ (ตามที่อธิบายไปแล้ว) ไม่ได้แปลง JSON ให้ จึงต้องทำเองด้วย r.json()
    .then((r) => r.json()) //.then() ตัวแรกคืนผลของ r.json() ส่งต่อให้ .then() ตัวถัดไป
    .then((names) => { //names คืออาร์เรย์ชื่อ sampler ที่ Backend ส่งมา เป็น ["Euler a", "DPM++ 2M", ...]
      samplerSelect.innerHTML = ""; //ล้างตัวเลือกเดิมทิ้ง (รวมค่า default ที่เขียนไว้ใน HTML)
      names.forEach((name) => { //วนทุกรายชื่อ sampler ที่ได้จาก Backend สร้าง <option> ใหม่แล้วเติมลงใน <select>
        const opt = document.createElement("option"); //สร้างแท็ก <option> ใหม่
        opt.value = name; //กำหนด value ของ <option> เป็นชื่อ sampler
        opt.textContent = name; //กำหนดข้อความที่แสดงใน dropdown เป็นชื่อ sampler
        samplerSelect.appendChild(opt); //เติม <option> ที่สร้างใหม่ลงใน <select id="sampler">
      });
    })
    .catch(() => {
      // เงียบไว้ ใช้ค่า default "Euler a" ที่มีอยู่แล้วในหน้า
    })
    .finally(() => { //ทำทุกกรณี ไม่ว่า samplers จะสำเร็จหรือพั
      apiFetch("/api/checkpoints")//เรียก GET /api/checkpoints ของ Backend (PC2) เพื่อดึงรายชื่อ checkpoint preset
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

          checkpoints.forEach((cp) => { //วนทุกรายการ checkpoint preset ที่ Backend ส่งมา สร้าง <option> ใหม่แล้วเติมลงใน <select>
            const opt = document.createElement("option");
            opt.value = cp.title; //คืออาร์เรย์ของ object แต่ละตัว (cp) เป็นข้อมูลของโมเดลหนึ่งตัว
            opt.textContent = cp.model_name; //ข้อความที่แสดงใน dropdown เป็นชื่อโมเดล (เช่น "Stable Diffusion 1.5")
            // เก็บ preset ไว้กับตัว <option> เอง ให้ applyCheckpointPreset() หยิบไปเติมฟอร์ม
            opt.dataset.sampler = cp.sampler || "";
            opt.dataset.width = cp.width || "";
            opt.dataset.height = cp.height || "";
            opt.dataset.steps = cp.steps || "";
            opt.dataset.cfgScale = cp.cfg_scale || "";
            checkpointSelect.appendChild(opt);
          });
          /*ค่าที่เก็บ: ค่าแนะนำของโมเดลนั้น ได้แก่ sampler, ขนาดภาพ (กว้าง/สูง), 
          จำนวน steps และ CFG scale (ค่าที่บอกว่าให้ภาพทำตาม prompt เข้มงวดแค่ไหน) 
          โมเดลแต่ละตัวให้ภาพดีที่สุดกับค่าไม่เหมือนกัน
          || "": ถ้าโมเดลนั้นไม่ได้กำหนดค่าไหน (เป็น undefined/null/0) ให้เก็บสตริงว่างแทน ถ้าไม่ใส่ dataset.steps = undefined จะกลายเป็นข้อความ "undefined" จริงๆ*/

          applyCheckpointPreset(); //เรียกฟังก์ชันที่ (ตามคอมเมนต์) หยิบค่า preset จาก option ที่เลือกอยู่ไปเติม
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

  form.addEventListener("submit", async (e) => { //เมื่อผู้ใช้กดปุ่ม "สร้างภาพ" หรือกด Enter ในฟอร์ม
    e.preventDefault(); //ป้องกันไม่ให้ฟอร์มส่งค่าไปที่เซิร์ฟเวอร์แบบเดิม (reload หน้า) เพราะเราจะส่งผ่าน fetch เอง

    const payload = {
      prompt: document.getElementById("prompt").value, //ข้อความ prompt ที่ผู้ใช้พิมพ์
      negative_prompt: document.getElementById("negative_prompt").value, //ข้อความ negative prompt ที่ผู้ใช้พิมพ์
      steps: Number(stepsInput.value), //จำนวน steps ที่ผู้ใช้เลือก (แปลงเป็นตัวเลขด้วย Number() เพราะ .value เป็นสตริง)
      cfg_scale: Number(cfgInput.value), //ค่า CFG scale ที่ผู้ใช้เลือก (แปลงเป็นตัวเลขด้วย Number() เพราะ .value เป็นสตริง)
      width: Number(document.getElementById("width").value),//ความกว้างภาพที่ผู้ใช้เลือก (แปลงเป็นตัวเลขด้วย Number() เพราะ .value เป็นสตริง)
      height: Number(document.getElementById("height").value),//ความสูงภาพที่ผู้ใช้เลือก (แปลงเป็นตัวเลขด้วย Number() เพราะ .value เป็นสตริง)
      sampler: samplerSelect.value,//วิธีสุ่ม (เช่น Euler a)
      seed: Number(document.getElementById("seed").value),//ลขสุ่มตั้งต้น ค่าเดิม + prompt เดิม = ภาพเดิม
      checkpoint: checkpointSelect.value,//โมเดลที่ใช้สร้างภาพ
    };

    btn.disabled = true; //ปิดปุ่ม กันกดซ้ำ
    btn.textContent = "กำลังสร้างภาพ...";  //เปลี่ยนข้อความบนปุ่มให้เห็นว่ากำลังทำงาน (ต่างจากฟอร์มล็อกอินที่แค่ปิดปุ่ม)
    showStatus("กำลังส่งคำขอไปที่ AI Server กรุณารอสักครู่ (อาจใช้เวลาหลายสิบวินาที)..."); //สดงข้อความสถานะบนหน้า ที่บอกว่าอาจใช้เวลาหลายสิบวินาที ซึ่งเชื่อมกับ timeout 10 นาทีของ Nginx

    try {
      const data = await apiJson("/api/generate", { //โครงสร้างเหมือน login/register เป๊ะ ต่างแค่ endpoint
        method: "POST",
        headers: { "Content-Type": "application/json" },//แปลง object เป็นข้อความ JSON ใส่ใน body
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
  editSourceTabBtns.forEach((b) => { //editSourceTabBtns คือกลุ่มปุ่มแท็บ (น่าจะได้จาก querySelectorAll) วนทีละปุ่ม b แล้วผูก click ให้แต่ละปุ่ม
    b.addEventListener("click", () => {
      editSourceMode = b.dataset.source; //อ่านค่า data-source ของปุ่มที่ถูกคลิก เก็บในตัวแปร editSourceMode (ตัวแปรนี้ประกาศไว้นอกฟังก์ชัน ต้องเป็น let) ตอนกดปุ่ม "แก้ไขภาพ" โค้ดส่วนอื่นจะอ่านตัวแปรนี้เพื่อรู้ว่าต้องใช้ภาพจากประวัติหรือไฟล์อัปโหลด
      editSourceTabBtns.forEach((x) => x.classList.toggle("active", x === b)); //วนทุกรายการปุ่มแท็บ (x) แล้วสลับ class "active" ให้ปุ่มที่ถูกคลิก (b) เป็น active ส่วนปุ่มอื่นไม่ active
      editSourcePanels.forEach((p) => //วนทุกรายการ panel (p) แล้วสลับ class "active" ให้ panel ที่ตรงกับ editSourceMode เป็น active ส่วน panel อื่นไม่ active
        p.classList.toggle("active", p.id === "edit-source-" + editSourceMode) //หลักการเดียวกัน แต่เทียบ id ของแผงกับชื่อที่ประกอบจาก "edit-source-" + editSourceMode เช่น กดแท็บ history → แผงที่ id="edit-source-history" ได้ active แผงอื่นถูกถอด
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
  editDropzone.addEventListener("click", () => editFileInput.click()); //เมื่อคลิก dropzone ให้เปิด file input (ซ่อนอยู่) เพื่อเลือกไฟล์
  editFileInput.addEventListener("change", () => { //เมื่อผู้ใช้เลือกไฟล์แล้ว (change event ของ input type=file) ให้ทำงานฟังก์ชันนี้
    const file = editFileInput.files[0]; //ดึงไฟล์ที่ผู้ใช้เลือกมา (files เป็นอาร์เรย์ของไฟล์ แต่เราสนใจแค่ไฟล์แรก)
    if (!file) return; //ถ้าไม่มีไฟล์ (ผู้ใช้กด cancel) ให้ return ออกจากฟังก์ชัน
    editSelectedFile = file; //เก็บไฟล์ที่เลือกไว้ในตัวแปร editSelectedFile (ประกาศไว้ข้างบน) เพื่อใช้ตอนส่งไปแก้ไขภาพ
    editSelectedGenerationId = null; //ถ้าเลือกไฟล์ใหม่ ให้ล้างค่า generation_id ที่เคยเลือกจากประวัติออก (เพราะตอนนี้ใช้ไฟล์อัปโหลดแทน)
    setEditPreview(URL.createObjectURL(file), `อัปโหลด: ${file.name}`); //สร้าง URL ชั่วคราวจากไฟล์ที่เลือก (URL.createObjectURL) แล้วเรียก setEditPreview() เพื่อแสดงภาพตัวอย่างและชื่อไฟล์
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
  editHistoryPicker.addEventListener("click", (e) => { //เมื่อผู้ใช้คลิกที่ภาพใน editHistoryPicker (แท็บ "เลือกจากภาพที่เคยสร้าง") ให้ทำงานฟังก์ชันนี้
    const img = e.target.closest(".history-picker-item"); //ตรวจสอบว่าผู้ใช้คลิกที่ element ที่มี class "history-picker-item" หรือไม่ (คือภาพที่แสดงใน editHistoryPicker) ถ้าไม่ใช่ return ออกไป
    if (!img) return; //ถ้าไม่ใช่ภาพที่ต้องการ ให้ return ออกจากฟังก์ชัน
    editSelectedGenerationId = img.dataset.id; //เก็บ generation_id ของภาพที่เลือกไว้ในตัวแปร editSelectedGenerationId (ประกาศไว้ข้างบน) เพื่อใช้ตอนส่งไปแก้ไขภาพ
    editSelectedFile = null; //ถ้าเลือกภาพจากประวัติ ให้ล้างค่าไฟล์อัปโหลดออก (เพราะตอนนี้ใช้ภาพจากประวัติแทน)
    editHistoryPicker 
      .querySelectorAll(".history-picker-item") //ดึง element ทั้งหมดที่มี class "history-picker-item" (คือภาพทั้งหมดใน editHistoryPicker) แล้ววนทีละตัว
      .forEach((el) => el.classList.toggle("selected", el === img)); //สลับ class "selected" ให้กับ element ที่ถูกคลิก (img) ส่วน element อื่นๆ จะถูกถอด class "selected" ออก
    setEditPreview(img.src, img.title ? `ภาพที่สร้างไว้: ${img.title}` : "ภาพที่เลือกจากประวัติ"); //เรียก setEditPreview() เพื่อแสดงภาพตัวอย่างและข้อความบอกว่าเป็นภาพจากประวัติ
  });

  // --- เลือกฟังก์ชันแก้ไข ---
  opBtns.forEach((b) => { //วนทุกรายการปุ่มฟังก์ชันแก้ไข (opBtns) แล้วผูก click ให้แต่ละปุ่ม
    b.addEventListener("click", () => { //เมื่อผู้ใช้คลิกที่ปุ่มฟังก์ชันแก้ไข ให้ทำงานฟังก์ชันนี้
      currentOp = b.dataset.op; //อ่านค่า data-op ของปุ่มที่ถูกคลิก เก็บในตัวแปร currentOp (ประกาศไว้ข้างบน) เพื่อใช้ตอนส่งไปแก้ไขภาพ
      opBtns.forEach((x) => x.classList.toggle("active", x === b)); //วนทุกรายการปุ่มฟังก์ชันแก้ไข (x) แล้วสลับ class "active" ให้ปุ่มที่ถูกคลิก (b) เป็น active ส่วนปุ่มอื่นไม่ active
      opParamsBoxes.forEach((p) => { //วนทุกรายการกล่องตั้งค่าฟังก์ชันแก้ไข (p) แล้วสลับการแสดงผลให้กล่องที่ตรงกับ currentOp เป็น visible ส่วนกล่องอื่นซ่อน
        p.style.display = p.id === "op-params-" + currentOp ? "" : "none"; //หลักการเดียวกัน แต่เทียบ id ของกล่องกับชื่อที่ประกอบจาก "op-params-" + currentOp เช่น กดปุ่ม point_op → กล่องที่ id="op-params-point_op" ได้ visible ส่วนกล่องอื่นถูกซ่อน
      });
    });
  });

  // --- เลือกวิธีย่อยในแต่ละกลุ่ม: แสดงเฉพาะคำอธิบาย/ช่องตั้งค่าของวิธีที่เลือก ---
  //     (element ที่มี class method-fields ระบุวิธีที่ใช้ไว้ใน data-methods)
  function updateMethodFields(panel) { //ฟังก์ชันนี้ใช้สำหรับอัปเดตการแสดงผลของกล่องตั้งค่าฟังก์ชันแก้ไข (panel) ให้แสดงเฉพาะคำอธิบาย/ช่องตั้งค่าของวิธีย่อยที่ถูกเลือกใน dropdown (select) ของ panel นั้น
    const method = panel.querySelector(".op-method").value; //ดึงค่าของ select ที่มี class "op-method" ใน panel นั้น (คือวิธีย่อยที่ถูกเลือก) เก็บในตัวแปร method
    panel.querySelectorAll(".method-fields").forEach((el) => { //วนทุกรายการ element ที่มี class "method-fields" ใน panel นั้น (คือคำอธิบาย/ช่องตั้งค่าของวิธีย่อยทั้งหมด) แล้วตรวจสอบว่า element นั้นควรแสดงหรือซ่อน
      el.style.display = el.dataset.methods.split(" ").includes(method) ? "" : "none"; //หลักการคือ: ถ้า data-methods ของ element นั้น (เป็นสตริงที่มีชื่อวิธีหลายชื่อคั่นด้วย space) มีชื่อวิธีที่ถูกเลือก (method) ให้แสดง (style.display = "") ส่วน element อื่นๆ ให้ซ่อน (style.display = "none")
    });
  }
  opParamsBoxes.forEach((panel) => { //วนทุกรายการกล่องตั้งค่าฟังก์ชันแก้ไข (panel) แล้วผูก change ให้ select ของ panel นั้น
    const select = panel.querySelector(".op-method"); //ดึง select ที่มี class "op-method" ใน panel นั้น (คือ dropdown ของวิธีย่อย) เก็บในตัวแปร select
    if (!select) return; //ถ้า panel นั้นไม่มี select ให้ return ออกจากฟังก์ชัน (ไม่ทำอะไร)
    select.addEventListener("change", () => updateMethodFields(panel)); //เมื่อผู้ใช้เปลี่ยนวิธีย่อยใน select ให้เรียกฟังก์ชัน updateMethodFields(panel) เพื่ออัปเดตการแสดงผลของคำอธิบาย/ช่องตั้งค่าของวิธีย่อยที่ถูกเลือก
    updateMethodFields(panel); //เรียกฟังก์ชัน updateMethodFields(panel) ทันทีหลังโหลดหน้า เพื่อให้แสดงคำอธิบาย/ช่องตั้งค่าของวิธีย่อยที่ถูกเลือกเป็นค่าเริ่มต้น
  });

  // --- แสดงตัวเลขข้าง slider ---
  document.querySelectorAll("#tab-edit input[type=range][data-param]").forEach((input) => {
    const out = document.querySelector(`[data-val-for="${input.id}"]`);
    if (out) input.addEventListener("input", () => (out.textContent = input.value));
  });

  // อ่านวิธี + ค่าตั้งค่าของกลุ่มที่เลือกอยู่ ใส่ลง formData (ส่งเฉพาะช่องที่แสดงอยู่)
  function collectOpParams(formData) { //ฟังก์ชันนี้ใช้สำหรับอ่านวิธี + ค่าตั้งค่าของกลุ่มที่เลือกอยู่ (currentOp) แล้วใส่ลงใน formData (ส่งเฉพาะช่องที่แสดงอยู่)
    const panel = document.getElementById("op-params-" + currentOp); //ประกอบ id
    formData.append("method", panel.querySelector(".op-method").value); //อ่านค่า dropdown .op-method ของกลุ่มนั้น เช่น "stretch" ส่งในฟิลด์ method ให้ Backend รู้ว่าใช้วิธีไหน
    panel.querySelectorAll("[data-param]").forEach((el) => { //หาทุก element ที่มี attribute data-param
      const box = el.closest(".method-fields"); //หาก element นั้นอยู่ในกล่อง .method-fields ของวิธีย่อยใดๆ ให้เก็บไว้ใน box
      if (box && box.style.display === "none") return; //ถ้า box นั้นถูกซ่อน (style.display = "none") แสดงว่าผู้ใช้ไม่ได้เลือกวิธีนั้น ให้ return ออกจาก forEach ไม่ต้องส่งค่าของ element นี้
      formData.append(el.dataset.param, el.value); //ใส่ชื่อพารามิเตอร์ (เช่น "r1")
    });
  }

  function prependEditHistory(item) {
    const placeholder = editHistoryGrid.querySelector(".placeholder-text");
    if (placeholder) placeholder.remove();
    editHistoryGrid.insertAdjacentHTML("afterbegin", editItemHtml(item));
  }

  // --- กด "แปลงภาพ" ---
  editApplyBtn.addEventListener("click", async () => { //เมื่อผู้ใช้กดปุ่ม "แปลงภาพ" ให้ทำงานฟังก์ชันนี้
    if (editSourceMode === "upload" && !editSelectedFile) { //ถ้าเลือกแท็บอัปโหลด แต่ยังไม่ได้เลือกไฟล์ ให้แสดงข้อความเตือน
      showEditStatus("กรุณาเลือกไฟล์ภาพที่จะอัปโหลดก่อน", true); //แสดงข้อความเตือนใน editStatusBox (สีแดง) โดยเรียกฟังก์ชัน showEditStatus() ที่ประกาศไว้ข้างบน
      return; //ออกจากฟังก์ชัน ไม่ส่งคำขอไปแก้ไขภาพ
    }
    if (editSourceMode === "history" && !editSelectedGenerationId) { //ถ้าเลือกแท็บประวัติ แต่ยังไม่ได้เลือกภาพ ให้แสดงข้อความเตือน
      showEditStatus("กรุณาเลือกภาพจากประวัติก่อน", true); //แสดงข้อความเตือนใน editStatusBox (สีแดง) โดยเรียกฟังก์ชัน showEditStatus() ที่ประกาศไว้ข้างบน
      return; //ออกจากฟังก์ชัน ไม่ส่งคำขอไปแก้ไขภาพ
    }

    const formData = new FormData(); //สร้าง FormData object เพื่อเก็บข้อมูลที่จะส่งไปแก้ไขภาพ (เหมือน form HTML แต่ส่งผ่าน fetch)
    formData.append("operation", currentOp); //ใส่ชื่อฟังก์ชันแก้ไขที่เลือกอยู่ (currentOp) ลงใน formData
    if (editSourceMode === "upload") { //ถ้าเลือกแท็บอัปโหลด ให้ใส่ไฟล์ภาพที่เลือกอยู่ (editSelectedFile) ลงใน formData
      formData.append("image", editSelectedFile); //ใส่ไฟล์ภาพที่เลือกอยู่ (editSelectedFile) ลงใน formData โดยใช้ key "image" (เหมือน name ของ input type=file ใน form HTML)
    } else { //ถ้าเลือกแท็บประวัติ ให้ใส่ generation_id ของภาพที่เลือกอยู่ (editSelectedGenerationId) ลงใน formData
      formData.append("generation_id", editSelectedGenerationId); //ใส่ generation_id ของภาพที่เลือกอยู่ (editSelectedGenerationId) ลงใน formData โดยใช้ key "generation_id" (เหมือน name ของ input type=hidden ใน form HTML)
    }
    collectOpParams(formData); //เรียกฟังก์ชัน collectOpParams(formData) เพื่อใส่วิธี + ค่าตั้งค่าของกลุ่มที่เลือกอยู่ลงใน formData (ส่งเฉพาะช่องที่แสดงอยู่)

    editApplyBtn.disabled = true;
    editApplyBtn.textContent = "กำลังแปลงภาพ...";
    showEditStatus("กำลังประมวลผล...");

    try {
      const data = await apiJson("/api/edit", { method: "POST", body: formData });

      const paramsTag = data.params_summary ? `<span>${escapeHtml(data.params_summary)}</span>` : ""; //ถ้า data.params_summary มีค่า ให้สร้าง <span> แสดงข้อความนั้น ถ้าไม่มีค่า ให้เป็นสตริงว่าง
      //เติมผลลัพธ์ลงใน editResultArea (แท็บแก้ไขภาพ) โดยแสดงภาพที่แก้ไขแล้วและข้อความบอกว่าฟังก์ชันอะไร + ค่าตั้งค่าอะไรบ้าง
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
