import json
import math
from datetime import datetime
from typing import Any

def make_json_serializable(obj: Any) -> Any:
    """
    Recursively converts non-serializable objects into JSON-friendly formats.
    Handles Datetime, Sets, and complex nesting.
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(i) for i in obj]
    elif isinstance(obj, set):
        return [make_json_serializable(i) for i in list(obj)]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif hasattr(obj, "to_dict"): # Handle LlamaIndex or other objects with to_dict
        return make_json_serializable(obj.to_dict())
    elif hasattr(obj, "__dict__"):
        return make_json_serializable(obj.__dict__)
    else:
        try:
            # Test if it's already serializable
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            return str(obj)
