import discord
import re
import requests
import bs4


def generate_count_dict(splitted, min_length, phrase_length, joiner):
    """Count the frequency of words/phrases from a list of words
        min_length: ignore phrases with words that has a char count less than this
        phrase_length: number of words in a phrase
        joiner: what to use to join the words to phrases
    """
    n_words = len(splitted)
    words = {}
    if n_words < phrase_length:
        return words
    tooshort_count = 0
    splitted.append('')
    for i in range(phrase_length):
        tooshort_count += int(len(splitted[i]) < min_length)
    for i in range(n_words-phrase_length+1):
        if tooshort_count == 0:
            word = splitted[i:i+phrase_length]
            word = joiner.join(word)
            if word in words:
                words[word] += 1
            else:
                words[word] = 1
        tooshort_count += int(len(splitted[i+phrase_length]) < min_length)
        tooshort_count -= int(len(splitted[i]) < min_length)
    return words


def count_words(s, min_length, phrase_length):
    """For English text"""
    s = s.lower()
    s = s.replace('’', "'")
    s = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿĀ-ɏΑ-ӿ']+", " ", s)
    s = s.strip().split(' ')
    s = [t.strip("'") for t in s]
    return generate_count_dict(s, min_length, phrase_length, ' ')


def count_identifiers(s, min_length, phrase_length):
    """For source code"""
    s = re.sub(r"[^_A-Za-z0-9À-ÖØ-öø-ÿĀ-ɏΑ-ӿ]+", " ", s)
    s = s.strip().split(' ')
    return generate_count_dict(s, min_length, phrase_length, ' ')


def count_characters(s, min_length, phrase_length):
    """Count individual characters"""
    # s = re.sub(r"\s+", "", s)
    s = list(s)
    return generate_count_dict(s, 1, phrase_length, '')


def stats_words(words, num_words):
    """Take a word dictionary, generate stats text"""

    ws = sorted(list(words))
    fs = [words[w] for w in ws]
    word_count = sum(fs)

    words = list(zip(ws, fs))
    words.sort(key=lambda x: -x[1])
    words = words[:num_words]

    lines = [
        ['', 'freq', 'rel'],
        ['----', '----', '----']]
    maxl = [1, 1, 1]
    for word in words:
        line = [word[0], str(word[1]), "{:.3g}%".format(
            100.*word[1]/word_count)]
        for i in range(3):
            maxl[i] = max(maxl[i], len(line[i]))
        lines.append(line)
    req_l = [l+4 for l in maxl]
    for li in range(len(lines)):
        line = lines[li]
        for i in range(3):
            line[i] += ' ' * (req_l[i]-len(line[i]))
        lines[li] = ''.join(line).rstrip()
    return {
        'num_words': len(words),
        'stats': '\n'.join(lines)
    }


def stats_words_url(text_url, count_fun, num_words, min_length, phrase_length):
    """Word stats entry function, receives document URL and parameters"""

    # get text
    print("Request", text_url)
    req = requests.get(
        text_url,
        headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'pragma': 'no-cache'
    },
        timeout=(10, 10))
    if req.status_code >= 400:
        raise ValueError(f"Request URL returns {req.status_code}.")
    content_type = req.headers['content-type'].lower()
    if ';' in content_type:
        content_type = content_type[:content_type.index(';')]
    text = req.content
    if content_type == "text/html":  # get HTML text
        def get_text(element):
            texts = []
            if element.name.lower() in ['head', 'style', 'script', 'noscript']:
                return texts
            for child in element.children:
                if isinstance(child, bs4.Comment):
                    continue
                elif isinstance(child, str):
                    texts.append(child.strip())
                else:
                    texts += get_text(child)
            return texts
        parsed = bs4.BeautifulSoup(text, "html.parser")
        texts = []
        title = parsed.find('title')
        if title is not None:
            texts.append(title.text)
        description = parsed.find('meta', {'name': 'description'})
        if description is not None and 'content' in description.attrs:
            texts.append(str(description.attrs['content']))
        texts += get_text(parsed)
        text = '\n'.join(texts)
        text = re.sub(r"(\r?\n)+", "\n", text).strip()
        open(".html.temp", 'w').write(text)  # for debugging
    elif isinstance(text, bytes):  # try to decode UTF-8
        try:
            text = req.content.decode('utf-8')
        except:
            raise ValueError(
                f"Error decoding response with content type `{content_type}`.")
    if not isinstance(text, str):  # not str type?
        raise ValueError(
            f"Error intepreting response with content type `{content_type}` to string.\n"
            + f"Interpreted type: {type(text)}.")

    # generate stats
    words = count_fun(text, min_length, phrase_length)
    res = stats_words(words, num_words)
    return res


def stats_words_message(message: str):
    """Parse stat prompt information from a string message and call `stats_words_url`"""
    url_regex = r"^((http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#\-\(\)]*[\w@?^=%&\/~+#\-\(\)]))$"

    # split message
    if message[0] not in ['+', '$']:
        return None
    message = message[1:].strip().split(' ')
    if len(message) < 2:
        return None
    command = message[0].lower()
    if not (('word' in command or 'code' in command or 'char' in command)
            and ('count' in command or 'stat' in command)):
        return None
    message0, message = message, []
    for seg in message0:
        seg = seg.strip('`').strip('"').strip("'")
        if seg.strip() == '':
            continue
        elif re.match(url_regex, seg):
            message.append(seg)
        else:
            subm = seg.split('=')
            for sm in subm:
                if sm.strip() != '':
                    message.append(sm)

    # get parameters from message
    count_fun = None
    url = None
    min_length = None
    phrase_length = None
    word_count = None
    for i in range(1, len(message)):
        prev = message[i-1].lower()
        cur = message[i].strip(',').strip(';').strip('.').strip("'").strip('"')
        if re.match(url_regex, cur):
            url = cur if url is None else url
            continue
        if cur.isnumeric() and not re.match(url_regex, prev):
            cur = int(cur)
            if 'min' in prev or ('char' in prev and i > 3):
                min_length = cur if min_length is None else min_length
            elif 'phras' in prev or ('word' in prev and i > 3):
                phrase_length = cur if phrase_length is None else phrase_length
            elif 'count' in prev or 'num' in prev:
                word_count = cur if word_count is None else word_count
        elif count_fun is None:
            if 'word' in cur:
                count_fun = count_words
            elif 'code' in cur or 'identi' in cur:
                count_fun = count_identifiers
            elif 'char' in cur:
                count_fun = count_characters

    # check parameters
    if url is None:
        raise ValueError("No URL detected.")
    ext = url.split('.')[-1].lower()
    if '#' in ext:
        ext = ext[:ext.index('#')]
    if '?' in ext:
        ext = ext[:ext.index('?')]
    is_source = ext in ['js', 'json', 'css', 'py', 'c', 'cpp', 'h', 'glsl']
    if count_fun is None:
        if 'char' in command:
            count_fun = count_characters
        elif 'code' in command:
            count_fun = count_identifiers
        else:
            if is_source:
                count_fun = count_identifiers
            else:
                count_fun = count_words
    if min_length is None:
        if count_fun == count_identifiers:
            min_length = 2 if is_source else 1
        else:
            min_length = 1
    if phrase_length is None:
        phrase_length = 1
    if word_count is None:
        word_count = 15
    min_length = max(min_length, 1)
    phrase_length = max(phrase_length, 1)
    if count_fun == count_characters:
        if phrase_length > 100:
            raise ValueError(
                f"Phrase length too large (max 100, currently {phrase_length}).")
    else:
        if phrase_length > 20:
            raise ValueError(
                f"Phrase length too large (max 20, currently {phrase_length}).")
    if word_count > 500:
        raise ValueError(
            f"Word count too large (max 500, currently {word_count}).")

    # generate stats and message
    stats = stats_words_url(url, count_fun, word_count,
                            min_length, phrase_length)
    num_words = stats['num_words']
    if count_fun == count_words:
        if phrase_length == 1:
            message = f"Here are the {num_words} most occurring words" + \
                f" with a minimum length of {min_length}" * (min_length != 1) + \
                ", ignoring case:"
        else:
            message = f"Here are the {num_words} most occurring {phrase_length}-word phrases" + \
                f", each word with a minimum of {min_length} letters" * (min_length != 1) + \
                ", ignoring case:"
    elif count_fun == count_identifiers:
        if phrase_length == 1:
            message = f"Here are the {num_words} most occurring identifiers with a minimum length of {min_length}:"
        else:
            message = f"Here are the {num_words} most occurring length-{phrase_length} consecutive identifier groups" + \
                f", each identifier with a minimum of {min_length} characters" * (min_length != 1) + \
                ":"
    elif count_fun == count_characters:
        message = f"Here are the {num_words} most occurring {phrase_length}-character strings (may contain whitespaces and line breaks):"
    return message, stats['stats']


async def message_main(message):
    try:
        result = stats_words_message(message.content)
        if result is None:
            return
    except BaseException as e:
        content = ":warning: " + str(e)
        await message.reply(content, mention_author=False)
        return
    content, stats = result
    if len(content) + len(stats) > 1980 or stats.count('\n')-1 > 30 or "```" in stats:
        with open('.temp', 'w') as fp:
            fp.write(stats)
        await message.reply(
            content, mention_author=False,
            file=discord.File(".temp", "word_count.txt"))
    else:
        content = content + "\n```\n" + stats + "\n```"
        await message.reply(content, mention_author=False)


if __name__ == "__main__":
    # try some examples!
    examples = [
        "+word-stats https://en.wikipedia.org/wiki/Human count=10 min-length=2 phrase-length=2",
        "+char-stats https://en.wikipedia.org/wiki/Human count=20",
        "+word-stats https://harry7557558.github.io/desmos/graphs/z7zooq9zsh.json",
        "+word-stats https://harry7557558.github.io/desmos/graphs/z7zooq9zsh.json words",
        "+word-stats https://harry7557558.github.io/desmos/graphs/z7zooq9zsh.json chars phrase-length=32",
        "+word-stats https://harry7557558.github.io/shadertoy/shaders.json",
        "+word-stats https://www.gutenberg.org/files/10/10-h/10-h.htm identifier min-length=1 count=20",
        "+char-stats https://docs.google.com/document/d/1B7MUQFnMzgEBi-z0o2QsG-hHXcAOOsIbx4dPGrtVTNM/mobilebasic word count=500"
    ]
    command = examples[0]
    message, stats = stats_words_message(command)
    print(message)
    print(stats)
