import os
from haystack import Pipeline
from haystack.components.embedders import OpenAITextEmbedder
from haystack.components.builders import PromptBuilder
from haystack.components.generators.openai import OpenAIGenerator
from haystack_integrations.components.retrievers.chroma import ChromaEmbeddingRetriever
from haystack_integrations.document_stores.chroma import ChromaDocumentStore
from haystack.components.routers import ConditionalRouter
from custom_components import LocationRetriever, DateTimeRetriever, WeatherRetriever, SerpAPIWebSearch
from rag_config import PROMPT_TEMPLATE, ROUTES
from dotenv import load_dotenv

load_dotenv()

class RAGPipeline:
    def __init__(self, user_name: str):
        self.user_name = user_name
        self.prompt_template = PROMPT_TEMPLATE
        self.routes = ROUTES

        self.document_store = ChromaDocumentStore(persist_path="data/databases/chroma_db", collection_name="conversations")
        self.embedder = OpenAITextEmbedder(model="text-embedding-3-large")
        self.chroma_retriever = ChromaEmbeddingRetriever(document_store=self.document_store)
        self.prompt_builder = PromptBuilder(template=self.prompt_template)
        self.generator = OpenAIGenerator(model="gpt-4o-mini")
        self.weather_retriever = WeatherRetriever(api_key=os.getenv('WEATHER_API_KEY'))
        self.location_retriever = LocationRetriever(api_key=os.getenv('GOOGLE_MAPS_API_KEY'))
        self.datetime_retriever = DateTimeRetriever(api_key=os.getenv('WEATHER_API_KEY'))
        self.web_search = SerpAPIWebSearch(api_key=os.getenv('SERP_API_KEY'))
        self.router = ConditionalRouter(routes=self.routes)

        self.pipeline = Pipeline()
        self.pipeline.add_component("query_embedder", self.embedder)
        self.pipeline.add_component("retriever", self.chroma_retriever)
        self.pipeline.add_component("location_retriever", self.location_retriever)
        self.pipeline.add_component("datetime_retriever", self.datetime_retriever)
        self.pipeline.add_component("weather_retriever", self.weather_retriever)
        self.pipeline.add_component("web_search", self.web_search)
        self.pipeline.add_component("prompt", self.prompt_builder)
        self.pipeline.add_component("generator", self.generator)
        self.pipeline.add_component("router", self.router)

        self.pipeline.connect("query_embedder.embedding", "retriever.query_embedding")
        self.pipeline.connect("retriever.documents", "prompt.documents")
        self.pipeline.connect("prompt", "generator")
        self.pipeline.connect("generator.replies", "router.replies")
        self.pipeline.connect("router.weather_search", "weather_retriever.query")
        self.pipeline.connect("router.location_search", "location_retriever.query")
        self.pipeline.connect("router.datetime_search", "datetime_retriever.query")
        self.pipeline.connect("router.web_search", "web_search.query")

    def process_query(self, query: str, top_k: int = 5):
        """Process a query through the RAG pipeline with advanced routing"""
        result = self.pipeline.run(
            {
                "query_embedder": {"text": query},
                "retriever": {"top_k": top_k},
                "prompt": {"query": query, "user_name": self.user_name},
                "router": {"query": query}
            },
            include_outputs_from={"retriever", "generator"}
        )
        
        generator_reply = result["generator"]["replies"][0]
        prompt_type_map = {
            ('question: ', 'Question: '): 'question',
            ('statement: ', 'Statement: '): 'statement',
            'use_weather_tool': 'weather',
            'use_datetime_tool': 'datetime',
            'use_location_tool': 'location',
            'use_web_search_tool': 'web_search'
        }

        prompt_type = None
        content = None
        url = None

        for prefix, type_name in prompt_type_map.items():
            if isinstance(prefix, tuple):
                if any(generator_reply.startswith(p) for p in prefix):
                    prompt_type = type_name
                    content = generator_reply[len(prefix[0]):].strip()
                    break
            elif generator_reply.startswith(prefix):
                prompt_type = type_name
                if type_name == 'web_search':
                    content = result["web_search"]["web_documents"]["content"]
                    url = result["web_search"]["web_documents"]["url"]
                else:
                    content = result[f"{type_name}_retriever"]["content"]
                break
        
        print("Prompt type:", prompt_type)
        print("Content:", content)
        
        return {
            "answer": content,
            "prompt_type": prompt_type,
            "url": url
        }

    def export_pipeline_diagram(self, output_path: str = 'pipeline_diagrams.png'):
        """
        Export the pipeline diagram to a PNG file.
        """ 
        self.pipeline.draw(output_path, params={
            "format": "img",
            "theme": "default",
            "bgColor": "#FFFFFF"
        })
        return