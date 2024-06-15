# custom preview for Desmos graphs

import discord
import requests
import re
import html
import json
import datetime
import dateutil.parser
from trigger import remove_spoilers


def get_graph_info(url, state_required=True):
    print("Request", url)
    req = requests.get(url)
    if req.status_code != 200:
        raise ValueError(f"Request returns {req.status_code}")
    content = req.content.decode('utf-8')
    matches = re.findall(r'data-load-data="([^\"]+?)"', content)
    if len(matches) == 0:
        raise ValueError(f"Graph contains no `data-load-data`.")
    info = html.unescape(matches[0])
    graph = json.loads(info)['graph']
    if state_required and "state" not in graph:
        state_url = graph['stateUrl']
        print("Request", state_url)
        state_str = requests.get(state_url).content
        graph['state'] = json.loads(state_str)
    return graph


def get_graph_size_summary(state) -> str:
    """Generate a string of the size of the graph as a summary"""

    def format_plural(count: int, name: str, suffix: str='') -> str:
        name += "s" * (count > 1)
        count_s = ""
        while count >= 1000:
            count_s = "," + "{:03d}".format(count % 1000) + count_s
            count //= 1000
        count_s = str(count) + count_s
        return ' '.join([count_s, name, suffix]).strip()

    # get size
    byte_count = len(bytearray(json.dumps(
        state, separators=(',', ':')), 'utf-8'))  # may vary
    (
        expr_count, tone_count, regression_count,
        note_count, folder_count, table_count, img_count
    ) = [0]*7
    for expr in state['expressions']['list']:
        if 'type' not in expr:
            continue  # ??
        if expr['type'] == "expression" and 'latex' in expr:
            expr_count += 1
            if "\\operatorname{tone}" in expr['latex']:
                tone_count += 1
            if "residualVariable" in expr or "regressionParameters" in expr:
                regression_count += 1
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
    if tone_count != 0:
        size_info.append(format_plural(tone_count, "tone", "🎵"))
    if note_count != 0:
        size_info.append(format_plural(note_count, "note", "📝"))
    if folder_count != 0:
        size_info.append(format_plural(folder_count, "folder", "📁"))
    if table_count != 0:
        size_info.append(format_plural(table_count, "table", "📋"))
    if regression_count != 0:
        size_info.append(format_plural(regression_count, "regression", "📈"))
    if img_count != 0:
        size_info.append(format_plural(img_count, "image", "🖼️"))

    # detect animation
    for expr in state['expressions']['list']:
        if 'type' not in expr or expr['type'] != "expression":
            continue
        if 'slider' in expr and 'isPlaying' in expr['slider'] \
                and expr['slider']['isPlaying'] is True:
            size_info.append("slider ▶️")
            break
    if 'ticker' in state['expressions'] and \
        'playing' in state['expressions']['ticker'] and \
            state['expressions']['ticker']['playing'] is True:
        size_info.append("ticker ⏲️")
    return " • ".join(size_info)


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


def generate_embed(calculator, graph_id, check_history: bool):
    # basic graph info
    url = f"https://www.desmos.com/{calculator}/{graph_id}"
    graph = get_graph_info(url)
    state = graph['state']
    hash = graph['hash']
    calculator_name = {
        'calculator': "Graphing Calculator",
        '3d': "3D Graphing Calculator",
        'geometry': "Geometry"
    }[calculator]
    if 'title' in graph and graph['title'] is not None:
        title = graph['title']
    else:
        title = f"Desmos | {calculator_name}"
    thumbnail = graph['thumbUrl'] if 'thumbUrl' in graph else "https://s3.amazonaws.com/desmos/img/calc_thumb.png"
    try:
        time = datetime.datetime.strptime(
            graph['created'], "%a, %d %b %Y %H:%M:%S GMT")
    except:
        time = dateutil.parser.isoparse(graph['created'])

    # generate embed
    embed = discord.Embed(title=title, color=0x107030)
    embed.set_author(name="Desmos")
    embed.url = url
    # embed.set_thumbnail(url=thumbnail)
    embed.set_image(url=thumbnail)
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
                purl = f"https://www.desmos.com/{calculator}/{phash}"
                pgraph = get_graph_info(purl, False)
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
    graph_ids = {}
    for match in re.findall(
            r"https?://(?:www\.)?desmos\.com/(calculator|3d|geometry)/([a-z0-9]+)", message):
        calculator = match[-2]
        graph_id = match[-1]
        graph_ids[graph_id] = True
    embeds = []
    for graph_id in graph_ids:
        try:
            embed = generate_embed(calculator, graph_id, check_history)
            embeds.append(embed)
        except BaseException as error:
            raise error
            print("Desmos graph error", graph_id, error)
    return embeds


async def message_main(message):
    content = remove_spoilers(message.content)
    check_history = "history" in content.lower()
    graph_embeds = parse_message_links(content, check_history)
    if len(graph_embeds) != 0:
        for embed in graph_embeds:
            await message.channel.send(embed=embed)
        await message.edit(suppress=True)
