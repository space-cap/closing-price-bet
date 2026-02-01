"""
데이터 수집기 모듈
- KRXCollector: pykrx 기반 가격/수급 데이터 수집
- EnhancedNewsCollector: 네이버/다음 뉴스 크롤링
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
import pandas as pd
import re
from bs4 import BeautifulSoup

from engine.config import SignalConfig
from engine.models import StockData, NewsItem, SupplyData, ChartData


class KRXCollector:
    """KRX 데이터 수집기 (pykrx 기반)"""
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or SignalConfig()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def get_top_gainers(self, market: str = "KOSPI", top_n: int = 30) -> List[StockData]:
        """상승률 상위 종목 조회"""
        try:
            from pykrx import stock
            
            today = datetime.now().strftime("%Y%m%d")
            
            # 동기 함수를 비동기로 실행
            df = await asyncio.to_thread(
                stock.get_market_ohlcv_by_ticker,
                today,
                market=market
            )
            
            if df.empty:
                # 오늘 데이터가 없으면 가장 최근 거래일 시도
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                df = await asyncio.to_thread(
                    stock.get_market_ohlcv_by_ticker,
                    yesterday,
                    market=market
                )
            
            if df.empty:
                print(f"[{market}] 데이터 없음")
                return []
            
            # 등락률 계산 및 필터링
            df['change_pct'] = df['등락률']
            df = df[df['change_pct'] >= self.config.min_change_pct]
            df = df[df['change_pct'] <= self.config.max_change_pct]
            df = df[df['거래대금'] >= self.config.min_trading_value]
            df = df[df['종가'] >= self.config.min_price]
            df = df[df['종가'] <= self.config.max_price]
            
            # 상승률 상위 N개
            df = df.nlargest(top_n, 'change_pct')
            
            # 종목명 가져오기
            ticker_names = await asyncio.to_thread(stock.get_market_ticker_name, today, market=market)
            
            stocks = []
            for code in df.index:
                row = df.loc[code]
                name = ticker_names.get(code, code)
                
                # 제외 키워드 체크
                if any(kw in name for kw in self.config.exclude_keywords):
                    continue
                
                stocks.append(StockData(
                    code=code,
                    name=name,
                    market=market,
                    close=float(row['종가']),
                    open=float(row['시가']),
                    high=float(row['고가']),
                    low=float(row['저가']),
                    change_pct=float(row['change_pct']),
                    volume=int(row['거래량']),
                    trading_value=int(row['거래대금']),
                ))
            
            return stocks
            
        except Exception as e:
            print(f"Error in get_top_gainers: {e}")
            return []
    
    async def get_stock_detail(self, code: str) -> Optional[StockData]:
        """종목 상세 정보 조회"""
        try:
            from pykrx import stock
            
            today = datetime.now().strftime("%Y%m%d")
            start = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            
            # OHLCV 데이터
            df = await asyncio.to_thread(
                stock.get_market_ohlcv,
                start, today, code
            )
            
            if df.empty:
                return None
            
            # 52주 고가/저가
            high_52w = float(df['고가'].max())
            low_52w = float(df['저가'].min())
            
            latest = df.iloc[-1]
            name = await asyncio.to_thread(stock.get_market_ticker_name, today, code)
            
            return StockData(
                code=code,
                name=name or code,
                market="",
                close=float(latest['종가']),
                high_52w=high_52w,
                low_52w=low_52w,
            )
            
        except Exception as e:
            print(f"Error in get_stock_detail: {e}")
            return None
    
    async def get_chart_data(self, code: str, days: int = 60) -> List[ChartData]:
        """차트 데이터 조회"""
        try:
            from pykrx import stock
            
            today = datetime.now().strftime("%Y%m%d")
            start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
            
            df = await asyncio.to_thread(
                stock.get_market_ohlcv,
                start, today, code
            )
            
            if df.empty:
                return []
            
            # 최근 N일만
            df = df.tail(days)
            
            charts = []
            for idx, row in df.iterrows():
                charts.append(ChartData(
                    date=idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx),
                    open=float(row['시가']),
                    high=float(row['고가']),
                    low=float(row['저가']),
                    close=float(row['종가']),
                    volume=int(row['거래량']),
                ))
            
            return charts
            
        except Exception as e:
            print(f"Error in get_chart_data: {e}")
            return []
    
    async def get_supply_data(self, code: str) -> Optional[SupplyData]:
        """수급 데이터 조회 (5일/20일 누적)"""
        try:
            from pykrx import stock
            
            today = datetime.now().strftime("%Y%m%d")
            start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            
            df = await asyncio.to_thread(
                stock.get_market_net_purchases_of_equities,
                start, today, code
            )
            
            if df.empty:
                return None
            
            # 최근 데이터 기준
            recent_5d = df.tail(5)
            recent_20d = df.tail(20)
            
            foreign_5d = int(recent_5d['외국인합계'].sum()) if '외국인합계' in df.columns else 0
            foreign_20d = int(recent_20d['외국인합계'].sum()) if '외국인합계' in df.columns else 0
            inst_5d = int(recent_5d['기관합계'].sum()) if '기관합계' in df.columns else 0
            inst_20d = int(recent_20d['기관합계'].sum()) if '기관합계' in df.columns else 0
            
            # 연속 매수일 계산
            foreign_consecutive = 0
            inst_consecutive = 0
            
            if '외국인합계' in df.columns:
                for val in df['외국인합계'].iloc[::-1]:
                    if val > 0:
                        foreign_consecutive += 1
                    else:
                        break
            
            if '기관합계' in df.columns:
                for val in df['기관합계'].iloc[::-1]:
                    if val > 0:
                        inst_consecutive += 1
                    else:
                        break
            
            is_double = foreign_5d > 0 and inst_5d > 0
            
            return SupplyData(
                code=code,
                foreign_buy_5d=foreign_5d,
                foreign_buy_20d=foreign_20d,
                foreign_consecutive_days=foreign_consecutive,
                inst_buy_5d=inst_5d,
                inst_buy_20d=inst_20d,
                inst_consecutive_days=inst_consecutive,
                is_double_buy=is_double,
            )
            
        except Exception as e:
            print(f"Error in get_supply_data: {e}")
            return None


class EnhancedNewsCollector:
    """뉴스 수집기 (네이버/다음)"""
    
    MAJOR_SOURCES = {
        "한국경제": 0.9,
        "매일경제": 0.9,
        "머니투데이": 0.85,
        "서울경제": 0.85,
        "이데일리": 0.85,
        "연합뉴스": 0.85,
        "뉴스1": 0.8,
        "헤럴드경제": 0.8,
        "파이낸셜뉴스": 0.8,
    }
    
    def __init__(self, config: SignalConfig = None):
        self.config = config or SignalConfig()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self._session = aiohttp.ClientSession(headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def get_stock_news(self, code: str, limit: int = 5, name: str = "") -> List[NewsItem]:
        """종목별 뉴스 조회"""
        news_items = []
        
        try:
            # 네이버 금융 뉴스
            url = f"https://finance.naver.com/item/news_news.nhn?code={code}&page=1"
            
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    return []
                
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 뉴스 목록 파싱
                news_table = soup.find('table', class_='type5')
                if not news_table:
                    return []
                
                rows = news_table.find_all('tr')
                
                for row in rows[:limit * 2]:  # 여유있게 가져옴
                    title_tag = row.find('a', class_='tit')
                    if not title_tag:
                        continue
                    
                    title = title_tag.get_text(strip=True)
                    link = title_tag.get('href', '')
                    
                    # 날짜 파싱
                    date_tag = row.find('td', class_='date')
                    date_str = date_tag.get_text(strip=True) if date_tag else ""
                    
                    # 언론사 파싱
                    source_tag = row.find('td', class_='info')
                    source = source_tag.get_text(strip=True) if source_tag else ""
                    
                    # 관련도 계산
                    relevance = self.MAJOR_SOURCES.get(source, 0.7)
                    
                    news_items.append(NewsItem(
                        title=title,
                        summary="",  # 본문은 별도 호출 필요
                        source=source,
                        url=f"https://finance.naver.com{link}" if link.startswith('/') else link,
                        relevance=relevance,
                    ))
                    
                    if len(news_items) >= limit:
                        break
            
            # 본문 요약 수집 (상위 3개만)
            for i, news in enumerate(news_items[:3]):
                if news.url:
                    summary = await self._fetch_news_summary(news.url)
                    news.summary = summary
            
        except Exception as e:
            print(f"Error fetching news for {code}: {e}")
        
        return news_items
    
    async def _fetch_news_summary(self, url: str) -> str:
        """뉴스 본문 요약 추출"""
        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return ""
                
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 본문 추출 시도
                content = None
                
                # 네이버 금융 뉴스 본문
                content_div = soup.find('div', id='news_read')
                if content_div:
                    content = content_div.get_text(strip=True)
                
                if not content:
                    # 일반 기사 본문
                    article = soup.find('article') or soup.find('div', class_='article_body')
                    if article:
                        content = article.get_text(strip=True)
                
                if content:
                    # 앞부분 200자만 반환
                    content = re.sub(r'\s+', ' ', content)
                    return content[:200] + "..." if len(content) > 200 else content
                
        except Exception as e:
            pass
        
        return ""
