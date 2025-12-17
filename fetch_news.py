"""
Cybersecurity News Aggregator
Fetches news from RSS feeds, extracts keywords, and generates reports.
"""

import feedparser
import json
import os
import re
import html
from datetime import datetime
from rake_nltk import Rake
from collections import Counter

# ============================================
# CONFIGURATION - Add/remove RSS feeds here
# ============================================
RSS_FEEDS = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Krebs on Security": "https://krebsonsecurity.com/feed/",
    "Dark Reading": "https://www.darkreading.com/rss.xml",
    "Security Week": "https://feeds.feedburner.com/securityweek",
    "Naked Security": "https://nakedsecurity.sophos.com/feed/",
    "Threatpost": "https://threatpost.com/feed/",
    "CISA Alerts": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
}

ARTICLES_PER_SOURCE = 8   # Number of articles to fetch per source
TOP_KEYWORDS = 20         # Number of keywords to extract
HISTORY_FILE = "data/keyword_history.json"


# Minimal built-in English stopwords so RAKE doesn't require NLTK corpora downloads
RAKE_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on",
    "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same",
    "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when",
    "where", "which", "while", "who", "whom", "why", "with", "you", "your", "yours",
    "yourself", "yourselves",
}


def simple_sentence_tokenizer(text: str):
    # Avoid NLTK punkt dependency (good enough for headlines/summaries)
    return [s.strip() for s in re.split(r"[.!?]+\s+", text) if s.strip()]


def simple_word_tokenizer(sentence: str):
    return re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?", sentence)


def clean_html(text):
    """Remove HTML tags and clean text."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()[:500]


def fetch_articles():
    """Fetch articles from all RSS feeds."""
    articles = []
    all_text = ""
    source_counts = Counter()
    
    for source_name, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            count = 0
            
            for entry in feed.entries[:ARTICLES_PER_SOURCE]:
                title = entry.get('title', 'No Title')
                link = entry.get('link', '#')
                summary = entry.get('summary', entry.get('description', ''))
                published = entry.get('published', entry.get('updated', ''))
                
                clean_summary = clean_html(summary)
                
                articles.append({
                    'source': source_name,
                    'title': title,
                    'link': link,
                    'summary': clean_summary,
                    'published': published
                })
                
                all_text += f" {title} {clean_summary}"
                count += 1
            
            source_counts[source_name] = count
            print(f"✅ {source_name}: {count} articles")
                
        except Exception as e:
            print(f"❌ Error fetching from {source_name}: {e}")
            source_counts[source_name] = 0
            
    return articles, all_text, source_counts


def extract_keywords(text):
    """Extract keywords using RAKE algorithm."""
    r = Rake(
        stopwords=RAKE_STOPWORDS,
        min_length=1,
        max_length=4,
        include_repeated_phrases=False,
        sentence_tokenizer=simple_sentence_tokenizer,
        word_tokenizer=simple_word_tokenizer,
    )
    r.extract_keywords_from_text(text)
    
    keywords = []
    seen = set()
    
    # Common words to filter out
    stopwords = {'new', 'use', 'used', 'using', 'one', 'two', 'first', 'last', 
                 'also', 'may', 'could', 'would', 'said', 'says', 'according',
                 'year', 'years', 'day', 'days', 'week', 'weeks', 'month'}
    
    for phrase in r.get_ranked_phrases():
        phrase_lower = phrase.lower().strip()
        words = phrase_lower.split()
        
        # Filter criteria
        if (len(phrase_lower) > 3 and 
            phrase_lower not in seen and
            not phrase_lower.isdigit() and
            not any(w in stopwords for w in words) and
            len(words) <= 3):
            keywords.append(phrase)
            seen.add(phrase_lower)
            
        if len(keywords) >= TOP_KEYWORDS:
            break
            
    return keywords


def load_keyword_history():
    """Load keyword history from file."""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {'dates': [], 'keywords': {}, 'updates': []}


def save_keyword_history(history, keywords, timestamp, articles_count):
    """Save keyword history to track trends."""
    today = timestamp.split()[0]
    
    # Add update record
    history['updates'].append({
        'timestamp': timestamp,
        'articles': articles_count,
        'top_keywords': keywords[:5]
    })
    
    # Keep only last 100 updates
    history['updates'] = history['updates'][-100:]
    
    # Track keyword frequency over time
    if today not in history['dates']:
        history['dates'].append(today)
        history['dates'] = history['dates'][-30:]  # Keep 30 days
    
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in history['keywords']:
            history['keywords'][kw_lower] = {'count': 0, 'dates': []}
        history['keywords'][kw_lower]['count'] += 1
        if today not in history['keywords'][kw_lower]['dates']:
            history['keywords'][kw_lower]['dates'].append(today)
    
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    
    return history


def get_trending_keywords(history, current_keywords):
    """Identify trending keywords based on history."""
    trending = []
    for kw in current_keywords[:10]:
        kw_lower = kw.lower()
        if kw_lower in history['keywords']:
            count = history['keywords'][kw_lower]['count']
            trending.append({'keyword': kw, 'mentions': count})
        else:
            trending.append({'keyword': kw, 'mentions': 1, 'new': True})
    return trending


def generate_html_dashboard(articles, keywords, trending, history, source_counts, timestamp):
    """Generate a beautiful HTML dashboard."""
    
    # Prepare data for charts
    source_labels = json.dumps(list(source_counts.keys()))
    source_data = json.dumps(list(source_counts.values()))
    
    keyword_labels = json.dumps([t['keyword'][:20] for t in trending[:10]])
    keyword_data = json.dumps([t['mentions'] for t in trending[:10]])
    
    # Recent updates for timeline
    recent_updates = history.get('updates', [])[-10:]
    
    # Group articles by source for display
    articles_by_source = {}
    for article in articles:
        src = article['source']
        if src not in articles_by_source:
            articles_by_source[src] = []
        articles_by_source[src].append(article)
    
    # Generate article cards HTML
    article_cards = ""
    for source, arts in articles_by_source.items():
        for art in arts[:5]:
            summary_preview = art['summary'][:150] + "..." if len(art['summary']) > 150 else art['summary']
            escaped_title = html.escape(art['title'])
            escaped_summary = html.escape(summary_preview)
            article_cards += f'''
            <div class="article-card" data-source="{source}">
                <div class="article-source">{source}</div>
                <h3 class="article-title">
                    <a href="{art['link']}" target="_blank" rel="noopener">{escaped_title}</a>
                </h3>
                <p class="article-summary">{escaped_summary}</p>
                <div class="article-meta">{art['published'][:25] if art['published'] else 'Recent'}</div>
            </div>'''
    
    # Generate keyword tags
    keyword_tags = ""
    for i, t in enumerate(trending):
        new_badge = '<span class="new-badge">NEW</span>' if t.get('new') else ''
        size_class = 'large' if i < 3 else 'medium' if i < 7 else 'small'
        keyword_tags += f'<span class="keyword-tag {size_class}">{html.escape(t["keyword"])} ({t["mentions"]}) {new_badge}</span>'
    
    # Source filter buttons
    source_buttons = '<button class="filter-btn active" data-filter="all">All Sources</button>'
    for source in source_counts.keys():
        source_buttons += f'<button class="filter-btn" data-filter="{source}">{source}</button>'
    
    # Timeline HTML
    timeline_html = ""
    for update in reversed(recent_updates[-8:]):
        timeline_html += f'''
        <div class="timeline-item">
            <div class="timeline-time">{update['timestamp']}</div>
            <div class="timeline-content">
                <strong>{update['articles']} articles</strong> analyzed
                <div class="timeline-keywords">{', '.join(update['top_keywords'][:3])}</div>
            </div>
        </div>'''

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🛡️ CyberNews Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --accent: #00ff88;
            --accent-dim: #00cc6a;
            --accent-glow: rgba(0, 255, 136, 0.3);
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --border: #2a2a3a;
            --danger: #ff4757;
            --warning: #ffa502;
            --info: #3742fa;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .cyber-grid {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: 
                linear-gradient(rgba(0, 255, 136, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 255, 136, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            pointer-events: none;
            z-index: 0;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }}
        
        header {{
            text-align: center;
            padding: 40px 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 30px;
        }}
        
        .logo {{
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), #00ccff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 0 40px var(--accent-glow);
        }}
        
        .tagline {{
            color: var(--text-secondary);
            margin-top: 10px;
            font-size: 1.1rem;
        }}
        
        .live-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--bg-card);
            padding: 8px 16px;
            border-radius: 20px;
            margin-top: 20px;
            font-size: 0.9rem;
            border: 1px solid var(--border);
        }}
        
        .live-dot {{
            width: 10px;
            height: 10px;
            background: var(--accent);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; box-shadow: 0 0 10px var(--accent); }}
            50% {{ opacity: 0.5; box-shadow: 0 0 20px var(--accent); }}
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{
            border-color: var(--accent);
            box-shadow: 0 0 30px var(--accent-glow);
            transform: translateY(-2px);
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--accent);
            font-family: 'JetBrains Mono', monospace;
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            margin-top: 5px;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            overflow: hidden;
        }}
        
        .card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border);
        }}
        
        .card-title {{
            font-size: 1.1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .card-icon {{
            font-size: 1.3rem;
        }}
        
        .keywords-section {{
            grid-column: span 8;
        }}
        
        .timeline-section {{
            grid-column: span 4;
        }}
        
        .charts-row {{
            grid-column: span 12;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        
        .chart-container {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            height: 350px;
        }}
        
        .keyword-cloud {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .keyword-tag {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 8px 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 20px;
            font-size: 0.85rem;
            transition: all 0.2s ease;
            cursor: default;
        }}
        
        .keyword-tag:hover {{
            border-color: var(--accent);
            background: rgba(0, 255, 136, 0.1);
        }}
        
        .keyword-tag.large {{
            font-size: 1rem;
            padding: 10px 20px;
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.2), rgba(0, 204, 255, 0.1));
            border-color: var(--accent);
        }}
        
        .keyword-tag.medium {{
            font-size: 0.9rem;
        }}
        
        .new-badge {{
            background: var(--danger);
            color: white;
            font-size: 0.65rem;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }}
        
        .timeline {{
            display: flex;
            flex-direction: column;
            gap: 15px;
            max-height: 400px;
            overflow-y: auto;
        }}
        
        .timeline-item {{
            padding: 15px;
            background: var(--bg-secondary);
            border-radius: 8px;
            border-left: 3px solid var(--accent);
        }}
        
        .timeline-time {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--accent);
            margin-bottom: 5px;
        }}
        
        .timeline-content {{
            font-size: 0.9rem;
        }}
        
        .timeline-keywords {{
            color: var(--text-secondary);
            font-size: 0.8rem;
            margin-top: 5px;
        }}
        
        .filter-section {{
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s ease;
        }}
        
        .filter-btn:hover, .filter-btn.active {{
            background: var(--accent);
            color: var(--bg-primary);
            border-color: var(--accent);
        }}
        
        .articles-section {{
            grid-column: span 12;
        }}
        
        .articles-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            max-height: 800px;
            overflow-y: auto;
            padding: 5px;
        }}
        
        .article-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s ease;
        }}
        
        .article-card:hover {{
            border-color: var(--accent);
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }}
        
        .article-source {{
            font-size: 0.75rem;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .article-title {{
            font-size: 1rem;
            margin-bottom: 10px;
            line-height: 1.4;
        }}
        
        .article-title a {{
            color: var(--text-primary);
            text-decoration: none;
            transition: color 0.2s;
        }}
        
        .article-title a:hover {{
            color: var(--accent);
        }}
        
        .article-summary {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 10px;
        }}
        
        .article-meta {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            font-family: 'JetBrains Mono', monospace;
        }}
        
        footer {{
            text-align: center;
            padding: 40px 20px;
            border-top: 1px solid var(--border);
            margin-top: 40px;
            color: var(--text-secondary);
        }}
        
        footer a {{
            color: var(--accent);
            text-decoration: none;
        }}
        
        @media (max-width: 1200px) {{
            .keywords-section, .timeline-section {{
                grid-column: span 12;
            }}
            .charts-row {{
                grid-template-columns: 1fr;
            }}
        }}
        
        @media (max-width: 768px) {{
            .logo {{ font-size: 2rem; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .articles-grid {{ grid-template-columns: 1fr; }}
        }}
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: var(--bg-secondary);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: var(--border);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--accent-dim);
        }}
    </style>
</head>
<body>
    <div class="cyber-grid"></div>
    
    <div class="container">
        <header>
            <h1 class="logo">🛡️ CyberNews Intelligence</h1>
            <p class="tagline">Real-time Cybersecurity News Aggregation & Trend Analysis</p>
            <div class="live-indicator">
                <span class="live-dot"></span>
                <span>Last updated: {timestamp} UTC</span>
            </div>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(articles)}</div>
                <div class="stat-label">Articles Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(source_counts)}</div>
                <div class="stat-label">Active Sources</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(keywords)}</div>
                <div class="stat-label">Keywords Extracted</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(history.get('updates', []))}</div>
                <div class="stat-label">Total Updates</div>
            </div>
        </div>
        
        <div class="dashboard-grid">
            <div class="card keywords-section">
                <div class="card-header">
                    <div class="card-title"><span class="card-icon">🔥</span> Trending Keywords</div>
                </div>
                <div class="keyword-cloud">
                    {keyword_tags}
                </div>
            </div>
            
            <div class="card timeline-section">
                <div class="card-header">
                    <div class="card-title"><span class="card-icon">📊</span> Recent Updates</div>
                </div>
                <div class="timeline">
                    {timeline_html}
                </div>
            </div>
            
            <div class="charts-row">
                <div class="chart-container">
                    <canvas id="sourceChart"></canvas>
                </div>
                <div class="chart-container">
                    <canvas id="keywordChart"></canvas>
                </div>
            </div>
            
            <div class="card articles-section">
                <div class="card-header">
                    <div class="card-title"><span class="card-icon">📰</span> Latest News</div>
                </div>
                <div class="filter-section">
                    {source_buttons}
                </div>
                <div class="articles-grid">
                    {article_cards}
                </div>
            </div>
        </div>
        
        <footer>
            <p>🤖 Automatically updated every 2 hours via <a href="https://github.com/features/actions" target="_blank">GitHub Actions</a></p>
            <p style="margin-top: 10px; font-size: 0.85rem;">
                Data sources: The Hacker News, BleepingComputer, Krebs on Security, Dark Reading, Security Week, Naked Security, Threatpost, CISA
            </p>
        </footer>
    </div>
    
    <script>
        // Source Distribution Chart
        const sourceCtx = document.getElementById('sourceChart').getContext('2d');
        new Chart(sourceCtx, {{
            type: 'doughnut',
            data: {{
                labels: {source_labels},
                datasets: [{{
                    data: {source_data},
                    backgroundColor: [
                        '#00ff88', '#00ccff', '#ff6b6b', '#ffd93d', 
                        '#6c5ce7', '#a29bfe', '#fd79a8', '#00b894'
                    ],
                    borderColor: '#1a1a25',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{
                            color: '#a0a0b0',
                            padding: 15,
                            font: {{ size: 11 }}
                        }}
                    }},
                    title: {{
                        display: true,
                        text: 'Articles by Source',
                        color: '#ffffff',
                        font: {{ size: 14, weight: '600' }}
                    }}
                }}
            }}
        }});
        
        // Keyword Frequency Chart
        const keywordCtx = document.getElementById('keywordChart').getContext('2d');
        new Chart(keywordCtx, {{
            type: 'bar',
            data: {{
                labels: {keyword_labels},
                datasets: [{{
                    label: 'Mentions',
                    data: {keyword_data},
                    backgroundColor: 'rgba(0, 255, 136, 0.6)',
                    borderColor: '#00ff88',
                    borderWidth: 1,
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }},
                    title: {{
                        display: true,
                        text: 'Keyword Frequency (All Time)',
                        color: '#ffffff',
                        font: {{ size: 14, weight: '600' }}
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{ color: 'rgba(255,255,255,0.1)' }},
                        ticks: {{ color: '#a0a0b0' }}
                    }},
                    y: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#a0a0b0', font: {{ size: 10 }} }}
                    }}
                }}
            }}
        }});
        
        // Article filtering
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                const filter = btn.dataset.filter;
                document.querySelectorAll('.article-card').forEach(card => {{
                    if (filter === 'all' || card.dataset.source === filter) {{
                        card.style.display = 'block';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});
            }});
        }});
    </script>
</body>
</html>'''
    
    return html_content


def generate_markdown_report(articles, keywords, timestamp):
    """Generate the Markdown report file."""
    
    md_content = f"""# 🛡️ Daily Cyber Security Intelligence

> **Last Updated:** {timestamp} UTC  
> **Sources Monitored:** {len(RSS_FEEDS)}  
> **Articles Analyzed:** {len(articles)}

---

## 🔥 Rising Topics & Keywords

{' • '.join([f'**{k}**' for k in keywords])}

---

## 📰 Latest News by Source

"""
    
    by_source = {}
    for article in articles:
        source = article['source']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(article)
    
    for source, source_articles in by_source.items():
        md_content += f"### {source}\n\n"
        for article in source_articles:
            md_content += f"- [{article['title']}]({article['link']})\n"
        md_content += "\n"
    
    md_content += """---

*🤖 Automated by CyberNews Bot using GitHub Actions*
"""
    
    return md_content


def generate_json_report(articles, keywords, trending, timestamp):
    """Generate JSON data file."""
    return {
        'last_updated': timestamp,
        'sources_count': len(RSS_FEEDS),
        'articles_count': len(articles),
        'keywords': keywords,
        'trending': trending,
        'articles': articles,
        'sources': list(RSS_FEEDS.keys())
    }


def update_readme(keywords, articles_count, timestamp, update_count):
    """Update the main README with latest stats."""
    
    readme_content = f"""# 🛡️ CyberNews - Automated Security Intelligence

[![Daily CyberSec News](https://github.com/YOUR_USERNAME/cyberNews/actions/workflows/daily_news.yml/badge.svg)](https://github.com/YOUR_USERNAME/cyberNews/actions/workflows/daily_news.yml)

> 🔄 **Updates every 2 hours** (12x daily) | 📊 **[View Live Dashboard](https://YOUR_USERNAME.github.io/cyberNews/)**

## 📊 Latest Stats

| Metric | Value |
|--------|-------|
| 🕐 Last Updated | {timestamp} UTC |
| 📰 Articles Analyzed | {articles_count} |
| 🔑 Keywords Extracted | {len(keywords)} |
| 📈 Total Updates | {update_count} |

## 🔥 Trending Topics

{' • '.join([f'`{k}`' for k in keywords[:10]])}

## 📄 Reports

| Report | Description |
|--------|-------------|
| **[🌐 Live Dashboard](https://YOUR_USERNAME.github.io/cyberNews/)** | Visual dashboard with charts |
| **[📝 Daily Report](data/daily_report.md)** | Markdown news digest |
| **[📦 JSON Data](data/daily_report.json)** | Raw data for API access |

## 🔗 Sources Monitored

"""
    
    for source_name in RSS_FEEDS.keys():
        readme_content += f"- {source_name}\n"
    
    readme_content += """
## 🚀 How It Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Actions │────▶│  Python Script  │────▶│  HTML Dashboard │
│  (Every 2 hrs)  │     │  (Fetch & NLP)  │     │  (GitHub Pages) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 🛠️ Setup Your Own

1. Fork this repository
2. Enable **Settings → Actions → Workflow permissions → Read and write**
3. Enable **Settings → Pages → Source: main branch**
4. Replace `YOUR_USERNAME` with your GitHub username
5. Manually trigger first run: **Actions → Run workflow**

---

*🤖 Powered by GitHub Actions • Updated every 2 hours*
"""
    
    return readme_content


def main():
    """Main execution function."""
    print("🚀 Starting Cybersecurity News Aggregator...")
    print("="*50)
    
    os.makedirs("data", exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    
    # Load history
    history = load_keyword_history()
    
    # Fetch articles
    print("\n📡 Fetching articles from RSS feeds...\n")
    articles, all_text, source_counts = fetch_articles()
    print(f"\n✅ Total: {len(articles)} articles fetched")
    
    # Extract keywords
    print("\n🔍 Extracting keywords...")
    keywords = extract_keywords(all_text)
    print(f"✅ Extracted {len(keywords)} keywords")
    
    # Update history
    history = save_keyword_history(history, keywords, timestamp, len(articles))
    
    # Get trending analysis
    trending = get_trending_keywords(history, keywords)
    
    # Generate Markdown report
    print("\n📝 Generating reports...")
    md_report = generate_markdown_report(articles, keywords, timestamp)
    with open("data/daily_report.md", "w", encoding="utf-8") as f:
        f.write(md_report)
    
    # Generate JSON report
    json_report = generate_json_report(articles, keywords, trending, timestamp)
    with open("data/daily_report.json", "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    
    # Generate HTML Dashboard
    print("🎨 Generating HTML dashboard...")
    html_dashboard = generate_html_dashboard(articles, keywords, trending, history, source_counts, timestamp)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_dashboard)
    
    # Update README
    update_count = len(history.get('updates', []))
    readme = update_readme(keywords, len(articles), timestamp, update_count)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    
    print("\n" + "="*50)
    print("✨ COMPLETE!")
    print("="*50)
    print(f"📰 Articles: {len(articles)}")
    print(f"🔑 Keywords: {', '.join(keywords[:5])}...")
    print(f"📊 Updates: {update_count}")


if __name__ == "__main__":
    main()
