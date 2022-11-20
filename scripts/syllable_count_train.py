import requests

import numpy as np
import scipy.sparse.linalg
import scipy.sparse

import random
random.seed(0)


def clean_word(word):
    word = word.lower()
    word = ''.join([c for c in word if c.isalpha()])
    return word

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

prons = load_prons()
phones = load_phones()


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


S = 3

def map_char(c):
    if ord('a') <= ord(c) <= ord('z'):
        return ord(c) - ord('a') + 1
    return 0

def map_chars(cs):
    ans = 0
    for c in cs:
        ans = 27*ans + map_char(c)
    return ans

def word_to_seq(word):
    eles = []
    for i in range(-S+1, len(word)):
        s = ' '*max(-i,0) + word[max(i,0):min(i+S,len(word))] + ' '*max(i+S-len(word),0)
        eles.append(map_chars(s))
    return eles

def solve_c(words):
    ii, ij, iv = [], [], []
    b = []
    for i in range(len(words)):
        word = words[i]
        js = word_to_seq(word)
        ii += [i] * (len(js)+2)
        ij += js + [27**S, 27**S+1]
        iv += [1] * len(js) + [len(word), 1]
        b.append(count_word_syllables(word))
    A = scipy.sparse.csr_matrix((iv, (ii, ij)),
                                shape=(len(words), 27**S+2))
    print(A.shape, "matrix,",
          len(set(zip(ii, ij))), "nonzero elements")
    x, istop, itn, r1norm = scipy.sparse.linalg.lsqr(A, b)[:4]
    print("loss:", r1norm/len(words)**0.5)
    return x

def eval_c(c, word):
    word = clean_word(word)
    eles = word_to_seq(word)
    ans = c[-2]*len(word)+c[-1]
    for i in eles:
        ans += c[i]
    return ans

def test_c(c, words):
    correct_count = 0
    for word in words:
        x = round(eval_c(c, word))
        if x == count_word_syllables(word):
            correct_count += 1
    print(f"{correct_count}/{len(words)} correct")
    print("{:.1f}%".format(correct_count/len(words)*100))


if __name__ == "__main__":

    words = list(prons.keys())
    random.shuffle(words)

    train = words[10000:]  # 94.9%
    train = words[:]  # 95.6%
    test = words[:10000]

    c = solve_c(train)
    c = c.astype(np.float32)

    test_c(c, test)

    c.tofile('syllable_count_weights.bin')
