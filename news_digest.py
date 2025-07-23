import feedparser
import openai
import yagmail
from datetime import datetime
from dotenv import load_dotenv
import os

# === 설정 ===
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
RECIPIENT = os.getenv("RECIPIENT")
SENDER = os.getenv("SENDER")
APP_PASSWORD = os.getenv("APP_PASSWORD")
KEYWORDS = ["요식업", "외식", "식음료", "프라이빗 다이닝"]

# === 1. Google 뉴스 RSS 크롤링 ===
def fetch_news():
    url = "https://news.google.com/rss/search?q=요식업+외식+행사+when:1d&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    return [
        {"title": entry.title, "link": entry.link, "summary": entry.summary}
        for entry in feed.entries
        if any(k in entry.title for k in KEYWORDS)
    ]

# === 2. GPT로 요약 ===
def summarize_news(news_items):
    summaries = []
    for item in news_items[:5]:
        content = item["summary"]
        prompt = f"다음 내용을 3줄로 요약해줘:\n\n{content}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response["choices"][0]["message"]["content"].strip()
        summaries.append((item["title"], summary, item["link"]))
    return summaries

# === 3. 이메일 생성 ===
def build_email(summaries):
    today = datetime.now().strftime("%Y년 %m월 %d일")
    html = f"<h2>📬 {today} 요식업 뉴스 요약</h2><ul>"
    for title, summary, link in summaries:
        html += f"<li><b>{title}</b><br>{summary}<br><a href='{link}'>원문 보기</a><br><br></li>"
    html += "</ul><p>매일 오전 9시에 자동 발송됩니다.</p>"
    return html

# === 4. 메일 전송 ===
def send_email(html):
    yag = yagmail.SMTP(SENDER, APP_PASSWORD)
    yag.send(to=RECIPIENT, subject="📬 요식업 뉴스 요약", contents=html)

# === 실행 ===
if __name__ == "__main__":
    news = fetch_news()
    if news:
        summaries = summarize_news(news)
        html = build_email(summaries)
        send_email(html)
