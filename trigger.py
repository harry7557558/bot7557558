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
    content = re.sub(r"[^A-Za-z0-9\u0080-\uffff]", ' ', content)
    content = re.sub(r"\s+", ' ', content)
    words = content.split()

    # detect triggers
    triggers_o = b'>9\\!+H6OmaDgETY,\'.mJ+tOpSD..?,/0\\nIAmoU%/0\\\\K@r!8>,\'S-@+tOpZBPDQ4/0\\PGCi"0+BlkOM,%P,!DB^VUA79=mBlkOM,&_=2+tOpZF^o22/0\\M>DeF36+tOpWASu4\'+tOpJF`):F>l'
    triggers = {}
    for trigger in json.loads(base64.a85decode(triggers_o).decode('utf-8')):
        triggers[dedup(trigger)] = trigger
    keywords = {}
    for word in words:
        word = dedup(word)
        if word in triggers:
            keyword = triggers[word]
            if keyword not in keywords:
                keywords[keyword] = 0
            keywords[keyword] += 1
    if len(keywords) == 0:
        return None
    for (keyword, count) in keywords.items():
        if count == 1:
            keywords[keyword] = keyword
        else:
            keywords[keyword] = keyword + f"(×{count})"

    # apply trigger
    embed = discord.Embed(title="Trigger Detected!", color=0xff0000)
    embed.add_field(name="User",
                    value=message.author.mention,
                    inline=True)
    embed.add_field(name="Message",
                    value=message.content[:600],
                    inline=True)
    embed.add_field(name="Trigger"+'s'*(len(keywords) > 1),
                    value=', '.join(list(keywords.values())),
                    inline=True)
    embed.timestamp = datetime.datetime.utcnow()
    return embed
