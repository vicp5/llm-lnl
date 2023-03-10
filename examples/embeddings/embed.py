import numpy as np
import openai
import pandas as pd
import tiktoken
import os
import time

COMPLETIONS_MODEL = 'text-davinci-003'
EMBEDDING_MODEL = 'text-embedding-ada-002'

COMPLETIONS_API_PARAMS = {
        "temperature": 0.0,
        "max_tokens": 300,
        "model": COMPLETIONS_MODEL,
}

MAX_SECTION_LEN = 800
SEPARATOR = "\n* "
ENCODING = "cl100k_base"  # encoding for text-embedding-ada-002

encoding = tiktoken.get_encoding(ENCODING)
separator_len = len(encoding.encode(SEPARATOR))


openai.api_key = os.getenv('OPENAI_API_KEY')


def get_embedding(text, model=EMBEDDING_MODEL):
    time.sleep(0.25)  # avoid rate limit
    result = openai.Embedding.create(
            model=model,
            input=text
    )
    return result["data"][0]["embedding"]


def compute_doc_embeddings(df):
    """
    Create an embedding for each row in the dataframe using
    the OpenAI Embeddings API. Return a dictionary that maps
    between each embedding vector and the index of the row
    that it corresponds to.
    """
    return {
        idx: get_embedding(r.content) for idx, r in df.iterrows()
    }


def save_embeddings(fname,
                    document_embeddings):
    """
    Write the document embeddings and their keys to a CSV.
    fname is the path to a CSV with exactly these named columns:
        "title", "heading", "0", "1",
        ... up to the length of the embedding vectors.
    """
    df = pd.DataFrame(document_embeddings)
    df = df.transpose()
    df.rename(columns={'Unnamed: 0': 'title',
                       'Unnamed: 1': 'heading'}, inplace=True)
    df.to_csv(fname)


def load_embeddings(fname):
    """
    Read the document embeddings and their keys from a CSV.
    fname is the path to a CSV with exactly these named columns:
        "title", "heading", "0", "1",
        ... up to the length of the embedding vectors.
    """
    df = pd.read_csv(fname, header=0)
    max_dim = max([int(c) for c in df.columns
                  if c != "title" and c != "heading"])
    return {
        (r.title, r.heading):
        [r[str(i)] for i in range(max_dim + 1)] for _, r in df.iterrows()
    }


def vector_similarity(x, y):
    """
    Returns the similarity between two vectors.
    Because OpenAI Embeddings are normalized to length 1, the cosine
    similarity is the same as the dot product.
    """
    return np.dot(np.array(x), np.array(y))


def order_document_sections_by_query_similarity(
        query, contexts):
    """
    Find the query embedding for the supplied query, and compare
    it against all of the pre-calculated document embeddings to find
    the most relevant sections.
    Return the list of document sections, sorted by relevance in descending
    order.
    """
    query_embedding = get_embedding(query)
    document_similarities = sorted([
        (vector_similarity(query_embedding, doc_embedding),
            doc_index) for doc_index, doc_embedding in contexts.items()],
        reverse=True)
    return document_similarities


def construct_prompt(question, context_embeddings, df):
    """
    Fetch relevant
    """
    most_relevant_document_sections = \
        order_document_sections_by_query_similarity(
            question, context_embeddings)
    chosen_sections = []
    chosen_sections_len = 0
    chosen_sections_indexes = []
    for _, section_index in most_relevant_document_sections:
        # Add contexts until we run out of space.
        document_section = df.loc[section_index]
        chosen_sections_len += document_section.tokens + separator_len
        if chosen_sections_len > MAX_SECTION_LEN:
            break
        chosen_sections.append(SEPARATOR +
                               document_section.content.replace("\n", " "))
        chosen_sections_indexes.append(str(section_index))

    # Useful diagnostic information
    print(f"Selected {len(chosen_sections)} document sections:")
    print("\n".join(chosen_sections_indexes))

    header = """Answer the question as truthfully as possible using the """ \
             """provided context, and if the answer is not contained """ \
             """within the text below, say "I don't know."\n\nContext:\n"""
    return header + "".join(chosen_sections) + "\n\n Q: " + question + "\n A:"


def answer_query_with_context(
        query,
        df,
        document_embeddings,
        show_prompt=False):
    prompt = construct_prompt(
            query,
            document_embeddings,
            df
            )

    if show_prompt:
        print(prompt)

    response = openai.Completion.create(
            prompt=prompt,
            **COMPLETIONS_API_PARAMS
            )

    return response["choices"][0]["text"].strip(" \n")
