# -*- coding: utf-8 -*-
# author: chb
import html
import logging
from odoo import http, tools
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController as BaseThreadController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context

_logger = logging.getLogger(__name__)


class DiscussThreadController(BaseThreadController):
    @http.route("/mail/message/post", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        res = super().mail_message_post(thread_model, thread_id, post_data, context=context, **kwargs)

        try:
            if thread_model not in ["mail.channel", "discuss.channel"]:
                return res

            channel = request.env[thread_model].sudo().browse(int(thread_id))
            if not channel.exists():
                return res

            if request.env.context.get("mcp_bot_post"):
                return res

            odoobot_partner = request.env.ref("base.partner_root")
            if odoobot_partner not in channel.channel_member_ids.partner_id:
                return res

            user_text = tools.html2plaintext((post_data or {}).get("body") or "").strip()
            if not user_text:
                return res

        except Exception as e:
            _logger.exception(str(e))
            try:
                odoobot_partner = request.env.ref("base.partner_root")
                channel = request.env["mail.channel"].sudo().browse(int(thread_id))
                channel.with_context(mcp_bot_post=True).message_post(
                    body=f"<p><i>AI出错：</i>{html.escape(str(e))}</p>",
                    author_id=odoobot_partner.id,
                    email_add_signature=False,
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )
            except Exception:
                pass

        return res
