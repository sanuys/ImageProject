/* ============================================================
   PC1 : FRONTEND — common.js
   ฟังก์ชันที่ทุกหน้าใช้ร่วมกัน: เรียก API, เช็คล็อกอิน, แถบเมนู
   ============================================================ */

/* เรียก API ของ Backend (PC2) พร้อมแนบ cookie session ไปด้วยเสมอ 
 * path	เส้นทาง API เช่น "/api/login"
 * options = {}	ตัวเลือกเพิ่มเติม (method, headers, body) ถ้าไม่ส่งมา ใช้ object ว่าง
*/
async function apiFetch(path, options = {}) { //ฟังก์ชันสำหรับเรียก API ของ Backend (PC2) โดยแนบ cookie session ไปด้วยเสมอ
  const res = await fetch(API_BASE + path, { //เรียก API ของ Backend (PC2) โดยแนบ cookie session ไปด้วยเสมอ
    credentials: "include", // ต้องมี ไม่งั้น session cookie ไม่ถูกส่งไป
    ...options, //กระจายค่าจาก options มาใส่ต่อ (method, headers, body ที่ auth.js ส่งมา)
  });
  return res; //คืน object response ทั้งก้อน (ยังไม่แปลงอะไร)
}
/*apiFetch คืน response ดิบ เหมาะกับกรณีที่ไม่ต้องการ JSON เช่น ดาวน์โหลดไฟล์/รูป
  apiJson ครอบอีกชั้นสำหรับ API ทั่วไปที่ตอบ JSON จะได้ไม่ต้องเขียน parse + เช็ก error ซ้ำทุกที่*/

/** เรียก API แล้วคืนค่าเป็น JSON — โยน Error พร้อมข้อความไทยถ้าไม่สำเร็จ */
async function apiJson(path, options = {}) { //ฟังก์ชันสำหรับเรียก API ของ Backend (PC2) โดยแนบ cookie session ไปด้วยเสมอ และแปลง response เป็น JSON
  const res = await apiFetch(path, options); // เรียก API ของ Backend (PC2) โดยแนบ cookie session ไปด้วยเสมอ
  let data = {}; //data = {} ค่าเริ่มต้นเป็น object ว่าง ใช้ let เพราะจะถูกเปลี่ยนค่าทีหลัง
  try {
    data = await res.json(); //แปลง response เป็น JSON (ถ้า response ไม่ใช่ JSON จะเกิด error แล้วกระโดดไป catch {...})
  } catch (e) { //มีerror
    /* บาง response อาจไม่ใช่ JSON */
  }
  if (!res.ok) { //ถ้า status code ไม่ใช่ 2xx (เช่น 400, 401, 500) ให้โยน error ออกไป
    const err = new Error(data.error || `เกิดข้อผิดพลาด (HTTP ${res.status})`); //สร้าง error พร้อมข้อความ โดย data.error || ... ใช้ข้อความจาก Backend ก่อน ถ้าไม่มีใช้ข้อความสำรอง
    err.status = res.status;//แนบเลข status ติดไปกับ error นี่คือสิ่งที่ requireLogin() ใช้เช็ก if (err.status === 401)
    throw err;//โยน error ออกไปให้ผู้เรียก (เช่น auth.js) จัดการต่อ
  }
  return data;
}

/** แปลง path ของภาพที่ backend ส่งมา (/media/outputs/x.png) ให้เป็น URL เต็ม */
function mediaUrl(url) {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return API_BASE + url;
}

/** หนีอักขระพิเศษก่อนยัดลง innerHTML (กัน prompt ที่มี < > ทำหน้าเว็บพัง) */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

/**
 * เช็คว่าล็อกอินอยู่ไหม — ถ้ายัง ให้เด้งไปหน้า login.html
 * เดิมงานนี้ Flask-Login ทำให้ตอน render หน้า แต่ตอนนี้ HTML เป็น static
 * ที่เครื่อง PC1 แล้ว จึงต้องถาม Backend (PC2) ผ่าน /api/me เอง
 * คืนค่า user object ถ้าผ่าน
 */
async function requireLogin({ adminOnly = false } = {}) { //ถามbackend ว่าผู้ใช้ล็อกอินอยู่ไหม  รับ option adminOnly ถ้าเป็น true จะเช็คด้วยว่าผู้ใช้เป็น admin หรือไม่ ถ้าไม่ใช่ admin จะเด้งไปหน้า index.html
  let data;
  try {
    data = await apiJson("/api/me"); //เรียก GET /api/me ซึ่ง Nginx จะส่งต่อไป PC2 (ตรงกับ location /api/) เพื่อขอข้อมูลผู้ใช้ปัจจุบัน 
  } catch (err) {
    if (err.status === 401) { //401 แปลว่า Unauthorized (ยังไม่ล็อกอิน) ให้เด้งไปหน้า login.html
      window.location.href = "login.html";
      return null;
    }
    document.body.innerHTML =
      '<div class="container"><div class="flash flash-error">' +
      "ติดต่อ Backend (PC2) ไม่ได้: " + escapeHtml(err.message) + // แปลงอักขระพิเศษในข้อความ error ก่อนใส่ลงหน้า เพื่อป้องกันการแทรกโค้ด HTML/JS (XSS)
      "<br>ตรวจสอบว่าเครื่อง Backend เปิดอยู่ และ Nginx ตั้งค่า proxy ถูกต้อง" +
      "</div></div>";
    return null;
  }

  const user = data.user;             
  if (adminOnly && !user.is_admin) {
    window.location.href = "index.html";
    return null;
  }      //ถ้าหน้านั้นสงวนไว้สำหรับแอดมิน (adminOnly) แต่ผู้ใช้ไม่ใช่แอดมิน ให้เด้งกลับ index.html (ส่วนท้ายที่ถูกตัดไปน่าจะคืนค่า user กลับไป)

  renderNavbar(user); //เรียกฟังก์ชัน renderNavbar() เพื่อเติมชื่อผู้ใช้/ลิงก์ Admin ลงในแถบเมนู
  return user; //คืนข้อมูลผู้ใช้ให้ผู้เรียก ซึ่งก็คือ main.js ที่รับไปไว้ในตัวแปร user
}

/** เติมชื่อผู้ใช้/ลิงก์ Admin ลงในแถบเมนู (เดิมเป็นงานของ base.html + Jinja) */
function renderNavbar(user) { //ฟังก์ชันสำหรับเติมชื่อผู้ใช้/ลิงก์ Admin ลงในแถบเมนู (เดิมเป็นงานของ base.html + Jinja)
  const navRight = document.getElementById("nav-right"); //หา element ที่มี id="nav-right" ในหน้า HTML (กล่องว่างที่เตรียมไว้ให้ใส่เมนู)
  if (!navRight) return; //ถ้าหน้านั้นไม่มีกล่องนี้ (เช่น login.html ที่ไม่มี navbar) ก็ออกจากฟังก์ชันเงียบๆ ไม่ error ทำให้เรียกฟังก์ชันนี้ได้ทุกหน้าอย่างปลอดภัย

  const adminLink = user.is_admin //ใช้ตัวดำเนินการ ternary เงื่อนไข ? ค่าถ้าจริง : ค่าถ้าเท็จ
    ? '<a href="admin.html" class="nav-link">Admin</a>' //ข้อความ HTML ลิงก์ไป admin.html
    : ""; //สตริงว่าง "" (ไม่แสดงอะไร)

  //ใส่ HTML ลงในกล่อง nav-right 
  // แทรกลิงก์ Admin (หรือว่างเปล่า)
  //${escapeHtml(user.username)} แทรกชื่อผู้ใช้ หลังแปลงอักขระพิเศษ (< > & ฯลฯ)
  navRight.innerHTML = `   
    ${adminLink} 
    <span class="nav-user">สวัสดี, ${escapeHtml(user.username)}</span>
    <a href="#" id="logout-link" class="nav-link">ออกจากระบบ</a>
  `;
  navRight.style.display = "";

  document.getElementById("logout-link").addEventListener("click", async (e) => { //หา element id="logout-link" ซึ่งเพิ่งถูกสร้างด้วย innerHTML ในบรรทัด,ผูก event click ไว้ได้ทันทีหลังสร้าง
    e.preventDefault(); //ลิงก์ <a href="#"> ปกติเมื่อคลิกจะกระโดดไปบนสุดของหน้าและเปลี่ยน URL เป็น # บรรทัดนี้ยกเลิกพฤติกรรมนั้น เพื่อให้โค้ดเราควบคุมเองทั้งหมด
    try {
      await apiFetch("/api/logout", { method: "POST" }); //ให้ Backend ลบ session ฝั่งเซิร์ฟเวอร์และสั่งล้าง cookie ใช้ POST เพราะเป็นการเปลี่ยนสถานะ ตามที่คุยเรื่อง GET/POST ไว้
    } catch (err) {                                       //ใช้ apiFetch ไม่ใช่ apiJson เพราะไม่สนใจเนื้อหาที่ตอบกลับ ไม่ต้องแปลง JSON และไม่ต้อง throw เมื่อ status ผิดปกติ
      /* ต่อไม่ติดก็ยังพากลับหน้า login อยู่ดี */
    }
    window.location.href = "login.html"; //ทำงานทุกกรณี ไม่ว่า logout สำเร็จหรือไม่
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
