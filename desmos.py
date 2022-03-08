# custom preview for Desmos graphs

import discord
import requests
import re
import html
import json
import email.utils
import datetime


def get_graph_info(url):
    print("Request", url)
    req = requests.get(url)
    if req.status_code != 200:
        raise ValueError(f"Request returns {req.status_code}")
    content = req.content.decode('utf-8')
    matches = re.findall(r'data-load-data="([^\"]+?)"', content)
    if len(matches) == 0:
        raise ValueError(f"Graph contains no `data-load-data`.")
    info = html.unescape(matches[0])
    return json.loads(info)


def generate_embed(url, check_history: bool):
    info = get_graph_info(url)
    graph = info['graph']
    hash = graph['hash']
    title = "Desmos | Graphing Calculator" if graph['title'] == None else graph['title']
    thumbnail = graph['thumbUrl']
    time = datetime.datetime(*email.utils.parsedate(graph['created'])[:6])

    embed = discord.Embed(title=title, color=0x107030)
    embed.set_author(name="Desmos")
    embed.url = url
    embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text=hash)
    embed.timestamp = time

    if check_history:
        history = []
        pgraph = graph
        ended = False
        for i in range(20):
            try:
                phash = pgraph['parent_hash']
                if phash == hash:
                    break
                purl = "https://www.desmos.com/calculator/"+phash
                pinfo = get_graph_info(purl)
                pgraph = pinfo['graph']
                history.append(purl)
            except:
                ended = True
                break
        if not ended:
            history.append("......")
        if len(history) != 0:
            history = '\n'.join(history)
            embed.add_field(name="History", value=history)

    return embed


def parse_message_links(message, check_history: bool):
    links = re.findall(
        r"https://www.desmos.com/calculator/[a-z0-9]+", message)
    embeds = []
    for link in links:
        try:
            embed = generate_embed(link, check_history)
            embeds.append(embed)
        except BaseException as error:
            print("Desmos graph error", link, error)
    return embeds


if __name__ == "__main__":
    parse_message_links(
        """https://www.desmos.com/calculator/ftuogjzprg""", True)
