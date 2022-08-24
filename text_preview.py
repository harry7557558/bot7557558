# Misc link preview
#  - Discord message link
#  - GitHub code line link

import discord
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
from trigger import remove_spoilers


async def preview_discord_message_link(client, message):
    """Preview the link to a message
        In the form https://discord.com/channels/[guild_id]/[channel_id]/[message_id]
       When a link is pasted, it shows a preview if it has access to the message.
    """
    content = remove_spoilers(message.content)
    message_channel = message.channel
    for (guild_id, channel_id, message_id) in re.findall(
            r"https?://(?:www\.)?discord\.com/channels/([0-9]+)/([0-9]+)/([0-9]+)", content):
        try:
            # get message
            channel = client.get_channel(int(channel_id))
            if channel.nsfw and not message.channel.nsfw:
                continue
            message = await channel.fetch_message(int(message_id))

            # get message summary
            channel = message.channel.mention
            author = message.author.mention
            timestamp = message.created_at
            content = message.content
            if len(content) > 1024:
                content = content[:1000] + '...'
            # attachments
            image = None
            attachments = []
            for attachment in message.attachments:
                url = attachment.url
                is_spoiler = attachment.is_spoiler()
                if attachment.content_type in ["image/jpeg", "image/png"] \
                        and image is None and not is_spoiler:  # image attachment
                    image = url
                if is_spoiler:
                    url = "||" + url + "||"
                attachments.append(url)
            if (len(attachments) == 1 and image is not None) and \
                    content in ["", image]:  # image-only message
                content = ""
                attachments = []
            # embeds
            embeds = [embed for embed in message.embeds]
            if len(embeds) > 0:  # embed-only message
                content += f"\n\n***Message has {len(embeds)} embed" + \
                    's'*(len(embeds) > 1) + ".***"

            # generate embed
            embed = discord.Embed(color=0xddbbdd)
            embed.url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
            embed.description = content
            embed.set_footer(text=f"Message preview" +
                             " (edited)" * int(message.edited_at is not None))
            if image is not None:
                embed.set_image(url=image)
            embed.timestamp = timestamp
            if len(attachments) > 0:
                embed.add_field(name="Attachment" + 's'*(len(attachments) != 1),
                                value='\n'.join(attachments), inline=False)
            await message_channel.send(
                f"Message by {author} on {channel}.",
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none())

        except BaseException as e:
            print("Error:", e)
            continue


async def preview_github_line_link(message):
    """Preview the link to a line of GitHub code.
        https://github.com/[username]/[repo]/blob/[branch]/[path]#[line_range]
    """

    message_content = remove_spoilers(message.content)

    def preview_source(raw_url: str, response_test: str, line_range: str):
        line_range = [int(l.lstrip('L')) for l in line_range.split('-')]
        source = response_test.replace('\r\n', '\n').replace('\r', '\n')
        lines = source.split('\n')
        truncated = ""
        if len(line_range) == 1:
            lines = lines[line_range[0]-1]
        elif len(line_range) == 2:
            lines = lines[line_range[0]-1:line_range[1]]
            lines1 = ''
            for i in range(len(lines)):
                line = lines[i]
                if len(lines1)+len(line) < 1000 or len(lines)-i <= 1 or lines1 == '':
                    lines1 += line + '\n'
                else:
                    truncated = f"{len(lines)-i-1} more lines."
                    break
            lines = lines1.rstrip('\n')
        else:
            raise ValueError("Invalid line range: " + str(line_range))
        if len(lines) > 1000:
            lines = lines[:1000]
            truncated = "Code truncated due to message length limitation."
        if lines.strip() == '':
            raise ValueError("Selected line(s) consist(s) of only whitespace.")
        ext = raw_url.split('.')[-1]
        if not re.match(r"^\w+$", ext):
            ext = ''
        source = "```{}\n{}\n```".format(ext, lines)
        return source + truncated

    async def process_source(username, repo, path, line_range):
        branch = path.split('/')[0]
        relative_path = '/'.join(path.split('/')[1:])
        raw_url = f"https://raw.githubusercontent.com/{username}/{repo}/{path}"
        print("Request", raw_url)
        req = requests.get(raw_url)
        if req.status_code != 200:
            raise BaseException(f"{raw_url} returns {req.status_code}.")
        source = preview_source(raw_url, req.text, line_range)
        description = '\n'.join([
            f"`{relative_path}` in `{username}/{repo}/{branch}`.",
            source
        ]).strip()
        await message.channel.send(
            description,
            allowed_mentions=discord.AllowedMentions.none())

    async def process_gist(username, gist_id, file_line):
        # get file ID and line range from hash
        file_line = file_line.split('-')
        line_range = ""
        if re.match(r"^L\d+$", file_line[-1]):
            line_range = file_line.pop()
            if len(file_line) > 1 and re.match(r"^L\d+", file_line[-1]):
                line_range = file_line.pop() + '-' + line_range
        else:
            raise ValueError("No line range specified in gist.")
        file_id = '-'.join(file_line)
        # get gist file URL
        gist_url = f"https://gist.github.com/{username}/{gist_id}"
        print("Request", gist_url)
        req = requests.get(gist_url)
        if req.status_code != 200:
            raise BaseException(f"{gist_url} returns {req.status_code}.")
        soup = BeautifulSoup(req.content, "html.parser")
        content = soup.find('div', {'class': 'gist-content'})
        description = content.find('div', {'itemprop': 'about'})
        if description is not None:
            description = ', from gist "' + description.text.strip() + '"'
        else:
            description = ''
        filediv = content.find('div', {'id': file_id})
        filetitle = filediv.find('div', {'class': 'file-actions'})
        raw_url = filetitle.find('a').attrs['href']
        raw_url = urllib.parse.urljoin(gist_url, raw_url)
        # get gist content and generate embed
        print("Request", raw_url)
        req = requests.get(raw_url)
        if req.status_code != 200:
            raise BaseException(f"{raw_url} returns {req.status_code}.")
        lines = [
            f"`{raw_url[raw_url.rfind('/')+1:]}` by `{username}`{description}.",
            preview_source(raw_url, req.text, line_range)
        ]
        await message.channel.send(
            '\n'.join(lines).strip(),
            allowed_mentions=discord.AllowedMentions.none())

    # get matches
    source_matches = re.findall(
        r"https?://(?:www\.)?github\.com/([\w\-]+)/([\w.,@^=%:~+-]*[\w@^=%~+-])/blob/([\w.,@^=%:~+-\/]*[\w@^=%~+-\/])#([L\d\-]*)",
        message_content)
    gist_matches = re.findall(
        r"https?://gist\.github\.com/([\w\-]+)/([a-z0-9]+)/?#([\w.,@^=%:~+-]+)",
        message_content)
    success_count = len(source_matches) + \
        len(gist_matches)  # get subtracted on error

    # source files within repository
    for matched in source_matches:
        try:
            await process_source(*matched)
        except BaseException as e:
            print("Error:", e)
            success_count -= 1
            continue

    # gists within repository
    for matched in gist_matches:
        try:
            await process_gist(*matched)
        except BaseException as e:
            print("Error:", e)
            success_count -= 1
            continue

    # suppress default preview
    if len(source_matches) + len(gist_matches) > 0 and success_count > 0:
        await message.edit(suppress=True)


async def message_main(client, message):
    await preview_discord_message_link(client, message)
    await preview_github_line_link(message)
