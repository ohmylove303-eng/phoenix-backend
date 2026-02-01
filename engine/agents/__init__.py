# engine/agents/__init__.py
from .signal_agents import (
    TechnicalAgent,
    OnChainAgent,
    SentimentAgent,
    MacroAgent,
    InstitutionalAgent,
    SignalAggregator
)

__all__ = [
    'TechnicalAgent',
    'OnChainAgent', 
    'SentimentAgent',
    'MacroAgent',
    'InstitutionalAgent',
    'SignalAggregator'
]
