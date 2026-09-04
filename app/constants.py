# -*- coding: utf-8 -*-
"""全局常量：快递公司表、配色、接口地址"""
from __future__ import annotations

# ---------------------------------------------------------------
# 快递公司表
# (cpCode 菜鸟编码, 中文全名, 徽章简称, 徽章颜色, 快递100公司代码)
# ---------------------------------------------------------------
COMPANIES: list[tuple[str, str, str, str, str]] = [
    ("SF",   "顺丰速运",     "顺丰", "#2f7bff", "shunfeng"),
    ("ZTO",  "中通快递",     "中通", "#0e8a5a", "zhongtong"),
    ("YTO",  "圆通速递",     "圆通", "#1e6fd9", "yuantong"),
    ("STO",  "申通快递",     "申通", "#e2532f", "shentong"),
    ("YD",   "韵达速递",     "韵达", "#d9292f", "yunda"),
    ("EMS",  "中国邮政速递", "EMS",  "#0072bc", "ems"),
    ("YZPY", "邮政快递包裹", "邮政", "#5c9a00", "youzhengguonei"),
    ("HTKY", "百世快递",     "百世", "#f59a23", "huitongkuaidi"),
    ("JT",   "极兔速递",     "极兔", "#7b2d8e", "jtexpress"),
    ("JD",   "京东物流",     "京东", "#e8432f", "jd"),
    ("DBL",  "德邦快递",     "德邦", "#0e66c4", "debangkuaidi"),
    ("ZJS",  "宅急送",       "宅急", "#e60012", "zhaijisong"),
    ("UC",   "优速物流",     "优速", "#00a1e9", "youshuwuliu"),
    ("TST",  "天天快递",     "天天", "#f36b21", "tiantian"),
    ("ST",   "苏宁物流",     "苏宁", "#ff6600", "suning"),
    ("ANXL", "安能物流",     "安能", "#005bac", "annengwuliu"),
    ("GTO",  "国通快递",     "国通", "#005bac", "guotongkuaidi"),
    ("QFKD", "全峰快递",     "全峰", "#005bac", "quanfengkuaidi"),
    ("BEST", "百世汇通",     "百世", "#f59a23", "huitongkuaidi"),
    ("OTHER","其他快递",     "快递", "#8a9bb5", ""),
]

# 常用快递名称 -> cpCode 映射，用于从页面文本识别公司
COMPANY_NAME_MAP: dict[str, str] = {}
for _code, _name, _short, _color, _com100 in COMPANIES:
    COMPANY_NAME_MAP[_name] = _code
    COMPANY_NAME_MAP[_short] = _code
COMPANY_NAME_MAP.update({
    "顺丰快递": "SF", "顺丰速运": "SF", "中通": "ZTO", "圆通": "YTO",
    "申通": "STO", "韵达": "YD", "中国邮政": "YZPY", "邮政": "YZPY",
    "EMS": "EMS", "百世": "HTKY", "汇通": "HTKY", "极兔": "JT",
    "京东": "JD", "京东快递": "JD", "德邦": "DBL", "天天": "TST",
    "优速": "UC", "苏宁": "ST", "安能": "ANXL", "宅急送": "ZJS",
})

def company_info(code_or_name: str) -> tuple[str, str, str, str, str]:
    """根据 cpCode 或名称查公司信息，找不到返回 OTHER"""
    for code, name, short, color, com100 in COMPANIES:
        if code == code_or_name or name == code_or_name or short == code_or_name:
            return (code, name, short, color, com100)
    return ("OTHER", "其他快递", "快递", "#8a9bb5", "")

def com100_of(code_or_name: str) -> str:
    """取快递100公司代码，未知返回空串"""
    return company_info(code_or_name)[4]

# ---------------------------------------------------------------
# 配色 —— Surfboard 风格（深色玻璃拟态 + 青蓝渐变光晕）
# 背景：深海军蓝渐变；强调色：青 (#00D4FF) → 蓝 (#3E7BFA)；
# 卡片：半透明白玻璃 + 细高光边框；文字：近白 + 灰蓝次级
# ---------------------------------------------------------------
COLOR_BG_TOP       = "#0A1122"      # 背景渐变（上）
COLOR_BG_BOTTOM    = "#0E1A33"      # 背景渐变（下）
COLOR_ACCENT       = "#00D4FF"      # 主强调色（青）
COLOR_ACCENT_BLUE  = "#3E7BFA"      # 强调色（蓝）
COLOR_ACCENT_SOFT  = "#7DE8FF"      # 强调色上的浅色文字
COLOR_ON_ACCENT    = "#04121F"      # 强调色上的深色文字
COLOR_GLASS        = "rgba(255,255,255,0.06)"    # 玻璃卡片底
COLOR_GLASS_BORDER = "rgba(255,255,255,0.12)"    # 玻璃卡片边
COLOR_GLASS_STRONG = "rgba(20,28,48,0.94)"       # 顶栏/底栏/浮层
COLOR_TEXT         = "#E9F1FF"      # 主文字
COLOR_TEXT_SUB     = "#8A97B5"      # 次级文字
COLOR_OUTLINE      = "rgba(255,255,255,0.16)"
COLOR_OK           = "#34D399"
COLOR_WARN         = "#FBBF24"
COLOR_ERR          = "#F87171"
# 状态 Chip 容器色（按状态）
COLOR_CHIP_CYAN_BG    = "rgba(0,212,255,0.14)"
COLOR_CHIP_CYAN_FG    = "#7DE8FF"
COLOR_CHIP_ORANGE_BG  = "rgba(251,191,36,0.14)"
COLOR_CHIP_ORANGE_FG  = "#FFD58A"
COLOR_CHIP_GREEN_BG   = "rgba(52,211,153,0.14)"
COLOR_CHIP_GREEN_FG   = "#8AF0C8"
COLOR_CHIP_RED_BG     = "rgba(248,113,113,0.16)"
COLOR_CHIP_RED_FG     = "#FFA8A8"

# ---------- 兼容旧名（供历史模块引用） ----------
COLOR_PRIMARY            = COLOR_ACCENT
COLOR_PRIMARY_DARK       = "#00A8CC"
COLOR_ON_PRIMARY         = COLOR_ON_ACCENT
COLOR_PRIMARY_CONTAINER  = "rgba(0,212,255,0.14)"
COLOR_ON_PRIMARY_CONTAINER = COLOR_ACCENT_SOFT
COLOR_SECONDARY_CONTAINER  = "rgba(255,255,255,0.08)"
COLOR_ON_SECONDARY_CONTAINER = COLOR_TEXT
COLOR_TERTIARY_CONTAINER  = COLOR_CHIP_ORANGE_BG
COLOR_ON_TERTIARY_CONTAINER = COLOR_CHIP_ORANGE_FG
COLOR_ERROR               = COLOR_ERR
COLOR_ERROR_CONTAINER     = "rgba(248,113,113,0.16)"
COLOR_ON_ERROR_CONTAINER  = COLOR_CHIP_RED_FG
COLOR_SURFACE             = COLOR_BG_TOP
COLOR_ON_SURFACE          = COLOR_TEXT
COLOR_ON_SURFACE_VARIANT  = COLOR_TEXT_SUB
COLOR_OUTLINE_VARIANT     = "rgba(255,255,255,0.10)"
COLOR_SURFACE_CONTAINER_LOWEST  = "#0C1428"
COLOR_SURFACE_CONTAINER_LOW     = "rgba(255,255,255,0.05)"
COLOR_SURFACE_CONTAINER         = "rgba(255,255,255,0.07)"
COLOR_SURFACE_CONTAINER_HIGH    = "rgba(255,255,255,0.10)"
COLOR_SURFACE_CONTAINER_HIGHEST = "rgba(255,255,255,0.12)"
COLOR_INVERSE_SURFACE       = "#E9F1FF"
COLOR_INVERSE_ON_SURFACE    = "#0A1122"

WULIU_BASE   = "https://wuliu.taobao.com"
WULIU_LIST   = WULIU_BASE + "/user/query_package_list.htm"
WULIU_DETAIL = WULIU_BASE + "/trace/query_package_detail.htm"

KUADI100_QUERY = "https://www.kuaidi100.com/query"
KUADI100_POLL = "https://poll.kuaidi100.com/poll/query.do"   # 快递100 企业版轮询接口
KDNIAO_URL   = "https://api.kdniao.com/Ebusiness/EbusinessOrderHandle.aspx"  # 快递鸟即时查询


# （地图功能已移除，OSM/Nominatim 相关常量已删除）

DEFAULT_REFRESH_MIN = 5        # 默认刷新间隔（分钟）
MIN_REFRESH_MIN     = 1        # 最小刷新间隔

# 快递鸟 ShpperCode 映射（菜鸟 cpCode → 快递鸟编码）
KDNIAO_CODE_MAP: dict[str, str] = {
    "SF": "SF", "ZTO": "ZTO", "YTO": "YTO", "STO": "STO", "YD": "YD",
    "EMS": "EMS", "YZPY": "YZPY", "HTKY": "HHTT", "BEST": "HHTT",
    "JT": "JT", "JD": "JD", "DBL": "DBL", "ZJS": "ZJS", "UC": "UC",
    "TST": "TST", "ST": "STO", "ANXL": "ANE", "GTO": "GTO", "QFKD": "QFKD",
    "OTHER": "",
}

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
