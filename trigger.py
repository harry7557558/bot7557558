# magical

import discord
import re
import datetime
import base64
import json


def remove_spoilers(content: str) -> str:
    """Prevent unwanted content from triggering the bot"""

    content = content.replace('\r', '')

    # remove blockquotes
    content = '\n' + content
    content = re.sub(r"\n\s*\>\>\>.*", "", content, flags=re.S)
    content = re.sub(r"\n\s*\>.*?$", "", content, flags=re.M)
    content = content.strip('\n')

    # remove codeblocks and spoilers
    content = re.sub(r"```.*?```", "", content, flags=re.S)
    content = re.sub(r"\|\|.*?\|\|", "", content, flags=re.S)
    content = re.sub(r"`.*?`", "", content, flags=re.S)

    return content


checked_messages = {}


# https://www.englishhints.com/list-of-prefixes.html
# https://www.thoughtco.com/common-suffixes-in-english-1692725
PREFIXES = "a,an,ab,ad,ac,as,ante,anti,auto,ben,bi,circum,co,com,con,contra,counter,de,di,dis,eu,ex,exo,ecto,extra,extro,fore,hemi,hyper,hypo,il,im,in,ir,inter,intra,macro,mal,micro,mis,mono,multi,non,ob,oc,op,omni,over,peri,poly,post,pre,pro,quad,re,semi,sub,sup,super,supra,sym,syn,trans,tri,ultra,un,uni"
SUFFIXES = "s,d,es,ed,in,ing,acy,al,ance,ence,dom,er,or,ism,ist,ity,ty,ment,nes,ship,sion,tion,ate,en,ify,fy,ize,izes,ized,ise,ises,ised,able,ables,ability,ible,ibles,ibility,al,esque,ful,ic,ical,ious,ous,ish,ive,ives,les,y"


def dedup(s: str):
    """Remove the prefixes/suffixes of a word"""
    # remove consecutive letters
    t = ""
    for c in s.lower():
        if len(t) != 0 and c == t[-1]:
            continue
        t += c
    s = t
    # remove prefixes
    prefixes = sorted(PREFIXES.split(','), key=lambda s: -len(s))
    for prefix in prefixes:
        if len(s) < len(prefix) + 3:
            continue
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    # remove suffixes
    suffixes = sorted(SUFFIXES.split(','), key=lambda s: -len(s))
    iter = 0
    while iter < 3:
        t = re.sub(r'ie[sdr]$', 'y', s)
        if t != s:
            s = t
            iter += 1
        for suffix in suffixes:
            if len(s) < len(suffix) + 3:
                continue
            if s.endswith(suffix):
                s = s[:len(s) - len(suffix)]
                break
        iter += 1
    return s


def detect_trigger(message):
    """Detect trigger in the message, returns embed if triggered"""
    global checked_messages
    if type(message) is not str and message.id in checked_messages and \
            checked_messages[message.id] == message.content:
        return
    checked_messages[message.id] = message.content

    # get message content
    if type(message) == str:  # debug
        content = message
    else:
        content = message.content
    content = remove_spoilers(content)
    nummap = {'0': 'o', '1': 'l', '2': 'z', '5': 's', '9': 'g'}  # 1=>I ?
    content = ''.join([nummap[c] if c in nummap else c for c in list(content)])
    content = re.sub(r"[^A-Za-z0-9\u0080-\uffff]", ' ', content)
    content = re.sub(r"\s+", ' ', content)
    words = content.split()

    # detect triggers
    # triggers_o = b">9\\!+H6OmaDffe>/0].WD^$_VF*2OJ/0\\\\K@r!8>,'S-@+tOpSD.[3p+tOpVD.[E)/0].KBlkOM,%>\\2Cia9(F<W7[F(f90E,Tf>+tOpWASu4'+tOpJF`):F>l"
    triggers_o = b">9\\!+H6OmaDffe>/0].WD^$_VAp%U!+tOpVD.[E)/0].KBlkOM,%>\\2Cia9(F<W7[F(f90E,Tf>+tOpWASu4'+tOpJF`):F>l"
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
    content = message.content[:600]
    if content != message.content:
        content += "..."
    embed = discord.Embed(title="Trigger Detected!", color=0xff0000)
    embed.add_field(name="User",
                    value=message.author.mention,
                    inline=True)
    embed.add_field(name="Message",
                    value=content,
                    inline=True)
    embed.add_field(name="Trigger"+'s'*(len(keywords) > 1),
                    value=', '.join(list(keywords.values())),
                    inline=True)
    embed.timestamp = datetime.datetime.utcnow()
    return embed


def detect_ghost_ping(msg1, msg2=None):
    """Returns embed if ghost ping detected"""

    def get_mentions(msg):
        if msg is None:
            return set([])
        user_mentions = [f"<@{user.id}>" for user in msg.mentions]
        role_mentions = [f"<@&{role.id}>" for role in msg.role_mentions]
        everyone_mention = ["@everyone"] if msg.mention_everyone else []
        mentions = everyone_mention + role_mentions + user_mentions
        return set(mentions)

    mentions1 = get_mentions(msg1)
    mentions2 = get_mentions(msg2)
    # print(mentions1, mentions2)
    triggers = []
    for mention in mentions1:
        if mention not in mentions2:
            triggers.append(mention)
    if len(triggers) == 0:
        return None

    embed = discord.Embed(title="Ghost Ping Detected!", color=0xff0000)
    embed.add_field(name="User",
                    value=msg1.author.mention,
                    inline=True)
    embed.add_field(name="Mention" + 's' * (len(triggers) != 1),
                    value=' '.join(triggers),
                    inline=True)
    embed.add_field(name="Message",
                    value=msg1.content,
                    inline=True)
    embed.timestamp = msg1.edited_at or msg1.created_at
    return embed


if __name__ == "__main__":
    detect_trigger("")
