from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os
import time
import logging

# Add project root for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.state import load_state

# NICE/Palantir 모듈 (폴백 포함)
try:
    from engine.collectors.robust_collector import RobustDataCollector
    from engine.agents.signal_agents import SignalAggregator
    from engine.llm.orchestrator import LLMOrchestrator
    PALANTIR_AVAILABLE = True
except ImportError as e:
    PALANTIR_AVAILABLE = False
    logging.warning(f"Palantir modules not fully available: {e}")

app = Flask(__name__)
CORS(app)

# 싱글톤 인스턴스
_collector = None
_aggregator = None
_orchestrator = None

def get_collector():
    global _collector
    if _collector is None and PALANTIR_AVAILABLE:
        _collector = RobustDataCollector()
    return _collector

def get_aggregator():
    global _aggregator
    if _aggregator is None and PALANTIR_AVAILABLE:
        _aggregator = SignalAggregator()
    return _aggregator

def get_orchestrator():
    global _orchestrator
    if _orchestrator is None and PALANTIR_AVAILABLE:
        _orchestrator = LLMOrchestrator()
    return _orchestrator


# ==================== 기존 엔드포인트 (유지) ====================

@app.route('/')
def index():
    return "Phoenix API Online ⚡ NICE/Palantir Enabled"

@app.route('/health')
def health():
    return jsonify({
        "status": "online",
        "palantir_enabled": PALANTIR_AVAILABLE,
        "timestamp": time.time()
    })

@app.route('/api/market')
@app.route('/api/state')
def get_market():
    """기존 Market Data Endpoint (유지)"""
    start = time.time()
    state = load_state()
    duration_ms = (time.time() - start) * 1000
    
    if not state:
        return jsonify({"error": "Engine warming up...", "status": "WAITING"}), 200
    
    if '_meta' not in state:
        state['_meta'] = {}
    state['_meta']['api_latency_ms'] = round(duration_ms, 3)
    
    return jsonify(state)


# ==================== 새 NICE/Palantir 엔드포인트 ====================

@app.route('/api/analyze/<symbol>')
def analyze_symbol(symbol: str):
    """
    단일 심볼 분석 (NICE 모델)
    3-Tier 데이터 수집 + 5개 Agent 분석 + LLM 종합
    """
    if not PALANTIR_AVAILABLE:
        return jsonify({"error": "Palantir modules not available"}), 503
    
    start = time.time()
    symbol = symbol.upper()
    
    try:
        # 1. 데이터 수집 (절대 실패 안 함)
        collector = get_collector()
        market_data = collector.collect_with_fallback(symbol)
        
        # 2. 5개 Agent 분석
        aggregator = get_aggregator()
        agent_result = aggregator.get_all_signals(market_data=market_data)
        
        # 3. LLM CIO Decision (폴백 포함)
        orchestrator = get_orchestrator()
        client_key = request.headers.get('X-Gemini-API-Key')
        cio_decision = orchestrator.synthesize(
            symbol, 
            agent_result['agent_scores'], 
            agent_result['weighted_score'],
            override_key=client_key
        )
        
        duration_ms = (time.time() - start) * 1000
        
        return jsonify({
            "symbol": symbol,
            "price": market_data.get('price', 0),
            "change_rate": market_data.get('change_rate', 0),
            "source": market_data.get('source', 'unknown'),
            "agent_scores": agent_result['agent_scores'],
            "score": agent_result['weighted_score'],
            "signal": agent_result['signal'],
            "type": agent_result['signal_type'],
            "confidence": agent_result['confidence'],
            "cio_decision": cio_decision,
            "latency_ms": round(duration_ms, 2)
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "symbol": symbol}), 500


@app.route('/api/agents/signals')
def get_agent_signals():
    """
    모든 감시 종목의 Agent 신호 조회
    """
    if not PALANTIR_AVAILABLE:
        return jsonify({"error": "Palantir modules not available"}), 503
    
    symbols = request.args.get('symbols', 'BTC,ETH,XRP,SOL,ADA').split(',')
    
    results = []
    collector = get_collector()
    aggregator = get_aggregator()
    
    for symbol in symbols:
        try:
            market_data = collector.collect_with_fallback(symbol.strip().upper())
            signal = aggregator.get_all_signals(market_data=market_data)
            
            results.append({
                "symbol": symbol.upper(),
                "price": market_data.get('price', 0),
                "change_rate": market_data.get('change_rate', 0),
                "scores": signal['agent_scores'],
                "weighted_score": signal['weighted_score'],
                "signal": signal['signal']
            })
        except Exception as e:
            results.append({"symbol": symbol, "error": str(e)})
    
    return jsonify({
        "count": len(results),
        "signals": results,
        "timestamp": time.time()
    })


@app.route('/api/palantir/status')
def palantir_status():
    """Palantir 시스템 상태"""
    return jsonify({
        "enabled": PALANTIR_AVAILABLE,
        "modules": {
            "robust_collector": PALANTIR_AVAILABLE,
            "signal_agents": PALANTIR_AVAILABLE,
            "llm_orchestrator": PALANTIR_AVAILABLE,
            "candles": True,
            "technical_analysis": True
        },
        "version": "2.0.0-phoenix",
        "timestamp": time.time()
    })


# ==================== 캔들 & 기술 분석 엔드포인트 ====================

# 캔들/기술분석 모듈 임포트
try:
    from engine.analysis.candles import CandleCollector
    from engine.analysis.technical import TechnicalAnalyzer
    _candle_collector = CandleCollector()
    _technical_analyzer = TechnicalAnalyzer()
    CANDLE_AVAILABLE = True
except ImportError as e:
    CANDLE_AVAILABLE = False
    logging.warning(f"Candle modules not available: {e}")


@app.route('/api/candles/<symbol>')
def get_candles(symbol: str):
    """
    캔들 데이터 조회
    
    Query params:
        tf: 시간대 (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M) - 기본값 1h
        count: 개수 (기본값 100, 최대 200)
    """
    if not CANDLE_AVAILABLE:
        return jsonify({"error": "Candle module not available"}), 503
    
    timeframe = request.args.get('tf', '1h')
    count = min(int(request.args.get('count', 100)), 200)
    
    try:
        candles = _candle_collector.get_candles(symbol.upper(), timeframe, count)
        
        return jsonify({
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "count": len(candles),
            "candles": candles
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/technical/<symbol>')
def get_technical(symbol: str):
    """
    기술적 분석 조회
    RSI, 피보나치, 매물대, 엘리엇 파동, 매수/매도 레벨
    
    Query params:
        tf: 시간대 (기본값 1h)
    """
    if not CANDLE_AVAILABLE:
        return jsonify({"error": "Technical analysis not available"}), 503
    
    timeframe = request.args.get('tf', '1h')
    
    try:
        # 캔들 데이터 수집
        candles = _candle_collector.get_candles(symbol.upper(), timeframe, 100)
        
        if not candles:
            return jsonify({"error": "캔들 데이터를 가져올 수 없습니다"}), 404
        
        # 기술적 분석 수행
        analysis = _technical_analyzer.analyze(candles, symbol.upper())
        analysis['timeframe'] = timeframe
        
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/chart-data/<symbol>')
def get_chart_data(symbol: str):
    """
    차트에 필요한 모든 데이터 한 번에 조회
    캔들 + 기술분석 + 현재 시세
    """
    if not CANDLE_AVAILABLE:
        return jsonify({"error": "Chart data not available"}), 503
    
    timeframe = request.args.get('tf', '1h')
    
    try:
        start = time.time()
        
        # 캔들 데이터
        candles = _candle_collector.get_candles(symbol.upper(), timeframe, 100)
        
        # 기술 분석
        technical = _technical_analyzer.analyze(candles, symbol.upper()) if candles else {}
        
        # 현재 시세 (Agent API 활용)
        current_data = {}
        if PALANTIR_AVAILABLE:
            collector = get_collector()
            if collector:
                current_data = collector.collect_with_fallback(symbol.upper())
        
        duration_ms = (time.time() - start) * 1000
        
        return jsonify({
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "candles": candles,
            "technical": technical,
            "current": {
                "price": current_data.get('price', candles[-1]['close'] if candles else 0),
                "change_rate": current_data.get('change_rate', 0),
                "volume_24h": current_data.get('volume_24h', 0)
            },
            "latency_ms": round(duration_ms, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== 추천 시스템 엔드포인트 ====================

# 추천 시스템 모듈 임포트
try:
    from engine.recommendation.screener import CoinScreener
    _screener = CoinScreener()
    SCREENER_AVAILABLE = True
except ImportError as e:
    SCREENER_AVAILABLE = False
    logging.warning(f"Screener module not available: {e}")


@app.route('/api/recommend/major')
def get_major_recommendations():
    """
    메이저 코인 5종 추천
    BTC, ETH, XRP, SOL, ADA
    """
    if not SCREENER_AVAILABLE:
        return jsonify({"error": "Screener not available"}), 503
    
    try:
        recommendations = _screener.get_major_recommendations()
        return jsonify({
            "type": "메이저",
            "count": len(recommendations),
            "recommendations": recommendations,
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recommend/scalp')
def get_scalp_recommendations():
    """
    단타/스캘핑 추천
    시간대별 유동성 기반
    
    Query params:
        time: 시간대 (09:00, 16:00, 19:00, 21:30) - 기본값: 현재 시간
    """
    if not SCREENER_AVAILABLE:
        return jsonify({"error": "Screener not available"}), 503
    
    time_slot = request.args.get('time')
    
    try:
        recommendations = _screener.get_scalp_recommendations(time_slot=time_slot)
        return jsonify({
            "type": "단타",
            "time_slot": time_slot or "현재",
            "count": len(recommendations),
            "recommendations": recommendations,
            "description": "상승률+거래량 상위 10개 중 매집 흔적 5개 필터링",
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recommend/swing')
def get_swing_recommendations():
    """
    스윙 트레이딩 추천
    
    Query params:
        period: 투자 기간 (short/medium/long) - 기본값: short
            - short: 단기 (1-3일)
            - medium: 중기 (1주-1개월)
            - long: 장기 (1개월+)
    """
    if not SCREENER_AVAILABLE:
        return jsonify({"error": "Screener not available"}), 503
    
    period = request.args.get('period', 'short')
    
    period_labels = {
        'short': '단기 (1-3일)',
        'medium': '중기 (1주-1개월)',
        'long': '장기 (1개월+)'
    }
    
    try:
        recommendations = _screener.get_swing_recommendations(period=period)
        return jsonify({
            "type": f"스윙-{period}",
            "period": period,
            "period_label": period_labels.get(period, period),
            "count": len(recommendations),
            "recommendations": recommendations,
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recommend/all')
def get_all_recommendations():
    """
    모든 추천 한 번에 조회
    """
    if not SCREENER_AVAILABLE:
        return jsonify({"error": "Screener not available"}), 503
    
    try:
        start = time.time()
        
        major = _screener.get_major_recommendations()
        scalp = _screener.get_scalp_recommendations()
        swing_short = _screener.get_swing_recommendations('short')
        
        duration_ms = (time.time() - start) * 1000
        
        return jsonify({
            "major": {"type": "메이저", "recommendations": major},
            "scalp": {"type": "단타", "recommendations": scalp},
            "swing_short": {"type": "단기 스윙", "recommendations": swing_short},
            "latency_ms": round(duration_ms, 2),
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== Kelly Criterion & Guard Chain ====================

# Kelly/Guard Chain 모듈 임포트
try:
    from engine.risk.position_sizer import PositionSizer
    from engine.risk.guard_chain import GuardChain
    import asyncio
    _position_sizer = PositionSizer(account_size=10_000_000)  # 1천만원 기본
    _guard_chain = GuardChain()
    RISK_AVAILABLE = True
except ImportError as e:
    RISK_AVAILABLE = False
    logging.warning(f"Risk modules not available: {e}")


@app.route('/api/kelly/<symbol>')
def get_kelly_position(symbol: str):
    """
    Kelly Criterion 포지션 사이징
    - 신호 타입에 따른 최적 포지션 크기 계산
    """
    if not RISK_AVAILABLE:
        return jsonify({"error": "Risk modules not available"}), 503
    
    symbol = symbol.upper()
    signal_type = request.args.get('signal_type', 'B')
    entry_price = float(request.args.get('entry_price', 0))
    account_size = float(request.args.get('account_size', 10_000_000))
    
    if entry_price <= 0:
        return jsonify({"error": "entry_price required"}), 400
    
    try:
        result = _position_sizer.calculate_position_size(
            signal_type=signal_type.upper(),
            entry_price=entry_price,
            account_size=account_size
        )
        
        return jsonify({
            "symbol": symbol,
            **result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/guard/<symbol>')
def run_guard_chain(symbol: str):
    """
    Guard Chain 7단계 검증
    - 거래 실행 전 안전성 검증
    """
    if not RISK_AVAILABLE:
        return jsonify({"error": "Risk modules not available"}), 503
    
    symbol = symbol.upper()
    price = float(request.args.get('price', 1))
    quantity = float(request.args.get('quantity', 0.001))
    side = request.args.get('side', 'BUY').upper()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            _guard_chain.execute_all(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price
            )
        )
        loop.close()
        
        return jsonify({
            "symbol": symbol,
            **result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v4/signal/<symbol>')
def get_v4_signal(symbol: str):
    """
    Phoenix V4 통합 신호
    - 5 Agent + Type A/B/C + Kelly + Guard Chain
    """
    if not PALANTIR_AVAILABLE:
        return jsonify({"error": "Palantir modules not available"}), 503
    
    symbol = symbol.upper()
    account_size = float(request.args.get('account_size', 10_000_000))
    
    start = time.time()
    
    try:
        # 1. 데이터 수집
        collector = get_collector()
        market_data = collector.collect_with_fallback(symbol)
        entry_price = market_data.get('price', 0)
        
        # 2. 5 Agent 분석
        aggregator = get_aggregator()
        signal_result = aggregator.get_all_signals(market_data=market_data)
        
        # 3. Kelly 포지션 사이징 (RISK_AVAILABLE 확인)
        kelly_result = {}
        if RISK_AVAILABLE and entry_price > 0:
            kelly_result = _position_sizer.calculate_position_size(
                signal_type=signal_result.get('signal_type', {}).get('type', 'C'),
                entry_price=entry_price,
                account_size=account_size
            )
        
        # 4. Guard Chain (비동기)
        guard_result = {}
        if RISK_AVAILABLE:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            guard_result = loop.run_until_complete(
                _guard_chain.execute_all(
                    symbol=symbol,
                    side="BUY",
                    quantity=kelly_result.get('quantity', 0.001),
                    price=entry_price
                )
            )
            loop.close()
        
        duration_ms = (time.time() - start) * 1000
        
        return jsonify({
            "symbol": symbol,
            "price": entry_price,
            "change_rate": market_data.get('change_rate', 0),
            "source": market_data.get('source', 'unknown'),
            
            # 5 Agent 분석
            "agent_scores": signal_result.get('agent_scores', {}),
            "weighted_score": signal_result.get('weighted_score', 50),
            "signal_type": signal_result.get('signal_type', {}),
            
            # Kelly 포지션
            "kelly": kelly_result,
            
            # Guard Chain
            "guard_chain": guard_result,
            
            # 최종 판정
            "action": "TRADE" if guard_result.get('passed', False) else "NO_TRADE",
            "latency_ms": round(duration_ms, 2),
            "timestamp": time.time()
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "symbol": symbol}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True, threaded=True)




