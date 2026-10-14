/* ============================================================
   PC1 : FRONTEND — auth.js
   หน้า login.html และ register.html
   เดิมเป็น <form method="POST"> ที่ Flask รับตรง ๆ
   ตอนนี้ส่งเป็น JSON ไปที่ API ของ PC2 แทน
   ============================================================ */
document.addEventListener("DOMContentLoaded", () => {
  consumeFlash();

  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");

  // ถ้าล็อกอินอยู่แล้ว ไม่ต้องให้อยู่หน้านี้ (เทียบเท่า current_user.is_authenticated เดิม)
  apiFetch("/api/me").then((res) => {
    if (res.ok) window.location.href = "index.html";
  });

  if (loginForm) { //ทำเฉพาะเมื่อหน้านั้นมีฟอร์มล็อกอินอยู่จริง
    loginForm.addEventListener("submit", async (e) => { //เมื่อกดปุ่ม submit ของฟอร์มล็อกอิน
      e.preventDefault(); //ยกเลิกการส่งฟอร์มแบบเดิม (ไม่ต้องรีเฟรชหน้า)
      const btn = loginForm.querySelector("button[type=submit]"); //สร้างตัวแปรชื่อ btnแล้วelement ฟอร์มล็อกอินค้นหา element ตัวแรก ที่ตรงกับ selector ที่ระบุ แบบ CSS
      btn.disabled = true; //ปิดปุ่ม submit ชั่วคราวเพื่อป้องกันผู้ใช้กดซ้ำ

      try { //ทำ code ในบล็อก try {...} ถ้าเกิด error จะกระโดดไป catch {...}
        await apiJson("/api/login", { //เรียก POST /api/login ของ รอ PC2 เพื่อขอเข้าสู่ระบบ
          method: "POST", //ส่งข้อมูลใน body ไม่แสดงใน URL
          headers: { "Content-Type": "application/json" }, //บอก Backend ว่า body เป็นรูปแบบ JSON
          body: JSON.stringify({
            username: document.getElementById("username").value,
            password: document.getElementById("password").value,
          }),
        });
        window.location.href = "index.html"; //ล็อกอินสำเร็จแล้ว ให้เด้งไปหน้า index.html
      } catch (err) { // มี error
        showFlash(err.message, "error"); //แสดงข้อความ error ด้านบนของหน้า (แทน flash message ของ Flask)
      } finally { //ทำงานเสมอ
        btn.disabled = false; //เปิดปุ่มกลับมากดได้
      }
    });
  }

  if (registerForm) { //ทำเฉพาะเมื่อหน้านั้นมีฟอร์มสมัครสมาชิกอยู่จริง
    registerForm.addEventListener("submit", async (e) => { //เมื่อกดปุ่ม submit ของฟอร์มสมัครสมาชิก
      e.preventDefault(); //ยกเลิกการส่งฟอร์มแบบเดิม (ไม่ต้องรีเฟรชหน้า)
      const btn = registerForm.querySelector("button[type=submit]"); //สร้างตัวแปรชื่อ btnแล้วelement ฟอร์มสมัครสมาชิกค้นหา element ตัวแรก ที่ตรงกับ selector ที่ระบุ แบบ CSS
      btn.disabled = true; //ปิดปุ่ม submit ชั่วคราวเพื่อป้องกันผู้ใช้กดซ้ำ

      try { //ทำในวงเล็บก่อน
        const data = await apiJson("/api/register", { //ฟังก์ชันสำหรับส่งคำขอ POST ไปยัง API
          method: "POST", //ส่งข้อมูลใน body (ไม่โชว์ใน URL)
          headers: { "Content-Type": "application/json" },//บอก Backend ว่า body เป็นรูปแบบ JSON
          body: JSON.stringify({
            username: document.getElementById("username").value, //ดึงค่าที่ผู้ใช้พิมในช่อง username
            password: document.getElementById("password").value, //ดึงค่าที่ผู้ใช้พิมในช่อง password
            confirm: document.getElementById("confirm").value,  //คือช่อง "ยืนยันรหัสผ่าน" ส่งไปให้ Backend ตรวจว่าตรงกับ password
          }),
        });
        setFlash(data.message || "สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ", "success"); //ใช้ข้อความจาก Backend ถ้ามี ถ้าไม่มีใช้ข้อความสำรองแทน
        window.location.href = "login.html"; //พาผู้ใช้ไปหน้าล็อกอิน
      } catch (err) { //มี error
        showFlash(err.message, "error"); //แสดงข้อความ errorด้านบนของหน้า (แทน flash message ของ Flask)
      } finally { //ทำงานเสมอ
        btn.disabled = false;
      }
    });
  }
});
