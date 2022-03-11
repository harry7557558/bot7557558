# magical

from email.mime import base
import discord
import re
import datetime
import base64
import json


def detect_trigger(message):
    """Detect trigger in the message, returns embed if triggered"""
    def dedup(s: str):
        t = ""
        for c in s.lower():
            if len(t) != 0 and c == t[-1]:
                continue
            t += c
        if len(t) > 3:
            if t.endswith('ing') or t.endswith('nes'):
                t = t[:len(t)-3]
            elif t.endswith('ed') or t.endswith('er') or t.endswith('es'):
                t = t[:len(t)-2]
            elif t.endswith('y') or t.endswith('s'):
                t = t[:len(t)-1]
        return t

    # get message content
    if type(message) == str:  # debug
        content = message
    else:
        content = message.content
    if '`' in content or '|' in content:
        return None  # hmmm
    content = re.sub(r"[^A-Za-z0-9_\w]", ' ', content)
    content = re.sub(r"\s+", ' ', content)
    words = content.split()

    # detect triggers
    triggers_o = b">9\\!+H6OmaF*2OJ/0\\nI@;d>@,&D+.@;d>@,%bt-CEb;RGB@F@/0].KBlkOM,%>\\2Cia9(F<W7[A79=m+tOpK@;TmrF<W7[Df',2/0].X@r!8o"
    triggers = {}
    for trigger in json.loads(base64.a85decode(triggers_o).decode('utf-8')):
        triggers[dedup(trigger)] = trigger
    keywords = []
    for word in words:
        word = dedup(word)
        if word in triggers:
            keywords.append(triggers[word])
    if len(keywords) == 0:
        return None

    # apply trigger
    embed = discord.Embed(title="Trigger Detected!", color=0xff0000)
    embed.add_field(name="User",
                    value=message.author.mention,
                    inline=True)
    embed.add_field(name="Message",
                    value=message.content[:600],
                    inline=True)
    embed.add_field(name="Trigger"+'s'*(len(keywords) > 1),
                    value=', '.join(keywords),
                    inline=True)
    embed.timestamp = datetime.datetime.utcnow()
    return embed
