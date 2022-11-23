"""
Model:
Find the most frequent N substrings with a maximum length of S
(including leading and trailing whitespaces).
Assign each substring a weight dot the weight with number of
substring occurrences to get the number of syllables.
Training: least squares fitting (linear)
"""

S, N = 4, 20000
#S, N = 3, 2000


import numpy as np
import scipy.sparse.linalg
import scipy.sparse
import scipy.optimize

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


def word_substrings(word):
    subs = []
    for s in range(1, S+1):
        for i in range(0, len(word)-s+1):
            ss = word[i:i+s]
            subs.append(ss)
        if s == 1:
            word = ' ' + word + ' '
    return subs


def get_top_substrings(words):
    counts = {}
    for word in words:
        subs = word_substrings(word)
        for ss in subs:
            if ss not in counts:
                counts[ss] = 0
            counts[ss] += 1
    counts = sorted(list(counts.items()),
                    key=lambda p: (-p[1], p[0]))
    res = {}
    for i in range(N):
        ss = counts[i][0]
        res[ss] = i
    return res


def solve_c(words, substrs):
    ii, ij, iv = [], [], []
    b = []
    for i in range(len(words)):
        word = words[i]
        subs = word_substrings(word)
        for ss in subs:
            if ss not in substrs:
                continue
            ii.append(i)
            ij.append(substrs[ss])
            iv.append(1)
        ii += [i] * 2
        ij += [N, N+1]
        iv += [len(word), 1]
        b.append(data[word])
    A = scipy.sparse.csr_matrix((iv, (ii, ij)),
                                shape=(len(words), N+2))
    print(A.shape, "matrix,",
          len(set(zip(ii, ij))), "nonzero elements")
    if True:
        x, istop, itn, r1norm = scipy.sparse.linalg.lsqr(
            A, b, atol=1e-4, btol=1e-3, show=True)[:4]
    else:
        def fun(x, info):
            y = A @ x - b
            m = np.dot(y, y)
            g = 2.0 * A.T @ y
            info['Nfeval'] += 1
            if info['Nfeval'] % 10 == 0:
                print(info['Nfeval'], np.sqrt(m)/len(words)**0.5)
            return (m, g)
        optres = scipy.optimize.minimize(
            fun, np.zeros(N+2), jac=True, method='L-BFGS-B',
            args=({'Nfeval':0},),
            options={'maxcor': 100, 'ftol': 1e-5, 'gtol': 1e-4})
        r1norm = np.sqrt(optres.fun)
        x = optres.x
    print("loss:", r1norm/len(words)**0.5)
    return x


def eval_c(c, substrs, word):
    word = clean_word(word)
    subs = word_substrings(word)
    ans = c[-2]*len(word)+c[-1]
    for ss in subs:
        if ss in substrs:
            ans += c[substrs[ss]]
    return ans

def test_c(c, substrs, words):
    t1 = perf_counter()
    corrects = [lookup(w) for w in words]
    t2 = perf_counter()
    k = 100000/len(test)
    print("Lookup: {:.2f} secs per 100000 words".format(k*(t2-t1)))

    t1 = perf_counter()
    guesses = [round(eval_c(c, substrs, w)) for w in words]
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

    #train = words[10000:20000]
    train = words[:]
    test = words[:10000]

    t1 = perf_counter()
    substrs = get_top_substrings(train)
    t2 = perf_counter()
    print("Substrings in {:.2f} secs".format(t2-t1))

    t1 = perf_counter()
    c = solve_c(train, substrs)
    c = c.astype(np.float32)
    t2 = perf_counter()
    print("Trained in {:.2f} secs".format(t2-t1))

    test_c(c.tolist(), substrs, test)
    open("freqs_substrs.txt", "w").write(','.join(substrs))
    c.tofile("freqs_weights.bin")

