import feedparser
from openai import OpenAI
# import yagmail  # yagmail 삭제
from datetime import datetime
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import time
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import re
import json
# pip install feedfinder2 필요
try:
    from feedfinder2 import find_feeds
except ImportError:
    find_feeds = None

# === 설정 ===
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
RECIPIENT = os.getenv("RECIPIENT")
SENDER = os.getenv("SENDER")
# APP_PASSWORD = os.getenv("APP_PASSWORD")  # 삭제

# === Gmail API 인증 ===
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def gmail_authenticate():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

# === 뉴스 소스 구조화 ===
NEWS_SOURCES = [
    # RSS 지원
    {
        "name": "식품외식경제",
        "type": "rss",
        "url": "https://www.foodbank.co.kr/rss/all.xml",
        "keywords": ["외식업", "요식업", "행사", "이벤트", "네트워킹", "교류", "교육", "이벤트", "행사"],
        "region": "국내"
    },
    {
        "name": "푸드투데이",
        "type": "rss",
        "url": "http://www.foodtoday.or.kr/rss/allArticle.xml",
        "keywords": ["외식업", "요식업", "행사", "이벤트", "네트워킹", "교류", "교육", "이벤트", "행사"],
        "region": "국내"
    },
    {
        "name": "식품저널",
        "type": "rss",
        "url": "http://www.foodnews.co.kr/rss/allArticle.xml",
        "keywords": ["외식업", "요식업", "행사", "이벤트", "네트워킹", "교류", "교육", "이벤트", "행사"],
        "region": "국내"
    },
    {
        "name": "식품음료신문",
        "type": "rss",
        "url": "http://www.thinkfood.co.kr/rss/allArticle.xml",
        "keywords": ["외식업", "요식업", "행사", "이벤트", "네트워킹", "교류", "교육", "이벤트", "행사"],
        "region": "국내"
    },
    # HTML 크롤링 필요 (예시)
    {
        "name": "농림축산식품부 보도자료",
        "type": "html",
        "url": "https://www.mafra.go.kr/mafra/293/subview.do",
        "keywords": ["외식업", "요식업", "행사", "이벤트", "네트워킹", "교류", "교육", "이벤트", "행사"],
        "region": "국내"
    },
    {
        "name": "외식경영",
        "type": "html",
        "url": "http://www.foodservice.co.kr/",
        "keywords": ["외식업", "요식업", "행사", "이벤트", "네트워킹", "교류", "교육", "이벤트", "행사"],
        "region": "국내"
    },
    {
        "name": "매일경제 유통경제",
        "type": "html",
        "url": "https://www.mk.co.kr/news/business/retail/",
        "keywords": ["외식업", "요식업", "행사", "이벤트", "네트워킹", "교류", "교육", "이벤트", "행사"],
        "region": "국내"
    },
    {
        "name": "한경 FOOD섹션",
        "type": "html",
        "url": "https://www.hankyung.com/food",
        "keywords": ["외식업", "요식업", "행사", "이벤트", "네트워킹", "교류", "교육", "이벤트", "행사"],
        "region": "국내"
    },
    # 해외 예시(기존 유지)
    {
        "name": "Nation’s Restaurant News",
        "type": "rss",
        "url": "https://www.nrn.com/rss.xml",
        "keywords": ["restaurant", "event", "networking", "education", "news"],
        "region": "해외"
    },
    {
        "name": "Eater",
        "type": "rss",
        "url": "https://www.eater.com/rss/index.xml",
        "keywords": ["restaurant", "event", "networking", "education", "news"],
        "region": "해외"
    },
]

# === 구글 Custom Search API로 새 사이트 자동 추가 ===
GOOGLE_API_KEY = "AIzaSyDU5fjMpbNl6fk9LuasX8s3F9woP_RmB9A"
GOOGLE_CX = "a0a8f206f396641ac"
SEARCH_KEYWORDS = [
    "외식업 행사", "외식업 이벤트", "요식업 행사", "요식업 이벤트", "외식업 뉴스", "요식업뉴스", "요식업 이벤트", "식품개발", "케이터링"
]

def get_domain(url):
    match = re.match(r"https?://([^/]+)/", url)
    if match:
        return match.group(1)
    return None

def update_news_sources_from_google():
    print("[LOG] 구글에서 외식업 행사/이벤트 관련 사이트 자동 탐색...")
    global NEWS_SOURCES
    existing_domains = set(get_domain(src["url"]) for src in NEWS_SOURCES)
    new_sources = []
    for keyword in SEARCH_KEYWORDS:
        params = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CX,
            "q": keyword,
            "num": 10
        }
        resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
        if resp.status_code != 200:
            print(f"[LOG] 구글 검색 실패: {resp.text}")
            continue
        data = resp.json()
        for item in data.get("items", []):
            link = item.get("link")
            domain = get_domain(link)
            if not domain or any(domain in get_domain(src["url"]) for src in NEWS_SOURCES):
                continue
            # RSS 피드 자동 탐지
            rss_url = None
            if find_feeds:
                try:
                    feeds = find_feeds(link)
                    if feeds:
                        rss_url = feeds[0]
                except Exception as e:
                    print(f"[LOG] RSS 탐지 실패: {e}")
            if rss_url:
                new_sources.append({
                    "name": domain,
                    "type": "rss",
                    "url": rss_url,
                    "keywords": ["외식업", "요식업", "행사", "이벤트", "네트워킹", "교류", "교육", "이벤트", "행사"],
                    "region": "국내"
                })
            else:
                new_sources.append({
                    "name": domain,
                    "type": "html",
                    "url": link,
                    "keywords": ["외식업", "요식업", "행사", "이벤트", "네트워킹", "교류", "교육", "이벤트", "행사"],
                    "region": "국내"
                })
    # 중복 도메인 제거
    added_domains = set(get_domain(src["url"]) for src in NEWS_SOURCES)
    for src in new_sources:
        d = get_domain(src["url"])
        if d and d not in added_domains:
            NEWS_SOURCES.append(src)
            added_domains.add(d)
    print(f"[LOG] 구글 검색 기반 국내 소스 {len(new_sources)}개 자동 추가 완료.")

# === 1. 뉴스 크롤링 (RSS/HTML 자동 분기, 커스텀 파서 구조화) ===
def fetch_news():
    print("[LOG] 뉴스 크롤링 시작...")
    all_news = []
    for source in NEWS_SOURCES:
        print(f"[LOG] {source['name']} ({source['type']}) 크롤링 중...")
        try:
            if source["type"] == "rss":
                feed = feedparser.parse(source["url"])
                for entry in feed.entries:
                    title = entry.title
                    summary = entry.summary if hasattr(entry, 'summary') else ''
                    link = entry.link
                    # 날짜 정보 추출 (가능한 경우)
                    pub_date = ''
                    if hasattr(entry, 'published'):
                        pub_date = entry.published
                    elif hasattr(entry, 'updated'):
                        pub_date = entry.updated
                    # 키워드 필터
                    if any(k in title or k in summary for k in source["keywords"]):
                        all_news.append({
                            "title": title,
                            "link": link,
                            "summary": summary,
                            "source": source["name"],
                            "date": pub_date,
                            "region": source["region"]
                        })
            elif source["type"] == "html":
                # 커스텀 파서 구조: 사이트별로 함수 분리 가능
                if source["name"] == "농림축산식품부 보도자료":
                    all_news.extend(parse_mafra_news(source))
                else:
                    # 기본 HTML 파서 (필요시 확장)
                    resp = requests.get(source["url"], timeout=10)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.select("a")
                    for a in articles[:10]:
                        title = a.get_text(strip=True)
                        link = a.get("href")
                        if not link or not title:
                            continue
                        if not link.startswith("http"):
                            link = source["url"] + link
                        if any(k in title for k in source["keywords"]):
                            all_news.append({
                                "title": title,
                                "link": link,
                                "summary": title,
                                "source": source["name"],
                                "date": '',
                                "region": source["region"]
                            })
            print(f"[LOG] {source['name']} 크롤링 완료.")
            time.sleep(1)  # 과도한 요청 방지
        except Exception as e:
            print(f"[LOG] {source['name']} 크롤링 실패: {e}")
    print(f"[LOG] 전체 뉴스 크롤링 완료. {len(all_news)}개 기사 수집.")
    return all_news

# === 농림축산식품부 보도자료 커스텀 파서 ===
def parse_mafra_news(source):
    news = []
    try:
        resp = requests.get(source["url"], timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.select(".bd-list .bd-title a")
        for a in articles[:10]:
            title = a.get_text(strip=True)
            link = a.get("href")
            if not link or not title:
                continue
            if not link.startswith("http"):
                link = "https://www.mafra.go.kr" + link
            # 날짜 정보 추출 (같은 행의 날짜 span 등에서 추출 가능)
            date = ''
            row = a.find_parent("tr")
            if row:
                date_td = row.find_all("td")
                if len(date_td) > 2:
                    date = date_td[2].get_text(strip=True)
            if any(k in title for k in source["keywords"]):
                news.append({
                    "title": title,
                    "link": link,
                    "summary": title,
                    "source": source["name"],
                    "date": date,
                    "region": source["region"]
                })
    except Exception as e:
        print(f"[LOG] 농림축산식품부 파싱 실패: {e}")
    return news

# === 2. 중복 제거 ===
def deduplicate_news(news_items):
    seen = set()
    unique_news = []
    for item in news_items:
        key = (item["title"], item["link"])
        if key not in seen:
            unique_news.append(item)
            seen.add(key)
    print(f"[LOG] 중복 제거 후 {len(unique_news)}개 기사 남음.")
    return unique_news

# === 3. GPT로 요약 및 해외 번역 ===
def summarize_news(news_items):
    print("[LOG] 뉴스 요약 시작...")
    summaries = []
    for idx, item in enumerate(news_items[:10]):
        content = item["summary"]
        prompt = f"[{item['source']}] {item['title']}\n\n다음 내용을 3줄로 요약해줘:\n\n{content}"
        print(f"[LOG] {idx+1}번째 뉴스 요약 요청 중...")
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            summary = response.choices[0].message.content.strip()
            # 해외 뉴스는 한국어 번역 추가
            if item.get("region") == "해외":
                translate_prompt = f"다음 영어 요약을 자연스러운 한국어로 번역해줘.\n\n{summary}"
                print(f"[LOG] {idx+1}번째 해외 뉴스 번역 요청 중...")
                tr_response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": translate_prompt}]
                )
                summary = tr_response.choices[0].message.content.strip()
        except Exception as e:
            summary = f"요약 실패: {e}"
        summaries.append({
            "title": item["title"],
            "summary": summary,
            "link": item["link"],
            "source": item["source"],
            "date": item["date"],
            "region": item.get("region", "국내")
        })
        print(f"[LOG] {idx+1}번째 뉴스 요약 완료.")
    print(f"[LOG] 뉴스 요약 전체 완료. {len(summaries)}개 요약.")
    return summaries

# === 4. 이메일 생성 (국내/해외 섹션 구분, 카드형, 날짜 포함) ===
def build_email(summaries):
    print("[LOG] 이메일 생성 시작...")
    today = datetime.now().strftime("%Y년 %m월 %d일")
    # 국내/해외로 그룹핑
    grouped = {"국내": [], "해외": []}
    for item in summaries:
        grouped[item["region"]].append(item)
    # 카드형 스타일 CSS
    style = """
    <style>
    .news-category {margin-bottom: 32px;}
    .news-title {font-size: 1.2em; font-weight: bold; margin-bottom: 8px;}
    .news-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
        background: #fafbfc;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .news-date {color: #888; font-size: 0.95em; margin-bottom: 6px;}
    .news-link {margin-top: 8px; display: inline-block; color: #1976d2; text-decoration: none;}
    </style>
    """
    html = f"<h2>📬 {today} 요식업 뉴스 요약</h2>" + style
    # 국내 섹션
    if grouped["국내"]:
        html += '<div class="news-category"><div class="news-title">[ 국내 ]</div>'
        for item in grouped["국내"]:
            html += '<div class="news-card">'
            if item["date"]:
                html += f'<div class="news-date">{item["date"]}</div>'
            html += f'<div><b>{item["title"]}</b></div>'
            html += f'<div>{item["summary"]}</div>'
            html += f'<a class="news-link" href="{item["link"]}">원문 보기</a>'
            html += '</div>'
        html += '</div>'
    # 해외 섹션
    if grouped["해외"]:
        html += '<div class="news-category"><div class="news-title">[ 해외 ]</div>'
        for item in grouped["해외"]:
            html += '<div class="news-card">'
            if item["date"]:
                html += f'<div class="news-date">{item["date"]}</div>'
            html += f'<div><b>{item["title"]}</b></div>'
            html += f'<div>{item["summary"]}</div>'
            html += f'<a class="news-link" href="{item["link"]}">원문 보기</a>'
            html += '</div>'
        html += '</div>'
    html += "<p>매일 오전 9시에 자동 발송됩니다.</p>"
    print("[LOG] 이메일 생성 완료.")
    return html

# === 5. 메일 전송 (Gmail API) ===
def send_email(html):
    print("[LOG] 이메일 전송 시작...")
    service = gmail_authenticate()
    message = MIMEText(html, 'html')
    message['to'] = RECIPIENT
    message['from'] = SENDER
    message['subject'] = "📬 요식업 뉴스 요약"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'raw': raw}
    sent = service.users().messages().send(userId='me', body=body).execute()
    print(f"[LOG] 이메일 전송 완료. Message Id: {sent['id']}")

# === 실행 ===
if __name__ == "__main__":
    print("[LOG] 프로그램 실행 시작.")
    print("SENDER:", SENDER)
    # print("APP_PASSWORD:", APP_PASSWORD[:4] + "************") # 삭제
    print("RECIPIENT:", RECIPIENT)
    update_news_sources_from_google()
    news = fetch_news()
    if news:
        news = deduplicate_news(news)
        summaries = summarize_news(news)
        html = build_email(summaries)
        send_email(html)
    else:
        print("[LOG] 오늘의 뉴스가 없습니다.")
    print("[LOG] 프로그램 실행 종료.")
