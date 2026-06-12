"""Gradio Web 界面：金融 Agent 对话 + 工具调用面板（兼容 Gradio 6）。"""
from __future__ import annotations

import json
from typing import Any

import gradio as gr

from agent_core import chat, create_session
from config import AppConfig
from env_loader import load_env_file

load_env_file()

CUSTOM_CSS = """
/* 全局：金融终端风深色底 */
.gradio-container {
    background: radial-gradient(1200px 600px at 10% -10%, #1a2a44 0%, transparent 55%),
                radial-gradient(900px 500px at 100% 0%, #1f2937 0%, transparent 50%),
                linear-gradient(180deg, #0b1120 0%, #0f172a 55%, #0b1120 100%) !important;
    max-width: 1280px !important;
    margin: 0 auto !important;
    padding: 1.25rem 1rem 2rem !important;
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif !important;
}

footer { display: none !important; }

/* 顶栏品牌区 */
#hero-card {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.92), rgba(15, 23, 42, 0.95));
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 16px;
    padding: 1.1rem 1.25rem 0.9rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
}
#hero-card h1 {
    margin: 0 0 0.35rem 0 !important;
    font-size: 1.55rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em;
    color: #f8fafc !important;
}
#hero-card p {
    margin: 0 !important;
    color: #94a3b8 !important;
    font-size: 0.92rem !important;
    line-height: 1.55 !important;
}
#hero-badges {
    margin-top: 0.65rem !important;
}
#hero-badges p {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
}
.badge {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1px solid transparent;
}
.badge-gold { background: rgba(217, 169, 56, 0.16); color: #f5d98b; border-color: rgba(217, 169, 56, 0.35); }
.badge-teal { background: rgba(45, 212, 191, 0.12); color: #99f6e4; border-color: rgba(45, 212, 191, 0.28); }
.badge-slate { background: rgba(148, 163, 184, 0.12); color: #cbd5e1; border-color: rgba(148, 163, 184, 0.25); }

/* 面板卡片 */
.panel-card {
    background: rgba(17, 24, 39, 0.82) !important;
    border: 1px solid rgba(100, 116, 139, 0.28) !important;
    border-radius: 14px !important;
    padding: 0.65rem 0.75rem 0.75rem !important;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.22);
}
.panel-card > .label-wrap span {
    color: #e2e8f0 !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
}

/* 对话区 */
#main-chat {
    border-radius: 12px !important;
    border: 1px solid rgba(71, 85, 105, 0.45) !important;
    background: rgba(2, 6, 23, 0.55) !important;
}
#main-chat .message.user {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    color: #eff6ff !important;
    border: none !important;
}
#main-chat .message.bot {
    background: rgba(30, 41, 59, 0.95) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(71, 85, 105, 0.5) !important;
}

/* 输入区 */
#input-row input, #input-row textarea {
    background: rgba(15, 23, 42, 0.9) !important;
    color: #f1f5f9 !important;
    border-color: rgba(100, 116, 139, 0.45) !important;
    border-radius: 10px !important;
}
#send-btn {
    min-height: 42px;
    border-radius: 10px !important;
    font-weight: 600 !important;
}
#clear-btn {
    border-radius: 10px !important;
    margin-top: 0.35rem;
}

/* 工具日志：等宽终端感 */
#tools-panel textarea {
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace !important;
    font-size: 12px !important;
    line-height: 1.45 !important;
    background: rgba(2, 6, 23, 0.75) !important;
    color: #a7f3d0 !important;
    border-radius: 10px !important;
}
#meta-panel textarea {
    font-family: "Cascadia Code", "Consolas", monospace !important;
    font-size: 12px !important;
    background: rgba(2, 6, 23, 0.6) !important;
    color: #cbd5e1 !important;
    border-radius: 10px !important;
}

/* 示例问题按钮 */
#examples-row button {
    border-radius: 999px !important;
    font-size: 0.82rem !important;
    border: 1px solid rgba(148, 163, 184, 0.35) !important;
    background: rgba(30, 41, 59, 0.75) !important;
    color: #e2e8f0 !important;
}
#examples-row button:hover {
    border-color: rgba(217, 169, 56, 0.55) !important;
    color: #fde68a !important;
}

/* 免责声明 */
#disclaimer p {
    margin: 0.85rem 0 0 !important;
    text-align: center;
    color: #64748b !important;
    font-size: 0.78rem !important;
}
"""

EXAMPLES: list[list[str]] = [
    ["600519 最近收盘价多少？"],
    ["AAPL 最近股价多少？"],
    ["美元兑人民币汇率多少？"],
    ["1 万本金年化 3% 按月复利存 5 年多少钱？"],
    ["帮我看看示例组合的盈亏情况"],
]


def _build_theme() -> gr.Theme:
    return (
        gr.themes.Base(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.amber,
            neutral_hue=gr.themes.colors.slate,
            font=gr.themes.GoogleFont("Inter"),
        )
        .set(
            body_background_fill="*neutral_950",
            body_background_fill_dark="*neutral_950",
            block_background_fill="*neutral_900",
            block_background_fill_dark="*neutral_900",
            block_border_width="1px",
            block_border_color="*neutral_700",
            block_label_text_color="*neutral_200",
            block_title_text_color="*neutral_50",
            body_text_color="*neutral_100",
            button_primary_background_fill="linear-gradient(135deg, *primary_600, *primary_500)",
            button_primary_background_fill_hover="linear-gradient(135deg, *primary_500, *primary_400)",
            button_primary_text_color="white",
            input_background_fill="*neutral_950",
            input_background_fill_dark="*neutral_950",
        )
    )


def _format_tool_log(name: str, args: str, result: str) -> str:
    preview = result if len(result) <= 600 else result[:600] + "..."
    return f"[tool] {name}\n  args: {args}\n  result: {preview}\n"


def _append_turn(history: list[dict[str, Any]], user_message: str, answer: str) -> list[dict[str, Any]]:
    return history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": answer},
    ]


def build_app() -> gr.Blocks:
    config = AppConfig.from_env()
    session = create_session(config)
    trace = session["trace"]
    tool_logs: list[str] = []
    scene_mode = session.get("scene_mode", config.scene_mode)

    def respond(user_message: str, history: list[dict[str, Any]], mode: str):
        history = history or []
        if not user_message.strip():
            return history, "\n".join(tool_logs), ""

        def on_tool(name: str, args: str, payload: str) -> None:
            tool_logs.append(_format_tool_log(name, args, payload))

        if mode and mode != session.get("scene_mode"):
            new_sess = create_session(config, scene_mode=mode)
            session.clear()
            session.update(new_sess)
            nonlocal trace
            trace = new_sess["trace"]
            session["scene_mode"] = mode

        try:
            answer = chat(session, user_message.strip(), on_tool_event=on_tool)
        except Exception as e:
            answer = f"请求失败: {e}"

        meta = {
            "trace_id": trace.trace_id,
            "scene_mode": session.get("scene_mode", mode),
            "tools": trace.stats["tool_calls"],
            "tool_ms": trace.stats["tool_ms_total"],
        }
        return (
            _append_turn(history, user_message, answer),
            "\n".join(tool_logs),
            json.dumps(meta, ensure_ascii=False, indent=2),
        )

    def clear_session(mode: str):
        tool_logs.clear()
        new_session = create_session(config, scene_mode=mode or config.scene_mode)
        session.clear()
        session.update(new_session)
        nonlocal trace
        trace = new_session["trace"]
        return [], "", f"会话已重置，新 trace: {trace.trace_id}"

    with gr.Blocks() as demo:
        with gr.Column(elem_id="hero-card"):
            gr.Markdown(
                "# FinAgent 金融学习助手\n"
                "基于智谱 GLM 的工具增强对话：联网行情、金融计算、本地知识库检索。"
            )
            gr.Markdown(
                f'<div id="hero-badges">'
                f'<p>'
                f'<span class="badge badge-gold">模型 {config.glm_model}</span>'
                f'<span class="badge badge-teal">Tool Use</span>'
                f'<span class="badge badge-teal">Live Market</span>'
                f'<span class="badge badge-slate">trace {trace.trace_id[:8]}…</span>'
                f"</p></div>",
            )

        mode_dropdown = gr.Dropdown(
            choices=["educational", "quick", "portfolio"],
            value=scene_mode,
            label="场景模式",
            info="educational=教学讲解 | quick=快答 | portfolio=组合分析",
        )

        with gr.Row():
            with gr.Column(scale=3, elem_classes=["panel-card"]):
                chatbot = gr.Chatbot(
                    label="对话",
                    height=500,
                    elem_id="main-chat",
                    show_label=True,
                )
                with gr.Row(elem_id="input-row"):
                    msg = gr.Textbox(
                        label="输入问题",
                        placeholder="例如：600519 最近收盘价？贷款 80 万 30 年月供？",
                        scale=5,
                        show_label=False,
                        container=False,
                    )
                    send = gr.Button("发送", variant="primary", scale=1, elem_id="send-btn")
                with gr.Column(elem_id="examples-row"):
                    gr.Examples(examples=EXAMPLES, inputs=msg, label="快捷提问")
                clear = gr.Button("清空会话", variant="secondary", elem_id="clear-btn")

            with gr.Column(scale=2):
                with gr.Column(elem_classes=["panel-card"]):
                    tools_box = gr.Textbox(
                        label="工具调用链路",
                        lines=20,
                        max_lines=28,
                        interactive=False,
                        elem_id="tools-panel",
                        value="等待提问…\n发送金融/行情类问题后，将在此展示工具名、参数与返回摘要。",
                    )
                with gr.Column(elem_classes=["panel-card"]):
                    meta_box = gr.Textbox(
                        label="会话观测",
                        lines=5,
                        interactive=False,
                        elem_id="meta-panel",
                        value=f"trace_id: {trace.trace_id}",
                    )

        gr.Markdown(
            "免责声明：行情与计算结果仅供学习演示，不构成任何投资建议。",
            elem_id="disclaimer",
        )

        send.click(respond, [msg, chatbot, mode_dropdown], [chatbot, tools_box, meta_box]).then(
            lambda: "", outputs=msg
        )
        msg.submit(respond, [msg, chatbot, mode_dropdown], [chatbot, tools_box, meta_box]).then(
            lambda: "", outputs=msg
        )
        clear.click(clear_session, [mode_dropdown], outputs=[chatbot, tools_box, meta_box])

    return demo


if __name__ == "__main__":
    app = build_app()
    config = AppConfig.from_env()
    app.launch(
        server_name=config.web_host,
        server_port=config.web_port,
        theme=_build_theme(),
        css=CUSTOM_CSS,
        inbrowser=True,
    )
