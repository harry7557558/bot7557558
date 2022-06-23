# custom preview for Shadertoy shaders

import discord
import requests
import json
import re
import datetime
from trigger import remove_spoilers


def request_headers(shader_id):
    return {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'pragma': 'no-cache',
        'origin': 'https://www.shadertoy.com',
        'referer': f'https://www.shadertoy.com/view/{shader_id}'
    }


def get_shader(shader_id: str) -> dict:
    print("Request Shadertoy", shader_id)
    data = {
        's': json.dumps({"shaders": [shader_id]}),
        'nt': '1',
        'nl': '1',
        'np': '1'
    }
    req = requests.post(
        "https://www.shadertoy.com/shadertoy",
        data=data,
        headers=request_headers(shader_id)
    )
    if req.status_code != 200:
        return None
    response = req.content.decode('utf-8')
    response = json.loads(response)
    if len(response) == 0:
        return None
    return response[0]


def minify_code(code: str):
    """Grabbed from Shadertoy implementation"""
    def isSpace(s):
        return s in [' ', '\t']

    def isLine(s):
        return s == '\n'

    def replaceChars(s):
        dst = ""
        isPreprocessor = False
        for i in range(len(s)):
            if s[i] == "#":
                isPreprocessor = True
            elif s[i] == "\n":
                if isPreprocessor:
                    isPreprocessor = False
                else:
                    dst += " "
                    continue
            elif s[i] in ["\r", "\t"]:
                dst += " "
                continue
            elif i < len(s) - 1 and s[i] == "\\" and s[i+1] == "\n":
                i += 1
                continue
            dst += s[i]
        return dst

    def removeEmptyLines(s):
        d = ""
        isPreprocessor = False
        for i in range(len(s)):
            if s[i] == '#':
                isPreprocessor = True
            isDestroyableChar = isLine(s[i])
            if isDestroyableChar and not isPreprocessor:
                continue
            if isDestroyableChar and isPreprocessor:
                isPreprocessor = False
            d += s[i]
        return d

    def removeMultiSpaces(s):
        dst = ""
        for i in range(len(s)):
            if isSpace(s[i]) and i == len(s) - 1:
                continue
            if isSpace(s[i]) and isLine(s[i-1]):
                continue
            if isSpace(s[i]) and isLine(s[i+1]):
                continue
            if isSpace(s[i]) and isSpace(s[i+1]):
                continue
            dst += s[i]
        return dst

    def removeSingleSpaces(s):
        dst = ""
        for i in range(len(s)):
            iss = isSpace(s[i])
            if i == 0 and iss:
                continue
            if i > 0:
                if iss and s[i-1] in ";,}{()+-*/?<>[]:=^%\n\r":
                    continue
            if i > 1:
                if iss and s[i-2:i] in ["&&", "||", "^^", "!=", "=="]:
                    continue
            if iss and s[i+1] in ";,}{()+-*/?<>[]:=^%\n\r":
                continue
            if i < len(s) - 2:
                if iss and s[i+1:i+3] in ["&&", "||", "^^", "!=", "=="]:
                    continue
            dst += s[i]
        return dst

    def removeComments(s):
        dst = ""
        state = 0
        i = 0
        while i < len(s):
            if i <= len(s)-2:
                if state == 0 and s[i:i+2] == "/*":
                    state = 1
                    i += 2
                    continue
                if state == 0 and s[i:i+2] == "//":
                    state = 2
                    i += 2
                    continue
                if state == 1 and s[i:i+2] == "*/":
                    dst += " "
                    state = 0
                    i += 2
                    continue
                if state == 2 and s[i] in "\r\n":
                    state = 0
                    i += 1
                    continue
            if state == 0:
                dst += s[i]
            i += 1
        return dst

    code = removeComments(code)
    code = replaceChars(code)
    code = removeMultiSpaces(code)
    code = removeSingleSpaces(code)
    code = removeEmptyLines(code)
    return code


def get_description(info):
    s = info['description']
    # parent
    if info['parentid'] != '':
        prefix = f"Forked from {info['parentname']} (https://www.shadertoy.com/view/{info['parentid']})\n\n"
        s = prefix + s
    # clear formatting
    s = re.sub(r'\[([a-z]+)\](.*?)\[\/\1\]', '\\2', s)
    # hyperlink
    s = re.sub(r'\[url=([\"\']?)(.*?)\1\](.*?)\[\/url\]', '\\3 (\\2)', s)
    return s


def generate_embed(shader_id: str):

    # basic info
    shader = get_shader(shader_id)
    if shader is None:
        return None
    with open(".shader.temp", "w") as fp:  # so I can pull out and debug later
        json.dump(shader, fp)
    info = shader['info']
    title = info['name']
    author = info['username']
    date = datetime.datetime.fromtimestamp(int(info['date']))
    description = get_description(info)
    tags = ', '.join(info['tags'])
    views = info['viewed']
    likes = info['likes']
    like_rate = 100.0 * min(float(likes) / max(float(views), 1), 1.0)
    status = {
        0: "private",
        1: "public",
        2: "unlisted",
        3: "public+api"
    }[info['published']]
    footer = " • ".join([tags, status])
    thumb_url = f"https://www.shadertoy.com/media/shaders/{shader_id}.jpg"
    author_url = f"https://www.shadertoy.com/user/{author}"
    author_icon_url = "https://www.shadertoy.com/img/profile.jpg"
    for ext in ['png', 'jpg', 'jpeg', 'webp']:
        url = f"https://www.shadertoy.com/media/users/{author}/profile.{ext}"
        r = requests.get(url, headers=request_headers(shader_id))
        print("Request", url, "-", r.status_code)
        if r.status_code < 300:
            author_icon_url = url
            break

    # renderpass

    orders = ["Common", "Buffer A", "Buffer B",
              "Buffer C", "Buffer D", "Cube A", "Image", "Sound"]
    passes = []

    mains_count = {
        'mainImage': 0,
        'mainSound': 0,
        'mainVR': 0,
    }
    uniforms_count = {
        'iResolution': 0,
        'iTime': 0,
        'iTimeDelta': 0,
        'iChannelTime': 0,
        'iFrame': 0,
        'iMouse': 0,
        'iDate': 0,
        'iSampleRate': 0,
        'iChannelResolution': 0,
    }
    textures_count = {
        'buffer': 0,
        'texture': 0,
        'cubemap': 0,
        'video': 0,
        'music': 0,
        'musicstream': 0,
        'mic': 0,
        'webcam': 0,
        'volume': 0,
        'keyboard': 0,
    }

    for renderpass in shader['renderpass']:
        name = renderpass['name']
        name = name.replace("Buf ", "Buffer ")
        if name == "":
            name = "Image"
        assert name in orders
        code = minify_code(renderpass['code'])
        open(".code.temp", "w").write(minify_code(code))  # check for bug
        passes.append({
            "name": name,
            "chars": len(code)
        })
        words = re.sub(r"[^A-Za-z0-9_]+", ' ', code).strip()
        for word in words.split():
            if word in mains_count:
                mains_count[word] += 1
            if word in uniforms_count:
                uniforms_count[word] += 1
        for input in renderpass['inputs']:
            if input['type'] in textures_count:  # should be
                textures_count[input['type']] += 1

    if len(passes) == 1:
        passes_str = passes[0]['name'] + " • " + \
            str(passes[0]['chars']) + " chars"
    else:
        passes = sorted(passes, key=lambda rp: orders.index(rp['name']))
        passes_name_str = " • ".join([ps['name'] for ps in passes])
        passes_chars = [ps['chars'] for ps in passes]
        passes_chars_str = " + ".join(map(str, passes_chars)) + \
            " = " + str(sum(passes_chars)) + " chars"
        passes_str = passes_name_str + "\n" + passes_chars_str

    mains = [item[0] for item in mains_count.items() if item[1] > 0]
    uniforms = [item[0] for item in uniforms_count.items() if item[1] > 0]
    textures = [item[0] for item in textures_count.items() if item[1] > 0]
    ios = ' ｜ '.join([' • '.join(s)
                      for s in [mains, uniforms, textures] if s != []])
    passes_str += '\n' + ios

    # generate embed
    embed = discord.Embed(title=title, color=0x404040)
    embed.url = "https://www.shadertoy.com/view/" + shader_id
    embed.set_author(name=author, url=author_url, icon_url=author_icon_url)
    embed.description = description
    embed.set_image(url=thumb_url)
    embed.set_footer(text=footer)
    embed.timestamp = date
    embed.add_field(name="Renderpass", value=passes_str, inline=False)
    embed.add_field(name="Views", value=str(views), inline=True)
    embed.add_field(name="Likes", value=str(likes), inline=True)
    embed.add_field(name="Like rate", value="{:.2f} %".format(like_rate),
                    inline=True)

    return embed


def parse_message_links(message):
    shader_ids = {}
    for url in re.findall(
            r"https?://(?:www\.)?shadertoy\.com/view/[A-Za-z0-9_]+", message):
        shader_id = url[url.rfind('/')+1:]
        shader_ids[shader_id] = True
    embeds = []
    for shader_id in shader_ids:
        try:
            embed = generate_embed(shader_id)
            embeds.append(embed)
        except BaseException as error:
            print("Shadertoy error", shader_id, error)
    return embeds


async def message_main(message):
    content = remove_spoilers(message.content)
    graph_embeds = parse_message_links(content)
    if len(graph_embeds) != 0:
        for embed in graph_embeds:
            await message.channel.send(embed=embed)
        # await message.edit(suppress=True)
