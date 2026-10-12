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

  function cardHtml(r) {
    const negativeRow = r.negative_prompt
      ? `<p class="admin-prompt admin-negative"><strong>Negative:</strong> ${escapeHtml(r.negative_prompt)}</p>`
      : "";
    const checkpointTag = r.checkpoint ? `<span>${escapeHtml(r.checkpoint)}</span>` : "";

    return `
      <div class="admin-card" data-username="${escapeHtml((r.username || "").toLowerCase())}"
           data-prompt="${escapeHtml((r.prompt || "").toLowerCase())}">
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

  try {
    const data = await apiJson("/api/admin/records");

    metaEl.textContent =
      `แสดง ${data.shown_count} จาก ${data.total_count} รายการทั้งหมด (ล่าสุดก่อน)` +
      (data.total_count > data.shown_count
        ? " — รายการเก่ากว่านี้ยังไม่แสดง เพื่อไม่ให้หน้าโหลดหนักเกินไป"
        : "");

    if (!data.records.length) {
      grid.innerHTML = '<p class="placeholder-text">ยังไม่มีข้อมูลการสร้างภาพในระบบ</p>';
      return;
    }
    grid.innerHTML = data.records.map(cardHtml).join("");
  } catch (err) {
    grid.innerHTML = `<p class="placeholder-text">โหลดข้อมูลไม่สำเร็จ: ${escapeHtml(err.message)}</p>`;
    return;
  }

  // --- ลบรายการ ---
  grid.addEventListener("click", async (e) => {
    const btn = e.target.closest(".admin-delete-btn");
    if (!btn) return;
    if (!confirm("ลบรายการนี้ถาวร? (ลบทั้ง record และไฟล์ภาพ กู้คืนไม่ได้)")) return;

    btn.disabled = true;
    try {
      await apiJson(`/api/admin/delete/${btn.dataset.id}`, { method: "POST" });
      btn.closest(".admin-card").remove();
      showFlash("ลบรายการนี้แล้ว", "success");
    } catch (err) {
      showFlash(err.message, "error");
      btn.disabled = false;
    }
  });

  // --- ค้นหาจาก username / prompt ---
  searchBox.addEventListener("input", () => {
    const q = searchBox.value.trim().toLowerCase();
    grid.querySelectorAll(".admin-card").forEach((card) => {
      const match = card.dataset.username.includes(q) || card.dataset.prompt.includes(q);
      card.style.display = match ? "" : "none";
    });
  });
});
