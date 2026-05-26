# ggzy-bid-scraper

🕷️ Hermes Agent Skill：全国公共资源交易平台 (ggzy.gov.cn) 招标数据抓取

[![Skill](https://img.shields.io/badge/Hermes-Skill-blue)](https://github.com/BruceLee1024/ggzy-bid-scraper)

## 安装

```bash
npx skills add BruceLee1024/ggzy-bid-scraper
```

## 触发方式

在 Hermes 对话中说：
- "查一下招标公告"
- "抓一下广东近十天的工程建设招标"
- "帮我看看中标结果"
- "下载招标 Excel"

## 功能

- 六种业务类型 × 31省 × 五时间范围 × 四交易阶段
- 详情页字段提取（预算、截止时间、资金来源等）
- 自动生成格式化 Excel（冻结首行、筛选、交替色、金额高亮）
- Playwright 驱动浏览器绕过 WAF

## 依赖

```bash
pip install playwright openpyxl
playwright install chromium
```

## 命令行直接使用

```bash
# 工程建设，全国近三天，3页20条详情
python3 scripts/ggzy_scraper_simple.py -b 1 -p 3 -d 20 --headless

# 交互式菜单
python3 scripts/ggzy_scraper.py
```

## License

MIT
