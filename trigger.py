# magical

import discord
import re
import datetime
import base64
import json
import unicodedata


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

    # start by an exclainmation mark to suppress link preview
    content = re.sub(r"!(http|https|ftp)\:\/\/[^\s]+", "", content)

    return content


checked_messages = {}


def dedup(s: str):
    """Remove the consecutive letters of a word"""
    # remove consecutive letters
    t = ""
    for c in s.lower():
        if len(t) != 0 and c == t[-1]:
            continue
        t += c
    return t


PREFICES = set(open("trigger-prefices.txt").read().split(' '))
SUFFICES = set(open("trigger-suffices.txt").read().split(' '))
PREFICES.add('')
SUFFICES.add('')

# Not perfect
UNICODE_CONFUSABLES = {
    'a': 'АΑᗅаꓮ⍺ȺѦɑᎪα',
    'b': 'ᖯƄЪɃѣҍƁҌƀᏏᗷƃɓВЬΒѢꓐƂБᏴƅ',
    'c': 'ȻꓚҀҁௐᴄЄϾΣҪᏟςсⲤƈɕ¢ȼСҫƇⲥ',
    'd': 'ꓒᎠԁÐᗪᑻ₫ᗞĐȡᑯƊđƉɗɖƌꓓ',
    'e': 'еҽΕҿⴹɆꓰɇ⋿Ꭼ℮Е',
    'f': 'ꓝẝᖴƒƑϜք',
    'g': 'ցᏳƓɡᶃǥԌᏀꓖǤƍɠ',
    'h': 'ӉᏂԨիНᏲɧћӇᕼɦĦħⲎᎻҤհⱧΗꓧһҢ',
    'i': 'ιɨіɪı⍳ƗᎥӀΙɩІӏ',
    'j': 'ЈȷɟјɈᒙᎫյɉᏧᒍϳꓙ',
    'k': 'ⲔƙⱩқΚҟҠĸᴋᏦκꓗкКҞϏԟԞƘⲕҜӃҚ',
    'l': 'ŁꓡⳐⵏᏞᒪȽߊו|ꓲ│Ⲓ∣ΙᒷІƚƖɭǀɬ1ױƗԼӀłןɫ',
    'm': 'ⲘɱᗰΜꓟᎷӎӍϺМ',
    'n': 'ƞπΝրղոŋƝⲚꓠɲηпդɳռʼᴨИҊ',
    'o': '〇ծ⍬ө0௦ංѻಂØɵΟⵔᎾƟ٥૦໐ѳѲ⊖ᴑס೦ⴱ๐օσΘՕ߀⊝ϙ০൦ᴏ੦ӨθОоⲟѺഠⲞø౦ဝꓳంο၀ം०୦ଠ',
    'p': 'ᏢҏρᑷƿҎꓑƥРΡⲣрƤᑭϼⲢ⍴',
    'q': 'ԛգʠɊԚզɋ',
    'r': 'ɌᎡⲅɍɼꓣᴦɽЯᖇғᏒƦг',
    's': 'ѕꓢՏꜱᏚȿƽЅᏕʂ$',
    't': 'ƭԎҭƬŦƮТꓔŧƫҬᴛȾтᎢⲦ⟙τΤꜨ',
    'u': 'ՄʋᑘᴜᑌՍƲսɄцꓴԱυ',
    'v': 'ⴸѵ⋁ɣνѴᴠꓦטᏙ∨ᐯ',
    'w': 'ѿѡᏔԝꓪᎳ₩Ԝω',
    'x': '⤫ꓫҳ×ΧӽҖХ⨯ᕁχⲬⵝ᙮Ҳжх⨰Ӽ⤬᙭Жᕽҗӿ╳Ӿ',
    'y': 'ƴᎩᶌꓬүγᎽƳⲨҮҰʏყɏұ¥ỿΥɎу',
    'z': 'ƶʐƵᴢɀꓜᏃȤʑȥΖ'
}
UNICODE_CONFUSABLES_MAP = {}


def detect_trigger(message):
    """Detect trigger in the message, returns embed if triggered"""
    if not isinstance(message, str):
        global checked_messages
        if type(message) is not str and message.id in checked_messages and \
                checked_messages[message.id] == message.content:
            return
        checked_messages[message.id] = message.content

    # get message content
    if isinstance(message, str):  # debug
        content = message
    else:
        content = message.content
    content = remove_spoilers(content)
    content = re.sub(  # don't check URL
        r"((http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-]))",
        " ", content)
    content1 = ""
    for chr in content:
        if ord(chr) < 0x80:
            content1 += chr
            continue
        chr = unicodedata.normalize('NFKD', chr)  # "simplify" characters
        chr = re.sub(  # remove combining characters
            r"[\u0300-\u036F\u1AB0-\u1AFF\u1DC0-\u1DFF\u20D0-\u20FF\uFE20-\uFE2F\.\,·]",
            '', chr)
        content1 += chr
    content = content1
    if len(UNICODE_CONFUSABLES_MAP) == 0:  # initialize confusable character map
        for (letter, confusables) in UNICODE_CONFUSABLES.items():
            UNICODE_CONFUSABLES[letter] = letter
            for confusable in confusables:
                if confusable not in UNICODE_CONFUSABLES_MAP:
                    UNICODE_CONFUSABLES_MAP[confusable] = letter
    content = ''.join([  # map confusable characters
        UNICODE_CONFUSABLES_MAP[c] if c in UNICODE_CONFUSABLES_MAP else c
        for c in content])
    nummap = {'0': 'o', '1': 'l', '2': 'z', '5': 's', '9': 'g'}  # 1=>I ?
    content = ''.join([nummap[c] if c in nummap else c for c in list(content)])
    content = re.sub(r"[\u0080-\uffff]", ' ', content)  # remove Unicode
    content = re.sub(r"[^A-Za-z0-9]", ' ', content)  # letter/digit-only
    content = re.sub(r"\s+", ' ', content)
    words = content.split()

    # initialize trigger list
    # triggers_o = b"DfU.TAp%U!/8]<IBOu3rF^o2<GB@FJCi*cmD_,gDAnNZ9BPDQ>@WcL'F(f90/9>K=FDu/>F=_BBDJ=/C@s)[2"
    triggers_o = b'DfU.TAp%U!/8]<IBOu3rF^o2<Df\'*!/9>K=F=^mDCi"0+BlknIBPDR-Df^"OE+Np$F"CgDDKG'
    triggers = {}
    for trigger in base64.a85decode(triggers_o).decode('utf-8').split(','):
        triggers[dedup(trigger)] = trigger
    for trigger in triggers.keys():
        for (key, value) in triggers.items():
            if trigger != key and trigger in value:
                triggers[key] = trigger
    for key in triggers.keys():
        if 'f' in triggers[key][1:]:
            triggers[key] = triggers[key].replace('f', '*')
        elif triggers[key][0] not in "aeiou":
            triggers[key] = re.sub(r"[aeiou]", '*', triggers[key], count=1)

    # detect triggers
    keywords = {}
    for word in words:
        word = dedup(word)
        for trigger in triggers:
            index = word.find(trigger)
            if index == -1:
                continue
            if (word[:index] in PREFICES or
                word[:index+1] in PREFICES) and \
                    (word[index+len(trigger):] in SUFFICES or
                        word[index+len(trigger)-1:] in SUFFICES):
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
    keywords = ', '.join(list(keywords.values()))

    # apply trigger
    if isinstance(message, str):
        print(content)
        print(keywords)
        return
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
    embed.add_field(name="Trigger"+'s'*(keywords.count(',') > 0),
                    value=keywords.replace('*', '\\*'),
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
    detect_trigger(
        "Let's reorz the orzing orzness of orziful Moana! "
        "Orz! Õȑż! Οɍɀ! 〇rz! ０ｒｚ！ e⁻ᶴᵒʳᶻ⁽ˣ⁾ᵈˣ!")
