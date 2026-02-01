# app/routes/__init__.py
"""라우트 모듈"""

from app.routes.kr_market import kr_bp
from app.routes.common import common_bp

__all__ = ['kr_bp', 'common_bp']
