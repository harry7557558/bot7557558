import requests

def clean_word(word):
    return ''.join([c for c in word.lower() if c.isalpha()])

def load_prons():
    req = requests.get("http://svn.code.sf.net/p/cmusphinx/code/trunk/cmudict/cmudict-0.7b")
    content = req.text
    res = {}
    for line in content.strip().split('\n'):
        if line.startswith(';;;'):
            continue
        assert '  ' in line
        line = line.split('  ')
        res[clean_word(line[0])] = line[1].split()
    print(f"Loaded the pronounciation of {len(res)} words.")
    return res

def load_phones():
    req = requests.get("http://svn.code.sf.net/p/cmusphinx/code/trunk/cmudict/cmudict-0.7b.phones")
    content = req.text
    res = {}
    for line in content.strip().split('\n'):
        name, type = line.split('\t')
        res[name] = type
    print(f"Loaded {len(res)} phones.")
    return res


def count_word_vowels(word):
    word = clean_word(word)
    if word not in prons:
        return 0
    count = 0
    for s in prons[word]:
        s = s[:2]
        assert s in phones
        count += int(phones[s] == 'vowel')
    return count

def count_word_syllables(word):
    word = clean_word(word)
    if word not in prons:
        return 0
    count = 0
    prevs = None
    for s in prons[word]:
        s = s[:2]
        assert s in phones
        if prevs is None:
            count += int(phones[s] == 'vowel')
        else:
            count += int(phones[s] == 'vowel' and phones[prevs] != 'vowel')
        prevs = s
    return count


def load_data():
    """load from file"""
    content = open("data.txt", "r").read()
    content = content.strip().split('\n')
    res = {}
    for pair in content:
        word, count = pair.split()
        res[word] = int(count)
    return res


if __name__ == "__main__":
    """generate file"""
    prons = load_prons()
    phones = load_phones()

    words = ""
    for word in prons:
        count = count_word_syllables(word)
        words += f"{word} {count}\n"
    open("data.txt", "w").write(words)

