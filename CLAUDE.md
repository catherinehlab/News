# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Korean restaurant/food industry news digest application that automatically crawls RSS feeds and HTML pages, summarizes articles using OpenAI GPT-4, and sends daily email digests via Gmail API. The application focuses on food service industry events, networking opportunities, education, and industry news.

## Setup and Environment

### Dependencies Installation
```bash
pip install -r requirements.txt
```

### Required Dependencies
- `feedparser` - RSS feed parsing
- `openai` - GPT-4 integration for summarization
- `python-dotenv` - Environment variable management
- `yagmail` - Email functionality (currently commented out)
- `requests` - HTTP requests for web scraping
- `beautifulsoup4` - HTML parsing
- `google-api-python-client` - Gmail API integration
- `google-auth-oauthlib` - Google OAuth authentication
- `google-auth` - Google authentication utilities

### Environment Variables Required
Create a `.env` file with:
- `OPENAI_API_KEY` - OpenAI API key for GPT-4 summarization
- `RECIPIENT` - Email address to receive the digest
- `SENDER` - Gmail address used to send emails

### Authentication Files Required
- `credentials.json` - Google OAuth credentials file for Gmail API
- `token.pickle` - Auto-generated OAuth token storage (created on first run)

### Google API Keys (Hardcoded - Consider Moving to .env)
- `GOOGLE_API_KEY` - Google Custom Search API key
- `GOOGLE_CX` - Custom Search Engine ID

## Running the Application

### Main Execution
```bash
python news_digest.py
```

The application runs as a single script that:
1. Updates news sources via Google Custom Search
2. Crawls RSS feeds and HTML pages
3. Deduplicates articles
4. Summarizes content with GPT-4
5. Generates HTML email format
6. Sends email via Gmail API

### Gmail API Authentication
On first run, the application will:
1. Open a browser window for Google OAuth consent
2. Request permission to send emails via Gmail
3. Save authentication token to `token.pickle`

## Architecture

### News Source Configuration
The application uses a structured approach to news sources in `NEWS_SOURCES` list:
- **RSS sources**: Direct RSS feed parsing with `feedparser`
- **HTML sources**: Custom HTML scraping with BeautifulSoup
- **Auto-discovery**: Google Custom Search API integration to find new sources

### Core Pipeline Functions
1. `update_news_sources_from_google()` - Dynamically discovers new news sources
2. `fetch_news()` - Multi-source news crawling with RSS/HTML branching
3. `deduplicate_news()` - Removes duplicate articles by title+link
4. `summarize_news()` - GPT-4 summarization with translation for international news
5. `build_email()` - HTML email generation with card-style layout
6. `send_email()` - Gmail API email delivery

### Custom Parsers
- `parse_mafra_news()` - Specialized parser for Korean Ministry of Agriculture website
- Extensible pattern for adding site-specific parsing logic

### Content Processing
- **Keyword filtering**: Articles filtered by industry-relevant keywords
- **Regional grouping**: Content separated into domestic (국내) and international (해외) sections
- **Date extraction**: Attempts to extract publication dates from various source formats
- **Translation**: International news automatically translated to Korean

## Key Features

### Multi-Source News Aggregation
- Korean food industry RSS feeds (식품외식경제, 푸드투데이, etc.)
- Government press releases (농림축산식품부)
- International sources (Nation's Restaurant News, Eater)
- Dynamic source discovery via Google Search

### AI-Powered Content Processing
- GPT-4 summarization to 3-line summaries
- Automatic Korean translation for international content
- Content relevance filtering based on industry keywords

### Professional Email Formatting
- Card-style HTML layout with CSS styling
- Grouped by domestic/international sections
- Include original article links and publication dates
- Daily automated scheduling capability

## Security Considerations

- API keys should be moved from hardcoded values to environment variables
- `credentials.json` contains sensitive OAuth configuration
- `token.pickle` stores authentication tokens - exclude from version control
- OpenAI API usage may incur costs based on article volume

## Deployment Notes

- Designed for daily automated execution (cron job or task scheduler)
- Includes rate limiting with `time.sleep(1)` between source requests
- Error handling for individual source failures doesn't stop entire pipeline
- Gmail API has daily sending limits that should be considered for high-volume usage