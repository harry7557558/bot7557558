# custom preview for Shadertoy shaders

import discord
import requests
import json
import re
from datetime import datetime


def get_shader(shader_id: str) -> dict:
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'pragma': 'no-cache',
        'origin': 'https://www.shadertoy.com',
        'referer': f'https://www.shadertoy.com/view/{shader_id}'
    }
    data = {
        's': json.dumps({"shaders": [shader_id]}),
        'nt': '1',
        'nl': '1',
        'np': '1'
    }
    req = requests.post(
        "https://www.shadertoy.com/shadertoy",
        data=data,
        headers=headers
    )
    if req.status_code != 200:
        return None
    response = req.content.decode('utf-8')
    response = json.loads(response)
    if len(response) == 0:
        return None
    return response[0]


def generate_embed(url: str):

    # basic info
    shader_id = url[url.rfind('/')+1:]
    shader = get_shader(shader_id)
    if shader is None:
        return None
    info = shader['info']
    title = info['name']
    author = info['username']
    date = datetime.fromtimestamp(int(info['date']))
    description = info['description']
    tags = ', '.join(info['tags'])
    views = info['viewed']
    likes = info['likes']
    status = {
        0: "private",
        1: "public",
        2: "unlisted",
        3: "public+api"
    }[info['published']]
    thumb_url = f"https://www.shadertoy.com/media/shaders/{shader_id}.jpg"
    author_url = f"https://www.shadertoy.com/user/{author}"
    author_icon_url = f"https://www.shadertoy.com/media/users/harry7557558/{author}.png"
    footer = " • ".join([tags, status])

    # generate embed
    embed = discord.Embed(title=title, color=0x404040)
    embed.url = url
    embed.set_author(name=author, url=author_url, icon_url=author_icon_url)
    embed.description = description
    embed.set_image(url=thumb_url)
    embed.set_footer(text=footer)
    embed.timestamp = date
    embed.add_field(name="Views", value=str(views), inline=True)
    embed.add_field(name="Likes", value=str(likes), inline=True)

    return embed


def parse_message_links(message):
    links = []
    for link in re.findall(
            r"https://www.shadertoy.com/view/[A-Za-z0-9_]+", message):
        if link not in links:
            links.append(link)
    embeds = []
    for link in links:
        try:
            embed = generate_embed(link)
            embeds.append(embed)
        except BaseException as error:
            print("Shadertoy error", link, error)
    return embeds


async def message_main(message):
    graph_embeds = parse_message_links(message.content)
    if len(graph_embeds) != 0:
        for embed in graph_embeds:
            await message.channel.send(embed=embed)
        # await message.edit(suppress=True)


if __name__ == "__main__":
    generate_embed("https://www.shadertoy.com/view/7dBfDt")
