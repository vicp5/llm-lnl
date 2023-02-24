import pandas as pd
import wikipedia
import re
from transformers import GPT2TokenizerFast
from nltk.tokenize import sent_tokenize

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

MAX_DEPTH_LEVEL = 3


def count_tokens(text):
    """count the number of tokens in a string"""
    return len(tokenizer.encode(text))


def reduce_long(long_text,
                long_text_tokens=False, max_len=590):
    """
    Reduce a long text to a maximum of `max_len` tokens
    by potentially cutting at a sentence end
    """
    if not long_text_tokens:
        long_text_tokens = count_tokens(long_text)
    if long_text_tokens > max_len:
        sentences = sent_tokenize(long_text.replace("\n", " "))
        ntokens = 0
        for i, sentence in enumerate(sentences):
            ntokens += 1 + count_tokens(sentence)
            if ntokens > max_len:
                return ". ".join(sentences[:i][:-1]) + "."

    return long_text


def filter_titles(titles, keywords):
    """
    Get the titles which are related, given a list of titles
    """
    titles = [title for title in titles if
              any(keyword.lower() in title.lower()
                  for keyword in keywords)]
    return titles


def get_option_by_keywords(options, keywords):
    processed_options = [option for option in options if
                         any(keyword.lower() in option.lower()
                             for keyword in keywords)]
    if len(processed_options) < 1:
        return None

    return processed_options[0]


def get_wiki_page(title, keywords, depth_level=1):
    """
    Get the wikipedia page given a title
    """
    try:
        return wikipedia.page(title)
    except wikipedia.exceptions.DisambiguationError as e:
        options_titles = filter_titles(e.options, keywords)
        option = get_option_by_keywords(options_titles, keywords)
        if option and depth_level < MAX_DEPTH_LEVEL:
            return get_wiki_page(option, keywords, depth_level+1)
        else:
            return None
    except wikipedia.exceptions.PageError:
        return None


def recursively_find_all_pages(
        titles, keywords, titles_so_far=set(), depth_level=1):
    """
    Recursively find all the pages that are linked to
    the Wikipedia titles in the list
    """
    all_pages = []
    if depth_level == MAX_DEPTH_LEVEL:
        return all_pages
    titles = list(set(titles) - titles_so_far)
    titles = filter_titles(titles, keywords)
    titles_so_far.update(titles)
    for title in titles:
        page = get_wiki_page(title, keywords)
        if page is None:
            continue
        print(f"downloaded wikipedia page: {title}")
        all_pages.append(page)

        new_pages = recursively_find_all_pages(
                page.links, keywords, titles_so_far, depth_level+1)
        for pg in new_pages:
            if pg.title not in [p.title for p in all_pages]:
                all_pages.append(pg)
        titles_so_far.update(page.links)
    return all_pages


discard_categories = ['See also', 'References', 'External links',
                      'Further reading', "Footnotes", "Bibliography",
                      "Sources", "Citations", "Literature", "Footnotes",
                      "Notes and references", "Photo gallery", "Works cited",
                      "Photos", "Gallery", "Notes", "References and sources",
                      "References and notes",]


def clean_wiki_contents(
        headings,
        contents,
        discard_categories=discard_categories,
):
    # discard the discard categories, accounting for a tree structure
    max_level = 100
    keep_group_level = max_level
    remove_group_level = max_level
    nheadings, ncontents = [], []
    for heading, content in zip(headings, contents):
        plain_heading = " ".join(heading.split(" ")[1:-1])
        num_equals = len(heading.split(" ")[0])
        if num_equals <= keep_group_level:
            keep_group_level = max_level

        if num_equals > remove_group_level:
            if (
                num_equals <= keep_group_level
            ):
                continue
        keep_group_level = max_level
        if plain_heading in discard_categories:
            remove_group_level = num_equals
            keep_group_level = max_level
            continue
        nheadings.append(heading.replace("=", "").strip())
        ncontents.append(content)
        remove_group_level = max_level
    return (nheadings, ncontents)


def extract_wiki_headings_contents(
        wiki_text,
        discard_categories=discard_categories,
):
    # find all headings and the coresponding contents
    headings = re.findall("==+ .* ==+", wiki_text)
    for heading in headings:
        wiki_text = wiki_text.replace(heading, "==+ !! ==+")
    contents = wiki_text.split("==+ !! ==+")
    contents = [c.strip() for c in contents]
    assert len(headings) == len(contents) - 1
    return (headings, contents)


def extract_wiki_sections(
        wiki_text,
        title,
        max_len=1500,
        discard_categories=discard_categories,
):
    """
    Extract the sections of a Wikipedia page, discarding the
    references and other low information sections
    """
    if len(wiki_text) == 0:
        return []

    headings, contents = extract_wiki_headings_contents(wiki_text)
    cont = contents.pop(0).strip()
    outputs = [(title, "Summary", cont, count_tokens(cont)+4)]

    nheadings, ncontents = clean_wiki_contents(headings, contents)

    # count the tokens of each section
    ncontent_ntokens = [
        count_tokens(c)
        + 3
        + count_tokens(" ".join(h.split(" ")[1:-1]))
        - (1 if len(c) == 0 else 0)
        for h, c in zip(nheadings, ncontents)
    ]

    # Create a tuple of (title, section_name, content, number of tokens)
    outputs += [(title, h, c, t) if t < max_len
                else (title, h, reduce_long(c, max_len),
                      count_tokens(reduce_long(c, max_len)))
                for h, c, t in zip(nheadings, ncontents, ncontent_ntokens)]
    return outputs


def tokenize_wikipedia_pages(fname, titles, keywords):
    print("recursively downloading pages")
    pages = recursively_find_all_pages(titles, keywords)
    print("extracting tokenized sections")
    res = []
    for page in pages:
        res += extract_wiki_sections(page.content, page.title)
    print(f"backing up csv to {fname}")
    df = pd.DataFrame(res, columns=['title', 'heading', 'content', 'tokens'])
    df = df[df.tokens > 40]
    df = df.drop_duplicates(['title', 'heading'])
    df = df.reset_index().drop('index', axis=1)
    df.to_csv(fname, index=False)
    return df
