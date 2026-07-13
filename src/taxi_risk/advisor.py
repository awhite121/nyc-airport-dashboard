def recommend_buffer_minutes(late_probability: float) -> int:
    """Simple demo policy for turning late-risk probability into a traveler buffer."""
    if late_probability >= 0.55:
        return 25
    if late_probability >= 0.40:
        return 20
    if late_probability >= 0.25:
        return 15
    if late_probability >= 0.15:
        return 10
    return 5

def leave_by_minutes_before_arrival(predicted_duration_min: float, late_probability: float) -> float:
    """ETA + risk buffer = recommended minutes before desired arrival to leave."""
    return predicted_duration_min + recommend_buffer_minutes(late_probability)
