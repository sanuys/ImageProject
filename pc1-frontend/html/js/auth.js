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

  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = loginForm.querySelector("button[type=submit]");
      btn.disabled = true;

      try {
        await apiJson("/api/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: document.getElementById("username").value,
            password: document.getElementById("password").value,
          }),
        });
        window.location.href = "index.html";
      } catch (err) {
        showFlash(err.message, "error");
      } finally {
        btn.disabled = false;
      }
    });
  }

  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = registerForm.querySelector("button[type=submit]");
      btn.disabled = true;

      try {
        const data = await apiJson("/api/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: document.getElementById("username").value,
            password: document.getElementById("password").value,
            confirm: document.getElementById("confirm").value,
          }),
        });
        setFlash(data.message || "สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ", "success");
        window.location.href = "login.html";
      } catch (err) {
        showFlash(err.message, "error");
      } finally {
        btn.disabled = false;
      }
    });
  }
});
