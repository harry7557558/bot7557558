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


def get_graph_size_summary(state) -> str:
    """Generate a string of the size of the graph as a summary"""
    def format_plural(count: int, name: str) -> str:
        name += "s" * (count > 1)
        count_s = ""
        while count >= 1000:
            count_s = "," + "{:03d}".format(count % 1000) + count_s
            count //= 1000
        count_s = str(count) + count_s
        return count_s + " " + name
    byte_count = len(bytearray(json.dumps(
        state, separators=(',', ':')), 'utf-8'))  # may vary
    expr_count, note_count, folder_count, table_count, img_count = [0]*5
    for expr in state['expressions']['list']:
        if 'type' not in expr:
            continue  # ??
        if expr['type'] == "expression" and 'latex' in expr:
            expr_count += 1
        if expr['type'] == "text" and 'text' in expr:
            note_count += 1
        if expr['type'] == "folder":
            folder_count += 1
        if expr['type'] == "table":
            table_count += 1
        if expr['type'] == "image":
            img_count += 1
    size_info = [format_plural(byte_count, "byte")]
    if expr_count != 0:
        size_info.append(format_plural(expr_count, "expression"))
    if note_count != 0:
        size_info.append(format_plural(note_count, "note"))
    if folder_count != 0:
        size_info.append(format_plural(folder_count, "folder"))
    if table_count != 0:
        size_info.append(format_plural(table_count, "table"))
    if img_count != 0:
        size_info.append(format_plural(img_count, "image"))
    size_info = " • ".join(size_info)
    return size_info


def get_graph_description(state) -> str:
    """Generate a description of the graph for preview purpose"""
    description = ""
    for expr in state['expressions']['list']:
        if 'type' not in expr:
            continue
        if expr['type'] == "expression" and 'latex' in expr:
            break
        if expr['type'] in ['table', 'image']:
            break
        if expr['type'] == "text" and 'text' in expr:
            description += expr['text'] + '\n\n'
    return description.strip()


def generate_embed(url, check_history: bool):
    # basic graph info
    info = get_graph_info(url)
    graph = info['graph']
    state = graph['state']
    hash = graph['hash']
    title = "Desmos | Graphing Calculator" if graph['title'] == None else graph['title']
    thumbnail = graph['thumbUrl'] if 'thumbUrl' in graph else "https://s3.amazonaws.com/desmos/img/calc_thumb.png"
    time = datetime.datetime(*email.utils.parsedate(graph['created'])[:6])

    # generate embed
    embed = discord.Embed(title=title, color=0x107030)
    embed.set_author(name="Desmos")
    embed.url = url
    embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text=hash)
    embed.timestamp = time

    # preview
    if not check_history or True:
        description = get_graph_description(state)
        size_summary = get_graph_size_summary(state)
        if description == "":
            embed.description = size_summary
        else:
            maxlen = 256 if check_history else 512
            if len(description) > maxlen:
                description = description[:maxlen]+'...'
            embed.description = description
            embed.set_footer(text=hash + " • " + size_summary)

    # history
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
    links = []
    for link in re.findall(
            r"https://www.desmos.com/calculator/[a-z0-9]+", message):
        if link not in links:
            links.append(link)
    embeds = []
    for link in links:
        try:
            embed = generate_embed(link, check_history)
            embeds.append(embed)
        except BaseException as error:
            print("Desmos graph error", link, error)
    return embeds


async def message_main(message):
    check_history = message.content.lower().strip().startswith("history")
    graph_embeds = parse_message_links(message.content, check_history)
    if len(graph_embeds) != 0:
        for embed in graph_embeds:
            await message.channel.send(embed=embed)
        await message.edit(suppress=True)


if __name__ == "__main__":
    generate_embed("https://www.desmos.com/calculator/z7zooq9zsh", False)
