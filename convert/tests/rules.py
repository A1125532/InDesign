# rules.py
# 半自動偵測題目（smart-rule）：題號 + 語意 + 結構 + 字符比例 綜合判斷
import re
from dataclasses import dataclass
from typing import Optional

# 既有標籤開頭
TAG_HEAD = re.compile(r'^\[(problem|option|formula|answer|title|instruction)\]\s*', re.I)

# 題號樣式（常見：1.、2)、（3）、3、、Q1.、第1題）
PROBLEM_HEAD = re.compile(
    r'^\s*(?:'
    r'\d+\s*[\.\)、）:]'                # 1. / 2) / 3）/ 4:
    r'|[（(]\s*\d+\s*[)）]'            # （3） / (12)
    r'|Q\s*\d+\s*[.:、)]'              # Q1. / Q2:
    r'|第\s*\d+\s*[題题]'               # 第3題
    r')'
)

# 選項起始（單行）
OPTION_HEAD = re.compile(r'^\s*[（(]?\s*[A-Ea-e]\s*[)）]\b')
# 文中多個選項標記（用來補標 [option]）
OPTION_INLINE = re.compile(r'(?<!\[option\]\s)([（(]\s*[A-Ea-e]\s*[)）])')

# 可能是解答/解析的語彙
ANSWER_HINT = re.compile(r'(?:^|\b)(解答|解析|證明|推導|proof|solution|ans(?:wer)?)(?:$|\b)', re.I)

# 一些常見「題目語意」關鍵詞（可視任務調整）
PROBLEM_KEYWORDS = [
    r'已知', r'若', r'求', r'計算', r'證明', r'化簡', r'下列何者', r'下列.*正確', r'選出', r'下列敘述',
    r'如右圖', r'如圖', r'函數', r'極限', r'導數', r'方程', r'不等式', r'機率', r'幾何', r'向量',
    r'det', r'矩陣', r'min', r'max', r'求值', r'滿足', r'條件', r'定義'
]
PROBLEM_KEYWORDS_RE = re.compile('|'.join(PROBLEM_KEYWORDS))

MATH_CHARS_RE = re.compile(r'[\+\-\*/=<>∈∉≤≥≈≠^√πΣ∑∏∫ΔΩθλαβγ]|\\frac|\\sqrt|\\sum|\\int')

END_QUESTION_RE = re.compile(r'[？?]$')
END_STATEMENT_RE = re.compile(r'[。．\.…]$')

@dataclass
class SmartRuleConfig:
    # 分數權重（可調）
    w_has_number_head: int = 3         # 題號開頭
    w_has_keywords: int = 2            # 題目語意關鍵詞
    w_has_math_sign: int = 2           # 數學符號/LaTeX 痕跡
    w_is_long_enough: int = 1          # 長度門檻
    w_end_question_mark: int = 1       # 問句結尾
    w_end_statement_mark: int = 0      # 句號結尾（弱）
    # 長度／比例門檻
    min_len_problem: int = 8
    max_punct_ratio_for_problem: float = 0.55
    # 判題門檻
    score_threshold_problem: int = 4
    # 是否在文中補 [option]
    enable_inline_option_tagging: bool = True

DEFAULT_CFG = SmartRuleConfig()

def _punct_ratio(s: str) -> float:
    if not s: return 1.0
    punct = sum(ch in '，,。．.；;：:？?！!、—-()（）[]【】「」『』' for ch in s)
    return punct / max(len(s), 1)

def _has_math(s: str) -> bool:
    return bool(MATH_CHARS_RE.search(s))

def _has_problem_keywords(s: str) -> bool:
    return bool(PROBLEM_KEYWORDS_RE.search(s))

def _score_problem_like(s: str, cfg: SmartRuleConfig) -> int:
    score = 0
    if PROBLEM_HEAD.match(s):
        score += cfg.w_has_number_head
    if _has_problem_keywords(s):
        score += cfg.w_has_keywords
    if _has_math(s):
        score += cfg.w_has_math_sign
    if len(s) >= cfg.min_len_problem:
        score += cfg.w_is_long_enough
    if END_QUESTION_RE.search(s):
        score += cfg.w_end_question_mark
    elif END_STATEMENT_RE.search(s):
        score += cfg.w_end_statement_mark
    # 過多標點（像是純選項/碎片）→ 降低可信度
    if _punct_ratio(s) > cfg.max_punct_ratio_for_problem:
        score -= 1
    return score

def auto_tag_smart(content: str, cfg: Optional[SmartRuleConfig] = None) -> str:
    """
    半自動偵測題目：
      1) 保留已標記行
      2) 明確選項開頭 → [option]
      3) 非選項也非已標 → 以加權分數是否達閾值來決定要不要加 [problem]
      4) 補齊文中 (A)(B)... 的 [option] 標籤（可關）
      5) 含「解答/解析/證明/solution」等 → 優先略過 problem 標記，可自行標 [answer]
    """
    if cfg is None:
        cfg = DEFAULT_CFG

    s = (content or "").strip()
    if not s:
        return s

    # ① 已有標籤 → 原樣返回
    if TAG_HEAD.match(s):
        return s

    # ② 解答/解析 類 → 可選擇標記為 [answer]（預設只避開 problem）
    if ANSWER_HINT.search(s):
        # 視需求：return f"[answer] {s}"
        return s  # 保留原樣或改成上行

    # ③ 明確選項開頭（(A)/(B)/（C）…）
    if OPTION_HEAD.match(s):
        s = f"[option] {s}"
    else:
        # ④ 智慧判題（只在「不是選項開頭」時）
        score = _score_problem_like(s, cfg)
        if score >= cfg.score_threshold_problem:
            s = f"[problem] {s}"
        # else: 低分 → 不加 problem，保持原樣

    # ⑤ 文中補齊 [option] 標籤（例如一行內同時有 (A)(B)(C)）
    if cfg.enable_inline_option_tagging:
        s = OPTION_INLINE.sub(r'[option] \1', s)

    return s