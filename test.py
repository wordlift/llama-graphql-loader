import os
import json
from llama_index import GPTVectorStoreIndex
from index import WordLiftGraphQLReader
from llama_index.readers.schema.base import Document

os.environ["OPENAI_API_KEY"] = 'Your openai_api_key'
test_key = "Your test key"
endpoint = "https://api.wordlift.io/graphql/graphql"
headers = {
    "Authorization": f"Key {test_key}",
    "Content-Type": "application/json"
}
default_page = 0
default_rows = 25

example_fields = "Your example fields"

config_options = {
    'text_fields': ['article_desc'],
    'metadata_fields': ['article_url']
}
endpoint = "https://api.wordlift.io/graphql/graphql"
headers = {
    "Authorization": f"Key {test_key}",
    "Content-Type": "application/json"
}
query = """
Your query
"""
reader = WordLiftGraphQLReader(
    endpoint, headers, query, example_fields, config_options)


class DocumentEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Document):
            return obj.__dict__
        return super().default(obj)


documents = reader.load_data()
documents_json = json.dumps(documents, cls=DocumentEncoder)
index = GPTVectorStoreIndex.from_documents(documents_json)

# Perform the query on the serialized index
query_result = index.query('Where did the author go to school?')

# Deserialize the query result
query_result = json.loads(query_result, object_hook=lambda d: Document(**d))
