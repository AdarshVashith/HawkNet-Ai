"""Fraud graph ML / graph-intelligence wrappers."""

from app.models.fraud_graph.predictor import FraudGraphModel
from app.models.fraud_graph.graph_intel import FraudGraphIntelligence, get_intelligence

__all__ = ["FraudGraphModel", "FraudGraphIntelligence", "get_intelligence"]
