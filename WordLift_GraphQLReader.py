import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List
from llama_index.readers.base import BaseReader
from llama_index.readers.schema.base import Document


class WordLiftGraphQLReader(BaseReader):
    def __init__(self, endpoint, headers, query, fields, configure_options):
        self.endpoint = endpoint
        self.headers = headers
        self.query = query
        self.fields = fields
        self.configure_options = configure_options

    def fetch_data(self):
        try:
            response = requests.post(self.endpoint, json={
                                     "query": self.query}, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            if 'errors' in data:
                raise Exception(data['errors'])
            return data
        except requests.exceptions.RequestException as e:
            print('Error connecting to the API:', e)
            raise

    def transform_data(self, data):
        try:
            data = data['data'][self.fields]
            df = pd.DataFrame(data)
            df = df.applymap(self.clean_value)
            documents = []
            for _, row in df.iterrows():
                text_parts = [
                    str(row[col]) for col in self.configure_options['text_fields'] if row[col] is not None]
                text = ' '.join(text_parts)
                metadata = {col: row[col]
                            for col in self.configure_options['metadata_fields']}
                document = Document(text, metadata)
                documents.append(document)
            return documents
        except Exception as e:
            print('Error transforming data:', e)
            raise

    def load_data(self):
        data = self.fetch_data()
        documents = self.transform_data(data)
        return documents

    @staticmethod
    def clean_value(x):
        if x is not None and not isinstance(x, list):
            return WordLiftGraphQLReader.clean_html(x)
        return x

    @staticmethod
    def clean_html(text):
        if text.startswith('http://') or text.startswith('https://'):
            response = requests.get(text)
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            cleaned_text = soup.get_text()
        else:
            soup = BeautifulSoup(text, 'html.parser')
            cleaned_text = soup.get_text()
        return cleaned_text
