"""Explicit adapters for text conversations and already-cleaned trace trees."""
from copy import deepcopy
from .engine.core.cleaner import run_pipeline
from .engine.core.features import get_messages

_ROLES = {"user": "human", "assistant": "ai", "system": "system", "tool": "tool"}


def normalize_traces(data):
    if not isinstance(data, list) or not data:
        raise ValueError("Input must be a non-empty JSON list of traces.")
    seen, result = set(), []
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
            raise ValueError("Each trace needs a non-empty string id.")
        if item["id"] in seen:
            raise ValueError("Trace IDs must be unique; full IDs are preserved.")
        seen.add(item["id"])
        trace = deepcopy(item)
        if "root" in trace and "messages" in trace:
            raise ValueError("Choose messages or root, not both.")
        if "messages" in trace:
            messages = trace.pop("messages")
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages must be a non-empty list.")
            normalized = []
            for m in messages:
                if not isinstance(m, dict) or m.get("role") not in _ROLES or not isinstance(m.get("content"), str):
                    raise ValueError("Messages require a supported role and text content.")
                msg = {k: deepcopy(v) for k, v in m.items() if k != "role"}
                msg["type"] = _ROLES[m["role"]]
                normalized.append(msg)
            trace["observations"] = [{"id": "conversation", "parentObservationId": None,
                "name": "LangGraph", "type": "CHAIN", "input": {"messages": []},
                "output": {"messages": normalized}}]
            trace = run_pipeline([trace])[0]
            if "metadata" in item:
                trace["metadata"] = deepcopy(item["metadata"])
        else:
            root = trace.get("root")
            if not isinstance(root, dict) or not isinstance(root.get("input", {}), dict) or not isinstance(root.get("output", {}), dict):
                raise ValueError("A cleaned trace needs root.input and root.output objects.")
        messages = get_messages(trace)
        if not messages or any(not isinstance(m, dict) or m.get("type") not in set(_ROLES.values()) or not isinstance(m.get("content"), str) for m in messages):
            raise ValueError("Cleaned traces need non-empty text messages with type human/ai/system/tool.")
        result.append(trace)
    return result
