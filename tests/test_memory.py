"""memory trim_messages 测试。"""
from memory import trim_messages, _is_tool_chain_start


def test_preserves_tool_chain():
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "function": {"name": "x"}}]},
        {"role": "tool", "tool_call_id": "1", "content": "{}"},
        {"role": "assistant", "content": "answer"},
        {"role": "user", "content": "new"},
    ]
    trim_messages(messages, max_messages=4)
    assert messages[0]["role"] == "system"
    assert any(m.get("role") == "tool" for m in messages)
    assert messages[-1]["content"] == "new"


def test_trim_by_user_turns():
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "u3"},
    ]
    trim_messages(messages, max_messages=100, max_user_turns=2)
    user_msgs = [m for m in messages if m.get("role") == "user"]
    assert len(user_msgs) == 2
    assert user_msgs[-1]["content"] == "u3"


def test_is_tool_chain_start():
    assert _is_tool_chain_start({"role": "assistant", "tool_calls": [{"id": "1"}]})
    assert not _is_tool_chain_start({"role": "assistant", "content": "hi"})
