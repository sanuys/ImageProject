"""
============================================================
 PC2 : BACKEND — image_ops.py
 ฟังก์ชัน Image Processing ทั้ง 4 กลุ่มของแท็บ "แก้ไขภาพ"
 อ้างอิงเนื้อหาวิชา 310-3311 Digital Image Processing
------------------------------------------------------------
 1) point_op          Point Operation (Lecture 4)
                      Negative · Log · Contrast stretching
 2) auto_contrast     ปรับ contrast อัตโนมัติจาก histogram (Lecture 4)
                      Automatic contrast adjustment · Histogram Equalization
 3) linear_filter     Spatial Filtering แบบ linear (Lecture 5)
                      Mean · Gaussian · Laplacian
 4) nonlinear_filter  Spatial Filtering แบบ non-linear (Lecture 5)
                      Median · Mean · Min · Max

 ทุกฟังก์ชันรับภาพ BGR (uint8) ที่อ่านด้วย cv2 แล้วคืน (ภาพผลลัพธ์, dict ค่าที่ใช้)
 dict นี้ถูกเก็บลงตาราง edits ที่ PC4 และใช้สรุปในประวัติการแก้ไข
============================================================
"""
import cv2
import numpy as np


class EditParamError(ValueError):
    """ค่าที่ผู้ใช้ส่งมาไม่ถูกต้อง -> /api/edit ตอบ 400 พร้อมข้อความนี้"""


# ------------------------------------------------------------
#  รายชื่อฟังก์ชัน (กลุ่ม -> วิธีย่อย)
#  ใช้ทั้งตรวจค่าที่ส่งมา และทำชื่อแสดงในผลลัพธ์/ประวัติ
# ------------------------------------------------------------
OPERATIONS = {
    "point_op": {
        "label": "Point Operation",
        "methods": {"negative": "Negative", "log": "Log", "stretch": "Contrast stretching"},
    },
    "auto_contrast": {
        "label": "Auto Contrast",
        "methods": {"auto": "Automatic contrast adjustment", "equalize": "Histogram Equalization"},
    },
    "linear_filter": {
        "label": "Linear Filter",
        "methods": {"mean": "Mean", "gaussian": "Gaussian", "laplacian": "Laplacian"},
    },
    "nonlinear_filter": {
        "label": "Non-linear Filter",
        "methods": {"median": "Median", "mean": "Mean", "min": "Min", "max": "Max"},
    },
}

# ชื่อฟังก์ชันชุดเดิม — เก็บไว้ให้ประวัติการแก้ไขเก่าใน DB ยังแสดงชื่ออ่านรู้เรื่อง
LEGACY_LABELS = {
    "resize": "ปรับขนาด (Resize)",
    "grayscale": "ขาว-ดำ (Grayscale)",
    "brightness_contrast": "ความสว่าง/คอนทราสต์ (Brightness/Contrast)",
    "negative": "กลับสี (Negative)",
}

# ขอบภาพที่ kernel ล้นออกไป ต้อง pad ก่อน — ที่นี่เติมด้วยการคัดลอกพิกเซลขอบ (Replicate)
BORDER = cv2.BORDER_REPLICATE

# ค่าเดิมทุกระดับ r = 0..255 ใช้สร้าง mapping table (LUT)
R = np.arange(256, dtype=np.float64)


# ============================================================
#  ตัวช่วยอ่านค่าจากฟอร์ม
# ============================================================
def _number(form, key, default, lo, hi, cast):
    raw = form.get(key, default)
    try:
        value = cast(float(raw))
    except (TypeError, ValueError):
        raise EditParamError(f"ค่า {key} ต้องเป็นตัวเลข")
    return max(lo, min(hi, value))


def _int(form, key, default, lo, hi):
    return _number(form, key, default, lo, hi, lambda v: int(round(v)))


def _float(form, key, default, lo, hi):
    return _number(form, key, default, lo, hi, float)


def _kernel_size(form, default=3):
    """ขนาด kernel ต้องเป็นเลขคี่ (มีช่องกลางไว้วางทับพิกเซล) อยู่ในช่วง 3–31"""
    k = _int(form, "ksize", default, 3, 31)
    return k if k % 2 == 1 else k + 1


def _apply_lut(img, table):
    """Mapping table (LUT): คำนวณค่าใหม่ของ 0–255 ไว้ครั้งเดียว แล้วเปิดตารางแทนค่าทุกพิกเซล
    ก่อนใช้ต้อง clamp ให้อยู่ใน 0–255 แล้วแปลงกลับเป็น uint8"""
    table = np.clip(np.round(table), 0, 255).astype(np.uint8)
    return cv2.LUT(img, table)


# ============================================================
#  1) POINT OPERATION — g(x,y) = T(f(x,y))
#     ค่าใหม่ขึ้นกับค่าเดิมของพิกเซลนั้นเท่านั้น ไม่ดูเพื่อนบ้าน
#     ใช้ตาราง LUT เดียวกันกับทั้ง 3 ช่องสี (B, G, R)
# ============================================================
def point_op(img, method, form):
    if method == "negative":
        # เอาค่าสูงสุด (L−1 = 255) ลบค่าเดิม: s = 255 − r  → ขาว↔ดำ
        return _apply_lut(img, 255 - R), {}

    if method == "log":
        # s = c · log(1 + r)  โดย c = 255 / log(1 + 255) ให้ r = 255 แล้วได้ s = 255 พอดี
        # ยืดช่วงมืด (ค่าน้อยถูกดึงขึ้นมาก) บีบช่วงสว่าง
        c = 255.0 / np.log(1.0 + 255.0)
        return _apply_lut(img, c * np.log1p(R)), {"c": round(c, 2)}

    # Contrast stretching (piecewise-linear)
    # เส้นหักมุมผ่าน (0,0) → (r1,s1) → (r2,s2) → (255,255)
    # ช่วง r1–r2 ถ้าชันกว่า 45° = ยืด contrast ของช่วงนั้น
    r1 = _int(form, "r1", 70, 1, 254)
    s1 = _int(form, "s1", 20, 0, 255)
    r2 = _int(form, "r2", 180, 1, 254)
    s2 = _int(form, "s2", 235, 0, 255)
    if r1 >= r2:
        raise EditParamError("Contrast stretching: ต้องตั้ง r1 ให้น้อยกว่า r2")
    table = np.interp(R, [0, r1, r2, 255], [0, s1, s2, 255])
    return _apply_lut(img, table), {"r1": r1, "s1": s1, "r2": r2, "s2": s2}


# ============================================================
#  2) ปรับ CONTRAST อัตโนมัติจาก HISTOGRAM
#     ทำบนช่องความสว่าง Y (YCrCb) แล้วใส่สีเดิมกลับ
#     (ถ้าทำแยกทีละช่อง B, G, R สัดส่วนสีจะเปลี่ยน ภาพสีเพี้ยน)
# ============================================================
def _split_luma(img):
    """คืน (ภาพความสว่าง Y, ฟังก์ชันเอา Y ใหม่ไปรวมกับสีเดิม)"""
    if img.ndim == 2:
        return img, lambda y: y
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)

    def merge(new_y):
        out = ycrcb.copy()
        out[:, :, 0] = new_y
        return cv2.cvtColor(out, cv2.COLOR_YCrCb2BGR)

    return ycrcb[:, :, 0], merge


def auto_contrast(img, method, form):
    y, merge = _split_luma(img)
    n = y.size                                       # จำนวนพิกเซลทั้งหมด (M × N)
    hist = np.bincount(y.ravel(), minlength=256)     # นับ: h(i) = จำนวนพิกเซลที่มีค่า i
    cdf = np.cumsum(hist)                            # สะสม: H(i) = จำนวนพิกเซลที่มีค่า ≤ i

    if method == "auto":
        # Automatic contrast adjustment
        # หาค่าต่ำสุด a_low กับสูงสุด a_high ที่มีในภาพ แล้วยืดช่วงนี้ให้เต็ม 0–255 แบบเส้นตรง
        #   s = (r − a_low) × 255 / (a_high − a_low)
        # clip > 0% = Modified auto contrast: ตัดหัวท้าย histogram ทิ้งฝั่งละ clip%
        # กันจุด noise ไม่กี่จุดที่เป็น 0 หรือ 255 ทำให้ยืดไม่ได้
        clip = _float(form, "clip", 1.0, 0.0, 10.0)
        a_low = int(np.argmax(cdf > n * clip / 100.0))
        a_high = int(np.argmax(cdf >= n * (1.0 - clip / 100.0)))
        if a_high <= a_low:
            raise EditParamError("ภาพนี้แทบมีค่าความสว่างค่าเดียว ยืด contrast ไม่ได้ — ลองลด % ตัดหัวท้าย")
        table = (R - a_low) * 255.0 / (a_high - a_low)
        return merge(_apply_lut(y, table)), {"clip": round(clip, 1), "a_low": a_low, "a_high": a_high}

    # Histogram Equalization
    #   1) นับ histogram  2) สะสมเป็น CDF
    #   3) เอายอดสะสมเทียบสัดส่วนกับจำนวนพิกเซลทั้งหมด แล้วขยายให้เต็ม 0–255
    #   4) แทนค่าทุกพิกเซลตามตาราง → histogram กระจายเต็มช่วง (CDF ใกล้เส้นตรง)
    table = np.floor(cdf * 255.0 / n)
    return merge(_apply_lut(y, table)), {}


# ============================================================
#  3) SPATIAL FILTERING แบบ LINEAR
#     วาง kernel ทับทุกพิกเซล → เอาค่าคูณน้ำหนักช่องที่ตรงกัน → บวกรวม = ค่าใหม่ → เลื่อนต่อ
#     (cv2.filter2D คำนวณแบบ correlation แต่ kernel ทุกตัวที่นี่สมมาตร ผลจึงเท่ากับ convolution)
# ============================================================
LAPLACIAN_KERNELS = {
    4: np.array([[0, 1, 0],
                 [1, -4, 1],
                 [0, 1, 0]], dtype=np.float64),
    8: np.array([[1, 1, 1],
                 [1, -8, 1],
                 [1, 1, 1]], dtype=np.float64),
}


def linear_filter(img, method, form):
    if method == "laplacian":
        # High-pass: น้ำหนักรวมกันได้ 0 → พื้นเรียบได้ค่า ~0 ส่วนที่ค่าเปลี่ยนเร็ว (ขอบ) ได้ค่าสูง
        # ทำบนภาพเทา ผลมีทั้งบวกและลบ จึงแสดงเป็น |ค่า| แล้ว clamp 0–255
        neighbors = 8 if str(form.get("neighbors", "4")) == "8" else 4
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        response = cv2.filter2D(gray, cv2.CV_64F, LAPLACIAN_KERNELS[neighbors], borderType=BORDER)
        result = np.clip(np.abs(response), 0, 255).astype(np.uint8)
        return result, {"neighbors": neighbors}

    k = _kernel_size(form)

    if method == "mean":
        # Box (Mean) filter: ทุกช่องน้ำหนักเท่ากัน = 1/(k×k) → ค่าเฉลี่ยในหน้าต่าง (low-pass เบลอ ลด noise)
        kernel = np.ones((k, k), dtype=np.float64) / (k * k)
        return cv2.filter2D(img, -1, kernel, borderType=BORDER), {"ksize": k}

    # Gaussian filter: ช่องกลางหนักสุด รอบนอกเบาลงตาม σ (หารด้วยผลรวมน้ำหนักแล้ว)
    # เบลอนุ่มเป็นธรรมชาติ ไม่เป็นบล็อกแบบ Mean — ใช้เป็นขั้นแรกของ Canny
    sigma = _float(form, "sigma", 1.5, 0.3, 20.0)
    result = cv2.GaussianBlur(img, (k, k), sigma, borderType=BORDER)
    return result, {"ksize": k, "sigma": round(sigma, 2)}


# ============================================================
#  4) SPATIAL FILTERING แบบ NON-LINEAR
#     เก็บค่าทั้งหมดในหน้าต่าง k×k → เรียงจากน้อยไปมาก → เลือกตัวที่ต้องการ (ไม่มีการคูณ-บวก)
#     Mean ใส่ไว้ในกลุ่มนี้เพื่อเปรียบเทียบกับ Median (ตัว Mean เองเป็น linear)
# ============================================================
def nonlinear_filter(img, method, form):
    k = _kernel_size(form)
    window = np.ones((k, k), dtype=np.uint8)

    if method == "median":
        # เลือกตัวกลาง → ลบ salt & pepper ได้ดีที่สุด เพราะค่า 0/255 อยู่ปลายแถว ไม่ถูกเลือก
        result = cv2.medianBlur(img, k)
    elif method == "mean":
        # ค่าเฉลี่ย → จุด noise ไม่หายแต่กลายเป็นรอยจาง และภาพเบลอทั้งภาพ
        result = cv2.blur(img, (k, k), borderType=BORDER)
    elif method == "min":
        # เลือกตัวน้อยสุด → ส่วนมืดขยาย ลบจุดขาว (salt) = grayscale erosion
        result = cv2.erode(img, window, borderType=BORDER)
    else:
        # เลือกตัวมากสุด → ส่วนสว่างขยาย ลบจุดดำ (pepper) = grayscale dilation
        result = cv2.dilate(img, window, borderType=BORDER)
    return result, {"ksize": k}


# ============================================================
#  ตัวเรียกใช้จาก app.py
# ============================================================
_HANDLERS = {
    "point_op": point_op,
    "auto_contrast": auto_contrast,
    "linear_filter": linear_filter,
    "nonlinear_filter": nonlinear_filter,
}


def apply_operation(img, operation, form):
    """เรียกจาก /api/edit — คืน (ภาพผลลัพธ์, params ที่จะเก็บลง DB)"""
    if operation not in OPERATIONS:
        raise EditParamError("ไม่รู้จักฟังก์ชันแก้ไขภาพนี้")
    method = form.get("method", "")
    if method not in OPERATIONS[operation]["methods"]:
        raise EditParamError("ไม่รู้จักวิธีที่เลือกในฟังก์ชันนี้")
    result, params = _HANDLERS[operation](img, method, form)
    return result, {"method": method, **params}


def operation_label(operation, params=None):
    """ชื่อที่แสดงในผลลัพธ์/ประวัติ เช่น 'Point Operation · Log'"""
    group = OPERATIONS.get(operation)
    if not group:
        return LEGACY_LABELS.get(operation, operation)
    method_label = group["methods"].get((params or {}).get("method"))
    return f"{group['label']} · {method_label}" if method_label else group["label"]


def params_summary(operation, params=None):
    """สรุปค่าที่ใช้เป็นข้อความสั้น ๆ ไว้โชว์ใต้ภาพผลลัพธ์และในประวัติ"""
    p = params or {}
    method = p.get("method")
    k = p.get("ksize")

    if operation == "point_op" and method == "stretch":
        return f"(r1, s1) = ({p.get('r1')}, {p.get('s1')}) · (r2, s2) = ({p.get('r2')}, {p.get('s2')})"
    if operation == "auto_contrast" and method == "auto":
        return f"ตัดหัวท้าย {p.get('clip', 0):g}% · ยืดช่วง {p.get('a_low')}–{p.get('a_high')} เป็น 0–255"
    if operation == "linear_filter":
        if method == "laplacian":
            return f"kernel 3×3 แบบ {p.get('neighbors', 4)} ทิศ"
        if method == "gaussian":
            return f"kernel {k}×{k} · σ = {p.get('sigma')}"
        return f"kernel {k}×{k}"
    if operation == "nonlinear_filter":
        return f"หน้าต่าง {k}×{k}"

    # ประวัติของฟังก์ชันชุดเดิม
    if operation == "resize":
        return f"{p.get('width', '?')} x {p.get('height', '?')} px"
    if operation == "brightness_contrast":
        return f"α (Contrast) = {p.get('alpha', '?')}, β (Brightness) = {p.get('beta', '?')}"
    return ""
