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
        res = super()._get_answer(record, body, values, command=command)
        # 避免递归：如果上下文已有 mcp_bot_post，跳过处理
        if self.env.context.get("mcp_bot_post"):
            return False

        odoo_bot = self.env.ref("base.partner_root1")
        odoo_partner = odoo_bot.partner_id  # 获取对应的 partner
        try:
            if (
                    record.channel_type in ("chat", "channel")
                    and odoo_partner in record.channel_member_ids.partner_id
                    and body
            ):
                # 直接同步执行
                import logging
                _logger = logging.getLogger(__name__)
                _logger.info(f"MCP Bot triggered for channel {record.id}")

                # 获取 AI 回复
                reply = self._mcp_answer_via_http(body)

                # 过滤多余的 True 后有有效内容
                if reply and len(reply) > 10:  # 确保不是空消息或只有 True
                    # 不再调用 super()，避免重复返回
                    # 直接发送 AI 回复
                    record.with_context(mcp_bot_post=True).message_post(
                        body=reply,
                        author_id=odoo_partner.id,
                        email_add_signature=False,
                        message_type="comment",
                        subtype_xmlid="mail.mt_comment",
                    )
                    return False  # 已处理，不显示默认回复

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"MCP Bot error: {e}")
            # 发送错误消息
            try:
                error_html = _render_llm_html(f"<p><i>AI Error: {html.escape(str(e))}</i></p>")
                record.with_context(mcp_bot_post=True).message_post(
                    body=error_html,
                    author_id=odoo_partner.id,
                    email_add_signature=False,
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )
            except:
                pass
            return False

        return res

    def _mcp_answer_via_http(self, body: str) -> str:
        user_text = body.strip()
        try:
            client = LLMChatClient()
            reply_text = client.chat(user_text)
        except Exception as e:
            reply_text = f"(AI出错：{html.escape(str(e))})"

        if not reply_text:
            return ""

        # 彻底清除 True/true/FALSE/false
        reply_text = reply_text.strip()
        import re
        # 移除任何位置的单独 True/true/FALSE/false 行
        lines = [line.strip() for line in reply_text.split('\n') if line.strip()]
        lines = [line for line in lines if line.lower() not in ['true', 'false']]
        reply_text = '\n'.join(lines)

        # 再移除末尾的
        reply_text = re.sub(r'\s+(True|true|FALSE|false)\s*$', '', reply_text)
        reply_text = reply_text.strip()

        if not reply_text:
            return ""

        reply_text = _render_llm_html(reply_text)
        return reply_text

    def _collect_history_plain(self, record, limit=10):
        msgs = record.sudo().message_ids.sorted(key=lambda m: m.date)[-limit:]
        out = []
        odoo_bot = self.env.ref("base.partner_root1")
        odoo_partner = odoo_bot.partner_id  # 使用 partner 进行比较
        for m in msgs:
            role = "assistant" if m.author_id == odoo_partner else "user"
            text = tools.html2plaintext(m.body or "").strip()
            if text:
                out.append({"role": role, "content": text})
        return out
