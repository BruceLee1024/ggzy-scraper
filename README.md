# ggzy-scraper

🕷️ 全国公共资源交易平台 (ggzy.gov.cn) 招标数据抓取工具

自动抓取全国各省市的工程建设、政府采购等招标公告，支持详情页字段提取，输出格式化 Excel 报告。

## ✨ 功能

- **六种业务类型**：工程建设 / 政府采购 / 土地使用权 / 矿业权 / 国有产权 / 全部
- **全国 31 省** + 全国模式，按省份筛选
- **五个时间范围**：当天 / 近三天 / 近十天 / 近一月 / 近三月
- **四种交易阶段**：招标公告 / 中标候选人 / 中标结果 / 更正事项
- **详情页抓取**：预算金额、投标保证金、投标截止时间、文件获取截止、资金来源、建设规模、计划工期、招标代理
- **Excel 输出**：自动生成格式化 Excel（冻结首行、自动筛选、交替行色、金额高亮）

## 📦 安装

```bash
# 1. 克隆仓库
git clone https://github.com/BruceLee1024/ggzy-scraper.git
cd ggzy-scraper

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器（首次使用）
playwright install chromium
```

## 🚀 快速开始

### 命令行模式（推荐）

```bash
# 工程建设，全国，近三天，3页，20条详情，无头模式
python3 ggzy_scraper_simple.py -b 1 -p 3 -d 20 --headless

# 政府采购，广东，近十天，10页，不抓详情
python3 ggzy_scraper_simple.py -b 2 -v 广东 -t 3 -p 10 -d 0

# 工程建设，云南，近三天，5页，30条详情，指定输出路径
python3 ggzy_scraper_simple.py -b 1 -v 云南 -t 2 -p 5 -d 30 -o ~/Documents/招标数据.xlsx
```

### 交互式菜单

```bash
python3 ggzy_scraper.py
# 依次选择业务类型 → 交易阶段 → 省份 → 时间 → 翻页数 → 详情数
```

## 📋 参数说明

| 参数 | 简写 | 说明 | 可选值 |
|------|------|------|--------|
| `--biz` | `-b` | 业务类型 | `1`=工程建设, `2`=政府采购, `3`=土地使用权, `4`=矿业权, `5`=国有产权, `6`=全部 |
| `--province` | `-v` | 省份 | `0`=全国, `1`=北京, `19`=广东, `23`=四川, `25`=云南... (支持中文名和数字 key) |
| `--time` | `-t` | 时间范围 | `1`=当天, `2`=近三天, `3`=近十天, `4`=近一月, `5`=近三月 |
| `--stage` | `-s` | 交易阶段 | `1`=招标公告, `2`=中标候选人, `3`=中标结果, `4`=更正事项 |
| `--pages` | `-p` | 翻页数 | 每页 20 条，默认 3 |
| `--details` | `-d` | 详情条数 | 0 = 不抓详情，默认 5 |
| `--out` | `-o` | 输出路径 | 默认 `~/Desktop/招标公告_数据.xlsx` |
| `--headless` |  | 无头模式 | 不传 = 有头模式（弹出浏览器窗口） |

## 🔧 技术要点

- **WAF 绕过**：使用 Playwright 驱动真实浏览器 + 隐身补丁 + URL 参数服务端过滤
- **Vue 2 实例交互**：通过 `document.querySelector('#app').__vue__` 调用内置翻页方法 `goToPage()`
- **限流保护**：每 50 页自动暂停 30 秒冷却
- **详情页提取**：通过 iframe 加载详情页，正则匹配提取结构化字段

详见 [`references/waf-bypass.md`](references/waf-bypass.md)

## 📊 输出示例

```
✅ 完成! 60条, 详情20条(含预算6)
保存: /tmp/ggzy_records.json
Excel: ~/Desktop/招标公告_数据.xlsx
```

Excel 包含字段：序号、标题、发布时间、省份、来源平台、业务类型、信息类型、行业、预算(万元)、保证金(万元)、投标截止时间、文件获取截止、资金来源、计划工期(天)、招标代理、URL

## ⚠️ 注意事项

- **建议使用有头模式**（不加 `--headless`），无头模式可能被 WAF 拦截
- 大规模抓取（50页以上）可能触发限流，等待几分钟后恢复
- 纯 HTTP 请求（curl/requests）会直接被 WAF 拦截，必须使用浏览器
- 仅支持 macOS / Linux，Windows 需要调整 Playwright 安装方式

## 📄 License

MIT
