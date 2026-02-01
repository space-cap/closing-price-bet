#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask 애플리케이션 진입점
"""

import os
import sys
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import create_app

# Flask 앱 생성
app = create_app()


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    print("\n" + "=" * 60)
    print("🚀 KR Market API Server")
    print("=" * 60)
    print(f"  URL: http://localhost:{port}")
    print(f"  Debug: {debug}")
    print(f"  Base Dir: {BASE_DIR}")
    print("=" * 60)
    print("\n📍 Endpoints:")
    print("  GET  /health                    - 헬스체크")
    print("  GET  /api/kr/market-status      - 시장 상태")
    print("  GET  /api/kr/signals            - VCP 시그널")
    print("  GET  /api/kr/market-gate        - Market Gate")
    print("  GET  /api/kr/jongga-v2/latest   - 종가베팅 V2")
    print("  POST /api/kr/jongga-v2/run      - 종가베팅 실행")
    print("  GET  /api/portfolio             - 포트폴리오")
    print("  GET  /api/system/data-status    - 데이터 상태")
    print("=" * 60 + "\n")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
    )
