# app/routes/common.py
"""공통 API 라우트"""

import os
import json
import traceback
import pandas as pd
import sys
import subprocess
from flask import Blueprint, jsonify, request

common_bp = Blueprint('common', __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')

# 섹터 맵
SECTOR_MAP = {
    "반도체": ["005930", "000660", "042700"],
    "2차전지": ["373220", "006400", "003670"],
    "자동차": ["005380", "000270", "012330"],
    "바이오": ["207940", "068270", "326030"],
    "인터넷": ["035420", "035720", "377300"],
}


def get_sector(code: str) -> str:
    """종목코드로 섹터 조회"""
    for sector, codes in SECTOR_MAP.items():
        if code in codes:
            return sector
    return "기타"


@common_bp.route('/portfolio')
def get_portfolio():
    """포트폴리오 조회"""
    try:
        portfolio_path = os.path.join(DATA_DIR, 'portfolio.json')
        
        if not os.path.exists(portfolio_path):
            return jsonify({
                "status": "ok",
                "positions": [],
                "summary": {
                    "total_value": 0,
                    "cash": 100000000,
                    "total_pnl": 0,
                    "total_pnl_pct": 0,
                }
            })
        
        with open(portfolio_path, 'r', encoding='utf-8') as f:
            portfolio = json.load(f)
        
        return jsonify(portfolio)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@common_bp.route('/system/data-status')
def get_data_status():
    """데이터 파일 상태 확인"""
    try:
        files = [
            'daily_prices.csv',
            'all_institutional_trend_data.csv',
            'signals.json',
            'market_gate.json',
            'jongga_v2_latest.json',
            'kr_ai_analysis.json',
            'portfolio.json',
        ]
        
        file_status = {}
        for filename in files:
            filepath = os.path.join(DATA_DIR, filename)
            if os.path.exists(filepath):
                stat = os.stat(filepath)
                file_status[filename] = {
                    "exists": True,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "modified": pd.Timestamp(stat.st_mtime, unit='s').isoformat(),
                }
            else:
                file_status[filename] = {
                    "exists": False,
                }
        
        return jsonify({
            "status": "ok",
            "data_dir": DATA_DIR,
            "files": file_status,
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@common_bp.route('/run-command', methods=['POST'])
def run_command():
    """관리용 커맨드 실행"""
    try:
        data = request.json
        command = data.get('command', '')
        
        # 허용된 커맨드만 실행
        allowed = {
            'screener': 'python screener.py',
            'market-gate': 'python market_gate.py',
            'jongga-v2': 'python -c "import asyncio; from engine.generator import run_screener; asyncio.run(run_screener())"',
        }
        
        if command not in allowed:
            return jsonify({
                "status": "error",
                "message": f"허용되지 않은 커맨드: {command}. 허용: {list(allowed.keys())}",
            }), 400
        
        cmd = allowed[command]
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            timeout=300,
        )
        
        return jsonify({
            "status": "ok" if result.returncode == 0 else "error",
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            "status": "error",
            "message": "명령어 실행 타임아웃 (5분)",
        }), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@common_bp.route('/sector-map')
def get_sector_map():
    """섹터 맵 조회"""
    return jsonify({
        "status": "ok",
        "sectors": SECTOR_MAP,
    })


@common_bp.route('/ticker-name/<code>')
def get_ticker_name(code):
    """종목코드로 종목명 조회"""
    try:
        from pykrx import stock
        from datetime import datetime
        
        today = datetime.now().strftime("%Y%m%d")
        name = stock.get_market_ticker_name(code)
        
        return jsonify({
            "status": "ok",
            "code": code,
            "name": name or code,
            "sector": get_sector(code),
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500
