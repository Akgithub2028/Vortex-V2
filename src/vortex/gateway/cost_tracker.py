"""
Model Gateway Cost Tracker.
"""

from __future__ import annotations

# Price table in USD per 1K tokens
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "openai/gpt-4o": (0.0025, 0.01),
    "openai/gpt-4o-mini": (0.00015, 0.0006),
    "anthropic/claude-3-5-sonnet-latest": (0.003, 0.015),
    "anthropic/claude-3-haiku": (0.00025, 0.00125),
    "google/gemini-1.5-pro": (0.00125, 0.005),
    "google/gemini-1.5-flash": (0.000075, 0.0003),
}


def calculate_cost(model: str, tokens_input: int, tokens_output: int) -> float:
    """Compute USD cost based on token counts and model pricing table."""
    pricing = MODEL_PRICING.get(model.lower(), (0.001, 0.002))
    input_cost = (tokens_input / 1000.0) * pricing[0]
    output_cost = (tokens_output / 1000.0) * pricing[1]
    return input_cost + output_cost
