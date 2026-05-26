#!/usr/bin/env python3
"""
ggzy 招标数据快速抓取（Hermes skill 入口）。
需与 ggzy_scraper.py 同目录运行。

用法：
  python3 ggzy_scraper_simple.py [选项]

选项：
  -b, --biz      业务类型 key (1=工程建设 2=政府采购 3=土地 4=矿业 5=国有产权 6=全部) [默认: 1]
  -p, --pages    翻页数，每页20条 [默认: 3]
  -d, --details  抓详情条数，0=不抓 [默认: 5]
  -v, --province 省份 key 或中文名（如 25 或 云南），0=全国 [默认: 0]
  -t, --time     时间范围 key (1=当天 2=近三天 3=近十天 4=近一月 5=近三月) [默认: 2]
  -s, --stage    交易阶段 key (1=招标公告 2=中标候选人 3=中标结果 4=更正事项) [默认: 1]
  -o, --out      Excel 输出路径 [默认: ~/Desktop/招标公告_数据.xlsx]
  --headless     使用无头隐身模式（默认有头模式）

示例：
  python3 ggzy_scraper_simple.py -b 1 -p 3 -d 20 -v 云南 -t 3 --headless
  python3 ggzy_scraper_simple.py -b 2 -p 10 -d 0 -o /tmp/采购数据.xlsx
  python3 ggzy_scraper_simple.py -v 广东 -t 1 -d 50
"""
import sys, os, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ggzy_scraper import BUSINESS_TYPES, TRANSACTION_STAGES, PROVINCES, TIME_RANGES, _do_scrape

def _resolve_province(val):
    """支持 key ('0'-'31') 或中文名 ('云南') 查找省份"""
    if val in PROVINCES:
        return val
    for k, v in PROVINCES.items():
        if v['name'] == val or v['name'].startswith(val):
            return k
    print(f"  ⚠️ 未找到省份 '{val}'，使用全国(0)")
    return "0"

parser = argparse.ArgumentParser(description='ggzy.gov.cn 招标数据抓取', add_help=True)
parser.add_argument('-b', '--biz',      default='1',  help='业务类型 key [1-6]')
parser.add_argument('-p', '--pages',    default=3,    type=int, help='翻页数')
parser.add_argument('-d', '--details',  default=5,    type=int, help='详情条数')
parser.add_argument('-v', '--province', default='0',  help='省份 key 或中文名')
parser.add_argument('-t', '--time',     default='2',  help='时间范围 key [1-5]')
parser.add_argument('-s', '--stage',    default='1',  help='交易阶段 key [1-4]')
parser.add_argument('-o', '--out',      default=None, help='Excel 输出路径')
parser.add_argument('--headless',       action='store_true', help='无头隐身模式')
args = parser.parse_args()

biz_key      = args.biz   if args.biz   in BUSINESS_TYPES    else "1"
stage_key    = args.stage if args.stage in TRANSACTION_STAGES else "1"
time_key     = args.time  if args.time  in TIME_RANGES        else "2"
province_key = _resolve_province(args.province)

filters = {
    'business_type':     BUSINESS_TYPES[biz_key],
    'transaction_stage': TRANSACTION_STAGES[stage_key],
    'province':          PROVINCES[province_key],
    'time_range':        TIME_RANGES[time_key],
}

print(f"抓取配置:")
print(f"  业务={filters['business_type']['name']}  阶段={filters['transaction_stage']['name']}")
print(f"  省份={filters['province']['name']}  时间={filters['time_range']['name']}")
print(f"  {args.pages}页  详情{args.details}条  {'无头隐身' if args.headless else '有头'}模式")
if args.out: print(f"  输出: {args.out}")

_do_scrape(args.pages, args.details, filters, headless=args.headless, out_path=args.out)
