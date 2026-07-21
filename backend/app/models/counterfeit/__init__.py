"""Counterfeit detection ML model wrappers."""

from app.models.counterfeit.predictor import CounterfeitModel, CurrencyCounterfeitModel

__all__ = ["CounterfeitModel", "CurrencyCounterfeitModel"]
