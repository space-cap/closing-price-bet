"""
LLM 분석기 - OpenAI 기반 뉴스 분석
gpt-4o-mini 모델 사용 (가성비 최고)
"""

import os
import re
import json
from typing import Dict, List, Optional

from engine.models import NewsItem


class LLMAnalyzer:
    """OpenAI 기반 LLM 분석기"""
    
    SYSTEM_PROMPT = """당신은 주식 뉴스 분석가입니다.
주식 종목의 뉴스를 분석하여 "호재 점수"를 0~3점으로 평가합니다.

평가 기준:
- 3점: 강력한 호재 (대규모 수주, 흑자전환, 신약 승인, M&A 등)
- 2점: 긍정적 뉴스 (실적 개선, 신제품 출시, 투자 유치 등)
- 1점: 약한 호재 또는 중립 뉴스
- 0점: 호재 없음 또는 악재

반드시 아래 JSON 형식으로만 응답하세요:
{"score": 0-3, "reason": "간단한 이유 (50자 이내)"}
"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self._client = None
    
    def _init_client(self):
        """OpenAI 클라이언트 초기화 (지연 로딩)"""
        if self._client is None and self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except Exception as e:
                print(f"OpenAI 초기화 실패: {e}")
                self._client = None
    
    async def analyze_news(
        self,
        stock_name: str,
        news_list: List[NewsItem]
    ) -> Dict:
        """
        뉴스 분석
        
        Returns:
            {"score": int, "reason": str}
        """
        if not news_list:
            return {"score": 0, "reason": "뉴스 없음"}
        
        self._init_client()
        
        if not self._client:
            # API 키가 없으면 키워드 기반 폴백
            return self._fallback_analyze(news_list)
        
        try:
            # 뉴스 목록을 텍스트로 변환
            news_text = "\n".join([
                f"- [{n.source}] {n.title}"
                for n in news_list[:5]  # 상위 5개만
            ])
            
            prompt = f"""종목: {stock_name}

뉴스 목록:
{news_text}

위 뉴스를 분석하여 호재 점수를 평가하세요."""
            
            # 동기 호출 (asyncio.to_thread 사용)
            import asyncio
            response = await asyncio.to_thread(
                self._generate_content,
                prompt
            )
            
            # JSON 파싱
            result = self._parse_response(response)
            return result
            
        except Exception as e:
            print(f"LLM 분석 오류: {e}")
            return self._fallback_analyze(news_list)
    
    def _generate_content(self, prompt: str) -> str:
        """OpenAI API 호출"""
        response = self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content
    
    def _parse_response(self, response: str) -> Dict:
        """응답 파싱"""
        try:
            # JSON 추출 시도
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "score": min(3, max(0, int(result.get("score", 0)))),
                    "reason": str(result.get("reason", ""))[:100]
                }
        except:
            pass
        
        # 파싱 실패 시 기본값
        return {"score": 1, "reason": "분석 결과 불명확"}
    
    def _fallback_analyze(self, news_list: List[NewsItem]) -> Dict:
        """키워드 기반 폴백 분석"""
        score = 0
        reasons = []
        
        positive_keywords = [
            "흑자", "수주", "계약", "승인", "성공", "최대", "증가",
            "개선", "호실적", "상향", "돌파", "신고가"
        ]
        
        negative_keywords = [
            "적자", "하락", "감소", "악화", "폐지", "매도",
            "횡령", "분식", "수사", "기소"
        ]
        
        for news in news_list[:5]:
            title = news.title
            
            # 긍정 키워드
            for kw in positive_keywords:
                if kw in title:
                    score += 1
                    reasons.append(kw)
                    break
            
            # 부정 키워드
            for kw in negative_keywords:
                if kw in title:
                    score -= 1
                    break
        
        final_score = max(0, min(3, score))
        reason = ", ".join(reasons[:3]) if reasons else "뉴스 분석"
        
        return {"score": final_score, "reason": reason}
    
    async def batch_analyze(
        self,
        items: List[tuple]  # [(stock_name, news_list), ...]
    ) -> List[Dict]:
        """
        배치 분석 (여러 종목 동시 처리)
        """
        import asyncio
        
        tasks = [
            self.analyze_news(name, news)
            for name, news in items
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            r if isinstance(r, dict) else {"score": 0, "reason": "오류"}
            for r in results
        ]
