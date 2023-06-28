import requests
from bs4 import BeautifulSoup
from typing import List
from graphql import parse, print_ast
from graphql.language.ast import FieldNode, ArgumentNode, NameNode, IntValueNode
from llama_index.readers.base import BaseReader
from llama_index.readers.schema.base import Document
import logging
from urllib.parse import urlparse

DATA_KEY = 'data'
ERRORS_KEY = 'errors'


class WordLiftGraphQLReaderError(Exception):
    """Base class for WordLiftGraphQLReader exceptions."""
    pass


class APICallError(WordLiftGraphQLReaderError):
    """Exception raised for errors in API calls."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class DataTransformError(WordLiftGraphQLReaderError):
    """Exception raised for errors in data transformation."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class WordLiftGraphQLReader(BaseReader):
    """
    A reader class for fetching and transforming data from WordLift GraphQL API.

    Args:
        endpoint (str): The API endpoint URL.
        headers (dict): The request headers.
        query (str): The GraphQL query.
        fields (str): The fields to extract from the API response.
        configure_options (dict): Additional configuration options.
        page (int): The page number.
        rows (int): The number of rows per page.

    Attributes:
        endpoint (str): The API endpoint URL.
        headers (dict): The request headers.
        query (str): The GraphQL query.
        fields (str): The fields to extract from the API response.
        configure_options (dict): Additional configuration options.
        page (int): The page number.
        rows (int): The number of rows per page.
    """

    def __init__(self, endpoint, headers, query, fields, configure_options, page, rows):
        self.endpoint = endpoint
        self.headers = headers
        self.query = query
        self.fields = fields
        self.configure_options = configure_options
        self.page = page
        self.rows = rows

    def fetch_data(self) -> dict:
        """
        Fetches data from the WordLift GraphQL API.

        Returns:
            dict: The API response data.

        Raises:
            APIConnectionError: If there is an error connecting to the API.
        """
        try:
            query = self.alter_query()
            response = requests.post(self.endpoint, json={
                "query": query}, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            if ERRORS_KEY in data:
                raise APICallError(data[ERRORS_KEY])
            return data
        except requests.exceptions.RequestException as e:
            logging.error('Error connecting to the API:', exc_info=True)
            raise APICallError('Error connecting to the API') from e

    def transform_data(self, data: dict) -> List[Document]:
        """
        Transforms the fetched data into a list of Document objects.

        Args:
            data (dict): The API response data.

        Returns:
            List[Document]: The list of transformed documents.

        Raises:
            DataTransformError: If there is an error transforming the data.
        """
        try:
            data = data[DATA_KEY][self.fields]
            documents = []
            text_fields = self.configure_options.get('text_fields', [])
            metadata_fields = self.configure_options.get('metadata_fields', [])

            for item in data:
                row = {}
                for key, value in item.items():
                    if key in text_fields or key in metadata_fields:
                        row[key] = value
                    else:
                        row[key] = clean_value(value)

                text_parts = [
                    get_separated_value(row, field.split('.'))
                    for field in text_fields
                    if get_separated_value(row, field.split('.')) is not None
                ]

                text_parts = flatten_list(text_parts)
                text = ' '.join(text_parts)

                extra_info = {}
                for field in metadata_fields:
                    field_keys = field.split('.')
                    value = get_separated_value(row, field_keys)
                    if isinstance(value, list) and len(value) != 0:
                        value = value[0]
                    if is_url(value) and is_valid_html(value):
                        extra_info[field] = value
                    else:
                        extra_info[field] = clean_value(value)

                document = Document(text=text, extra_info=extra_info)
                documents.append(document)

            return documents
        except Exception as e:
            logging.error('Error transforming data:', exc_info=True)
            raise DataTransformError('Error transforming data') from e

    def load_data(self) -> List[Document]:
        """
        Loads the data by fetching and transforming it.

        Returns:
            List[Document]: The list of loaded documents.
        """
        try:
            data = self.fetch_data()
            documents = self.transform_data(data)
            return documents
        except (APICallError, DataTransformError) as e:
            logging.error('Error loading data:', exc_info=True)
            raise

    def alter_query(self):
        """
        Alters the GraphQL query by adding pagination arguments.

        Returns:
            str: The altered GraphQL query with pagination arguments.
        """
        query = self.query
        page = self.page
        rows = self.rows

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


def is_url(text: str) -> bool:
    """
    Checks if the given text is a URL.

    Args:
        text (str): The text to check.

    Returns:
        bool: True if the text is a URL, False otherwise.
    """
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def is_valid_html(content: str) -> bool:
    """
    Checks if the given content is a valid HTML document.
    """
    if content is None:
        return False

    soup = BeautifulSoup(content, 'html.parser')
    return soup.find('html') is not None


@staticmethod
def clean_value(x: any) -> any:
    """
    Cleans a value by checking if it's a URL and fetching its content using the WordLift Inspect API.
    """
    if x is not None and not isinstance(x, list):
        return clean_html(x)
    return x


@staticmethod
def clean_html(text: str) -> str:
    """
    Cleans HTML content by fetching its text representation using BeautifulSoup.
    """
    if text is None:
        return ""

    if isinstance(text, dict):
        return str(text)
    if isinstance(text, str):
        if is_url(text) and is_valid_html(text):
            response = requests.get(text)
            if response.status_code == 200:
                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')
                cleaned_text = soup.get_text()
            else:
                cleaned_text = text
        else:
            soup = BeautifulSoup(text, 'html.parser')
            cleaned_text = soup.get_text()
        return cleaned_text
    return str(text)


@staticmethod
def get_separated_value(item: dict, field_keys: List[str]) -> any:
    """
    Retrieves the metadata value from the nested item based on field keys.
    """

    if not field_keys:
        return item
    key = field_keys[0]
    if isinstance(item, list):
        if len(item) == 0:
            return None
        else:
            item = item[0]
    if isinstance(item, dict) and key in item:
        return get_separated_value(item[key], field_keys[1:])
    return None


@staticmethod
def flatten_list(lst):
    """
    Flattens a nested list.
    """
    if lst is None:
        return []
    flattened = []
    for item in lst:
        if isinstance(item, list):
            flattened.extend(flatten_list(item))
        else:
            flattened.append(item)
    return flattened
