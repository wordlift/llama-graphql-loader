import requests
from bs4 import BeautifulSoup
from typing import List
from llama_index.readers.base import BaseReader
from llama_index.readers.schema.base import Document
import logging

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

    Attributes:
        endpoint (str): The API endpoint URL.
        headers (dict): The request headers.
        query (str): The GraphQL query.
        fields (str): The fields to extract from the API response.
        configure_options (dict): Additional configuration options.
    """

    def __init__(self, endpoint, headers, query, fields, configure_options):
        self.endpoint = endpoint
        self.headers = headers
        self.query = query
        self.fields = fields
        self.configure_options = configure_options

    def fetch_data(self) -> dict:
        """
        Fetches data from the WordLift GraphQL API.

        Returns:
            dict: The API response data.

        Raises:
            APIConnectionError: If there is an error connecting to the API.
        """
        try:
            response = requests.post(self.endpoint, json={
                "query": self.query}, headers=self.headers)
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
            for item in data:
                row = {}
                for key, value in item.items():
                    row[key] = clean_value(value)
                text_parts = [
                    str(row[col]) for col in self.configure_options['text_fields'] if row[col] is not None]
                text = ' '.join(text_parts)
                extra_info = {col: row[col]
                              for col in self.configure_options['metadata_fields']}
                document = Document(text, extra_info=extra_info)
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
    if text.startswith('http://') or text.startswith('https://'):
        response = requests.get(text)
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        cleaned_text = soup.get_text()
    else:
        soup = BeautifulSoup(text, 'html.parser')
        cleaned_text = soup.get_text()
    return cleaned_text
