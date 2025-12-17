# 🛡️ CyberNews - Automated Security Intelligence

[![Daily CyberSec News](https://github.com/YOUR_USERNAME/cyberNews/actions/workflows/daily_news.yml/badge.svg)](https://github.com/YOUR_USERNAME/cyberNews/actions/workflows/daily_news.yml)

> 🔄 **Updates every 2 hours** (12x daily) | 📊 **[View Live Dashboard](https://YOUR_USERNAME.github.io/cyberNews/)**

Automated cybersecurity news aggregator powered by GitHub Actions. Fetches news from multiple sources, extracts trending keywords using NLP, and displays everything on a beautiful dashboard.

## 📊 Status

⏳ **Waiting for first run...** The GitHub Action will populate this README with the latest stats.

## ✨ Features

- 🔄 **12 updates per day** - Fresh news every 2 hours
- 📊 **Visual Dashboard** - Beautiful charts and graphs via GitHub Pages
- 🔥 **Keyword Trends** - NLP-powered trending topic extraction  
- 📈 **History Tracking** - See how topics trend over time
- 🎯 **8 News Sources** - Comprehensive coverage of cybersecurity news
- 📱 **Responsive Design** - Works on desktop and mobile

## 🔗 Sources Monitored

- The Hacker News
- BleepingComputer
- Krebs on Security
- Dark Reading
- Security Week
- Naked Security

## 🚀 How It Works

1. **GitHub Actions** runs daily at 00:00 UTC (or manually triggered)
2. **Python script** fetches RSS feeds from cybersecurity news sources
3. **RAKE algorithm** extracts trending keywords from article titles and summaries
4. **Results** are committed back to this repository

## 🛠️ Setup Instructions

1. Push this repository to GitHub
2. Replace `YOUR_USERNAME` in this README with your GitHub username
3. Go to your repo **Settings → Actions → General**
4. Under "Workflow permissions", select **"Read and write permissions"**
5. Enable GitHub Actions if not already enabled
6. Manually trigger the first run: **Actions → Daily CyberSec News → Run workflow**

## 📁 Project Structure

```
├── .github/workflows/
│   └── daily_news.yml    # GitHub Actions workflow
├── data/
│   ├── daily_report.md   # Daily news digest (auto-generated)
│   └── daily_report.json # Raw JSON data (auto-generated)
├── fetch_news.py         # Main scraper script
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## 🎨 Optional: GitHub Pages

To host your reports as a website:

1. Go to **Settings → Pages**
2. Set source to **"Deploy from a branch"**
3. Select **main** branch and **/ (root)** folder
4. Your reports will be available at `https://YOUR_USERNAME.github.io/cyberNews/`

---

*🤖 Powered by GitHub Actions*
