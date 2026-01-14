# Marketing Analyst

An AI-powered data analyst that executes Python code to answer questions about your marketing campaigns.

## Available Data

The default dataset contains **marketing campaign performance** from January-February 2024:

| Column | Description |
|--------|-------------|
| campaign_name | Campaign identifier (e.g., "Brand Awareness", "Retargeting") |
| channel | Ad platform (Facebook, LinkedIn, Google Search, Instagram) |
| audience_segment | Target audience (broad, retargeting, decision_makers, etc.) |
| date | Weekly aggregation date |
| impressions | Number of ad views |
| clicks | Number of clicks |
| conversions | Number of completed actions |
| spend | Budget spent in USD |

## What You Can Ask

- **Performance metrics**: CTR, conversion rate, CPA, ROAS
- **Comparisons**: Across channels, campaigns, or time periods
- **Trends**: Week-over-week changes, patterns
- **Recommendations**: Budget allocation, optimization opportunities

## How It Works

1. You ask a question about the data
2. The agent writes and executes Python code (pandas, matplotlib)
3. Results are grounded in actual computed metrics
4. Charts and tables are generated as needed

---

*Select a starter question below or type your own.*
