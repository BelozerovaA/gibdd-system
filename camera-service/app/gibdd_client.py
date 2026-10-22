"""Устаревший HTTP-клиент. События идут только по WebSocket (ws_client.py)."""
from .ws_client import DeliveryError, DeliveryRejected

__all__ = ["DeliveryError", "DeliveryRejected"]
