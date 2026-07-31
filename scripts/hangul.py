"""
중국어 제목을 '중국 발음을 한글로 읽은 표기'로 변환한다.
국립국어원 외래어 표기법(중국어) 규칙을 근사 구현한 것으로, 100% 정확하지는
않지만 사람 이름/드라마 제목 수준에서는 충분히 통용되는 표기를 만든다.
"""

from pypinyin import lazy_pinyin, Style

CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅚㅙㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ",
        "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ",
        "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]

# 성모(초성) 대응
INITIALS = {
    "b": "ㅂ", "p": "ㅍ", "m": "ㅁ", "f": "ㅍ",
    "d": "ㄷ", "t": "ㅌ", "n": "ㄴ", "l": "ㄹ",
    "g": "ㄱ", "k": "ㅋ", "h": "ㅎ",
    "j": "ㅈ", "q": "ㅊ", "x": "ㅅ",
    "zh": "ㅈ", "ch": "ㅊ", "sh": "ㅅ", "r": "ㄹ",
    "z": "ㅉ", "c": "ㅊ", "s": "ㅆ",
}

# 운모(중성/종성/뒤따르는 음절) 대응: final -> (중성, 종성, 뒤에 붙는 글자)
FINALS = {
    "a": ("ㅏ", "", ""),      "o": ("ㅗ", "", ""),      "e": ("ㅓ", "", ""),
    "i": ("ㅣ", "", ""),      "u": ("ㅜ", "", ""),      "v": ("ㅟ", "", ""),
    "ai": ("ㅏ", "", "이"),   "ei": ("ㅔ", "", "이"),
    "ao": ("ㅏ", "", "오"),   "ou": ("ㅓ", "", "우"),
    "an": ("ㅏ", "ㄴ", ""),   "en": ("ㅓ", "ㄴ", ""),
    "ang": ("ㅏ", "ㅇ", ""),  "eng": ("ㅓ", "ㅇ", ""),
    "ong": ("ㅗ", "ㅇ", ""),  "er": ("ㅓ", "ㄹ", ""),
    "ia": ("ㅑ", "", ""),     "ie": ("ㅖ", "", ""),
    "iao": ("ㅑ", "", "오"),  "iu": ("ㅠ", "", ""),
    "ian": ("ㅖ", "ㄴ", ""),  "in": ("ㅣ", "ㄴ", ""),
    "iang": ("ㅑ", "ㅇ", ""), "ing": ("ㅣ", "ㅇ", ""),
    "iong": ("ㅠ", "ㅇ", ""),
    "ua": ("ㅘ", "", ""),     "uo": ("ㅝ", "", ""),
    "uai": ("ㅘ", "", "이"),  "ui": ("ㅜ", "", "이"),
    "uan": ("ㅘ", "ㄴ", ""),  "un": ("ㅜ", "ㄴ", ""),
    "uang": ("ㅘ", "ㅇ", ""), "ueng": ("ㅝ", "ㅇ", ""),
    "ve": ("ㅞ", "", ""),     "van": ("ㅟ", "", "안"),
    "vn": ("ㅟ", "ㄴ", ""),
}

# 통째로 예외 처리하는 음절 (성모 없이 쓰이거나 관용 표기가 굳어진 것)
WHOLE = {
    # 권설음/설치음 + i
    "zi": "쯔", "ci": "츠", "si": "쓰",
    "zhi": "즈", "chi": "츠", "shi": "스", "ri": "르",
    # y- 로 시작하는 음절
    "yi": "이", "ya": "야", "ye": "예", "yao": "야오", "you": "유",
    "yan": "옌", "yin": "인", "yang": "양", "ying": "잉", "yong": "융",
    "yu": "위", "yue": "웨", "yuan": "위안", "yun": "윈",
    # w- 로 시작하는 음절
    "wu": "우", "wa": "와", "wo": "워", "wai": "와이", "wei": "웨이",
    "wan": "완", "wen": "원", "wang": "왕", "weng": "웡",
    # 성모 없는 단독 운모
    "a": "아", "o": "오", "e": "어", "ai": "아이", "ei": "에이",
    "ao": "아오", "ou": "어우", "an": "안", "en": "언",
    "ang": "앙", "eng": "엉", "er": "얼",
    "n": "은", "ng": "응", "hm": "흠", "hng": "흥",
}

# ㅈ, ㅉ, ㅊ 뒤에서는 이중 모음을 단모음으로 적는다 (예: jiang → 장)
JOTA_SIMPLIFY = {"ㅑ": "ㅏ", "ㅕ": "ㅓ", "ㅛ": "ㅗ", "ㅠ": "ㅜ", "ㅖ": "ㅔ"}


def _compose(cho: str, jung: str, jong: str = "") -> str:
    """자모를 한글 음절 한 글자로 합친다."""
    return chr(0xAC00 + (CHO.index(cho) * 21 + JUNG.index(jung)) * 28 + JONG.index(jong))


def _split_syllable(py: str):
    """병음 한 음절을 (성모, 운모)로 나눈다."""
    for size in (2, 1):
        head = py[:size]
        if head in INITIALS:
            return head, py[size:]
    return "", py


def syllable_to_hangul(py: str) -> str:
    """병음 한 음절을 한글 한 표기로 바꾼다."""
    py = py.lower().replace("ü", "v").strip()
    if not py:
        return ""
    if py in WHOLE:
        return WHOLE[py]

    initial, final = _split_syllable(py)

    # j, q, x 뒤의 u 는 실제로는 ü 이다 (ju → 쥐)
    if initial in ("j", "q", "x") and final.startswith("u"):
        final = "v" + final[1:]
    # y 로 시작하지만 WHOLE 에 없는 조합 처리
    if not initial and py.startswith("y"):
        final = py[1:]
    if not initial and py.startswith("w"):
        final = "u" + py[1:]

    if final not in FINALS:
        return py  # 변환 불가 시 병음 그대로 남긴다

    jung, jong, tail = FINALS[final]
    cho = INITIALS.get(initial, "ㅇ")

    if cho in ("ㅈ", "ㅉ", "ㅊ") and jung in JOTA_SIMPLIFY:
        jung = JOTA_SIMPLIFY[jung]

    return _compose(cho, jung, jong) + tail


def _is_han(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def to_hangul(text: str) -> str:
    """
    한자 문자열 전체를 한글 발음 표기로 바꾼다.
    한자가 연속된 구간은 통째로 pypinyin 에 넘겨야 多音字(다음자)가 문맥에 맞게
    읽힌다. 예: 长安 을 글자별로 처리하면 zhang 으로 잘못 읽혀 '장안'이 된다.
    """
    if not text:
        return ""

    out = []
    buf = []

    def flush():
        if not buf:
            return
        chunk = "".join(buf)
        for py in lazy_pinyin(chunk, style=Style.NORMAL):
            out.append(syllable_to_hangul(py))
        buf.clear()

    for ch in text:
        if _is_han(ch):
            buf.append(ch)
        else:
            flush()
            out.append(" " if ch.isspace() else ch)
    flush()

    return "".join(out).strip()


if __name__ == "__main__":
    tests = [
        "生命树", "太平年", "正义女神", "唐宫奇案", "御赐小仵作",
        "胡歌", "杨紫", "白宇", "朱亚文", "周雨彤", "佘诗曼",
        "辛芷蕾", "白鹿", "王星越", "姚安娜", "龚俊", "魏大勋",
        "北京", "上海", "天津", "长安", "琅琊榜", "甄嬛传",
    ]
    for t in tests:
        print(f"{t:10s} {' '.join(lazy_pinyin(t)):24s} -> {to_hangul(t)}")
