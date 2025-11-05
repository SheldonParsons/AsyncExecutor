import random
import time
import datetime
import json
import uuid
import re
import urllib.parse


class ExceptionResult:
    pass


class MockFuncStaticFuncsMixin:

    @staticmethod
    def _default_function(*args, **kwargs):
        return 'null'

    @staticmethod
    def boolean(probability_true, probability_false, default_return=True):
        probability_false = int(probability_false)
        probability_true = int(probability_true)
        if probability_true + probability_false > 100 or probability_true < 1 or probability_false < 1:
            return ""

        random_value = random.uniform(0, 100)
        if random_value < probability_true:
            return True
        elif random_value < probability_true + probability_false:
            return False
        else:
            if default_return == "true":
                return True
            elif default_return == "false":
                return False
            else:
                return ""

    @staticmethod
    def natural(min_val, max_val):
        min_val = int(min_val)
        max_val = int(max_val)
        if not (isinstance(min_val, (int, float)) and isinstance(max_val, (int, float))):
            return ""
        if min_val < 0 or max_val < 0 or min_val > max_val:
            return ""

        return random.randint(int(min_val), int(max_val))

    @staticmethod
    def integer(min_val, max_val):
        min_val = int(min_val)
        max_val = int(max_val)
        if isinstance(min_val, int) is False and isinstance(max_val, int) is False:
            return ""
        if min_val > max_val:
            return ""

        return random.randint(min_val, max_val)

    @staticmethod
    def float(min_val, max_val, min_decimal, max_decimal):
        min_val = int(min_val)
        max_val = int(max_val)
        min_decimal = int(min_decimal)
        max_decimal = int(max_decimal)
        if not all(isinstance(x, int) for x in [min_val, max_val, min_decimal, max_decimal]):
            return ""
        if min_val > max_val or min_decimal > max_decimal or min_decimal < 0 or max_decimal < 0:
            return ""

        integer_part = random.randint(min_val, max_val)
        decimal_places = random.randint(min_decimal, max_decimal)
        decimal_part = random.randint(0, 10 ** decimal_places - 1)
        return float(f"{integer_part}.{decimal_part:0{decimal_places}}")

    @staticmethod
    def string(chars: str, min_length: int, max_length: int) -> str:
        try:
            max_length = int(max_length)
            min_length = int(min_length)
        except ValueError:
            return ""
        if max_length < min_length:
            return ""
        if min_length < 0 or max_length < 0:
            return ""
        length = random.randint(int(min_length), int(max_length))
        s = ''.join(random.choices(chars, k=length))
        return s

    @staticmethod
    def character(type_str):
        if not isinstance(type_str, str) or not type_str:
            return ""
        # 去重并排除空白字符（可选）
        candidates = [ch for ch in type_str if not ch.isspace()]
        if not candidates:
            return ""
        return random.choice(candidates)

    @staticmethod
    def date(format_str):
        if not isinstance(format_str, str):
            return ""

        now = datetime.datetime.now()
        year = random.randint(1900, now.year)
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # 简化处理，避免日期无效

        return format_str.replace("yyyy", str(year)) \
            .replace("MM", str(month).zfill(2)) \
            .replace("dd", str(day).zfill(2))

    @staticmethod
    def datetime(format_str):
        if not isinstance(format_str, str):
            return ""

        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        return format_str.replace("HH", str(hour).zfill(2)) \
            .replace("mm", str(minute).zfill(2)) \
            .replace("ss", str(second).zfill(2))

    @staticmethod
    def now(precision, format_str, offset="", mode="start"):
        units = {
            "year": "YYYY", "month": "MM", "week": "week",
            "day": "DD", "hour": "HH", "minute": "mm", "second": "ss"
        }

        if precision not in units or mode not in ["start", "end"]:
            return ""

        now = datetime.datetime.now()

        # 处理时间偏移
        if offset:
            match = re.match(r"^([+-]?\d+)\s*(year|month|week|day|hour|minute|second)$", offset)
            if not match:
                return ""

            amount = int(match.group(1))
            unit = match.group(2)

            if unit == "year":
                now = now.replace(year=now.year + amount)
            elif unit == "month":
                month = now.month + amount
                year = now.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                now = now.replace(year=year, month=month)
            elif unit == "week":
                now += datetime.timedelta(weeks=amount)
            elif unit == "day":
                now += datetime.timedelta(days=amount)
            elif unit == "hour":
                now += datetime.timedelta(hours=amount)
            elif unit == "minute":
                now += datetime.timedelta(minutes=amount)
            elif unit == "second":
                now += datetime.timedelta(seconds=amount)

        # 根据模式调整时间
        if mode == "start":
            if precision == "year":
                now = now.replace(month=1, day=1, hour=0, minute=0, second=0)
            elif precision == "month":
                now = now.replace(day=1, hour=0, minute=0, second=0)
            elif precision == "week":
                # 简化为周一开始
                now = now - datetime.timedelta(days=now.weekday())
                now = now.replace(hour=0, minute=0, second=0)
            elif precision == "day":
                now = now.replace(hour=0, minute=0, second=0)
            elif precision == "hour":
                now = now.replace(minute=0, second=0)
            elif precision == "minute":
                now = now.replace(second=0)
        elif mode == "end":
            if precision == "year":
                now = now.replace(month=12, day=31, hour=23, minute=59, second=59)
            elif precision == "month":
                # 获取下个月第一天然后减一天
                next_month = now.replace(day=28) + datetime.timedelta(days=4)
                last_day = next_month - datetime.timedelta(days=next_month.day)
                now = last_day.replace(hour=23, minute=59, second=59)
            elif precision == "week":
                # 简化为周日结束
                now = now + datetime.timedelta(days=6 - now.weekday())
                now = now.replace(hour=23, minute=59, second=59)
            elif precision == "day":
                now = now.replace(hour=23, minute=59, second=59)
            elif precision == "hour":
                now = now.replace(minute=59, second=59)
            elif precision == "minute":
                now = now.replace(second=59)

        return format_str.replace("yyyy", str(now.year)) \
            .replace("MM", str(now.month).zfill(2)) \
            .replace("dd", str(now.day).zfill(2)) \
            .replace("HH", str(now.hour).zfill(2)) \
            .replace("mm", str(now.minute).zfill(2)) \
            .replace("ss", str(now.second).zfill(2))

    @staticmethod
    def time(format_str):
        if not isinstance(format_str, str):
            return ""

        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        return format_str.replace("HH", str(hour).zfill(2)) \
            .replace("mm", str(minute).zfill(2)) \
            .replace("ss", str(second).zfill(2))

    @staticmethod
    def timestamp(precision, offset):
        if precision not in ["s", "ms"]:
            return ""
        ts = time.time() * 1000
        # 处理时间偏移
        if offset:
            match = re.match(r"^([+-]?\d+)\s*(year|month|week|day|hour|minute|second|msecond)$", offset)
            if not match:
                return ""

            amount = int(match.group(1))
            unit = match.group(2)

            if unit == "year":
                ts = ts + (12 * 30 * 24 * 60 * 60 * 1000 * amount)
            elif unit == "month":
                ts = ts + (30 * 24 * 60 * 60 * 1000 * amount)
            elif unit == "week":
                ts = ts + (7 * 24 * 60 * 60 * 1000 * amount)
            elif unit == "day":
                ts = ts + (24 * 60 * 60 * 1000 * amount)
            elif unit == "hour":
                ts = ts + (60 * 60 * 1000 * amount)
            elif unit == "minute":
                ts = ts + (60 * 1000 * amount)
            elif unit == "second":
                ts = ts + (1000 * amount)
            elif unit == "msecond":
                ts = ts + amount
        return int(ts / 1000) if precision == "s" else int(ts)

    @staticmethod
    def id():
        def calculate_check_code(id_base):
            weight = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
            check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

            total = sum(int(a) * b for a, b in zip(id_base, weight))
            return check_codes[total % 11]

        # 地址码
        province_code = random.randint(11, 65)
        city_code = random.randint(1, 30)
        district_code = random.randint(1, 99)
        address_code = f"{province_code:02d}{city_code:02d}{district_code:02d}"

        # 出生日期
        year = random.randint(1900, datetime.datetime.now().year)
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # 简化处理
        birth_date = f"{year}{month:02d}{day:02d}"

        # 顺序码
        sequence_code = f"{random.randint(0, 999):03d}"

        # 计算校验码
        id_base = address_code + birth_date + sequence_code
        check_code = calculate_check_code(id_base)

        return id_base + check_code

    @staticmethod
    def qq():
        length = random.randint(5, 11)
        first_digit = random.randint(1, 9)
        qq = str(first_digit)
        for _ in range(length - 1):
            qq += str(random.randint(0, 9))
        return qq

    @staticmethod
    def phone():
        second_digit = random.choice(['3', '4', '5', '7'])
        phone = '1' + second_digit
        for _ in range(9):
            phone += str(random.randint(0, 9))
        return phone

    @staticmethod
    def landline():
        area_codes = [
            "010",
            "021",
            "022",
            "023",
            "024",
            "025",
            "027",
            "028",
            "029",
            "0311",
            "0371",
            "0531",
            "0551",
            "0571",
            "0591",
            "0731",
        ]
        area_code = random.choice(area_codes)
        number = ''.join(str(random.randint(0, 9)) for _ in range(8))
        return f"{area_code}-{number}"

    @staticmethod
    def gender(gender=None):
        if gender in ["male", "female"]:
            return gender
        if gender is not None:
            return ""
        return random.choice(["male", "female"])

    # 中文姓氏和名字列表
    surnames = [
        "赵",
        "钱",
        "孙",
        "李",
        "周",
        "吴",
        "郑",
        "王",
        "冯",
        "陈",
        "褚",
        "卫",
        "蒋",
        "沈",
        "韩",
        "杨",
        "朱",
        "秦",
        "尤",
        "许",
        "何",
        "吕",
        "施",
        "张",
        "孔",
        "曹",
        "严",
        "华",
        "金",
        "魏",
        "陶",
        "姜",
        "戚",
        "谢",
        "邹",
        "孙",
        "章",
        "鲁",
        "韦",
        "常",
        "蔡",
        "杜",
        "阮",
        "雷",
        "贾",
        "尹",
        "邱",
        "方",
        "林",
        "袁",
        "罗",
        "邵",
        "程",
        "孟",
        "唐",
        "许",
        "董",
        "魏",
        "蔺",
        "彭",
        "曾",
        "卢",
        "鲍",
        "卢",
        "齐",
        "和",
        "戴",
        "陆",
        "卓",
        "钱",
        "潘",
        "袁",
        "欧阳",
        "欧",
        "焦",
        "白",
        "黄",
        "邵",
        "郑",
        "陶",
        "杜",
    ]
    first_name_chars = [
        "一",
        "乙",
        "三",
        "万",
        "丈",
        "七",
        "八",
        "九",
        "十",
        "百",
        "千",
        "万",
        "亿",
        "天",
        "地",
        "人",
        "大",
        "中",
        "小",
        "上",
        "下",
        "左",
        "右",
        "东",
        "西",
        "南",
        "北",
        "国",
        "家",
        "民",
        "风",
        "山",
        "水",
        "日",
        "月",
        "星",
        "光",
        "火",
        "土",
        "木",
        "金",
        "水",
        "土",
        "安",
        "明",
        "定",
        "宇",
        "天",
        "光",
        "海",
        "山",
        "立",
        "勇",
        "信",
        "才",
        "志",
        "远",
        "成",
        "升",
        "义",
        "志",
        "超",
        "俊",
        "华",
        "星",
        "宇",
        "庆",
        "欣",
        "乐",
        "春",
        "夏",
        "秋",
        "冬",
        "胜",
        "昌",
        "东",
        "辉",
        "强",
        "建",
        "达",
        "正",
        "和",
        "尚",
        "振",
        "福",
        "耀",
        "贤",
        "达",
        "勇",
        "哲",
        "凯",
        "俊",
        "婷",
        "芬",
        "萍",
        "霞",
        "玲",
        "晶",
        "丽",
        "倩",
        "婷",
        "芸",
        "文",
        "书",
        "丹",
        "静",
        "妍",
        "婷",
        "欣",
        "媛",
        "晶",
        "璇",
        "如",
        "梦",
        "娇",
        "蓉",
        "爱",
        "彤",
        "雯",
        "思",
        "梅",
        "舒",
        "畅",
        "雪",
        "琪",
        "莹",
        "昕",
        "佳",
        "芮",
        "兰",
        "琳",
        "依",
        "佳",
        "灵",
        "怡",
        "丽",
        "艺",
        "晓",
        "慧",
        "如",
        "爽",
        "雪",
        "然",
        "玲",
        "萍",
        "怡",
        "媛",
        "瑶",
        "雪",
        "雪",
        "霞",
        "霞",
        "萍",
        "紫",
        "琳",
        "倩",
        "洁",
        "丽",
        "欣",
        "丽",
        "蓉",
        "欣",
        "悦",
        "澜",
        "欣",
        "若",
        "雪",
        "珊",
        "莹",
        "美",
        "娜",
        "聪",
        "慧",
        "萍",
        "琪",
        "玲",
        "霞",
        "玲",
        "瑶",
        "莉",
        "秋",
        "芹",
        "明",
        "怡",
        "安",
        "琪",
        "琳",
        "丹",
        "琴",
        "柳",
        "艳",
        "柔",
        "竹",
        "婷",
        "慧",
        "心",
        "荣",
        "俊",
        "婷",
        "芳",
        "然",
        "芬",
        "婧",
        "娟",
        "灵",
        "晖",
        "诗",
        "忆",
        "思",
        "燕",
        "雯",
        "颖",
        "凯",
        "恬",
        "爱",
        "怡",
        "琳",
        "燕",
        "佳",
        "馨",
        "娇",
        "巧",
        "佳",
        "雯",
        "蕾",
        "甜",
        "蓉",
        "琼",
        "丽",
        "娅",
        "芬",
        "瑾",
        "璇",
        "怡",
        "丽",
        "雯",
        "婷",
        "玥",
        "艳",
        "玲",
        "莉",
        "璇",
        "婕",
        "岚",
        "沁",
        "晶",
        "丹",
        "玉",
        "雪",
        "艳",
        "娟",
        "玲",
        "阳",
        "婷",
        "兰",
        "雨",
        "玲",
        "莹",
        "晨",
        "霞",
        "岚",
        "芬",
        "琪",
        "琳",
        "婷",
        "怡",
        "欣",
        "慧",
        "琴",
        "倩",
        "娅",
        "怡",
        "莉",
        "露",
        "雪",
        "芬",
        "晨",
        "燕",
        "晴",
        "菁",
        "瑶",
    ]

    @classmethod
    def cname(cls):
        surname = random.choice(cls.surnames)
        name_length = 1 if random.random() < 0.5 else 2
        name = ''.join(random.choices(cls.first_name_chars, k=name_length))
        return surname + name

    @classmethod
    def cfirst(cls):
        return random.choice(cls.surnames)

    @classmethod
    def clast(cls):
        name_length = 1 if random.random() < 0.5 else 2
        return ''.join(random.choices(cls.first_name_chars, k=name_length))

    # 英文名字列表
    first_names = [
        "John",
        "James",
        "Michael",
        "David",
        "William",
        "Joseph",
        "Charles",
        "Thomas",
        "Daniel",
        "Matthew",
        "Andrew",
        "Joshua",
        "Ryan",
        "Ethan",
        "Nicholas",
        "Jacob",
        "Alexander",
        "Samuel",
        "Henry",
        "Benjamin",
        "Christopher",
        "Elijah",
        "Caleb",
        "Nathan",
        "Jack",
        "Luke",
        "Gabriel",
        "Mason",
        "Owen",
        "Liam",
        "Sophia",
        "Olivia",
        "Emma",
        "Ava",
        "Isabella",
        "Mia",
        "Amelia",
        "Harper",
        "Evelyn",
        "Abigail",
        "Ella",
        "Scarlett",
        "Grace",
        "Aria",
        "Chloe",
        "Lily",
        "Zoey",
        "Stella",
        "Victoria",
        "Lucy",
    ]
    last_names = [
        "Smith",
        "Johnson",
        "Brown",
        "Taylor",
        "Anderson",
        "Thomas",
        "Jackson",
        "White",
        "Harris",
        "Martin",
        "Thompson",
        "Garcia",
        "Martinez",
        "Roberts",
        "Clark",
        "Rodriguez",
        "Lewis",
        "Walker",
        "Allen",
        "Young",
    ]
    middle_names = [
        "Alexander",
        "Michael",
        "Marie",
        "Rose",
        "James",
        "Grace",
        "Elizabeth",
        "Ann",
        "Lee",
        "Evelyn",
    ]

    @classmethod
    def name(cls, generate_middle_name):
        first_name = random.choice(cls.first_names)
        last_name = random.choice(cls.last_names)

        if generate_middle_name == "true":
            middle_name = random.choice(cls.middle_names)
            return f"{first_name} {middle_name} {last_name}"
        return f"{first_name} {last_name}"

    @classmethod
    def first(cls):
        return random.choice(cls.first_names)

    @classmethod
    def last(cls):
        return random.choice(cls.last_names)

    chinese_chars = [
        "一",
        "丁",
        "七",
        "万",
        "丈",
        "三",
        "上",
        "下",
        "不",
        "与",
        "丑",
        "专",
        "丰",
        "临",
        "个",
        "中",
        "丰",
        "优",
        "传",
        "亨",
        "亩",
        "共",
        "关",
        "兴",
        "兰",
        "黄",
        "李",
        "张",
        "王",
        "方",
        "孔",
        "日",
        "月",
        "火",
        "水",
        "土",
        "山",
        "田",
        "甘",
        "木",
        "石",
        "红",
        "绿",
        "青",
        "白",
        "蓝",
        "紫",
        "黑",
        "猫",
        "狗",
        "牛",
        "羊",
        "兔",
        "鼠",
        "龙",
        "凤",
        "猪",
        "鸡",
        "鹰",
        "虫",
        "鱼",
        "花",
        "草",
        "树",
        "雷",
        "电",
        "风",
        "雪",
        "雨",
        "霜",
        "雾",
        "我",
        "你",
        "他",
        "她",
        "它",
        "是",
        "有",
        "在",
        "从",
        "向",
        "给",
        "来",
        "走",
        "看",
        "吃",
        "喝",
        "睡",
        "打",
        "玩",
        "听",
        "说",
        "读",
        "写",
        "做",
        "学",
        "上",
        "下",
        "进",
        "出",
        "问",
        "答",
        "坐",
        "站",
        "看",
        "了",
        "知",
    ]

    @classmethod
    def ctitle(cls, min_length, max_length):
        min_length = int(min_length)
        max_length = int(max_length)
        if min_length < 1 or max_length < 1 or min_length > max_length:
            return ""
        length = random.randint(min_length, max_length)
        result = ''.join(random.choices(cls.chinese_chars, k=length))
        return result

    @classmethod
    def cword(cls, min_length, max_length):
        min_length = int(min_length)
        max_length = int(max_length)
        return cls.ctitle(min_length, max_length)

    @classmethod
    def cparagraph(cls, min_sentences, max_sentences):
        min_sentences = int(min_sentences)
        max_sentences = int(max_sentences)
        if min_sentences < 1 or max_sentences < 1 or min_sentences > max_sentences:
            return ""

        num_sentences = random.randint(min_sentences, max_sentences)
        sentences = []
        for _ in range(num_sentences):
            sentence_length = random.randint(10, 20)
            sentence = ''.join(random.choices(cls.chinese_chars, k=sentence_length))
            sentences.append(sentence + "。")
        return ' '.join(sentences)

    @classmethod
    def csentence(cls, min_length, max_length):
        min_length = int(min_length)
        max_length = int(max_length)
        if min_length < 1 or max_length < 1 or min_length > max_length:
            return ""

        length = random.randint(min_length, max_length)
        return ''.join(random.choices(cls.chinese_chars, k=length))

    english_words = [
        "the",
        "is",
        "in",
        "and",
        "to",
        "a",
        "of",
        "for",
        "on",
        "with",
        "by",
        "an",
        "this",
        "that",
        "I",
        "you",
        "we",
        "he",
        "she",
        "it",
        "they",
        "are",
        "was",
        "were",
        "be",
        "have",
        "had",
        "will",
        "can",
        "could",
        "do",
        "does",
        "did",
        "doing",
        "say",
        "says",
        "said",
        "make",
        "makes",
        "made",
        "go",
        "goes",
        "went",
        "come",
        "comes",
        "came",
        "know",
        "knows",
        "knew",
        "want",
        "wants",
        "wanted",
        "see",
        "sees",
        "saw",
        "look",
        "looks",
        "looking",
        "find",
        "finds",
        "found",
        "think",
        "thinks",
        "thought",
        "talk",
        "talks",
        "talked",
        "work",
        "works",
        "worked",
        "play",
        "plays",
        "played",
        "eat",
        "eats",
        "ate",
        "drink",
        "drinks",
        "drank",
        "sleep",
        "sleeps",
        "slept",
        "read",
        "reads",
        "reading",
        "write",
        "writes",
        "wrote",
        "write",
        "writes",
        "wrote",
        "learn",
        "learns",
        "learned",
        "study",
        "studies",
        "studied",
        "teach",
        "teaches",
        "taught",
        "help",
        "helps",
        "helped",
        "try",
        "tries",
        "tried",
        "ask",
        "asks",
        "asked",
        "answer",
        "answers",
        "answered",
        "understand",
        "understands",
        "understood",
    ]

    @classmethod
    def paragraph(cls, min_sentences, max_sentences):
        min_sentences = int(min_sentences)
        max_sentences = int(max_sentences)
        if min_sentences < 1 or max_sentences < 1 or min_sentences > max_sentences:
            return ""

        num_sentences = random.randint(min_sentences, max_sentences)
        sentences = []
        for _ in range(num_sentences):
            sentence_length = random.randint(10, 20)
            sentence = ' '.join(random.choices(cls.english_words, k=sentence_length))
            sentences.append(sentence.capitalize() + ".")
        return ' '.join(sentences)

    @classmethod
    def sentence(cls, min_words, max_words):
        min_words = int(min_words)
        max_words = int(max_words)
        if min_words < 1 or max_words < 1 or min_words > max_words:
            return ""

        num_words = random.randint(min_words, max_words)
        sentence = ' '.join(random.choices(cls.english_words, k=num_words))
        return sentence.capitalize() + "."

    @staticmethod
    def word(min_length, max_length):
        min_length = int(min_length)
        max_length = int(max_length)
        if min_length < 1 or max_length < 1 or min_length > max_length:
            return ""

        length = random.randint(min_length, max_length)
        letters = "abcdefghijklmnopqrstuvwxyz"
        return ''.join(random.choices(letters, k=length))

    @classmethod
    def title(cls, min_words, max_words):
        min_words = int(min_words)
        max_words = int(max_words)
        if min_words < 1 or max_words < 1 or min_words > max_words:
            return ""

        num_words = random.randint(min_words, max_words)
        words = random.choices(cls.english_words, k=num_words)
        title = ' '.join(word.capitalize() for word in words)
        return title

    regions = ["华北", "华东", "华南", "华中", "西南", "西北", "东北"]
    provinces = ["北京", "上海", "天津", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽",
                 "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃",
                 "青海", "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门"]

    @classmethod
    def region(cls):
        return random.choice(cls.regions)

    @classmethod
    def province(cls):
        return random.choice(cls.provinces)

    @classmethod
    def city(cls, include_province):
        if include_province not in ["true", "false"]:
            return ""

        cities = ["北京", "上海", "广州", "深圳", "成都", "杭州", "武汉", "南京", "西安"]
        if include_province == "true":
            return f"{random.choice(cities)} ({random.choice(cls.provinces)})"
        return random.choice(cities)

    @classmethod
    def county(cls, include_province_city):
        if include_province_city not in ["true", "false"]:
            return ""

        zones = ["浦东新区", "朝阳区", "天河区", "福田区", "武侯区"]
        if include_province_city == "true":
            return f"{random.choice(zones)} ({random.choice(cls.provinces)} {random.choice(['北京', '上海', '广州', '深圳', '成都'])})"
        return random.choice(zones)

    @staticmethod
    def zip():
        return f"{random.randint(100000, 999999)}"

    @staticmethod
    def email():
        username = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(5, 10)))
        domain = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(3, 6)))
        tld = random.choice(["com", "net", "org", "cn"])
        return f"{username}@{domain}.{tld}"

    @staticmethod
    def ip():
        return ".".join(str(random.randint(0, 255)) for _ in range(4))

    @staticmethod
    def url(protocol):
        domain = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(5, 10)))
        tld = random.choice(["com", "net", "org"])
        path = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(3, 6)))
        return f"{protocol}://www.{domain}.{tld}/{path}"

    @staticmethod
    def domain(top_level_domain):
        domain = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(5, 10)))
        return f"{domain}.{top_level_domain}"

    @staticmethod
    def protocol():
        return random.choice(["http", "https", "ftp", "sftp"])

    @staticmethod
    def tld():
        return random.choice(["com", "net", "org", "edu", "gov"])

    @staticmethod
    def dataimage(image_size, text, color):
        match = re.match(r"(\d+)x(\d+)", str(image_size))
        if not match:
            return ""

        width, height = int(match.group(1)), int(match.group(2))
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        svg += f'<rect width="100%" height="100%" fill="{color}"/>'
        svg += f'<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="white">{text}</text>'
        svg += '</svg>'
        encoded = urllib.parse.quote(svg)
        return f"data:image/svg+xml;charset=UTF-8,{encoded}"

    @staticmethod
    def color():
        return "#{:06x}".format(random.randint(0, 0xFFFFFF)).upper()

    @classmethod
    def hex(cls):
        return cls.color()

    @staticmethod
    def rgba():
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        a = round(random.random(), 2)
        return f"rgba({r}, {g}, {b}, {a})"

    @staticmethod
    def rgb():
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        return f"rgb({r}, {g}, {b})"

    @staticmethod
    def hsl():
        h = random.randint(0, 360)
        s = random.randint(0, 100)
        l = random.randint(0, 100)
        return f"hsl({h}, {s}%, {l}%)"

    @staticmethod
    def regexp(regex):
        try:
            # 简化实现：仅支持简单正则
            if regex == "[a-z]":
                return random.choice("abcdefghijklmnopqrstuvwxyz")
            elif regex == "[A-Z]":
                return random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            elif regex == "[0-9]":
                return str(random.randint(0, 9))
            elif regex == ".":
                return random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
            else:
                return ""
        except:
            return ""

    # 注意：完整的正则表达式生成器非常复杂，这里只提供简化版本
    @staticmethod
    def generate_random_string_from_regex(regex_pattern):
        try:
            # 简化实现：仅支持基本字符集
            if regex_pattern == "[a-z]":
                return random.choice("abcdefghijklmnopqrstuvwxyz")
            elif regex_pattern == "[A-Z]":
                return random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            elif regex_pattern == "[0-9]":
                return str(random.randint(0, 9))
            elif regex_pattern == "[a-zA-Z0-9]":
                return random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
            else:
                return ""
        except:
            return ""

    current_number = 0

    @staticmethod
    def increment(step):
        step = int(step)
        if not isinstance(step, int) or step <= 0:
            return ""

        global current_number
        current_number += step
        return current_number

    @staticmethod
    def guid():
        return str(uuid.uuid4())

    @staticmethod
    def uuid():
        return str(uuid.uuid4())

    @staticmethod
    def upper(s):
        if not isinstance(s, str):
            return ""
        return s.upper()

    @staticmethod
    def lower(s):
        if not isinstance(s, str):
            return ""
        return s.lower()

    @staticmethod
    def pick(arr_str):
        try:
            arr = json.loads(arr_str)
            if not isinstance(arr, list) or len(arr) == 0:
                return ""
            return random.choice(arr)
        except:
            return ""

    @staticmethod
    def shuffle(arr_str):
        try:
            arr = json.loads(arr_str)
            if not isinstance(arr, list) or len(arr) == 0:
                return ""
            random.shuffle(arr)
            return arr
        except:
            return ""
