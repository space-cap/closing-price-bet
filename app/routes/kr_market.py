# app/routes/kr_market.py
"""KR 마켓 API 라우트"""

import os
import json
import traceback
from datetime import datetime
import pandas as pd
from flask import Blueprint, jsonify, request, current_app

kr_bp = Blueprint('kr', __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')


@kr_bp.route('/market-status')
def get_kr_market_status():
    """한국 시장 상태"""
    try:
        # 일봉 데이터에서 최신 정보 추출
        prices_path = os.path.join(DATA_DIR, 'daily_prices.csv')
        
        status = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "data_available": os.path.exists(prices_path),
        }
        
        if os.path.exists(prices_path):
            df = pd.read_csv(prices_path)
            if not df.empty:
                status["total_stocks"] = len(df)
                status["last_update"] = df.iloc[0].get('date', '')
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@kr_bp.route('/signals')
def get_signals():
    """VCP 시그널 조회"""
    try:
        signals_path = os.path.join(DATA_DIR, 'signals.json')
        
        if not os.path.exists(signals_path):
            return jsonify({
                "status": "ok",
                "signals": [],
                "message": "시그널 데이터 없음",
            })
        
        with open(signals_path, 'r', encoding='utf-8') as f:
            signals = json.load(f)
        
        return jsonify({
            "status": "ok",
            "count": len(signals),
            "signals": signals,
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@kr_bp.route('/market-gate')
def get_market_gate():
    """Market Gate 상태 조회"""
    try:
        gate_path = os.path.join(DATA_DIR, 'market_gate.json')
        
        if not os.path.exists(gate_path):
            # 실시간 분석 실행
            from market_gate import MarketGate
            gate = MarketGate()
            result = gate.analyze()
            return jsonify(result)
        
        with open(gate_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        return jsonify(result)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@kr_bp.route('/jongga-v2/latest')
def get_jongga_v2_latest():
    """종가베팅 V2 최신 결과"""
    try:
        latest_path = os.path.join(DATA_DIR, 'jongga_v2_latest.json')
        
        if not os.path.exists(latest_path):
            return jsonify({
                "status": "ok",
                "signals": [],
                "message": "종가베팅 V2 데이터 없음. 스크리너를 실행해주세요.",
            })
        
        with open(latest_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        return jsonify(result)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@kr_bp.route('/jongga-v2/run', methods=['POST'])
def run_jongga_v2():
    """종가베팅 V2 스크리너 실행"""
    try:
        import asyncio
        from engine.generator import run_screener
        
        capital = request.json.get('capital', 100_000_000) if request.json else 100_000_000
        
        # 비동기 실행
        result = asyncio.run(run_screener(capital=capital, save_result=True))
        
        return jsonify({
            "status": "ok",
            "message": "스크리닝 완료",
            "result": result.to_dict(),
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@kr_bp.route('/ai-analysis')
def get_ai_analysis():
    """AI 분석 결과 조회"""
    try:
        analysis_path = os.path.join(DATA_DIR, 'kr_ai_analysis.json')
        
        if not os.path.exists(analysis_path):
            return jsonify({
                "status": "ok",
                "analysis": None,
                "message": "AI 분석 데이터 없음",
            })
        
        with open(analysis_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        return jsonify({
            "status": "ok",
            "analysis": result,
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@kr_bp.route('/stock-chart/<ticker>')
def get_stock_chart(ticker):
    """종목 차트 데이터"""
    try:
        days = request.args.get('days', 60, type=int)
        
        from pykrx import stock
        from datetime import datetime, timedelta
        
        today = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
        
        df = stock.get_market_ohlcv(start, today, ticker)
        
        if df.empty:
            return jsonify({
                "status": "error",
                "message": "차트 데이터 없음",
            }), 404
        
        df = df.tail(days)
        
        chart_data = []
        for idx, row in df.iterrows():
            chart_data.append({
                "date": idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx),
                "open": int(row['시가']),
                "high": int(row['고가']),
                "low": int(row['저가']),
                "close": int(row['종가']),
                "volume": int(row['거래량']),
            })
        
        return jsonify({
            "status": "ok",
            "ticker": ticker,
            "data": chart_data,
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@kr_bp.route('/backtest-summary')
def get_backtest_summary():
    """백테스트 요약"""
    try:
        backtest_path = os.path.join(DATA_DIR, 'backtest_results.json')
        
        if not os.path.exists(backtest_path):
            return jsonify({
                "status": "ok",
                "vcp": {"status": "no_data", "message": "백테스트 결과 없음"},
                "closing_bet": {"status": "no_data", "message": "백테스트 결과 없음"},
            })
        
        with open(backtest_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500
