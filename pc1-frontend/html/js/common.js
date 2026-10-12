/* ============================================================
   PC1 : FRONTEND — common.js
   ฟังก์ชันที่ทุกหน้าใช้ร่วมกัน: เรียก API, เช็คล็อกอิน, แถบเมนู
   ============================================================ */

/** เรียก API ของ Backend (PC2) พร้อมแนบ cookie session ไปด้วยเสมอ */
async function apiFetch(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    credentials: "include", // ต้องมี ไม่งั้น session cookie ไม่ถูกส่งไป
    ...options,
  });
  return res;
}

/** เรียก API แล้วคืนค่าเป็น JSON — โยน Error พร้อมข้อความไทยถ้าไม่สำเร็จ */
async function apiJson(path, options = {}) {
  const res = await apiFetch(path, options);
  let data = {};
  try {
    data = await res.json();
  } catch (e) {
    /* บาง response อาจไม่ใช่ JSON */
  }
  if (!res.ok) {
    const err = new Error(data.error || `เกิดข้อผิดพลาด (HTTP ${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

/** แปลง path ของภาพที่ backend ส่งมา (/media/outputs/x.png) ให้เป็น URL เต็ม */
function mediaUrl(url) {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return API_BASE + url;
}

/** หนีอักขระพิเศษก่อนยัดลง innerHTML (กัน prompt ที่มี < > ทำหน้าเว็บพัง)
 *  ต้องหนี " และ ' ด้วย เพราะค่านี้ถูกใช้ใน attribute (alt="..." title="...") ด้วย */
const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
function escapeHtml(text) {
  return (text == null ? "" : String(text)).replace(/[&<>"']/g, (ch) => HTML_ESCAPES[ch]);
}

/**
 * เช็คว่าล็อกอินอยู่ไหม — ถ้ายัง ให้เด้งไปหน้า login.html
 * เดิมงานนี้ Flask-Login ทำให้ตอน render หน้า แต่ตอนนี้ HTML เป็น static
 * ที่เครื่อง PC1 แล้ว จึงต้องถาม Backend (PC2) ผ่าน /api/me เอง
 * คืนค่า user object ถ้าผ่าน
 */
async function requireLogin({ adminOnly = false } = {}) {
  let data;
  try {
    data = await apiJson("/api/me");
  } catch (err) {
    if (err.status === 401) {
      window.location.href = "login.html";
      return null;
    }
    document.body.innerHTML =
      '<div class="container"><div class="flash flash-error">' +
      "ติดต่อ Backend (PC2) ไม่ได้: " + escapeHtml(err.message) +
      "<br>ตรวจสอบว่าเครื่อง Backend เปิดอยู่ และ Nginx ตั้งค่า proxy ถูกต้อง" +
      "</div></div>";
    return null;
  }

  const user = data.user;
  if (adminOnly && !user.is_admin) {
    window.location.href = "index.html";
    return null;
  }

  renderNavbar(user);
  return user;
}

/** เติมชื่อผู้ใช้/ลิงก์ Admin ลงในแถบเมนู (เดิมเป็นงานของ base.html + Jinja) */
function renderNavbar(user) {
  const navRight = document.getElementById("nav-right");
  if (!navRight) return;

  const adminLink = user.is_admin
    ? '<a href="admin.html" class="nav-link">Admin</a>'
    : "";

  navRight.innerHTML = `
    ${adminLink}
    <span class="nav-user">สวัสดี, ${escapeHtml(user.username)}</span>
    <a href="#" id="logout-link" class="nav-link">ออกจากระบบ</a>
  `;
  navRight.style.display = "";

  document.getElementById("logout-link").addEventListener("click", async (e) => {
    e.preventDefault();
    try {
      await apiFetch("/api/logout", { method: "POST" });
    } catch (err) {
      /* ต่อไม่ติดก็ยังพากลับหน้า login อยู่ดี */
    }
    window.location.href = "login.html";
  });
}

/** แสดงข้อความแจ้งเตือนด้านบนของหน้า (แทน flash message ของ Flask) */
function showFlash(message, category = "error") {
  const box = document.getElementById("flash-area");
  if (!box) return;
  box.innerHTML = `<div class="flash flash-${category}">${escapeHtml(message)}</div>`;
}

/** อ่านข้อความที่หน้าก่อนหน้าฝากไว้ (เช่น "สมัครสมาชิกสำเร็จ") แล้วลบทิ้ง */
function consumeFlash() {
  const msg = sessionStorage.getItem("flash_message");
  const cat = sessionStorage.getItem("flash_category") || "success";
  if (msg) {
    sessionStorage.removeItem("flash_message");
    sessionStorage.removeItem("flash_category");
    showFlash(msg, cat);
  }
}

/** ฝากข้อความไว้ให้หน้าถัดไปแสดง */
function setFlash(message, category = "success") {
  sessionStorage.setItem("flash_message", message);
  sessionStorage.setItem("flash_category", category);
}
