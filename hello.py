# type `$hello` to see what happens

import discord
import requests
import json
import html
import random


def get_site_objects(url: str) -> dict:
    """Get quote or link list from https://harry7557558.github.io/"""
    assert url in ["https://harry7557558.github.io/src/quotes.json",
                   "https://harry7557558.github.io/src/links.json"]

    # fetch data
    req = requests.get(url)
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
                'weight': item['weight'],
                'alt': item['alt'] if 'alt' in item else None
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
                'alt': item['alt'],
                'psa': -1.0
            })
    assert abs(sum([item['probability'] for item in items])-1.0) < 1e-8
    return items


def stat_site_objects(objects) -> str:
    """Generate statistics text for site quote/link"""
    # objects
    lines = []
    for obj in sorted(objects, key=lambda obj: -obj['probability']):
        line = []
        line.append("{:.2f}%".format(100.*obj['probability']))
        line.append(obj['text'])
        if obj['alt'] != None:
            line.append('('+obj['alt']+')')
        lines.append(' '.join(line))
    # probability of two consecutive
    lines.append('')
    prob = 0.0
    for obj in objects:
        prob += obj['probability']**2
    lines.append(
        "The probability of generating two consecutive same objects is {:.2f}%.".format(100.*prob))
    # return
    return '\n'.join(lines)


async def send_hello_message(message):
    """Send a random quote from the website homepage"""

    filename = "links.json" if "link" in message.content else "quotes.json"
    objects = get_site_objects("https://harry7557558.github.io/src/"+filename)

    # statistics
    if "stat" in message.content:
        stats = stat_site_objects(objects)
        with open('.hello.temp', 'wb') as fp:
            fp.write(bytearray(stats, 'utf-8'))
        with open(".hello.temp", "rb") as fp:
            await message.channel.send(file=discord.File(fp, "stat.txt"))
        return

    # random quote/link
    rnd = random.random()
    s = 0.0
    object = objects[-1]
    for item in objects:
        s += item['probability']
        if s > rnd:
            object = item
            break
    if object['alt'] == None:  # quote
        text = html.unescape(object['text'])
        text = text.replace('<i>', '*').replace('</i>', '*')
        text = text.replace('<del>', '~~').replace('</del>', '~~')
    else:  # link
        text = object['alt'] + '\n' + object['text']

    # send object
    embed = discord.Embed(title="harry7557558 - Home Page", color=0x2020a0)
    embed.url = "https://harry7557558.github.io/"
    embed.description = text
    embed.set_thumbnail(
        url=" https://harry7557558.github.io/src/snowflake.jpg")
    await message.channel.send(embed=embed)
