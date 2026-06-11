# -*- coding: utf-8 -*-
"""
Generate the consolidated chapter view (17 chapters) from the 88 lesson files.

Non-destructive: reads lessons/lesson-NN.html, writes lessons/chapter-NN.html and
lessons/chapters.html. Original lessons are never modified.

Cleaning guarantees
-------------------
* Block-coverage assertion: the lesson body is tokenized into top-level blocks
  (<p>/<h2>/<h3>/<ul>); we assert the blocks cover every non-whitespace byte, so
  nothing can be silently dropped or duplicated.
* Image invariant: the count of ../images/ references in the cleaned section must
  equal the count in the source body (boilerplate carries no images), so no image
  is ever lost in the merge.

Only per-video boilerplate is removed: the greeting (こんにちは / みなさん),
the "Link:" line, leading "Last week…" recaps, and trailing sign-offs
("Class dismissed", "Thank you for attending", "yoroshiku onegai", "All right.",
"…next time" teasers). Cure Dolly's explanations, examples and images are verbatim.
"""
import os, re, html, glob

HERE = os.path.dirname(os.path.abspath(__file__))
LESSONS = os.path.join(HERE, "lessons")

# ---------------------------------------------------------------- raw helpers
def read(n):
    with open(os.path.join(LESSONS, "lesson-%02d.html" % n), encoding="utf-8") as f:
        return f.read()

def content_region(text):
    after_nav = text.split("</div>", 1)[1]
    return after_nav.split('<div class="cheatsheet-section">', 1)[0]

def meta(n):
    """(original lesson title, youtube url or None) for lesson n."""
    t = read(n)
    title = re.search(r"<title>(.*?)</title>", t, re.S).group(1).strip()
    m = re.search(r"youtube\.com/watch\?v(?:%3D|=)([A-Za-z0-9_-]{6,})", t)
    yt = "https://www.youtube.com/watch?v=%s" % m.group(1) if m else None
    return title, yt

# ---------------------------------------------------------------- cleaning
HR_RE = re.compile(r"<hr[^>]*>")
BLOCK_RE = re.compile(r"<(p|h1|h2|h3|h4|ul|ol|table|blockquote)\b[^>]*>.*?</\1>", re.S)
EMPTY_HEADING_RE = re.compile(r"<h[1-4][^>]*>\s*(?:<span[^>]*>\s*</span>\s*)*</h[1-4]>")
KONNICHIWA = "&#12371;&#12435;&#12395;&#12385;&#12399;"          # こんにちは
MINASAN = "&#12415;&#12394;&#12373;&#12435;"                     # みなさん
PREFIX_RE = re.compile(
    r"(\A\s*<p[^>]*>\s*<span[^>]*>)\s*(?:%s(?:&#12289;|、)?\s*)?%s\s*(?:\.|&#12290;|。)?\s*"
    % (re.escape(MINASAN), re.escape(KONNICHIWA)))

GREET_ONLY = re.compile(r"^(?:みなさん[、,]?\s*)?こんにちは\s*[.。]?$")
RECAP_LEAD = ("Last week", "Last time", "Last lesson", "Last episode")
SIGNOFF_CI = ("class dismissed", "thank you for attending", "thank you for watching",
              "yoroshiku onegai", "like to thank you", "thank you, all of you",
              "thank you all for")
FILLER = {"All right.", "All right", "Right.", "Alright."}
TEASER = ("next time", "next lesson", "next week", "next video", "next episode")

def decode(block):
    if hasattr(block, "group"):
        block = block.group(0)
    s = re.sub(r"<img[^>]*>", "", block)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def is_spacer(block):
    if hasattr(block, "group"):
        block = block.group(0)
    return decode(block) == "" and "<img" not in block

def blocks_of(body):
    out, pos = [], 0
    for m in BLOCK_RE.finditer(body):
        gap = body[pos:m.start()]
        assert gap.strip() == "", "uncovered text before block: %r" % gap[:80]
        out.append(m)
        pos = m.end()
    assert body[pos:].strip() == "", "uncovered trailing text: %r" % body[pos:][:80]
    return out

LINK_RE = re.compile(r'<p[^>]*>\s*<span>\s*Link\s*:.*?</p>', re.S)

def tag_of(b):
    return re.match(r"<(\w+)", b.group(0)).group(1)

# ---------------------------------------------------------------- YouTube-ism scrub
# Distinctive markers that appear ONLY in YouTube call-outs / credits, never in the
# grammar content. A *whole sentence* containing any of these is dropped; content
# sentences (incl. "topic-comment structure", 下="below") are untouched.
_AP = "(?:&#39;|')"
YT_MARK = [
    "comments below", "comment below", "in the comments below",
    "information section below", "links below", "link below", "link right below",
    "the links below", "links in the description", "in the description below",
    "gold kokeshi", "kokeshi", "patreon", "patrons and supporters", "my patrons",
    "all my patrons", "make these videos possible", "make this work possible",
    "make all this possible", "make all of this possible", "make this entire project possible",
    "making these videos possible", "making this possible", "make all of this work possible",
    "producer-angel", "supporter-angel", "produce-angel", "my angels",
    "put a card up", "card up for", "above my head", "over my head", "put a link above",
    "subscribe", "subscriber", "subscribing", "this channel", "watch the channel",
    "i looked half-asleep", "valuable to me", "become patrons", "support me this year",
    "supporting me this year", "so many of you support", "subject of this video",
    "watch my video", "ll link that", "put the link right below", "link to my video",
    "go to akasic tails channel", "go to our friends at akasic tails",
    "half-asleep", "charging bed", "rather than the camera", "at the camera",
    "made a video", "made videos", "done a video", "done a three-part series",
    "a video that i think", "watch this video on the subject", "link to the places",
    "attending this lesson", "thank you for attending", "like to thank you for attending",
]
SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[\"&A-Z\'])')
SPAN_RE = re.compile(r"(<span[^>]*>)(.*?)(</span>)", re.S)
# Trailing CTA clauses fused into a content sentence (removed before sentence scrub).
# Parenthetical kills run FIRST so a "(… and I'll put a link … below)" is removed as a
# unit and a later clause-kill can't eat its closing paren.
_PAREN_YT = (r"information section below|put a link|made a (?:video|whole set)|"
             r"i" + _AP + r"ll link|made a video|a video on|follow that up|follow it up|"
             r"link a video|written an article")
_CONN = r"(?:\s*[,;]\s*|\s*(?:--|–|—|-)\s*|\s+)"   # connector incl. trailing whitespace
CLAUSE_KILL = [re.compile(p, re.S) for p in [
    r"\s*\([^)<]*?(?:" + _PAREN_YT + r")[^)<]*?\)",
    # trailing "..., and I'll put a link ... below/above." style clauses
    _CONN + r"and I" + _AP + r"ll (?:put|link)[^.<]*?(?:below|head)[^.<]*?(?=\.|</)",
    _CONN + r"I" + _AP + r"ll put a link below[^.<]*?(?=\.|</)",
    # specific "..., and/which I've made/done a video / explained in another lesson …" clauses
    _CONN + r"(?:and |but |so |which )*I" + _AP + r"?(?:ve|d)?\s*(?:made|done)\s+(?:a |another |some )?videos?\b[^.<]*?(?=[.<])",
    _CONN + r"(?:and |but |so |which )*I" + _AP + r"?ve\s+explained (?:that )?in another (?:lesson|video)[^.<]*?(?=[.<])",
    _CONN + r"(?:and |but |so |which )*I" + _AP + r"?ve\s+talked about this[^.<]*?in another (?:video|lesson)[^.<]*?(?=[.<])",
    _CONN + r"(?:and |but |so |which )*I" + _AP + r"?ve\s+done a three-part series[^.<]*?(?=[.<])",
    _CONN + r"which (?:I" + _AP + r"ll link|you may want to watch)[^.<]*?(?=[.<])",
    _CONN + r"so I" + _AP + r"d recommend this video[^.<]*?(?=\.|</)",
    _CONN + r"and I" + _AP + r"m going to talk about that[^.<]*?future video[^.<]*?(?=\.|</)",
    _CONN + r"and I" + _AP + r"ve written an article[^.<]*?(?=\.|</)",
]]

def _is_yt(seg):
    s = html.unescape(re.sub("<[^>]+>", " ", seg)).lower()
    return any(m in s for m in YT_MARK)

def _scrub_span_text(text):
    if "<img" in text:
        return text
    kept = [s for s in SENT_SPLIT.split(text) if not _is_yt(s)]
    return " ".join(kept)

def scrub_youtube(html_str):
    out = []
    for b in blocks_of(html_str):
        bh = b.group(0)
        if tag_of(b) == "p":
            for c in CLAUSE_KILL:
                bh = c.sub("", bh)
            bh = SPAN_RE.sub(lambda m: m.group(1) + _scrub_span_text(m.group(2)) + m.group(3), bh)
            if "<img" not in bh and decode(bh) == "":
                continue        # whole paragraph was a call-out — drop it
        out.append(bh)
    return "\n".join(out)

def clean(src, start=None, end=None, keep_signoff=False, check_images=True):
    """Clean lesson file `src`. start/end are unique substrings; the kept region is
    aligned to the enclosing block boundaries (so a single file can yield two
    sections). Boilerplate (greeting, Link line, recaps, sign-offs) is then stripped."""
    region = content_region(read(src))

    def block_start_containing(text):
        pos = region.index(text)
        for b in blocks_of(region):
            if b.start() <= pos < b.end():
                return b.start()
        raise AssertionError("marker not on a block boundary: %r" % text)

    lo = block_start_containing(start) if start else 0
    hi = block_start_containing(end) if end else len(region)
    img_target = region[lo:hi].count("../images/")

    body = region[lo:hi]
    body = re.sub(r"\A.*?</h1>", "", body, count=1, flags=re.S)   # drop h1 if present
    body = LINK_RE.sub("", body, count=1)                         # drop a Link line if present
    body = HR_RE.sub("", body)
    body = EMPTY_HEADING_RE.sub("", body)                         # drop stray empty headings
    body = body.strip()

    blks = blocks_of(body)
    assert blks, "lesson %s: no blocks" % src

    # ---- leading: skip spacers + greeting-only paragraphs ----
    i = 0
    while i < len(blks):
        if is_spacer(blks[i]):
            i += 1; continue
        if tag_of(blks[i]) == "p" and GREET_ONLY.match(decode(blks[i])):
            i += 1; continue
        break

    # ---- trailing: sweep the whole outro (sign-offs, teasers, YouTube credits) ----
    drop = set()
    k = len(blks) - 1
    while k > i:
        b = blks[k]; d = decode(b); dl = d.lower(); t = tag_of(b)
        outro = t == "p" and (
            any(x in d for x in TEASER) or _is_yt(b.group(0)) or
            any(s in dl for s in SIGNOFF_CI) or d in FILLER)
        if is_spacer(b) or outro:
            drop.add(k); k -= 1; continue
        break
    # keep the final "Class dismissed." as the chapter closer (last section only)
    if keep_signoff:
        for idx in sorted(drop, reverse=True):
            if "class dismissed" in decode(blks[idx]).lower():
                drop.discard(idx)
                break
    kept = [b for x, b in enumerate(blks) if x >= i and x not in drop]
    # drop "Last week…" recap paragraphs that surface among the first few blocks
    out = []
    for idx, b in enumerate(kept):
        if idx < 5 and tag_of(b) == "p" and decode(b).startswith(RECAP_LEAD):
            continue
        out.append(b)
    assert out, "lesson %s: nothing kept" % src

    first = PREFIX_RE.sub(r"\1", out[0].group(0), count=1)       # strip fused greeting prefix
    result = "\n".join([first] + [b.group(0) for b in out[1:]])
    # if the greeting strip emptied the first paragraph entirely, drop it
    result = re.sub(r"\A\s*<p[^>]*>\s*<span[^>]*>\s*</span>\s*</p>\s*", "", result, count=1)
    result = scrub_youtube(result)                  # remove YouTube call-outs / credits
    result = result.strip()

    got = result.count("../images/")
    if check_images:
        assert got == img_target, "lesson %s images %d != %d" % (src, got, img_target)
    return result

# ---------------------------------------------------------------- chrome
def norm(entry):
    """Normalize a lesson config entry to a dict with num/title/src/start/end/yt."""
    num, title, opts = entry
    opts = opts or {}
    return {"num": num, "title": title, "src": opts.get("src", num),
            "start": opts.get("start"), "end": opts.get("end"), "yt": opts.get("yt")}

def section_header(n, title, first=False):
    cls = "chapter-section first" if first else "chapter-section"
    return ('<h2 class="%s" id="lesson-%d"><span class="chapter-section-kicker">'
            'Lesson %d</span>%s</h2>' % (cls, n, n, title))

def bridge(text, a, b):
    return '<p class="chapter-bridge" id="bridge-%d-%d">%s</p>' % (a, b, text)

def cheats(sections):
    """One cheat-sheet embed per unique source file (skips files with no cheatsheet)."""
    rows = ['<div class="cheatsheet-section">', "    <h2>Cheat Sheets</h2>"]
    seen = set()
    for s in sections:
        src = s["src"]
        if src in seen:
            continue
        seen.add(src)
        if not os.path.exists(os.path.join(HERE, "cheatsheets", "lesson-%02d.html" % src)):
            continue
        label, _ = meta(src)
        rows.append('    <h3>%s</h3>' % html.escape(label))
        rows.append('    <div class="cheatsheet-embed">')
        rows.append('        <iframe src="../cheatsheets/lesson-%02d.html" frameborder="0" '
                    'onload="requestAnimationFrame(()=>this.style.height='
                    "this.contentDocument.documentElement.scrollHeight+'px')\" "
                    'scrolling="no"></iframe>' % src)
        rows.append("    </div>")
    rows.append("</div>")
    return "\n".join(rows)

def sources(sections):
    rows = ['<div class="related-lessons" style="padding: 15px; margin: 20px 0; '
            'background-color: #f5f5f5; border-radius: 5px; font-family: Arial, sans-serif;">',
            '<h3 style="margin-top: 0; color: #333;">Source lessons</h3>',
            '<p style="margin: 0 0 8px 0; color: #666; font-size: 0.9rem;">'
            'This chapter merges the original standalone lessons, which remain available:</p>',
            '<ul style="margin: 0; padding-left: 20px;">']
    seen = set()
    for s in sections:
        src = s["src"]
        if src in seen:
            continue
        seen.add(src)
        title, _yt = meta(src)
        rows.append('<li><a href="lesson-%02d.html">%s</a></li>' % (src, html.escape(title)))
    rows += ["</ul>", "</div>"]
    return "\n".join(rows)

def nav(num, total, top):
    pos = "margin-bottom: 20px; border-bottom" if top else "margin-top: 20px; border-top"
    links = ['<a href="chapters.html" style="margin-right: 20px;">&larr; Chapters</a>']
    if num > 1:
        links.append('<a href="chapter-%02d.html" style="margin-right: 20px;">'
                      '&larr; Prev (Chapter %d)</a>' % (num - 1, num - 1))
    if num < total:
        links.append('<a href="chapter-%02d.html">Next (Chapter %d) &rarr;</a>'
                     % (num + 1, num + 1))
    return ('<div class="nav" style="padding: 10px; %s: 1px solid #ccc; '
            'font-family: Arial, sans-serif;">%s</div>' % (pos, "".join(links)))

def intro_card(sections, paras):
    out = ['<div class="chapter-intro">']
    for p in paras:
        out.append("<p>%s</p>" % p)
    nums = [s["num"] for s in sections]
    if nums == list(range(nums[0], nums[-1] + 1)):
        span = "Lessons %d&ndash;%d" % (nums[0], nums[-1])
    else:
        span = "Lessons " + ", ".join(str(n) for n in nums)
    out.append('<p class="chapter-sources-label">This chapter covers %s</p>' % span)
    out.append("<ul>")
    for s in sections:
        yt = s["yt"] or meta(s["src"])[1]
        link = (' &mdash; <a class="yt" href="%s">YouTube</a>' % yt) if yt else ""
        out.append("<li>Lesson %d: %s%s</li>" % (s["num"], s["title"], link))
    out += ["</ul>", "</div>"]
    return "\n".join(out)

HEAD = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chapter %d: %s &mdash; Cure Dolly Textbook</title>
    <link rel="stylesheet" href="../styles.css">
    <link rel="stylesheet" href="../chapters.css">
</head>
<body class="c44 doc-content">"""

def build_chapter(ch, total):
    num, title, theme, bridges, intro = (
        ch["num"], ch["title"], ch["theme"], ch["bridges"], ch["intro"])
    sections = [norm(e) for e in ch["lessons"]]
    # if one source file appears in two sections (a split), only its last section
    # may keep the sign-off; image-invariant is checked unless the file is split.
    src_counts = {}
    for s in sections:
        src_counts[s["src"]] = src_counts.get(s["src"], 0) + 1
    parts = [HEAD % (num, html.escape(title)),
             nav(num, total, True),
             '<p class="chapter-eyebrow">Chapter %d &middot; %s</p>' % (num, theme),
             '<h1 class="chapter-title">%s</h1>' % title,
             intro_card(sections, intro)]
    for idx, s in enumerate(sections):
        last = idx == len(sections) - 1
        parts.append(section_header(s["num"], s["title"], first=(idx == 0)))
        parts.append(clean(s["src"], start=s["start"], end=s["end"],
                           keep_signoff=last, check_images=(src_counts[s["src"]] == 1)))
        if not last:
            parts.append(bridge(bridges[idx], s["num"], sections[idx + 1]["num"]))
    parts.append(cheats(sections))
    parts.append(sources(sections))
    parts.append(nav(num, total, False))
    parts += ["</body>", "</html>"]
    out = "\n".join(parts) + "\n"
    path = os.path.join(LESSONS, "chapter-%02d.html" % num)
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    imgs = out.count("../images/")
    return imgs

# ---------------------------------------------------------------- chapters.html
def build_index(chapters):
    cards = []
    for ch in chapters:
        ls = [norm(e) for e in ch["lessons"]]
        nums = [s["num"] for s in ls]
        if nums == list(range(nums[0], nums[-1] + 1)):
            span = "Lessons %d&ndash;%d" % (nums[0], nums[-1])
        else:
            span = "Lessons " + ", ".join(str(n) for n in nums)
        covers = " &middot; ".join(s["title"] for s in ls)
        cards.append(
            '<a class="chapter-list-card" href="chapter-%02d.html">'
            '<p class="num">Chapter %d &middot; %s</p>'
            '<p class="title">%s</p>'
            '<p class="covers">%s</p></a>' % (ch["num"], ch["num"], span, ch["title"], covers))
    doc = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Read as Chapters &mdash; Cure Dolly Textbook</title>
    <link rel="stylesheet" href="../chapters.css">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
            'Helvetica Neue', sans-serif; max-width: 640px; margin: 0 auto;
            padding: 40px 20px; line-height: 1.6; color: #1a1a1a; }}
        .nav {{ padding: 10px 0; margin-bottom: 20px; border-bottom: 1px solid #ccc; }}
        .nav a {{ color: #2563eb; text-decoration: none; font-size: 0.95rem; margin-right: 18px; }}
        .nav a:hover {{ text-decoration: underline; }}
        header {{ margin-bottom: 24px; padding-bottom: 20px; border-bottom: 2px solid #e0e0e0; }}
        h1 {{ font-size: 1.75rem; font-weight: 700; margin: 0 0 6px 0; }}
        .subtitle {{ color: #666; font-size: 0.95rem; margin: 0; }}
        @media (max-width: 768px) {{ body {{ padding: 20px 16px; }} }}
    </style>
</head>
<body>
<div class="nav"><a href="../index.html">&larr; Home</a><a href="index.html">All 88 lessons</a></div>
<header>
    <h1>Read as Chapters</h1>
    <p class="subtitle">The 88-lesson course, stitched into {n} flowing chapters you can binge.
    Nothing is cut but the repetition &mdash; every explanation, example and image is Cure Dolly's own.</p>
</header>
{cards}
<div class="nav" style="margin-top: 24px; padding-top: 10px; border-top: 1px solid #ccc; border-bottom: none;">
    <a href="../index.html">&larr; Home</a><a href="index.html">All 88 lessons</a>
</div>
</body>
</html>
""".format(n=len(chapters), cards="\n".join(cards))
    with open(os.path.join(LESSONS, "chapters.html"), "w", encoding="utf-8") as f:
        f.write(doc)

# ================================================================ CONFIG
# Each lesson entry is (number, section-title, _reserved). Bridges has one entry
# per gap between consecutive lessons. Intro is a list of HTML paragraphs.
CHAPTERS = [
 {"num":1, "title":"The Core Sentence", "theme":"Foundations",
  "lessons":[(1,"The Three Sentence Types",{"start":"h.ajf89xo41fjk"}),
             (2,"The Zero Pronoun &amp; the を Particle",{"start":"h.8emxv8fx1n51"}),
             (3,"The は Particle, に, and Logical Particles",{"start":"h.xjz7l3dxnv6y"})],
  "bridges":[
    "Lesson&nbsp;1 promised more carriages around that unchanging core. Here is the first of them — and the one you can least afford to ignore, because most of the time you can’t even see it.",
    "So far every example has leaned on が, を and the invisible subject. Now for the famous particle we have deliberately kept waiting all this time."],
  "intro":[
    "<strong>Welcome to Organic Japanese</strong> — Japanese pure and simple, with no harmful additives. Most courses start by forcing Japanese into the shape of English. This one doesn't. We start instead with the one thing every Japanese sentence is built from: the <strong>core sentence</strong>.",
    "You'll meet the two elements every sentence is made of, the three ways it can end (a verb, the copula だ, or an い-adjective), the linchpin particle が, the invisible subject that is always there even when you can't see it, and the logical particles を and に — plus the famous topic-marker は. By the end you'll be able to see the skeleton of <em>any</em> Japanese sentence."]},

 {"num":2, "title":"The Engines: Verbs &amp; Adjectives", "theme":"Foundations",
  "lessons":[(4,"The Three Tenses (and the Non-Past)",None),(5,"Verb Groups and the て / た Forms",None),
             (6,"The Three Kinds of Adjective",None),(7,"Negative Verbs",None)],
  "bridges":[
    "Tense lives inside the engine, so the next question is how that engine is built and re-shaped — verb groups and the all-important て and た forms.",
    "Verbs are only one of the three engines. The describing engine — the adjective — works quite differently from its English cousin.",
    "We can now build and describe. The remaining basic operation is denial: making a verb negative."],
  "intro":[
    "With the core sentence in place, we look closely at the engines that drive it — verbs and adjectives — and how they change shape.",
    "This chapter covers how Japanese handles time (and why there is no true present tense), how verbs split into groups and form the essential て and た forms, what an adjective really is, and how to make things negative. By the end the engine of any sentence will hold no surprises."]},

 {"num":3, "title":"Desire, Potential &amp; Direction", "theme":"Foundations",
  "lessons":[(8,"The に and へ Particles",None),(9,"Expressing Desire: ほしい, たい, たがる",None),
             (10,"The Potential and Conjugations",None)],
  "bridges":[
    "に gives us direction and a target. The natural next step is to say what we want to reach — desire.",
    "Wanting leads straight to being able: the potential, and the helper forms it belongs to."],
  "intro":[
    "Now we add reach and intention to the core.",
    "This chapter covers the destination particles に and へ, the several ways Japanese expresses wanting (ほしい, たい, たがる), and the potential — being able to do something — together with the helper system that powers it."]},

 {"num":4, "title":"Expanding the Sentence", "theme":"Intermediate",
  "lessons":[(11,"Compound Sentences, くれる &amp; あげる",None),(12,"Quoting with と",None),
             (13,"The Receptive Helper Verb",None),(14,"も, こと and Adverbs",None),
             (15,"Self-Move &amp; Other-Move Verbs",None),(16,"てみる, の, と and や",None)],
  "bridges":[
    "Once sentences can be joined, we need a way to fold one whole sentence inside another — quotation with と.",
    "Quotation lets us carry a sentence as a unit. The receptive helper lets us flip which side of an action we stand on.",
    "With the receptive in hand, we pick up three small but constant tools: も, こと, and adverbs.",
    "One distinction underlies a great deal of Japanese and trips up almost every learner: verbs that move themselves versus verbs that move something else.",
    "To close, a handful of connectors and the helper てみる — small pieces that make speech flow."],
  "intro":[
    "From here we stop building single sentences and start joining them. Following Alice down the rabbit hole, the lessons grow into real narrative.",
    "This chapter covers compound sentences, the giving-and-receiving verbs くれる and あげる, quoting with と, the misnamed \"passive\" (really the receptive helper), the workhorses も and こと, and the crucial distinction between self-moving and other-moving verbs."]},

 {"num":5, "title":"Register, Voice &amp; Helper Verbs", "theme":"Intermediate",
  "lessons":[(17,"Formal Japanese: です / ます",None),(18,"って — the Casual Topic-marker",None),
             (19,"The Causative &amp; Causative-Passive",None),(20,"The こそあど System: それ・その・そんな・そう",None),
             (21,"Deeper て-form Uses: ておく &amp; てある",None)],
  "bridges":[
    "です/ます is the formal register; って is almost its opposite number — the most casual way to flag a topic or a quote.",
    "Having handled register, we return to voice: the causative, and its fusion with the receptive.",
    "From who-makes-whom-do-what we turn to pointing: the こそあど system of this, that, and that-over-there.",
    "こそあど includes そう; staying with the て-form, ておく and てある let us place an action and leave its result standing."],
  "intro":[
    "Japanese changes shape depending on who you're speaking to and how much you want to compress.",
    "This chapter covers polite です/ます, the casual って, the causative and causative-passive helpers, the こそあど pointing system, and two more て-form helpers, ておく and てある."]},

 {"num":6, "title":"How Things Seem", "theme":"Intermediate",
  "lessons":[(22,"ては and ても: Topic/Comment Magic",None),(23,"だって",None),
             (24,"そう: Hearsay and Likeness",None),(25,"らしい vs そう, and っぽい",None),
             (26,"Similes: のように・のような・みたい",None),
             (27,"ばかり",{"end":"Lesson 28: You ni"}),
             (28,"ように — Purpose and Manner",
                 {"src":27,"start":"Lesson 28: You ni",
                  "yt":"https://www.youtube.com/watch?v=IE7WgIOOGbM"})],
  "bridges":[
    "ても shows the topic/comment machinery flexing; だって runs on the very same logic of だ.",
    "From だって we reach そう — a single helper that does double duty: hearsay and likeness.",
    "そう is not alone in guessing: らしい and っぽい cover nearby ground with their own shades.",
    "Likeness has a fuller vocabulary still — the simile words のように, のような and みたい.",
    "ばかり is a word the textbooks scatter into a dozen meanings that are really one.",
    "Those softer uses of ばかり lean on ように する — the perfect moment to meet ように itself, the all-purpose word for purpose and manner."],
  "intro":[
    "This chapter is about appearance, report and resemblance — how Japanese says that something <em>seems</em>, is <em>said to be</em>, or is <em>like</em> something else.",
    "It covers ては/ても, the much-misunderstood だって, the two faces of そう, らしい and っぽい, the simile words, ばかり, and — bundled in with ばかり — the all-purpose ように."]},

 {"num":7, "title":"Conditionals &amp; Outcomes", "theme":"Advanced",
  "lessons":[(29,"ことにする and ことになる",None),(30,"The と Conditional",None),
             (31,"The ば / -れば Conditional",None),(32,"The たら and なら Conditionals",None)],
  "bridges":[
    "Deciding and becoming shade naturally into condition and consequence — the first conditional, と.",
    "と insists on a single inevitable outcome. ば opens the door to hypotheticals.",
    "Two conditionals remain, and they are the most flexible of all: たら and なら."],
  "intro":[
    "Japanese has several ways to say \"if\" and \"when\", and choosing between them is mostly a matter of feeling their different characters.",
    "This chapter first covers deciding and becoming (ことにする / ことになる), then walks through the four conditionals — と, ば, たら and なら — one quality at a time."]},

 {"num":8, "title":"Limiting, Comparing &amp; Placing", "theme":"Advanced",
  "lessons":[(33,"だけ, しか, ばかり, のみ",None),(34,"Analyzing Any Sentence: The Core Technique",None),
             (35,"より and のほう (Comparison)",None),(36,"ところ — the Concept of Place",None),
             (37,"な vs の, なる &amp; たる Adjectives",None)],
  "bridges":[
    "Limiting words show how much rides on a single particle — which is exactly what the next technique exploits to crack any sentence.",
    "Once you can find the core of a sentence, you can compare cores — より and のほう.",
    "Comparison places things against each other; ところ places them in space and time.",
    "Place leads to a structural payoff: seeing that な- and の-\"adjectives\" are really nouns."],
  "intro":[
    "This chapter gathers the tools for narrowing, comparing and placing.",
    "It covers the limiting words だけ, しか, ばかり and のみ; a powerful technique for cutting any sentence down to its logical core; comparison with より and のほう; the surprisingly broad ところ; and the truth about な- and の-\"adjectives\"."]},

 {"num":9, "title":"Reading &amp; Analyzing Japanese", "theme":"Advanced",
  "lessons":[(38,"じゃない and ではない",None),(39,"The か Particle's Secret Life",None),
             (40,"Three Pitfalls in Japanese",None),(41,"Five Key Facts About Japanese Words",None),
             (42,"まま",None),(43,"The Paradigm Shift",None)],
  "bridges":[
    "じゃない hides a question inside a negative; か is the question particle whose reach goes much further than the textbooks admit.",
    "か's hidden work is one case of a larger danger: tiny elements that change everything. Here are three of them.",
    "Avoiding the pitfalls depends on knowing what a Japanese word really is — five facts that clear the fog.",
    "With words understood, even a slippery one like まま falls into place.",
    "These pieces add up to a single change of view — the paradigm shift this chapter has been building toward."],
  "intro":[
    "This chapter turns from building sentences to reading them — and to the shifts in thinking that make real Japanese legible.",
    "It covers じゃない and ではない, the secret life of か, three small pitfalls that derail learners, five facts about what Japanese words actually are, まま, and a closing paradigm shift."]},

 {"num":10, "title":"Word Order, Ambiguity &amp; Point of View", "theme":"Advanced",
  "lessons":[(44,"ちゃう and ちゃった",None),(46,"Why Word Order Matters",None),
             (47,"Breaking Down Sentences: The Secret Weapon",None),(48,"Ambiguity: Three Laws",None),
             (49,"Point of View: もらう and てもらう",None),(50,"させてもらう — the Last Secret of the Potential",None)],
  "bridges":[
    "Casual contractions like ちゃう belong to natural speech; so does the next, larger question — how word order actually works.",
    "If order matters, we need a reliable way to take a long sentence apart. This is that secret weapon.",
    "Breaking a sentence down exposes its ambiguities — and there are three simple laws for resolving them.",
    "Much ambiguity is really about point of view: who benefits, who receives. Enter もらう and てもらう.",
    "もらう has one last secret to give up, where receiving and the potential meet: させてもらう."],
  "intro":[
    "This chapter is about reading real, natural Japanese — where word order, ambiguity and point of view all carry meaning.",
    "It covers the casual ちゃう, why word order genuinely matters, a secret weapon for breaking down long sentences, three laws for handling ambiguity, and the point-of-view verbs もらう, てもらう and させてもらう."]},

 {"num":11, "title":"Reading Native Japanese: Kaidan", "theme":"Deep Dive",
  "lessons":[(51,"Reading a Kaidan, Part 1",None),(52,"Sentence Analysis in Native Context",None),
             (53,"Japanese Horror in Japanese",None)],
  "bridges":[
    "The story continues, and so does the analysis — deeper into native context.",
    "One more instalment, and the horror is read entirely on its own terms."],
  "intro":[
    "A reading interlude. Everything so far now meets real, unsimplified Japanese in the form of a <em>kaidan</em> — a ghost story — read with our partner channel.",
    "These three sittings put structure to work in the wild, sentence by sentence. There is little new grammar here; the point is to watch the machinery you already know do its job."]},

 {"num":12, "title":"Particles &amp; Words in Depth", "theme":"Deep Dive",
  "lessons":[(54,"Irregularities: 見る・見られる・見れる・見える",None),(55,"Secrets of the で Particle",None),
             (56,"Deeper Secrets of は and の",None),(57,"込む and Multi-Meaning Words",None),
             (58,"Double Particles",None)],
  "bridges":[
    "Exceptions like 見える show how much a single particle decides; で is a particle whose range is wider than it looks.",
    "で deepened, we return to the two particles we can never quite finish with — は and の.",
    "From particles to word-building: how 込む packs many meanings into one ending.",
    "If single particles run deep, combined particles repay a close look too."],
  "intro":[
    "Back to structure, but deeper.",
    "This chapter looks at apparent irregularities (the 見る family), the real range of the で particle, the subtler workings of は and の, how a single element like 込む carries many meanings, and what happens when particles combine."]},

 {"num":13, "title":"The Two Halves of Japanese", "theme":"Deep Dive",
  "lessons":[(59,"Untranslatable Japanese: Passivity",None),(60,"The Other Half: Topic / Comment",None),
             (61,"は and が: The Deeper Secrets",None),(62,"ておく vs てしまう",None),
             (63,"Wild Sentence-Enders: かい・だい・ぜ・ぞ・さ",None)],
  "bridges":[
    "That untranslatable feeling has a precise cause — the half of Japanese we've been postponing.",
    "With both halves on the table, は and が finally give up their deeper secrets.",
    "From the topic layer back to the verb: the contrast between ておく and てしまう.",
    "And to end, the small enders that colour real speech — かい, だい, ぜ, ぞ, さ."],
  "intro":[
    "This chapter names something we've circled for a long time: Japanese has two halves — a logical core and a non-logical topic/comment layer.",
    "It covers the \"problem of passivity\" that makes some sentences feel untranslatable, the other half itself, the deeper secrets of は and が, ておく versus てしまう, and the wild sentence-enders of real speech."]},

 {"num":14, "title":"Things, Motion &amp; Hidden Meaning", "theme":"Deep Dive",
  "lessons":[(64,"もの and こと, Advanced",None),(65,"Deeper 行く and 来る",None),
             (66,"Hidden Subjects: the Hidden Hand",None),(67,"もう and まだ",None),
             (68,"わけ — Underlying Logic",None),(69,"Kaidan 4: Japanese in the Wild",None),
             (70,"かける and かかる",None)],
  "bridges":[
    "もの and こと are abstractions; 行く and 来る ground us again in motion — with hidden meanings of their own.",
    "Coming and going always imply someone; that someone is often hidden — the hidden hand.",
    "Hidden subjects sharpen our reading; now two small words that quietly reset time, もう and まだ.",
    "From time to reason: わけ, the word that names the underlying logic of a situation.",
    "Time to test all of this against real Japanese again — the kaidan returns.",
    "After the story, one more all-purpose verb pair for the toolkit: かける and かかる."],
  "intro":[
    "This chapter collects some of Japanese's most quietly powerful words and ideas.",
    "It covers もの and こと at depth, the hidden meanings of 行く and 来る, the \"hidden hand\" behind subjectless sentences, もう and まだ, the logic-word わけ, and the all-purpose かける/かかる — with a fourth kaidan reading woven in for practice."]},

 {"num":15, "title":"The Great Connector &amp; Deeper Patterns", "theme":"Mastery",
  "lessons":[(71,"Counters: Three Simple Rules",None),(72,"The Great Connector: the い-Stem",None),
             (73,"気: 気になる・気にする・気がする",None),(74,"こと and the Mystery of Love",None),
             (75,"Japanese Is NOT English",None),(76,"あく・あける・ひらく・ひらける",None)],
  "bridges":[
    "Counters hook onto the stem of a number; the い-stem is the great connector behind far more than counting.",
    "The stem connects words; 気 connects feeling to grammar in 気になる, 気にする and 気がする.",
    "From the workings of the mind to one of the deepest words in the language — こと, even love.",
    "こと's untranslatability points at the larger truth: Japanese is not English, and shouldn't be forced to be.",
    "Holding that in mind, a concrete example of Japanese thinking on its own terms — the opening verbs あく, あける, ひらく, ひらける."],
  "intro":[
    "This chapter pairs practical patterns with a change of mindset.",
    "It covers counters (three rules, not a hundred), the い-stem that connects so much of the language, the 気 expressions, the deepest sense of こと, the principle that Japanese is simply not English, and a family of \"opening\" verbs."]},

 {"num":16, "title":"Structure Re-examined: Tae Kim &amp; the Copula", "theme":"Mastery",
  "lessons":[(77,"Real Japanese Structure vs Tae Kim",None),(78,"Breaking the Core: Tae Kim vs the Copula",None),
             (79,"Cracking a Third of All Sentences",None),(80,"Dropped Particles &amp; Casual Omissions",None),
             (81,"The Global Principle of Word-Forms",None)],
  "bridges":[
    "The first critique is general; the second strikes at the core itself — the copula that the standard model mishandles.",
    "Getting the copula right is not academic: it cracks open a third of all Japanese sentences.",
    "Real speech, of course, leaves the particles out — so we learn to read what isn't written.",
    "Underneath every form and omission lies one principle: the global logic of Japanese word-forms."],
  "intro":[
    "This chapter sharpens our model by contrast — setting it against the popular Tae Kim explanation and showing where that account breaks down.",
    "It covers two critiques of the standard structure, the copula insight that unlocks a third of all sentences, how to read Japanese when particles are dropped, and the single global principle behind every word-form."]},

 {"num":17, "title":"Edge Cases &amp; Finishing Touches", "theme":"Mastery",
  "lessons":[(82,"なんて, なんか, など",None),(83,"Three Levels of Command",None),
             (84,"である and the Older Copulas",None),(85,"まい — the Negative Helper",None),
             (86,"次第 — What It Really Means",None),(87,"しか — Structure Inverted",None),
             (88,"Xをしたい vs Xがしたい",None),(89,"The Universal Subject",None),
             (90,"Japanese Punctuation",None)],
  "bridges":[
    "These vague-ing words soften statements; commands do the opposite — three levels of them.",
    "From how we order to how we equate: である and the older copulas behind だ.",
    "If である is an older positive copula, まい is the negative helper that time nearly forgot.",
    "Another word with a long dictionary entry and a single real meaning: 次第.",
    "次第 turns on dependency; しか turns the whole sentence inside out.",
    "しか inverts structure; をしたい versus がしたい shows the core holding firm under pressure.",
    "Behind every が-marked subject, visible or not, stands one more idea — the universal subject.",
    "And with the structure complete, the very last touch: how Japanese is punctuated on the page."],
  "intro":[
    "The final chapter sweeps up the edge cases and finishing touches that turn solid Japanese into fluent reading.",
    "It covers なんて/なんか/など, the levels of command, the older copula である, the negative helper まい, 次第, the structure-inverting しか, the をしたい/がしたい question, the universal subject, and — last of all — Japanese punctuation."]},
]

# ================================================================ RUN
if __name__ == "__main__":
    total = len(CHAPTERS)
    assert total == 17, total
    secs = [norm(e) for ch in CHAPTERS for e in ch["lessons"]]
    srcs = sorted(set(s["src"] for s in secs))
    expected = [n for n in range(1, 91) if n not in (28, 45)]
    assert srcs == expected, "source files: %s" % srcs
    print("sections: %d   source files: %d" % (len(secs), len(srcs)))
    grand = 0
    for ch in CHAPTERS:
        assert len(ch["bridges"]) == len(ch["lessons"]) - 1, "ch %d bridge count" % ch["num"]
        imgs = build_chapter(ch, total)
        grand += imgs
        print("chapter-%02d.html  lessons %-26s images=%d"
              % (ch["num"], str([norm(e)["num"] for e in ch["lessons"]]), imgs))
    build_index(CHAPTERS)
    src_imgs = sum(content_region(read(n)).count("../images/") for n in srcs)
    print("-" * 60)
    print("chapters images total: %d   source lessons images total: %d   %s"
          % (grand, src_imgs, "OK" if grand == src_imgs else "MISMATCH!"))
    print("wrote chapters.html and 17 chapter files")
