import requests
import pandas as pd
from graphql import parse, print_ast
from graphql.language.ast import FieldNode, ArgumentNode, NameNode, IntValueNode
from typing import List
from bs4 import BeautifulSoup

# Set up the necessary variables
test_key = "You can add test key here"
endpoint = "https://api.wordlift.io/graphql/graphql"
headers = {
    "Authorization": f"Key {test_key}",
    "Content-Type": "application/json"
}
default_page = 0
default_rows = 25

graphql_example_query = """
query {
   articles {
    id: iri
    title: string(name: "schema:headline")
    date: string(name: "schema:datePublished")
    author_id: string(name: "schema:author")    
    article_author: resource(name: "schema:author") {
      id: iri
      name: string(name: "schema:name")
    }
    article_url: string(name: "schema:mainEntityOfPage")
    article_about: resource(name: "schema:about") {
      names: string(name: "schema:name")
    }
    article_desc: string(name: "schema:description")
    mentions: resources(name: "schema:mentions") {
      names: strings(name: "schema:name")
    }
    body: string(name: "wordpress:content")
  }
}
"""
example_fields = "articles"

# Configuration options for document processing
config_options = {
    'text_fields': ['article_desc'],
    'metadata_fields': ['article_url']
}


class Document:
    def __init__(self, text, extra_info):
        self.text = text
        self.extra_info = extra_info


def create_docstore(dataframe, config_options):
    """
    Creates a document store from a dataframe.

    Args:
        dataframe (pd.DataFrame): The dataframe containing the data.
        config_options (dict): Configuration options for document processing.

    Returns:
        List[Document]: The list of documents in the document store.
    """
    text_fields = config_options['text_fields']
    metadata_fields = config_options['metadata_fields']

    results = []
    for index, row in dataframe.iterrows():
        text_parts = [str(row[col])
                      for col in text_fields if row[col] is not None]
        text = ' '.join(text_parts)
        extra_info = row[metadata_fields].to_dict()
        results.append(Document(text, extra_info=extra_info))

    return results


def clean_html(text):
    """
    Cleans HTML markup from the given text.

    Args:
        text (str): The text containing HTML markup.

    Returns:
        str: The cleaned text without HTML markup.
    """
    if text.startswith('http://') or text.startswith('https://'):
        response = requests.get(text)
        html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')
        cleaned_text = soup.get_text()
    else:
        soup = BeautifulSoup(text, 'html.parser')
        cleaned_text = soup.get_text()
    return cleaned_text


def alter_query(query, page, rows):
    """
    Alters the GraphQL query by adding pagination arguments.

    Args:
        query (str): The original GraphQL query.
        page (int): The page number.
        rows (int): The number of rows per page.

    Returns:
        str: The altered GraphQL query with pagination arguments.
    """
    ast = parse(query)

    field_node = ast.definitions[0].selection_set.selections[0]

    if not any(arg.name.value == 'page' for arg in field_node.arguments):
        page_argument = ArgumentNode(
            name=NameNode(value='page'),
            value=IntValueNode(value=page)
        )
        rows_argument = ArgumentNode(
            name=NameNode(value='rows'),
            value=IntValueNode(value=rows)
        )
        field_node.arguments = field_node.arguments + \
            (page_argument, rows_argument)
    altered_query = print_ast(ast)
    return altered_query


def sendGraphQLRequest(query):
    """
    Sends a GraphQL request to the API endpoint.

    Args:
        query (str): The GraphQL query.

    Returns:
        dict: The response JSON data.
    """
    try:
        response = requests.post(
            endpoint, json={"query": query}, headers=headers)
        response.raise_for_status()

        data = response.json()
        if 'errors' in data:
            raise Exception(data['errors'])

        return data

    except requests.exceptions.RequestException as e:
        print('Error connecting to the API:', e)
        raise


def clean_value(x):
    """
    Cleans the value by applying HTML cleaning if necessary.

    Args:
        x: The value to clean.

    Returns:
        The cleaned value.
    """
    if x is not None and not isinstance(x, list):
        return clean_html(x)
    return x


def transform_data(response_json):
    """
    Transforms the response JSON data into a pandas DataFrame.

    Args:
        response_json (dict): The response JSON data.

    Returns:
        pd.DataFrame: The transformed DataFrame.
    """
    data = response_json['data'][example_fields]
    df = pd.DataFrame(data)
    df = df.applymap(clean_value)
    return df


if __name__ == "__main__":
    # Alter the GraphQL query to include pagination arguments
    altered_query = alter_query(
        graphql_example_query, page=default_page, rows=default_rows)

    # Send the GraphQL request and retrieve the response data
    all_data = sendGraphQLRequest(altered_query)

    # Transform the response data into a DataFrame
    df = transform_data(all_data)

    # Create the document store from the DataFrame
    docstore = create_docstore(df, config_options)

    print(docstore)
