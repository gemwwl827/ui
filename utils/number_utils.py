import re
from decimal import Decimal, localcontext, ROUND_HALF_UP

# 可调：最终输出前保留的小数位（避免二进制浮点尾巴）
_OUTPUT_NDIGITS = 12

def _to_float(d: Decimal, ndigits: int = _OUTPUT_NDIGITS) -> float:
    if d is None:
        return None
    q = Decimal(f"1e-{ndigits}")
    d = d.quantize(q, rounding=ROUND_HALF_UP).normalize()
    f = float(d)
    return 0.0 if abs(f) < 1e-15 else f  # 避免 -0.0

def extract_number_smart(raw_text):
    """
    智能提取页面/Excel中的数值，返回 float 或 bool 或 None
    支持：
      - 百分比: "2%" / "２％" → 0.02
      - 金额: "980.00万"→9_800_000；"1,100,000.00元"→1_100_000；"3.2亿"→320_000_000
      - 布尔: "true"/"false"（不区分大小写）
      - 持续时间: "7.29年"→7.29；"8.0年"→8.0；"6个月"→0.5；"90天"→≈0.2466；"2季度"→0.5；"3周"→≈0.0577
      - 纯数字: "1234.56" → 1234.56
      - 无值/占位符: "--"、空串 → None
    兼容：传入 bool/int/float 也可用（float 会被 Decimal(str(x)) 纠偏后输出）
    """
    # ===== 1) 直接兼容非字符串输入 =====
    if raw_text is None:
        return None
    # 布尔优先
    if isinstance(raw_text, bool):
        return bool(raw_text)
    # 数值：int/float 走 Decimal(str(x)) 纠偏
    if isinstance(raw_text, (int, float)):
        with localcontext() as ctx:
            ctx.prec = 28
            ctx.rounding = ROUND_HALF_UP
            try:
                # 注意：对 float 必须用 str(x) 而不是直接 Decimal(x)，避免把二进制误差带进来
                d = Decimal(str(raw_text))
            except Exception:
                return None
            return _to_float(d)

    # ===== 2) 字符串路径（原逻辑的兼容 + Decimal 精确解析）=====
    # 去掉不可见字符 & 全角空格
    text = str(raw_text).replace("\u200b", "").replace("　", " ").strip()
    if text in ["", "--"]:
        return None

    # 标准化
    t = (text
         .replace(",", "")         # 去千分位
         .replace("％", "%")       # 中文百分号
         .lower()
         .strip())

    # 布尔
    if t in ("true", "false"):
        return t == "true"

    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP

        # 百分比
        if t.endswith("%"):
            m = re.search(r"[-+]?\d*\.?\d+", t)
            if not m:
                return None
            try:
                val = Decimal(m.group(0)) / Decimal(100)
            except Exception:
                return None
            return _to_float(val)

        # 抓数值（为后续单位换算做准备）
        num_match = re.search(r"[-+]?\d*\.?\d+", t)
        if not num_match:
            return None
        try:
            num = Decimal(num_match.group(0))
        except Exception:
            return None

        # 金额单位（优先匹配复合写法）
        if "亿元" in t:
            return _to_float(num * Decimal("1e8"))
        if "万元" in t or ("万" in t and "元" in t):
            return _to_float(num * Decimal("1e4"))
        if "亿" in t and "元" in t:
            return _to_float(num * Decimal("1e8"))
        if "亿" in t:
            return _to_float(num * Decimal("1e8"))
        if "万" in t:
            return _to_float(num * Decimal("1e4"))
        if "元" in t:
            return _to_float(num)

        # 持续时间单位（统一换算为“年”）
        if "年" in t:
            return _to_float(num)
        if "季度" in t or "季" in t:
            return _to_float(num / Decimal(4))
        if "月" in t:
            return _to_float(num / Decimal(12))
        if "周" in t:
            return _to_float(num / Decimal(52))
        if "天" in t or "日" in t:
            return _to_float(num / Decimal(365))

        # 默认：纯数字
        return _to_float(num)
