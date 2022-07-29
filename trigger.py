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
PREFICES = "a,an,ab,ad,ac,as,ante,anti,auto,ben,bi,circum,co,com,con,contra,counter,de,di,dis,eu,ex,exo,ecto,extra,extro,fore,hemi,hyper,hypo,il,im,in,ir,inter,intra,macro,mal,micro,mis,mono,multi,non,ob,oc,op,omni,over,peri,poly,post,pre,pro,quad,re,semi,sub,sup,super,supra,sym,syn,trans,tri,ultra,un,uni"
SUFFICES = "s,d,es,ed,in,ing,acy,al,ance,ence,dom,er,or,ism,ist,ity,ty,ment,nes,ship,sion,tion,ate,en,ify,fy,ize,ise,able,ability,ible,ibility,al,esque,ful,ic,ical,icate,ion,ious,ous,ish,ive,les,y"


def dedup(s: str):
    """Remove the consecutive letters of a word"""
    # remove consecutive letters
    t = ""
    for c in s.lower():
        if len(t) != 0 and c == t[-1]:
            continue
        t += c
    return t


def expand_suffices(word: str, iterations=3):
    # repeat adding suffices
    if iterations > 1:
        words = set([word])
        new_words = [word]
        for i in range(iterations):
            added_words = set({})
            for word in new_words:
                added_words = added_words.union(expand_suffices(word, 1))
            new_words = []
            for new_word in added_words:
                if len(new_word) > 16:
                    continue
                if new_word not in words:
                    new_words.append(new_word)
                words.add(new_word)
        return words

    # adding one suffix
    assert len(word) > 2
    new_words = []
    for suffix in SUFFICES.split(','):
        if suffix[0] in 'aeiouy':
            if word[-1] in 'aeiouy' and word[-2] not in 'aeiou':
                new_words.append(word[:-1]+suffix)
            if word[-1] not in 'aeiou':
                new_words.append(word+suffix)
        else:
            if word[-1] == 'y':
                new_words.append(word[:-1]+'i'+suffix)
                new_words.append(word[:-1]+'ie'+suffix)
            else:
                new_words.append(word+suffix)
    new_words = [dedup(word) for word in new_words]
    new_words = set(new_words)
    return new_words


def generate_trigger_suffices():
    """Generate a list of possible suffices of triggers"""
    filename = ".trigger-suffices"
    # load from file
    try:
        suffices = open(filename, 'r').read().split(' ')
        assert len(suffices) > 1
        return suffices
    # generate and save file (takes a while)
    except:
        word = "ash"  # an innocent 3-letter word
        suffices = list(expand_suffices(word))
        for i in range(len(suffices)):
            suffices[i] = suffices[i][len(word):]
        suffices = sorted(suffices)
        print(len(suffices), "suffices generated")
        open(filename, 'w').write(' '.join(suffices))
        return suffices


CHECK_PREFICES = sorted(PREFICES.split(','), key=lambda word: -len(word))
CHECK_SUFFICES = None


def detect_trigger(message):
    """Detect trigger in the message, returns embed if triggered"""
    global CHECK_PREFICES, CHECK_SUFFICES

    if not isinstance(message, str):
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
    # triggers_o = b">9\\!+H6OmaF*2OJ/0\\\\K@r!8>,'S-@+tOpSD.[3p+tOpVD.[E)/0].KBlkOM,%>\\2Cia9(F<W7[F(f90E,Tf>+tOpWASu4'+tOpJF`):F>l"
    triggers_o = b">9\\!+H6OmaAp%U!+tOpVD.[E)/0].KBlkOM,%>\\2Cia9(F<W7[F(f90E,Tf>+tOpWASu4'+tOpJF`):F>l"
    triggers = {}
    for trigger in json.loads(base64.a85decode(triggers_o).decode('utf-8')):
        triggers[dedup(trigger)] = trigger
    keywords = {}
    for word in words:
        word = dedup(word)
        for prefix in CHECK_PREFICES:
            if word.startswith(prefix):
                word = word[len(prefix):]
                break
        for trigger in triggers:
            if not word.startswith(trigger):
                continue
            if CHECK_SUFFICES is None:
                CHECK_SUFFICES = generate_trigger_suffices()
            if word == trigger or \
                    word[len(trigger):] in CHECK_SUFFICES or \
                    word[len(trigger)-1:] in CHECK_SUFFICES:
                keyword = triggers[trigger]
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
        mentions = set(everyone_mention + role_mentions + user_mentions)
        author_mention = msg.author.mention
        if author_mention in mentions:
            mentions.remove(author_mention)
        return mentions

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


# örz
if __name__ == "__main__":
    detect_trigger("Let's reorz the orzing orzness of orziful Moana! Orz!")
