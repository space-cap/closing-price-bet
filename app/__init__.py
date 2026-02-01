"""
Flask 앱 팩토리
"""

import os
from flask import Flask
from flask_cors import CORS


def create_app():
    """Flask 앱 생성"""
    app = Flask(__name__)
    
    # CORS 설정
    CORS(app, origins=["http://localhost:3000", "http://localhost:3001"])
    
    # 설정
    app.config['JSON_AS_ASCII'] = False
    app.config['JSON_SORT_KEYS'] = False
    
    # 라우트 등록
    from app.routes.kr_market import kr_bp
    from app.routes.common import common_bp
    
    app.register_blueprint(kr_bp, url_prefix='/api/kr')
    app.register_blueprint(common_bp, url_prefix='/api')
    
    # 헬스체크
    @app.route('/health')
    def health():
        return {"status": "ok"}
    
    @app.route('/')
    def index():
        return {
            "name": "KR Market API",
            "version": "2.0",
            "endpoints": [
                "/api/kr/market-status",
                "/api/kr/signals",
                "/api/kr/market-gate",
                "/api/kr/jongga-v2/latest",
                "/api/portfolio",
            ]
        }
    
    return app
