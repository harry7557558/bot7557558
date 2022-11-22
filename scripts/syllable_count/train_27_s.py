"""
Model:
Generate substrings with length S
(including leading and trailing whitespaces).
Total 27 possible characters, 27^S possible substrings.
Assign each substring a weight dot the weight with number of
substring occurrences to get the number of syllables.
Training: least squares fitting (linear)
"""

import numpy as np
import scipy.sparse.linalg
import scipy.sparse

import random
random.seed(0)

from time import perf_counter

from load_train_data import clean_word, load_data

data = load_data()

def lookup(word):
    word = clean_word(word)
    if word in data:
        return data[word]
    return 0


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
        b.append(data[word])
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
    t1 = perf_counter()
    corrects = [lookup(w) for w in words]
    t2 = perf_counter()
    k = 100000/len(test)
    print("Lookup: {:.2f} secs per 100000 words".format(k*(t2-t1)))

    t1 = perf_counter()
    guesses = [round(eval_c(c, w)) for w in words]
    t2 = perf_counter()
    print("Trained: {:.2f} secs per 100000 words".format(k*(t2-t1)))
    
    correct_count = 0
    for (correct, guess) in zip(corrects, guesses):
        correct_count += int(correct == guess)
    print(f"{correct_count}/{len(words)} correct")
    print("{:.1f}% accuracy".format(correct_count/len(words)*100))


if __name__ == "__main__":

    words = list(data.keys())
    random.shuffle(words)

    train = words[10000:]  # 94.9%
    train = words[:]  # 95.6%
    test = words[:10000]

    t1 = perf_counter()
    c = solve_c(train)
    c = c.astype(np.float32)
    t2 = perf_counter()
    print("Trained in {:.2f} secs".format(t2-t1))

    test_c(c.tolist(), test)

    c.tofile(f'weights_27_{S}.bin')
