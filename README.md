# WordLift GraphQL Reader

The WordLift GraphQL Reader is a Python library that allows you to fetch and transform data from the WordLift GraphQL API. It provides a convenient way to load data from WordLift and transform it into a list of documents for further processing.

## Usage
To use the WordLift GraphQL Reader, follow the steps below:

1. Set up the necessary configuration options, such as the API endpoint, headers, query, fields, and configuration options.
2. Create an instance of the `WordLiftGraphQLReader` class, passing in the configuration options.
3. Use the `load_data` method to fetch and transform the data.
4. Process the loaded documents as needed.

Here's an example of how to use the WordLift GraphQL Reader:

```python
import json
import logging
from llama_index import GPTVectorStoreIndex
from llama_index.readers.schema.base import Document
from base import WordLiftGraphQLReader

# Set up the necessary configuration options
endpoint = "https://api.wordlift.io/graphql/graphql"
headers = {
    "Authorization": "<YOUR_API_KEY>",
    "Content-Type": "application/json"
}
default_page = 0
default_rows = 30
query = """
# Your GraphQL query here
"""
fields = "<YOUR_FIELDS>"
config_options = {
    'text_fields': ['<YOUR_TEXT_FIELDS>'],
    'metadata_fields': ['<YOUR_METADATA_FIELDS>']
}
# Create an instance of the WordLiftGraphQLReader
reader = WordLiftGraphQLReader(endpoint, headers, query, fields, config_options, default_page, default_rows)

# Load the data
documents = reader.load_data()

# Convert the documents
converted_doc = []
for doc in documents:
    converted_doc_id = json.dumps(doc.doc_id)
    converted_doc.append(Document(text=doc.text, doc_id=converted_doc_id,
                         embedding=doc.embedding, doc_hash=doc.doc_hash, extra_info=doc.extra_info))

# Create the index and query engine
index = GPTVectorStoreIndex.from_documents(converted_doc)
query_engine = index.as_query_engine()

# Perform a query
result = query_engine.query("<YOUR_QUERY>")

# Process the result as needed
logging.info("Result: %s", result)

```

