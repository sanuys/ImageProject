/* ============================================================
   PC1 : FRONTEND — admin.js
   หน้า admin.html
   เดิม Jinja เรนเดอร์การ์ดทั้งหมดมาจาก Flask
   ตอนนี้ดึงผ่าน GET /api/admin/records แล้วสร้างการ์ดด้วย JS
   ============================================================ */
document.addEventListener("DOMContentLoaded", async () => {
  const user = await requireLogin({ adminOnly: true });
  if (!user) return;

  consumeFlash();

  const grid = document.getElementById("admin-grid");
  const metaEl = document.getElementById("admin-meta");
  const searchBox = document.getElementById("admin-search");

  function cardHtml(r) { //ฟังก์ชันสำหรับสร้าง HTML ของการ์ดแต่ละรายการจาก object r (record) ที่ได้จาก Backend
    const negativeRow = r.negative_prompt //ถ้า r.negative_prompt มีค่า ให้สร้าง <p> แสดงข้อความนั้น ถ้าไม่มีค่า ให้เป็นสตริงว่าง
      ? `<p class="admin-prompt admin-negative"><strong>Negative:</strong> ${escapeHtml(r.negative_prompt)}</p>` //ถ้ามี negative prompt สร้างย่อหน้า ถ้าไม่มีได้สตริงว่าง (ไม่แสดงอะไร) ส่วนเนื้อหา ผมเดาว่าใส่ escapeHtml(r.negative_prompt) เพราะบรรทัดถูกตัด
      : "";
    const checkpointTag = r.checkpoint ? `<span>${escapeHtml(r.checkpoint)}</span>` : ""; //ถ้า r.checkpoint มีค่า ให้สร้าง <span> แสดงข้อความนั้น ถ้าไม่มีค่า ให้เป็นสตริงว่าง

    return `
      <div class="admin-card" data-username="${escapeHtml((r.username || "").toLowerCase())}" 
        <img src="${mediaUrl(r.image_url)}" alt="${escapeHtml(r.prompt)}">
        <div class="admin-card-body">
          <div class="admin-user-badge">${escapeHtml(r.username)}</div>
          <p class="admin-prompt"><strong>Prompt:</strong> ${escapeHtml(r.prompt)}</p>
          ${negativeRow}
          <div class="admin-settings">
            <span>Steps: ${escapeHtml(r.steps)}</span>
            <span>CFG: ${escapeHtml(r.cfg_scale)}</span>
            <span>${escapeHtml(r.width)}x${escapeHtml(r.height)}</span>
            <span>${escapeHtml(r.sampler)}</span>
            <span>Seed: ${escapeHtml(r.seed)}</span>
            ${checkpointTag}
          </div>
          <div class="admin-timestamp">${escapeHtml(r.created_at)}</div>
          <button type="button" class="btn-danger admin-delete-btn" data-id="${r.id}">ลบรายการนี้</button>
        </div>
      </div>
    `;
  }
  /*เก็บชื่อผู้ใช้ใน data-username ของการ์ด (แปลงเป็นตัวพิมพ์เล็ก) เพื่อใช้ค้นหา
    26	รูป mediaUrl(r.image_url) พร้อม alt เป็น prompt
    28	ป้ายชื่อผู้ใช้ (admin-user-badge) บอกว่าเป็นภาพของใคร
    29	Prompt: ...
    30	${negativeRow} แถว negative (หรือว่าง)
    32–36	ค่าที่ใช้: Steps, CFG, ขนาด กว้างxสูง, sampler, Seed
    37	${checkpointTag}
    39	เวลาที่สร้าง created_at
    40	ปุ่มลบ btn-danger admin-delete-btn
  */
  try {
    const data = await apiJson("/api/admin/records"); //เรียก GET /api/admin/records เพื่อดึงข้อมูลการสร้างภาพทั้งหมดจาก Backend (PC2) ผ่าน Nginx

    metaEl.textContent = //ต่อสตริงสองส่วนด้วย + ส่วนแรกเป็นข้อความหลัก ส่วนที่สองเป็น ternary: ถ้ารายการทั้งหมดมากกว่าที่แสดง ต่อประโยคเตือนท้ายข้อความ ไม่งั้นต่อสตริงว่าง
    //แสดงว่า Backend จำกัดจำนวนที่ส่งมา (เรียงล่าสุดก่อน) ไม่ใช่ส่งทั้งหมด เพื่อไม่ให้หน้าหนัก (pagination แบบง่ายสุด คือตัดที่ N รายการ)  
    `แสดง ${data.shown_count} จาก ${data.total_count} รายการทั้งหมด (ล่าสุดก่อน)` +
      (data.total_count > data.shown_count
        ? " — รายการเก่ากว่านี้ยังไม่แสดง เพื่อไม่ให้หน้าโหลดหนักเกินไป"
        : "");

    if (!data.records.length) { //ถ้าไม่มีรายการเลย
      grid.innerHTML = '<p class="placeholder-text">ยังไม่มีข้อมูลการสร้างภาพในระบบ</p>';
      return;
    }
    grid.innerHTML = data.records.map(cardHtml).join(""); //วนทุกรายการใน data.records แล้วเรียก cardHtml(r) เพื่อสร้าง HTML ของการ์ดแต่ละรายการ แล้วต่อสตริงทั้งหมดด้วย join("") (ไม่เว้นวรรค) แล้วใส่ลงใน grid.innerHTML
  } catch (err) { //ถ้าเกิด error ตอนเรียก GET /api/admin/records
    grid.innerHTML = `<p class="placeholder-text">โหลดข้อมูลไม่สำเร็จ: ${escapeHtml(err.message)}</p>`; //แสดงข้อความ error แทนการ์ด
    return; //ออกจากฟังก์ชัน ไม่ต้องทำงานต่อ
  }

  // --- ลบรายการ ---
  grid.addEventListener("click", async (e) => { //ผูก event click ไว้กับ grid (กล่องที่มีการ์ดทั้งหมด) เพื่อใช้ event delegation แทนการผูก click กับปุ่มลบแต่ละปุ่ม
    const btn = e.target.closest(".admin-delete-btn"); //ถ้าผู้ใช้คลิกที่ปุ่มลบ (หรือ element ภายในปุ่ม) ให้หา element ที่ใกล้ที่สุดที่มี class admin-delete-btn (คือปุ่มลบ) ถ้าไม่เจอจะได้ null
    if (!btn) return; //ถ้าไม่ใช่ปุ่มลบ ให้ return ออกจากฟังก์ชัน ไม่ทำอะไร
    if (!confirm("ลบรายการนี้ถาวร? (ลบทั้ง record และไฟล์ภาพ กู้คืนไม่ได้)")) return; //แสดง confirm ถ้าผู้ใช้กด Cancel ให้ return ออกจากฟังก์ชัน ไม่ทำอะไร

    btn.disabled = true; //ปิดปุ่มลบชั่วคราวเพื่อป้องกันผู้ใช้กดซ้ำ (disabled จะทำให้ปุ่มไม่สามารถกดได้)
    try {
      await apiJson(`/api/admin/delete/${btn.dataset.id}`, { method: "POST" }); //เรียก POST /api/admin/delete/<id> เพื่อให้ Backend ลบรายการนั้น (id เก็บใน data-id ของปุ่ม) ใช้ POST เพราะเป็นการเปลี่ยนสถานะ (ลบ) ตามที่คุยเรื่อง GET/POST ไว้
      btn.closest(".admin-card").remove(); //หา element ที่ใกล้ที่สุดที่มี class admin-card (คือการ์ดของรายการนั้น) แล้วลบออกจาก DOM (ไม่ต้องรีเฟรชหน้า)
      showFlash("ลบรายการนี้แล้ว", "success"); //แสดงข้อความ flash ด้านบนของหน้า (แทน flash message ของ Flask) ว่า "ลบรายการนี้แล้ว" สีเขียว
    } catch (err) { //ถ้าเกิด error ตอนเรียก POST /api/admin/delete/<id>
      showFlash(err.message, "error"); //แสดงข้อความ error ด้านบนของหน้า (แทน flash message ของ Flask) ว่าเกิดอะไรขึ้น สีแดง
      btn.disabled = false; //เปิดปุ่มลบกลับมาให้กดได้อีกครั้ง (เพราะลบไม่สำเร็จ)
    }
  });

  // --- ค้นหาจาก username / prompt ---
  searchBox.addEventListener("input", () => { //เมื่อผู้ใช้พิมพ์ในช่องค้นหา (input) ให้ทำงานฟังก์ชันนี้
    const q = searchBox.value.trim().toLowerCase(); //ดึงค่าที่ผู้ใช้พิมพ์ในช่องค้นหา แล้ว trim() เพื่อลบ space ข้างหน้า/ข้างหลัง และ toLowerCase() เพื่อเปรียบเทียบแบบไม่สนใจตัวพิมพ์ใหญ่/เล็ก
    grid.querySelectorAll(".admin-card").forEach((card) => { //วนทุกรายการการ์ดใน grid แล้วตรวจสอบว่า username หรือ prompt ของการ์ดนั้นตรงกับคำค้นหา (q) หรือไม่
      const match = card.dataset.username.includes(q) || card.dataset.prompt.includes(q); //ตรวจสอบว่า data-username หรือ data-prompt ของการ์ดนั้นมีคำค้นหา (q) อยู่หรือไม่ (includes) ถ้ามี match = true ถ้าไม่มี match = false
      card.style.display = match ? "" : "none"; //ถ้า match = true ให้แสดงการ์ด (style.display = "") ถ้า match = false ให้ซ่อนการ์ด (style.display = "none")
    });
  });
});
