# magical

from chardet import detect
import discord
import requests
import json
import html
import random
import re
import datetime


def get_random_quote():
    """Get random quote from the quote list on https://harry7557558.github.io/"""

    # fetch data
    req = requests.get("https://harry7557558.github.io/src/quotes.json")
    if req.status_code != 200:
        return f"Status code {req.status_code}"
    content = json.loads(req.content)

    # get a list of probabilities
    items = []
    for group_key in content:
        group = content[group_key]['objects']
        sub_items = []
        for item in group:
            sub_items.append({
                'text': item['text'],
                'weight': item['weight']
            })
        s = 0.0
        for item in sub_items:
            s += item['weight']
        for item in sub_items:
            item['weight'] /= s
        for item in sub_items:
            items.append({
                'text': item['text'],
                'probability': item['weight'] * content[group_key]['probability'],
                'psa': -1.0
            })
    assert abs(sum([item['probability'] for item in items])-1.0) < 1e-8

    # get quote
    rnd = random.random()
    s = 0.0
    quote = items[-1]['text']
    for item in items:
        s += item['probability']
        if s > rnd:
            quote = item['text']
            break
    quote = html.unescape(quote)
    quote = quote.replace('<i>', '*').replace('</i>', '*')
    quote = quote.replace('<del>', '~~').replace('</del>', '~~')
    return quote


async def send_hello_message(message):
    """Send a random quote from the website homepage"""
    embed = discord.Embed(title="harry7557558 - Home Page", color=0x2020a0)
    embed.url = "https://harry7557558.github.io/"
    embed.description = get_random_quote()
    embed.set_thumbnail(
        url=" https://harry7557558.github.io/src/snowflake.jpg")
    await message.channel.send(embed=embed)


def detect_trigger(message):
    """Detect trigger in the message, returns embed if triggered"""
    def dedup(s: str):
        t = ""
        for c in s.lower():
            if len(t) != 0 and c == t[-1]:
                continue
            t += c
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
    triggers = {'orz', 'sus', 'susy', 'lmao', 'lfmao',
                'fuck', 'wtf', 'shit', 'bulshit',
                'damn', 'omg'}
    triggered = []
    for word in words:
        if dedup(word) in triggers:
            triggered.append(dedup(word))
    if len(triggered) == 0:
        return None

    # apply trigger
    embed = discord.Embed(title="Trigger Found!", color=0xff0000)
    embed.add_field(name="User",
                    value=message.author.mention,
                    inline=True)
    embed.add_field(name="Message",
                    value=message.content[:600],
                    inline=True)
    embed.add_field(name="Trigger"+'s'*(len(triggered) > 1),
                    value=', '.join(triggered),
                    inline=True)
    embed.timestamp = datetime.datetime.utcnow()
    return embed
