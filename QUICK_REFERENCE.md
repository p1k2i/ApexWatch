# ApexWatch Dashboard - Quick Reference Guide

## 🚀 New Features at a Glance

### **NEW: Analytics Page** 📈
**Access:** Navigation → Analytics

**What you'll find:**
- **System Overview**: Active wallets, tokens, news (last 24h)
- **Event Frequency**: Hourly event tracking across all services
- **Sentiment Trends**: 7-30 day sentiment analysis with charts
- **News Sources**: Distribution of articles by source
- **Whale Activity**: 30-day whale transaction patterns

**Best for:** Getting a bird's-eye view of system performance and trends

---

### **Enhanced: Market Page** 💹
**What's new:**
- ✨ **Volume Distribution**: Pie chart showing exchange dominance
- ✨ **Volatility Analysis**: Rolling volatility with statistics
- ✨ **Bid-Ask Spreads**: Spread percentage over time
- ✨ **Volume Trends**: Trading volume area charts

**Use cases:**
- Compare prices across exchanges
- Identify high-volatility periods
- Find exchanges with best liquidity
- Track volume trends

---

### **Enhanced: Wallet Page** 👛
**What's new:**
- ✨ **Whale Distribution**: Pie charts for whale vs regular wallets
- ✨ **Transaction Trends**: Frequency and volume over time
- ✨ **Whale Heatmap**: Activity by day/hour (last 30 days)
- ✨ **Top Transaction Pairs**: Most frequent routes
- ✨ **Balance History**: Per-wallet balance analyzer

**Use cases:**
- Identify whale behavior patterns
- Track specific wallet balances
- Find peak trading times
- Analyze transaction flows

---

### **Enhanced: News Page** 📰
**What's new:**
- ✨ **Sentiment Timeline**: Dual-axis sentiment + article count
- ✨ **Sentiment Distribution**: Histogram and box plot
- ✨ **Sentiment vs Price**: Correlation analysis with scatter plot
- ✨ **Color-coded Articles**: Visual sentiment indicators

**Use cases:**
- Correlate news sentiment with price movements
- Identify sentiment trends
- Track news frequency
- Find extreme sentiment periods

---

### **Enhanced: AI Thoughts Page** 💭
**What's new:**
- ✨ **Performance Analytics**: Processing activity charts
- ✨ **Event Distribution**: Pie chart of event types
- ✨ **Processing Time**: Histogram with statistics
- ✨ **Collapsible Metrics**: Expandable performance section

**Use cases:**
- Monitor AI processing efficiency
- Track event type distribution
- Identify processing bottlenecks
- Review AI insights

---

### **Enhanced: Overview Page** 📊
**What's new:**
- ✨ **System Health**: 10 key metrics dashboard
- ✨ **Price Correlation**: Heatmap of exchange correlations
- ✨ **Quick Navigation**: Feature summary cards
- ✨ **Enhanced Metrics**: Whale counts, sentiment indicators

**Use cases:**
- System health check at a glance
- Quick token selection and overview
- Identify synchronized exchanges
- Jump to detailed pages

---

## 🎨 Visualization Quick Reference

### Chart Types & Where to Find Them

| Chart Type | Location | Purpose |
|------------|----------|---------|
| **Line Charts** | Market, News, Analytics | Price trends, sentiment over time |
| **Bar Charts** | Market, Wallets, Thoughts | Comparisons, frequencies |
| **Area Charts** | Market, Wallets, News | Volumes, cumulative data |
| **Pie Charts** | Analytics, Wallets, Thoughts | Distributions, proportions |
| **Heatmaps** | Overview, Wallets | Correlations, activity patterns |
| **Scatter Plots** | Market, News | Correlations, spreads |
| **Histograms** | News, Thoughts | Distributions, frequencies |
| **Box Plots** | News | Statistical summaries |

---

## ⚡ Performance Features

### Data Caching
All pages use intelligent caching (5-minute TTL):
- Reduces database load
- Faster page loads
- Click "🔄 Refresh" to force update

### Interactive Controls
- **Time Range Selectors**: Choose your analysis period
- **Filters**: Event type, article count, date ranges
- **Sorting**: Newest/oldest first
- **Expandable Sections**: Show/hide detailed metrics

---

## 🎯 Common Tasks

### Monitor Whale Activity
1. Go to **Wallets** page
2. Check "Whale Activity Heatmap"
3. Identify peak activity times
4. Use "Wallet Detail Analyzer" for specific whales

### Analyze Sentiment Impact
1. Go to **News** page
2. Scroll to "Sentiment vs Price Correlation"
3. Check correlation coefficient
4. Review scatter plot for patterns

### Check System Health
1. Go to **Overview** page
2. Review "System Health Overview" metrics
3. Check sentiment indicator (😊😐😞)
4. Verify all services are operational

### Find Best Exchange
1. Go to **Market** page
2. Check "Exchange Volume Distribution"
3. Review "Bid-Ask Spread Analysis"
4. Compare prices across exchanges

### Track Processing Performance
1. Go to **AI Thoughts** page
2. Expand "Performance Analytics"
3. Review processing time histogram
4. Check event frequency

---

## 📱 Navigation Tips

### Sidebar Navigation
- **Overview**: Start here for system overview
- **Analytics**: For comprehensive analytics
- **Wallets/Market/News**: Specific data analysis
- **AI Thoughts**: Browse AI insights
- **Settings**: Configuration (existing)

### Page Layout
Most pages follow this structure:
1. **Top Metrics**: Key numbers at a glance
2. **Main Visualizations**: Charts and graphs
3. **Detailed Analysis**: Deep-dive sections
4. **Data Tables**: Raw data at bottom

### Refresh Strategy
- **Auto-cache**: 5 minutes
- **Manual refresh**: Click 🔄 button
- **Full reload**: F5 in browser

---

## 🔍 Data Interpretation

### Sentiment Scores
- **> 0.1**: Positive sentiment 😊
- **-0.1 to 0.1**: Neutral sentiment 😐
- **< -0.1**: Negative sentiment 😞

### Correlation Coefficients
- **> 0.7**: Strong correlation
- **0.4 to 0.7**: Moderate correlation
- **< 0.4**: Weak correlation

### Whale Classification
- Automatically detected based on balance
- Tracked separately in visualizations
- Activity patterns analyzed independently

### Volatility Metrics
- Calculated as rolling standard deviation
- Higher % = more volatile
- Useful for risk assessment

---

## 💡 Pro Tips

1. **Use Time Ranges**: Adjust time ranges to find patterns
2. **Compare Correlations**: Use heatmaps to find synchronized data
3. **Watch Heatmaps**: Identify peak activity times
4. **Track Sentiment**: Correlate with price for insights
5. **Monitor Whales**: Big transactions often signal movements
6. **Check Spreads**: Lower spreads = better liquidity
7. **Review Processing**: Ensure AI is working efficiently
8. **Use Filters**: Narrow down to specific event types

---

## 🆘 Troubleshooting

### "No data available"
- Check if monitors are running (docker-compose)
- Verify token is selected (Overview page)
- Wait for data collection to populate
- Check time range (may be too narrow)

### Slow Performance
- Click refresh button to clear cache
- Reduce time ranges on charts
- Close other browser tabs
- Check system resources

### Charts Not Displaying
- Ensure JavaScript is enabled
- Clear browser cache
- Try different browser
- Check console for errors

---

## 📚 Learn More

- **DATA_ANALYSIS.md**: Detailed data structure documentation
- **IMPLEMENTATION_SUMMARY.md**: Complete technical details
- **DEVELOPMENT_PLAN.md**: System architecture
- **TECHNOLOGY_STACK.md**: Technologies used

---

## ✨ Remember

**ApexWatch is now a professional-grade monitoring solution** with:
- 30+ visualizations
- 50+ metrics
- Real-time insights
- Advanced analytics

Explore each page to discover all the powerful features at your fingertips!
