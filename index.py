import os
import json
import openai
from llama_index import GPTVectorStoreIndex
from llama_index.readers.schema.base import Document
from WordLift_GraphQLReader import WordLiftGraphQLReader

openai.api_key = 'YOUR OPENAI API KEY'
os.environ["OPENAI_API_KEY"] = 'YOUR OPENAI API KEY'
test_key = "YOUR TEST KEY"
endpoint = "https://api.wordlift.io/graphql/graphql"
headers = {
    "Authorization": f"Key {test_key}",
    "Content-Type": "application/json"
}
default_page = 0
default_rows = 25

fields = "articles"

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
query {
  articles(page: 0, rows: 25) {
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
reader = WordLiftGraphQLReader(
    endpoint, headers, query, fields, config_options)

documents = reader.load_data()

converted_doc = []
for doc in documents:
    converted_doc_id = json.dumps(doc.doc_id)
    converted_doc.append(Document(text=doc.text, doc_id=converted_doc_id,
                         embedding=doc.embedding, doc_hash=doc.doc_hash, extra_info=doc.extra_info))

index = GPTVectorStoreIndex.from_documents(converted_doc)
query_engine = index.as_query_engine()
result = query_engine.query("What did the author do growing up?")

print("result: ", result)
