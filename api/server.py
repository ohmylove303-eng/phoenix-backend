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
            "llm_orchestrator": PALANTIR_AVAILABLE
        },
        "version": "1.0.0-phoenix",
        "timestamp": time.time()
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True, threaded=True)

