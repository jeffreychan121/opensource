# -*- coding: utf-8 -*-
# author: chb

import re
import html
import markdown
from odoo import models
from odoo import tools
from odoo.tools import html_escape
from ..utils.minimax_client import LLMChatClient, LLMProvider


def _render_llm_html(text: str) -> str:
    """LLM Markdown to HTML"""
    if not text:
        return "<p></p>"
    try:
        html = markdown.markdown(
            text,
            extensions=["sane_lists", "nl2br"],
            output_format="xhtml1",
        )
    except Exception:
        t = html.escape(text)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        lines = t.splitlines()
        out, in_ol = [], False
        for line in lines:
            m = re.match(r"^\s*\d+\.\s+(.*)", line)
            if m:
                if not in_ol:
                    out.append("<ol>")
                    in_ol = True
                out.append(f"<li>{m.group(1)}</li>")
            else:
                if in_ol:
                    out.append("</ol>")
                    in_ol = False
                if line.strip():
                    out.append(f"<p>{line}</p>")
        if in_ol:
            out.append("</ol>")
        html = "".join(out) or "<p></p>"
    return tools.html_sanitize(html, silent=True)


class MailBot(models.AbstractModel):
    _inherit = "mail.bot"

    def _get_answer(self, record, body, values, command=False):
        odoo_bot = self.env.ref("base.partner_root")
        try:
            if (
                    record.channel_type in ("chat", "channel")
                    and odoo_bot in record.channel_member_ids.partner_id
                    and body
            ):
                reply = self._mcp_answer_via_http(body)
                if reply:
                    return html_escape(reply)
        except Exception as e:
            record.with_context(mcp_bot_post=True).message_post(
                body=_render_llm_html(f"<p><i>AI ERROR：</i> {html.escape(str(e))}</p>"),
                author_id=odoo_bot.id,
                email_add_signature=False,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            return True
        return super()._get_answer(record, body, values, command=command)

    def _mcp_answer_via_http(self, body: str) -> str:
        user_text = body.strip()
        try:
            client = LLMChatClient()
            reply_text = client.chat(user_text)
        except Exception as e:
            reply_text = f"(AI出错：{html.escape(str(e))})"

        if not reply_text:
            return ""

        reply_text = _render_llm_html(reply_text)
        return reply_text

    def _collect_history_plain(self, record, limit=10):
        msgs = record.sudo().message_ids.sorted(key=lambda m: m.date)[-limit:]
        out = []
        odoo_bot = self.env.ref("base.partner_root")
        for m in msgs:
            role = "assistant" if m.author_id == odoo_bot else "user"
            text = tools.html2plaintext(m.body or "").strip()
            if text:
                out.append({"role": role, "content": text})
        return out
