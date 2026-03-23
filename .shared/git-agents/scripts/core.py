#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git Agents Skill Core - BM25 search engine for Git best practices and commands
"""

import csv
import re
from pathlib import Path
from math import log
from collections import defaultdict

# ============ CONFIGURATION ============
DATA_DIR = Path(__file__).parent.parent / "data"
MAX_RESULTS = 3

CSV_CONFIG = {
    "commits": {
        "file": "commits.csv",
        "search_cols": ["Command Name", "Keywords", "Description", "When to Use"],
        "output_cols": [
            "Command Name",
            "Keywords",
            "Description",
            "When to Use",
            "Command Example",
            "Gotchas",
            "Docs URL",
        ],
    },
    "branching": {
        "file": "branching.csv",
        "search_cols": ["Command Name", "Keywords", "Description", "When to Use"],
        "output_cols": [
            "Command Name",
            "Keywords",
            "Description",
            "When to Use",
            "Command Example",
            "Gotchas",
            "Docs URL",
        ],
    },
    "merging": {
        "file": "merging.csv",
        "search_cols": ["Command Name", "Keywords", "Description", "When to Use"],
        "output_cols": [
            "Command Name",
            "Keywords",
            "Description",
            "When to Use",
            "Command Example",
            "Gotchas",
            "Docs URL",
        ],
    },
    "history": {
        "file": "history.csv",
        "search_cols": ["Command Name", "Keywords", "Description", "When to Use"],
        "output_cols": [
            "Command Name",
            "Keywords",
            "Description",
            "When to Use",
            "Command Example",
            "Gotchas",
            "Docs URL",
        ],
    },
    "remotes": {
        "file": "remotes.csv",
        "search_cols": ["Command Name", "Keywords", "Description", "When to Use"],
        "output_cols": [
            "Command Name",
            "Keywords",
            "Description",
            "When to Use",
            "Command Example",
            "Gotchas",
            "Docs URL",
        ],
    },
    "hooks": {
        "file": "hooks.csv",
        "search_cols": ["Hook Name", "Keywords", "Description", "When to Use"],
        "output_cols": [
            "Hook Name",
            "Keywords",
            "Description",
            "When to Use",
            "Command Example",
            "Gotchas",
            "Docs URL",
        ],
    },
    "debugging": {
        "file": "debugging.csv",
        "search_cols": ["Command Name", "Keywords", "Description", "When to Use"],
        "output_cols": [
            "Command Name",
            "Keywords",
            "Description",
            "When to Use",
            "Command Example",
            "Gotchas",
            "Docs URL",
        ],
    },
    "workflows": {
        "file": "workflows.csv",
        "search_cols": ["Workflow Name", "Keywords", "Description", "When to Use"],
        "output_cols": [
            "Workflow Name",
            "Keywords",
            "Description",
            "When to Use",
            "Command Example",
            "Gotchas",
            "Docs URL",
        ],
    },
}


# ============ BM25 IMPLEMENTATION ============
class BM25:
    """BM25 ranking algorithm for text search"""

    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.doc_lengths = []
        self.avgdl = 0
        self.idf = {}
        self.doc_freqs = defaultdict(int)
        self.N = 0

    def tokenize(self, text):
        """Lowercase, split, remove punctuation, filter short words"""
        text = re.sub(r"[^\w\s]", " ", str(text).lower())
        return [w for w in text.split() if len(w) > 2]

    def fit(self, documents):
        """Build BM25 index from documents"""
        self.corpus = [self.tokenize(doc) for doc in documents]
        self.N = len(self.corpus)
        if self.N == 0:
            return
        self.doc_lengths = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_lengths) / self.N

        for doc in self.corpus:
            seen = set()
            for word in doc:
                if word not in seen:
                    self.doc_freqs[word] += 1
                    seen.add(word)

        for word, freq in self.doc_freqs.items():
            self.idf[word] = log((self.N - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query):
        """Score all documents against query"""
        query_tokens = self.tokenize(query)
        scores = []

        for idx, doc in enumerate(self.corpus):
            score = 0
            doc_len = self.doc_lengths[idx]
            term_freqs = defaultdict(int)
            for word in doc:
                term_freqs[word] += 1

            for token in query_tokens:
                if token in self.idf:
                    tf = term_freqs[token]
                    idf = self.idf[token]
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (
                        1 - self.b + self.b * doc_len / self.avgdl
                    )
                    score += idf * numerator / denominator

            scores.append((idx, score))

        return sorted(scores, key=lambda x: x[1], reverse=True)


# ============ SEARCH FUNCTIONS ============
def _load_csv(filepath):
    """Load CSV and return list of dicts"""
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _search_csv(filepath, search_cols, output_cols, query, max_results):
    """Core search function using BM25"""
    if not filepath.exists():
        return []

    data = _load_csv(filepath)
    documents = [" ".join(str(row.get(col, "")) for col in search_cols) for row in data]

    bm25 = BM25()
    bm25.fit(documents)
    ranked = bm25.score(query)

    results = []
    for idx, score in ranked[:max_results]:
        if score > 0:
            row = data[idx]
            results.append({col: row.get(col, "") for col in output_cols if col in row})

    return results


def detect_domain(query):
    """Auto-detect the most relevant domain from query"""
    query_lower = query.lower()

    domain_keywords = {
        "commits": [
            "commit",
            "message",
            "amend",
            "squash",
            "sign",
            "conventional",
            "fixup",
            "reword",
            "gpg",
        ],
        "branching": [
            "branch",
            "checkout",
            "switch",
            "create",
            "delete",
            "rename",
            "protect",
            "strategy",
            "naming",
        ],
        "merging": [
            "merge",
            "rebase",
            "conflict",
            "squash",
            "fast-forward",
            "cherry-pick",
            "integrate",
        ],
        "history": [
            "log",
            "blame",
            "bisect",
            "reflog",
            "history",
            "search",
            "grep",
            "find",
            "diff",
            "show",
        ],
        "remotes": [
            "remote",
            "push",
            "pull",
            "fetch",
            "clone",
            "fork",
            "upstream",
            "origin",
            "track",
            "pr",
        ],
        "hooks": [
            "hook",
            "pre-commit",
            "pre-push",
            "commit-msg",
            "husky",
            "lefthook",
            "automation",
            "lint",
        ],
        "debugging": [
            "debug",
            "stash",
            "patch",
            "recover",
            "reset",
            "revert",
            "undo",
            "lost",
            "restore",
            "clean",
        ],
        "workflows": [
            "workflow",
            "gitflow",
            "trunk",
            "release",
            "tag",
            "version",
            "ci",
            "pipeline",
            "deploy",
        ],
    }

    scores = {
        domain: sum(1 for kw in keywords if kw in query_lower)
        for domain, keywords in domain_keywords.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "commits"


def search(query, domain=None, max_results=MAX_RESULTS):
    """Main search function with auto-domain detection"""
    if domain is None:
        domain = detect_domain(query)

    config = CSV_CONFIG.get(domain, CSV_CONFIG["commits"])
    filepath = DATA_DIR / config["file"]

    if not filepath.exists():
        return {"error": f"File not found: {filepath}", "domain": domain}

    results = _search_csv(
        filepath, config["search_cols"], config["output_cols"], query, max_results
    )

    return {
        "domain": domain,
        "query": query,
        "file": config["file"],
        "count": len(results),
        "results": results,
    }
