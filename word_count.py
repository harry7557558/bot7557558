import discord
import re
import requests
import bs4
import unicodedata
import struct


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


def init_syllable_counter():
    global syllable_weights, syllable_cached
    global syllable_weights_m, syllable_weights_b
    substrs = open(
        "scripts/syllable_count/freqs_substrs.txt").read().split(',')
    weights = open("scripts/syllable_count/freqs_weights.bin", 'rb').read()
    weights = list(struct.unpack('<'+"f"*(len(weights)//4), weights))
    assert len(substrs)+2 == len(weights)
    syllable_weights = dict(zip(substrs, weights))
    syllable_cached = {}
    syllable_weights_m = weights[-2]
    syllable_weights_b = weights[-1]


def count_word_syllables(word) -> float:
    """Estimate the number of syllables in an English word
        Assumes `word` consists of only lowercase English letters"""
    if word in syllable_cached:
        return syllable_cached[word]
    total = syllable_weights_m * len(word) + syllable_weights_b
    for s in range(1, 4+1):
        for i in range(0, len(word)-s+1):
            ss = word[i:i+s]
            if ss in syllable_weights:
                total += syllable_weights[ss]
        if s == 1:
            word = ' ' + word + ' '
    syllable_cached[word] = total
    return total


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


def replace_special_characters(s: str) -> str:
    s = s.replace("“", '"').replace(
        "”", '"').replace("‘", "'").replace("’", "'")
    s = re.sub(r"[˗‐‑–﹘—]", '-', s)
    return s


def get_text_from_url(text_url: str):
    """Retrieves text from an URL
        Returns a tuple of plain text and the response header"""
    # replace URL
    if '#' in text_url:
        text_url = text_url[:text_url.find('#')]
    if '://docs.google.com/document/d/' in text_url:
        text_url = text_url.split('/')
        if text_url[-1] in ['', 'edit', 'preview']:
            text_url[-1] = 'mobilebasic'
        text_url = '/'.join(text_url)

    # get URL
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
    if 'content-encoding' not in req.headers:
        req.encoding = 'utf-8'
    if ';' in content_type:
        content_type = content_type[:content_type.index(';')]
    text = req.content

    # get HTML text
    if content_type == "text/html":
        def get_text(element):
            texts = ['']
            if element.name.lower() in ['head', 'style', 'script', 'noscript', 'math']:
                return texts
            stick = False

            def add_text(texts1):
                nonlocal texts
                if not stick or len(texts) == 0 or len(texts1) == 0:
                    texts += texts1
                else:
                    texts = texts[:-1] + [texts[-1]+' '+texts1[0]] + texts1[1:]
            for child in element.children:
                if isinstance(child, bs4.Comment):
                    continue
                elif isinstance(child, str):
                    add_text([child.strip().replace(
                        '\r\n', '\n').replace('\n', ' ')])
                    stick = True
                else:
                    text_child = get_text(child)
                    if child.name.lower() in ['a', 'abbr', 'b', 'code', 'del', 'em', 'i',
                                              's', 'span', 'sub', 'sup', 'u', 'math']:
                        add_text(text_child)
                        stick = True
                    else:
                        add_text(text_child)
                        stick = False
            if len(texts) > 0 and texts[0].strip() == '':
                texts = texts[1:]
            return texts
        parsed = bs4.BeautifulSoup(text, "html.parser")
        texts = []
        title = parsed.find('title')
        if title is not None:
            texts.append(title.text)
        description = parsed.find('meta', {'name': 'description'})
        if description is not None and 'content' in description.attrs:
            description = str(description.attrs['content']).strip()
        else:
            description = ""
        texts += get_text(parsed.find('body'))
        texts = [line.strip() for line in texts]
        if len(description) > 1000 or description not in texts:
            texts.append(description)
        text = '\n'.join(texts)
        text = re.sub(r"(\r?\n)+", "\n", text).strip()

    # try to decode UTF-8
    elif isinstance(text, bytes):
        try:
            text = req.content.decode('utf-8')
        except:
            raise ValueError(
                f"Error decoding response with content type `{content_type}`.")
    if not isinstance(text, str):  # not str type?
        raise ValueError(
            f"Error intepreting response with content type `{content_type}` to string.\n"
            + f"Interpreted type: {type(text)}.")
    text = replace_special_characters(text)

    # handle txt e-book alike line break
    if content_type == "text/plain":
        text = text.replace('\r\n', '\n').split('\n')
        texts = []
        capture = False
        long_line = False
        for line in text:
            line = line.strip()
            if line == '':
                capture = False
                continue
            if (capture and line[0].islower()) or \
                    (long_line and len(line) > 32):
                texts[-1] += ' ' + line
            else:
                texts.append(line)
            capture = line[-1].islower() or line[-1] in ",:'\"-)"
            long_line = len(line) > 48
        text = '\n'.join(texts)

    open(".html.temp", 'w').write(text)  # for debugging
    return text, req.headers


def is_wanted_html(line):
    """Test if a line from an HTML is wanted for readability check"""
    s = line.strip()
    s = re.sub(r"[a-z]", 'a', s)
    s = re.sub(r"[A-Z]", 'A', s)
    s = re.sub(r"[0-9]", '0', s)
    s = re.sub(r"\s", ' ', s)
    weights = {' ': -0.0085, '!': 1.8875, '"': 0.9782, '$': -0.1644, '&': 0.5831,
               "'": -0.6959, '(': -0.0929, ')': -0.0961, '*': 0.428, '+': -0.2615,
               ',': 0.0972, '-': 0.4882, '.': 0.3976, '/': 0.0095, '0': -0.3535,
               ':': -0.1494, ';': 0.5223, '<': 0.3736, '=': 0.2193, '>': -2.1398,
               '?': 3.2519, 'A': -0.3841, '[': 0.2734, '\\': -0.1707, ']': 0.5493,
               '^': 0.7976, '_': -0.6222, 'a': 0.0509, '{': 0.0975, '}': -0.1276}
    total = -1.2
    for c in s:
        if c in weights:
            total += weights[c]
    return total > 0.0


def flesch_kincaid_readability(text, is_html=False):
    """Returns (num_sentences, num_words, num_unique_words,
                grade_level, readability_level)
    """
    try:
        syllable_weights
        syllable_cached
    except:
        init_syllable_counter()
    if is_html:
        text = text.split('\n')
        text = [s for s in text if is_wanted_html(s)]
        text = '\n'.join(text)
    text = re.sub(r"[\.\!\?\;]", '.', text)  # sentence terminator
    text = ''.join([c for c in unicodedata.normalize('NFKD', text)
                    if unicodedata.category(c) != 'Mn'])  # remove accents
    text = re.sub(r"[\"']", '', text)
    text = ''.join([c if ord('a') <= ord(c) <= ord('z') or c in '.\n' else ' '
                    for c in text.lower()])  # letters only
    text = re.sub(r"\s*?\n\s*", '\n', text.strip())  # line separators
    sentences = []
    short_words = set(['a', 'i', 'am', 'an', 'as', 'at', 'by', 'if', 'in', 'is', 'it',
                       'me', 'my', 'of', 'or', 'so', 'to', 'up', 'us', 'we'])
    for line in text.split('\n'):
        line = re.sub(r"\s+", ' ', line.strip())
        line = [s.strip() for s in line.split('.')]
        for sentence in line:
            sentence = [w for w in sentence.split(' ') if w != '']
            word_count = len(
                [w for w in sentence if len(w) > 2 or w in short_words])
            if word_count > 2:  # hard constraint
                sentences.append(sentence)

    sentence_words = [len(s) for s in sentences]
    open(".fkstrip.temp", 'w').write(
        '\n'.join([' '.join(ws) for ws in sentences]))
    if len(sentence_words) == 0:
        return None
    if False:
        sx2 = sum([x**2 for x in sentence_words])
        sx = sum(sentence_words)
        n = len(sentence_words)
        print(sx/n, ((sx2-sx**2/n)/(n-1))**0.5, sorted(sentence_words)[n//2])
        import matplotlib.pyplot as plt
        plt.hist(sentence_words, bins=20)
        plt.gca().set_yscale("log")  # pretty linear
        plt.show()
    mean_sentence_words = sum(sentence_words) / len(sentence_words)

    words = []
    for ws in sentences:
        words.extend(ws)
    total_words = len(words)
    total_syllables = sum([count_word_syllables(w) for w in words])
    mean_word_syllables = total_syllables / total_words

    grade = 0.39 * mean_sentence_words + 11.8 * mean_word_syllables - 15.59
    level = 206.835 - 1.015 * mean_sentence_words - 84.6 * mean_word_syllables
    print("Readability (mw, ms, grade, level):",
          mean_sentence_words, mean_word_syllables, grade, level)
    # print(grade, level)
    grade = f"Grade {round(grade)}"
    level = "Preschool" if level > 100 else \
            "Very easy" if level > 90 else \
        "Easy" if level > 80 else \
        "Fairly easy" if level > 70 else \
        "Plain" if level > 60 else \
        "Fairly difficult" if level > 50 else \
        "Difficult" if level > 30 else \
        "Very difficult" if level > 10 else \
        "Extremely difficult"
    return (len(sentences), len(words), len(set(words)), grade, level)


def stats_words_url(text_url, count_fun, num_words, min_length, phrase_length):
    """Word stats entry function, receives document URL and parameters"""
    text, headers = get_text_from_url(text_url)
    words = count_fun(text, min_length, phrase_length)
    res = stats_words(words, num_words)
    if count_fun == count_words and num_words <= 15 and phrase_length == 1:
        fk = flesch_kincaid_readability(
            text,
            headers['content-type'].lower().startswith("text/html"))
        if fk is not None:
            res['readability'] = fk
    return res


def stats_words_message(message: str):
    """Parse stat prompt information from a string message and call `stats_words_url`"""
    url_regex = r"^((http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#\-\(\)]*[\w@?^=%&\/~+#\-\(\)]))$"

    # split message
    if message[0] not in ['+', '$']:
        return None
    if '\n' in message:
        message = message[:message.find('\n')]
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
        description = "Count the frequency of words/phrases/characters/strings in a document."
        if 'help' not in (' '.join(message)).lower():
            raise ValueError(
                "No URL detected. Type `+word-stats help` for examples of this command.")
        return description, """
+[word-stats|char-stats] [url] [type] [count=] [min-length=] [phrase-length=]
    @url: the URL to the document, must be `http` or `https`
    @type: [word|code|char], respectively for English words, source code (identifiers), and character strings. If not specified, the program will automatically detect it from the command and the URL extension.
    @count: the maximum number of items in the display list, default 15
    @min-length: minimum required length for the word/identifier, default 1 for word and 2 for identifier
    @phrase-length: the length of the phrase or string, default 1
""".strip(), "For English words with default parameters, readability information are calculated. Note that sentence count, word count, and Flesch-Kincaid readability measures are calculated independent of word statistics, and HTML contents that the program deemed to be not representing the readability may be stripped."
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
    if 'readability' in stats:
        ns, nw, nuw, grade, level = stats['readability']
        fk = "   •   ".join([
            f"{ns} sentence" + 's'*(ns != 1),
            f"{nw} word{'s'*(nw != 1)} ({nuw} unique)",
            f"Reading level: {grade}",
            f"Reading ease: {level}"
        ])
        return message, stats['stats'], fk
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
    if len(result) == 2:
        result = (result[0], result[1], '')
    content, stats, fk = result
    if len(content) + len(stats) + len(fk) > 1980 or \
            stats.count('\n')-1 > 30 or "```" in stats:
        with open('.temp', 'w') as fp:
            fp.write(stats)
        await message.reply(
            content, mention_author=False,
            file=discord.File(".temp", "word_count.txt"))
    else:
        content = content + "\n```\n" + stats + "\n```" + fk
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
        "+char-stats https://docs.google.com/document/d/1B7MUQFnMzgEBi-z0o2QsG-hHXcAOOsIbx4dPGrtVTNM/mobilebasic word count=500",
        "+word-stats https://lit.harry7557558.repl.co/amsnd.html"
    ]
    command = examples[3]
    testUrls = [
        # difficult to read
        "https://discord.com/terms",
        "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8025698/",
        # intentionally written for extreme reading difficulty
        "https://docs.google.com/document/d/1lEulxtrdUULsor7Mjg0I__7pnMB8yAFqLwvPOfzfMRU/edit",
        # extremely easy to read (or not?)
        "https://www.site.uottawa.ca/~lucia/courses/2131-02/A2/trythemsource.txt",
        # increasing reading difficulty
        "https://movies.fandom.com/wiki/Frozen_(2013)/Transcript",
        "https://frozen.fandom.com/wiki/Elsa",
        "https://en.m.wikipedia.org/wiki/Elsa_(Frozen)",
        "https://dsq-sds.org/article/download/5310/4648",
        # expect the same results for each pair
        # nautilus, frankenstein, peter pan, don quixote
        "https://www.gutenberg.org/cache/epub/164/pg164-images.html",
        "https://www.gutenberg.org/cache/epub/164/pg164.txt",
        "https://www.gutenberg.org/cache/epub/84/pg84-images.html",
        "https://www.gutenberg.org/cache/epub/84/pg84.txt",
        "https://www.gutenberg.org/cache/epub/16/pg16-images.html",
        "https://www.gutenberg.org/files/16/16-0.txt",
        "https://www.gutenberg.org/cache/epub/996/pg996-images.html",
        "https://www.gutenberg.org/cache/epub/996/pg996.txt",
        # math/figure heavy
        "https://pbr-book.org/3ed-2018/Reflection_Models/Microfacet_Models",
        "https://jamie-wong.com/2016/08/05/webgl-fluid-simulation/",
        "https://en.wikipedia.org/wiki/Bending_of_plates",
        # code heavy
        "https://pytorch.org/docs/stable/generated/torch.nn.BCELoss.html",
        "https://stackoverflow.com/questions/18364193/requests-disable-auto-decoding",
        "https://math.stackexchange.com/questions/1471825/derivative-of-the-inverse-of-a-matrix",
    ]
    command = "+word-stats " + testUrls[0]

    res = stats_words_message(command)
    if len(res) == 3:
        message, stats, fk = res
    else:
        message, stats, fk = res[0], res[1], ""
    print(message)
    print(stats)
    print(fk)
