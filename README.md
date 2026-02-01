# KR Market AI Stock Analysis System (Closing Price Bet) 📈

한국 주식 시장(KOSPI, KOSDAQ)을 분석하여 **VCP(Volatility Contraction Pattern)** 패턴과 **기관/외인 수급**을 포착하고, **종가베팅** 시그널을 제공하는 AI 분석 대시보드입니다.

![Dashboard Preview](https://via.placeholder.com/800x400?text=KR+Market+Dashboard+Preview)

<br/>

## 🌟 주요 기능 (Key Features)

- **🚦 Market Gate (시장 분석)**
  - 주식 시장의 현재 상태(GREEN/YELLOW/RED)를 진단
  - KOSPI/KOSDAQ 지수, 환율, 주요 섹터 흐름 분석
  - 이동평균선 정배열/역배열 및 RSI 과매수/과매도 분석

- **🔎 VCP & 수급 스크리너**
  - 변동성 축소 패턴(VCP) 종목 자동 탐지
  - **"쌍끌이 매수"**(외국인 + 기관 동시 순매수) 종목 포착
  - 거래대금 및 시가총액 필터링

- **🎯 종가베팅 V2 엔진**
  - **12점 만점 스코어링 시스템** 기반의 정량적 분석
  - **평가 항목**: 뉴스 호재, 거래량 급증, 차트 패턴, 캔들 모양, 수급 집중도 등
  - **등급 시스템**: S등급(강력 추천) / A등급 / B등급 / C등급(관망)

- **🤖 AI 뉴스 분석 (OpenAI)**
  - GPT-4o-mini 모델을 활용한 뉴스 감성 분석
  - 뉴스 제목과 본문을 분석하여 호재 점수(0~3점) 산출

<br/>

## 🛠 기술 스택 (Tech Stack)

### Backend
- **Python 3.10+**
- **Flask**: RESTful API 서버
- **FinanceDataReader**: 주식 데이터 수집 (pykrx 대체)
- **yfinance**: 글로벌 지수 및 환율 데이터
- **OpenAI API**: 뉴스 분석 및 AI 코멘트

### Frontend
- **Next.js 14** (App Router)
- **TypeScript**
- **Chart.js**: 주가 및 데이터 시각화
- **Styled-components / CSS Modules**: Apple Dark Mode 스타일링

### Infrastructure
- **uv**: 초고속 Python 패키지/프로젝트 매니저

<br/>

## 🚀 설치 및 실행 (Installation & Usage)

이 프로젝트는 **Windows** 환경에서 테스트되었습니다.

### 1. 프로젝트 설정

```bash
# 레포지토리 클론
git clone https://github.com/your-username/kr-market-ai.git
cd kr-market-ai

# 환경 변수 설정
copy .env.example .env
# .env 파일을 열어 OPENAI_API_KEY 등을 입력하세요.
```

### 2. 백엔드 실행 (Backend)

`uv` 패키지 매니저를 사용하여 의존성을 설치하고 서버를 실행합니다.

```bash
# 패키지 동기화
uv sync

# Flask 서버 실행
uv run python flask_app.py
# Server running at http://localhost:5001
```

### 3. 프론트엔드 실행 (Frontend)

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
# Dashboard running at http://localhost:3001
```

<br/>

## 📊 디렉토리 구조 (Directory Structure)

```
closing-price-bet/
├── app/                  # Flask API 라우트 및 설정
├── engine/               # 핵심 분석 엔진 (데이터 수집, 점수 계산, 시그널 생성)
│   ├── collectors.py     # FinanceDataReader/Naver 금융 데이터 수집
│   ├── generator.py      # 시그널 생성 오케스트레이터
│   ├── scorer.py         # 12점 점수 시스템 로직
│   └── llm_analyzer.py   # OpenAI 뉴스 분석기
├── frontend/             # Next.js 대시보드 소스
├── task.md               # 프로젝트 진행 상황 추적
├── market_gate.py        # 시장 상태 독립 실행 스크립트
├── screener.py           # 스크리너 독립 실행 스크립트
└── flask_app.py          # 메인 서버 실행 파일
```

<br/>

## ⚠️ 데이터 수집 주의사항

- **주말/휴일 처리**: 주말이나 공휴일에는 최근 10일 이내의 **마지막 거래일 데이터**를 자동으로 불러와 분석합니다. 대시보드 상단에 **"마지막 거래일"** 배너가 표시됩니다.
- **데이터 출처**: 한국거래소(KRX) 데이터는 `FinanceDataReader`를 통해 수집하며, 네이버 금융 뉴스 크롤링을 병행합니다.

<br/>

## 📄 라이선스 (License)

This project is licensed under the MIT License.
